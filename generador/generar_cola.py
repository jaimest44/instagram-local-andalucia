"""Rellena la cola de publicaciones hasta tener N dias preparados.

    python generar_cola.py            # deja 30 dias preparados
    python generar_cola.py --dias 45
    python generar_cola.py --subir    # ademas hace commit y push a GitHub

Cada dia de la cola es una carpeta cola/AAAA-MM-DD con las imagenes, caption.txt y meta.json.
estado/usadas.json guarda que preguntas ya se han usado para no repetirlas nunca.
"""
import argparse
import datetime as dt
import hashlib
import json
import os
import random
import subprocess
from collections import defaultdict

from caption import caption
from carrusel import generar
from reel import generar_reel
from datos import cargar, es_desarrollo, problemas
import plan_voz

AQUI = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(AQUI, ".."))
COLA = os.path.join(REPO, "cola")
USADAS = os.path.join(REPO, "estado", "usadas.json")

# Un dia test, otro supuesto, otro infraccion del codificado. La fecha fija mantiene el ciclo
# aunque la cola se rellene en semanas distintas.
ROTACION = ["test", "corta", "infraccion"]
INICIO_ROTACION = dt.date(2026, 10, 12)

# Dos publicaciones al dia: mediodia (carpeta AAAA-MM-DD_mediodia) y noche (carpeta AAAA-MM-DD)
FRANJAS = [("_mediodia", "mediodia"), ("", "noche")]

PESO_MATERIA = {"Tráfico": 3, "Seguridad Ciudadana": 2}

# Separacion minima (en publicaciones) antes de repetir tema / convocatoria / caso
SEPARACION_TEMA = 4
SEPARACION_CONV = 3
SEPARACION_CASO = 20


def leer_json(ruta, defecto):
    try:
        with open(ruta, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return defecto


def guardar_json(ruta, datos):
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=1, sort_keys=True)


def caso(p):
    """Identificador del supuesto: preguntas del mismo enunciado no deben ir seguidas."""
    return p["id"].split("#")[0] + "|" + hashlib.md5(p.get("enunciado", "").encode()).hexdigest()[:8]


def peso(p):
    if p["tipo"] == "infraccion":
        # trafico y seguridad ciudadana son lo que mas cae en el examen y en la calle
        return PESO_MATERIA.get(p["materia"], 1)
    # mas probabilidad para examenes recientes
    return 1 + max(0, p["anio"] - 2017) / 3


def elegir(candidatas, historial, rng):
    temas = [h["tema"] for h in historial[-SEPARACION_TEMA:]]
    convs = [h["convocatoria"] for h in historial[-SEPARACION_CONV:]]
    casos = [h.get("caso") for h in historial[-SEPARACION_CASO:]]
    for estricto in (3, 2, 1, 0):  # relaja las restricciones si no hay candidatas
        pool = [p for p in candidatas
                if (estricto < 3 or p["tema"] not in temas)
                and (estricto < 2 or p["convocatoria"] not in convs)
                and (estricto < 1 or caso(p) not in casos)]
        if pool:
            return rng.choices(pool, weights=[peso(p) for p in pool])[0]
    return None


def tipo_para(dia, franja, disponibles):
    """Noche: rotacion test -> supuesto -> infraccion. Mediodia: alterna test e infraccion
    (los supuestos son los que menos hay: se reservan para la noche)."""
    if franja == "mediodia":
        orden = ["test", "infraccion"] if dia.toordinal() % 2 else ["infraccion", "test"]
        orden += ["corta"]
    else:
        n = (dia - INICIO_ROTACION).days % len(ROTACION)
        orden = ROTACION[n:] + ROTACION[:n]  # si se agota un tipo, pasa al siguiente
    return next((t for t in orden if disponibles[t]), orden[0])


def caption_reel(texto):
    """El texto del carrusel habla de "deslizar"; en el Reel la solucion sale sola a los 5 segundos."""
    parrafos = texto.split("\n\n")
    for i, par in enumerate(parrafos):
        if "desliza" in par.lower():
            parrafos[i] = "Tienes 5 segundos ⏱️ Comenta tu respuesta antes de que aparezca la solución."
            break
    return "\n\n".join(parrafos)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dias", type=int, default=30, help="dias de cola que deben quedar preparados")
    ap.add_argument("--subir", action="store_true", help="commit + push a GitHub al terminar")
    a = ap.parse_args()

    usadas = leer_json(USADAS, {})
    os.makedirs(COLA, exist_ok=True)
    ya_en_cola = sorted(d for d in os.listdir(COLA) if os.path.isfile(os.path.join(COLA, d, "meta.json")))

    hoy = dt.date.today()
    fin = hoy + dt.timedelta(days=a.dias)
    en_cola = set(ya_en_cola)
    huecos = []  # (dia, sufijo de carpeta, franja) que faltan por generar
    dia = hoy + dt.timedelta(days=1)
    inicio_voz = plan_voz.inicio()
    while dia <= fin:
        for sufijo, franja in FRANJAS:
            if inicio_voz and dia >= inicio_voz:
                break  # desde el plan con voz, estas franjas las rellena plan_voz.py
            if dia.isoformat() + sufijo not in en_cola:
                huecos.append((dia, sufijo, franja))
        dia += dt.timedelta(days=1)
    nuevas_voz = plan_voz.programar(min(fin, dt.date.today() + dt.timedelta(days=plan_voz.DIAS_COLA)))
    if not huecos:
        print(f"La cola ya está completa hasta {fin}.")
        if a.subir and nuevas_voz:
            subir(nuevas_voz, fin)
        return

    disponibles = defaultdict(list)
    descartadas = 0
    for tipo in ROTACION:
        for p in cargar(tipo):
            if p["id"] in usadas:
                continue
            if problemas(p):
                descartadas += 1
                continue
            disponibles[tipo].append(p)

    historial = [leer_json(os.path.join(COLA, d, "meta.json"), {}) for d in ya_en_cola[-SEPARACION_CASO:]]
    rng = random.Random(hoy.isoformat())
    nuevas = 0
    for dia, sufijo, franja in huecos:
        tipo = tipo_para(dia, franja, disponibles)
        p = elegir(disponibles[tipo], historial, rng)
        if p is None:
            print("No quedan preguntas disponibles.")
            break
        disponibles[tipo].remove(p)

        clave = dia.isoformat() + sufijo
        carpeta = os.path.join(COLA, clave)
        imagenes = [os.path.basename(r) for r in generar(p, carpeta)]
        texto = caption(p)
        reel = None
        if franja == "mediodia":  # el de mediodia sale como Reel: llega a quien aun no te sigue
            try:
                reel = os.path.basename(generar_reel(carpeta))
                texto = caption_reel(texto)
            except Exception as e:  # si falla el video, se publica como carrusel
                print(f"   (no se pudo crear el Reel: {e})")
        with open(os.path.join(carpeta, "caption.txt"), "w", encoding="utf-8") as f:
            f.write(texto)
        meta = {
            "fecha": dia.isoformat(), "franja": franja, "id": p["id"],
            "formato": "desarrollo" if es_desarrollo(p) else p["tipo"],
            "convocatoria": p["convocatoria"], "tema": p["tema"], "caso": caso(p),
            "imagenes": imagenes,
        }
        if reel:
            meta["reel"] = reel
        guardar_json(os.path.join(carpeta, "meta.json"), meta)
        usadas[p["id"]] = clave
        historial.append(meta)
        nuevas += 1
        origen = p["convocatoria"] or p.get("materia", "")
        print(f"{dia}  {franja:<8} {meta['formato']:<10} {origen:<28} {(p.get('pregunta') or p.get('texto', ''))[:55]}")

    guardar_json(USADAS, usadas)
    print(f"\n{nuevas} publicaciones nuevas. Quedan sin usar: "
          f"{len(disponibles['test'])} test, {len(disponibles['corta'])} supuestos y "
          f"{len(disponibles['infraccion'])} infracciones "
          f"({descartadas} descartadas por el filtro de calidad).")

    if a.subir and (nuevas or nuevas_voz):
        subir(nuevas + nuevas_voz, fin)


def subir(nuevas, fin):
    def git(*args):
        subprocess.run(["git", *args], cwd=REPO, check=True)
    git("pull", "--rebase", "--autostash")
    git("add", "cola", "estado")
    git("commit", "-m", f"Cola: {nuevas} publicaciones hasta {fin}")
    git("push")


if __name__ == "__main__":
    main()
