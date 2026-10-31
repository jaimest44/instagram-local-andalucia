"""Plan de noviembre 2026 para @localandalucia: tres reels con voz al dia (sustituye a test/supuesto/infraccion).

    11:00  _manana    chuleta de ley      («3 trampas de X que caen en el examen», fichas de Esquemas visuales)
    14:00  _mediodia  infraccion          (escena -> ¿leve, grave o muy grave? -> multa, puntos y quien sanciona)
    20:30  (noche)    supuesto resuelto   (escena, caso, pregunta, 5 s para pensar y solucion; maximo 3 min)
    18:00  _tarde     no se toca: especiales (dibujos, patrullas, cuenta atras)

    python plan_voz.py inicio 2026-11-03     # fija el primer dia del plan nuevo y regenera la cola desde ahi
    python plan_voz.py programar             # rellena los huecos hasta DIAS_COLA (lo llama generar_cola.py)

Los ganchos (escenas de enganche) los escribe Claude por tandas en ganchos.json. Las infracciones salen de
infracciones_de_calle.md (material interno de la app, no se sube a GitHub; Quien sanciona revisado con BOE/BOJA).
"""
import datetime as dt
import json
import os
import re
import shutil
import sys

import datos
import infografias as I
import reels_voz as R

AQUI = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(AQUI, ".."))
COLA = os.path.join(REPO, "cola")
CONFIG = os.path.join(REPO, "estado", "plan_voz.json")       # {"inicio": "AAAA-MM-DD"}
USADOS = os.path.join(REPO, "estado", "plan_voz_usados.json")
GANCHOS = os.path.join(AQUI, "ganchos.json")
CALLE = os.path.join(AQUI, "infracciones_de_calle.md")
DIAS_COLA = 14
MAX_SUPUESTO = 178  # segundos: por encima de 3 min Instagram no lo acepta como Reel
FRANJAS = [("_manana", "manana", "chuleta"), ("_mediodia", "mediodia", "infraccion"), ("", "noche", "supuesto")]
HASHTAGS = "#policialocal #oposicionesandalucia #policialocalandalucia"


def leer_json(ruta, defecto):
    try:
        with open(ruta, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return defecto


def guardar_json(ruta, datos_):
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(datos_, f, ensure_ascii=False, indent=1, sort_keys=True)


def inicio():
    v = leer_json(CONFIG, {}).get("inicio")
    return dt.date.fromisoformat(v) if v else None


# ---------------------------------------------------------------- material

NORMAS = {"Real Decreto 1428/2003": "Reglamento General de Circulación", "Real Decreto Legislativo 6/2015": "Ley de Tráfico",
          "Real Decreto 818/2009": "Reglamento General de Conductores", "Ley 7/2006": "Ley 7/2006 (botellón)",
          "Ley Orgánica 4/2015": "Ley de Seguridad Ciudadana", "Ley 28/2005": "Ley del Tabaco",
          "Ley 50/1999": "Ley 50/1999 (perros peligrosos)", "Ley 11/2003": "Ley 11/2003 de Protección de Animales",
          "Ley 13/1999": "Ley 13/1999 de Espectáculos", "Ley 4/1997": "Ley 4/1997 de Drogodependencias"}


def multa_legible(m):
    m = re.sub(r"\s*\([^)]*ptas\.?\)", "", m).replace("Multa de ", "").rstrip(". ")
    m = re.sub(r"^Apercibimiento\s*/\s*([\d.,]+)$", r"Apercibimiento o hasta \1 €", m)
    return R.C.cuantia_legible(m)


def infracciones_calle():
    """Las infracciones de infracciones_de_calle.md, con la forma que espera reels_voz.reel_infraccion."""
    texto = open(CALLE, encoding="utf-8").read()
    escena, out = None, []
    for bloque in re.split(r"\n(?=## |- \*\*)", texto):
        if bloque.startswith("## "):
            escena = bloque[3:].split("\n")[0].strip()
            continue
        m = re.match(r"- \*\*(.+?)\*\* · (.+?), art\. (\S+)\n\s+- Hecho: (.+)\n\s+- Multa: (.+?)(?: · Puntos: (\d+))?\n"
                     r"\s+- Quién sanciona: (.+)", bloque)
        if not m:
            continue
        art = re.sub(r"(\.-)?\.\d[A-Z]$", "", m[3])  # «20.1.5F»: 5F es la opcion interna del codificado
        quien = m[7].strip().rstrip(".")
        voz = re.split(r"\s*\(", quien)[0]
        out.append({"n": len(out), "escena": escena, "gravedad": m[1], "norma": m[2], "hecho": m[4].strip(),
                    "cuantia": multa_legible(m[5].strip()), "puntos": m[6] or "", "organo": quien,
                    "organo_voz": voz[:200], "norma_media": NORMAS.get(m[2], m[2]), "referencia": f"art. {art}",
                    "id": f"calle:{m[2]}|{art}|{m[4][:40]}"})
    return out


NOMBRES = {  # nombre de cada ley para «3 trampas de X»
    "Constitucion": "la Constitución", "Codigo_Penal": "el Código Penal", "Ley_39-2015_Procedimiento_Administrativo": "la Ley 39/2015",
    "RGCir_RD_1428-2003_Reglamento_General_Circulacion": "el Reglamento General de Circulación",
    "LBRL_Ley_7-1985_Regimen_Local": "la Ley de Bases del Régimen Local", "LSV_RDL_6-2015_Trafico_y_Seguridad_Vial": "la Ley de Tráfico",
    "LECrim_Ley_Enjuiciamiento_Criminal": "la LECrim", "LO_2-1986_Fuerzas_y_Cuerpos_de_Seguridad": "la LO 2/1986 de Fuerzas y Cuerpos de Seguridad",
    "Estatuto_Autonomia_Andalucia": "el Estatuto de Autonomía", "Ley_6-2023_Policias_Locales_Andalucia": "la Ley 6/2023 de Policías Locales",
    "Decreto_8-2026_Ingreso_Policia_Local": "el Decreto 8/2026 de ingreso", "Emergencias_Ley_2-2002_y_Proteccion_Civil_Ley_17-2015": "emergencias y protección civil",
    "TREBEP_RDL_5-2015": "el TREBEP", "RD_137-1993_Reglamento_de_Armas": "el Reglamento de Armas",
    "Violencia_de_Genero_LO_1-2004_y_Ley_13-2007": "violencia de género",
    "Accidentes_de_Trafico_Tema_43": "los accidentes de tráfico", "Animales_Leyes_Proteccion_y_Tenencia": "la ley de animales",
    "Comercio_Interior_y_Ambulante_Andalucia": "comercio interior y ambulante", "Decreto_50-2025_Calidad_Acustica": "la normativa de ruido",
    "Igualdad_LO_3-2007_y_Ley_12-2007": "la ley de igualdad", "LOTT_Ley_16-1987_Transportes_Terrestres": "la LOTT",
    "LO_1-2002_Derecho_de_Asociacion": "la ley de asociación", "LO_10-2022_Libertad_Sexual": "la ley del «solo sí es sí»",
    "LO_12-1995_Contrabando": "la ley de contrabando", "LO_2-1979_Tribunal_Constitucional": "la LO del Tribunal Constitucional",
    "LO_3-1981_Defensor_del_Pueblo": "la LO del Defensor del Pueblo", "LO_3-2018_Proteccion_de_Datos": "la ley de protección de datos",
    "LO_4-1981_Estados_Alarma_Excepcion_Sitio": "los estados de alarma, excepción y sitio", "LO_4-2000_Extranjeria": "la ley de extranjería",
    "LO_4-2010_Regimen_Disciplinario_Policia": "el régimen disciplinario policial", "LO_5-1985_LOREG": "la LOREG",
    "LO_5-2000_Responsabilidad_Penal_Menores": "la ley del menor", "LO_6-1985_LOPJ_Poder_Judicial": "la LOPJ",
    "LO_8-2021_Proteccion_Infancia_Violencia": "la LOPIVI", "LO_9-1983_Derecho_de_Reunion": "la ley de reunión",
    "Ley_10-2010_Blanqueo_de_Capitales": "la ley de blanqueo de capitales", "Ley_13-2003_Consumidores_Andalucia": "la ley de consumidores",
    "Ley_13-2011_Turismo_Andalucia": "la ley de turismo de Andalucía", "Ley_14-2007_Patrimonio_Historico_Andalucia": "la ley de patrimonio histórico",
    "Ley_15-2022_Igualdad_de_Trato": "la ley de igualdad de trato", "Ley_17-1967_Estupefacientes": "la ley de estupefacientes",
    "Ley_19-2007_Violencia_en_el_Deporte": "la ley de violencia en el deporte", "Ley_19-2013_Transparencia": "la ley de transparencia",
    "Ley_2-1986_Juego_y_Apuestas_Andalucia": "la ley del juego de Andalucía", "Ley_2-2026_Gestion_Ambiental_Andalucia": "la ley de gestión ambiental",
    "Ley_21-2003_Seguridad_Aerea_Drones": "la normativa de drones", "Ley_4-2015_Estatuto_de_la_Victima": "el Estatuto de la víctima",
    "Ley_4-2017_Discapacidad_Andalucia": "la ley de discapacidad de Andalucía", "Ley_4-2021_Infancia_y_Adolescencia_Andalucia": "la ley de infancia de Andalucía",
    "Ley_4-2023_Trans_y_LGTBI": "la ley trans", "Ley_40-2015_Regimen_Juridico_Sector_Publico": "la Ley 40/2015",
    "Ley_5-2010_LAULA_Autonomia_Local": "la LAULA", "Ley_5-2014_Seguridad_Privada": "la ley de seguridad privada",
    "Ley_5-2023_Funcion_Publica_Andalucia": "la ley de función pública andaluza", "Ley_7-2021_LISTA_Urbanismo": "la LISTA de urbanismo",
    "Ley_8-2017_LGTBI_Andalucia": "la ley LGTBI de Andalucía", "Orden_INT-2223-2014_Victimas_Accidentes_Trafico": "la Orden INT/2223/2014",
    "RDL_8-2004_Seguro_Obligatorio": "el seguro obligatorio", "RD_1087-2010_Juntas_Locales_de_Seguridad": "las Juntas Locales de Seguridad",
    "RD_1295-2003_Escuelas_de_Conductores": "las autoescuelas", "RD_1690-1986_Poblacion_y_Padron": "el padrón",
    "RD_203-2021_Administracion_Electronica": "la administración electrónica", "RD_989-2015_Pirotecnia": "la normativa de pirotecnia",
    "RGCond_RD_818-2009_Reglamento_General_Conductores": "el Reglamento de Conductores", "RGVeh_RD_2822-1998_Reglamento_General_Vehiculos": "el Reglamento de Vehículos",
    "RSCL_Decreto_1955_Servicios_Corporaciones_Locales": "el Reglamento de Servicios", "Residuos_Decreto_73-2012_Ley_7-2022": "la normativa de residuos",
    "Tabaco_y_Drogas_Ley28-2005_Ley4-1997": "la ley del tabaco", "Temas_Deontologia_y_Criminologia": "deontología y criminología",
    "Transporte_Urbano_Andalucia_Taxi_VTC": "el taxi y los VTC", "Union_Europea_Tema_7": "la Unión Europea",
}


def chuletas():
    """(carpeta, pdf, ley) de todas las fichas, alternando leyes: primero las de LEYES, luego el resto."""
    por_ley = []
    hechas = set()
    for carpeta, ley, _ in I.LEYES:
        por_ley.append((carpeta, NOMBRES.get(carpeta, ley)))
        hechas.add(carpeta)
    for carpeta in sorted(os.listdir(I.FICHAS)):
        ruta = os.path.join(I.FICHAS, carpeta)
        if carpeta in hechas or carpeta in ("ADMINISTRATIVO", "fuentes", "recursos") or not os.path.isdir(ruta):
            continue
        por_ley.append((carpeta, NOMBRES.get(carpeta, carpeta.replace("_", " "))))
    listas = [[(c, pdf, ley) for pdf in I.fichas_de(c)] for c, ley in por_ley]
    out = []
    while any(listas):
        for lst in listas:
            if lst:
                out.append(lst.pop(0))
    return out


def supuestos_con_gancho(ganchos):
    por_id = {p["id"]: p for p in datos.cargar("corta")}
    return [(por_id[g["id"]], g["gancho"]) for g in ganchos.get("supuestos", []) if g["id"] in por_id]


# ---------------------------------------------------------------- textos

def caption(tipo, cosa, gancho):
    if tipo == "infraccion":
        cuerpo = [f"🚓 {gancho}", "¿Leve, grave o muy grave? ¿Cuánto es la multa y quién te sanciona? La respuesta, en el vídeo 👀",
                  f"Más de 2.400 infracciones del codificado, con su multa y quién sanciona, en {R.C.URL_APP} (enlace en la bio)."]
    elif tipo == "chuleta":
        cuerpo = [f"🧠 {gancho}", f"La ficha completa y las de los 45 temas del temario, en {R.C.URL_APP} → "
                  "Recursos → Supuestos → Esquemas visuales (enlace en la bio)."]
    else:
        conv = cosa.get("convocatoria", "")
        cuerpo = [f"🚨 {gancho}", f"Supuesto real de examen{' (' + conv + ')' if conv else ''}. ¿Lo habrías resuelto? "
                  "Pausa el vídeo antes de la solución.",
                  f"Más de 1.400 supuestos de examen resueltos paso a paso en {R.C.URL_APP} (enlace en la bio)."]
    return "\n\n".join(cuerpo + ["📌 Envíaselo a tu compañero de opos.", HASHTAGS])


# ---------------------------------------------------------------- programacion

def generar(tipo, cosa, gancho, carpeta):
    os.makedirs(carpeta, exist_ok=True)
    video = os.path.join(carpeta, "reel.mp4")
    if tipo == "infraccion":
        dur = R.reel_infraccion(cosa, gancho, video)
    elif tipo == "chuleta":
        carpeta_ley, pdf, ley = cosa
        dur = R.reel_chuleta(carpeta_ley, pdf, ley, video)
    else:
        dur = R.reel_supuesto(cosa, video, gancho)
    shutil.rmtree(video + "_trabajo", ignore_errors=True)
    return dur


def programar(hasta=None):
    ini = inicio()
    if not ini:
        print("Plan con voz sin fecha de inicio (python plan_voz.py inicio AAAA-MM-DD).")
        return 0
    usados = leer_json(USADOS, {})
    ganchos = leer_json(GANCHOS, {})
    hoy = dt.date.today()
    hasta = hasta or hoy + dt.timedelta(days=DIAS_COLA)
    dia = max(ini, hoy + dt.timedelta(days=1))

    ganchos_inf = {g["n"]: g["gancho"] for g in ganchos.get("infracciones", [])}
    infr = [i for i in infracciones_calle() if i["n"] in ganchos_inf and i["id"] not in usados]
    sups = [(p, g) for p, g in supuestos_con_gancho(ganchos) if p["id"] not in usados]
    # lo que ya salio con el formato antiguo antes del plan nuevo no se repite
    antes = {k for k, v in leer_json(os.path.join(REPO, "estado", "infografias_usadas.json"), {}).items() if v[:10] < ini.isoformat()}
    viejos = {k for k, v in leer_json(os.path.join(REPO, "estado", "usadas.json"), {}).items() if v[:10] < ini.isoformat()}
    sups = [(p, g) for p, g in sups if p["id"] not in viejos]
    fichas = [f for f in chuletas() if f"ficha:{f[0]}/{f[1]}" not in usados and f"{f[0]}/{f[1]}" not in antes]
    ultima_escena = None
    nuevas = 0
    while dia <= hasta:
        for sufijo, franja, tipo in FRANJAS:
            clave = dia.isoformat() + sufijo
            carpeta = os.path.join(COLA, clave)
            if os.path.exists(os.path.join(carpeta, "meta.json")):
                continue
            if tipo == "infraccion":
                if not infr:
                    print(f"{clave}: no quedan infracciones con gancho (añade más en ganchos.json).")
                    continue
                i = next((x for x in infr if x["escena"] != ultima_escena), infr[0])
                infr.remove(i)
                ultima_escena = i["escena"]
                cosa, gancho, ident, tema = i, ganchos_inf[i["n"]], i["id"], i["escena"]
            elif tipo == "chuleta":
                if not fichas:
                    print(f"{clave}: no quedan fichas.")
                    continue
                cosa = fichas.pop(0)
                trampas = R.consejos_ficha(os.path.join(I.FICHAS, cosa[0], cosa[1]))
                if len(trampas) < 2:
                    usados[f"ficha:{cosa[0]}/{cosa[1]}"] = "sin trampas"
                    continue
                gancho = R.de(f"{min(3, len(trampas))} trampas de {cosa[2]} que caen en el examen.")
                ident, tema = f"ficha:{cosa[0]}/{cosa[1]}", cosa[2]
            else:
                if not sups:
                    print(f"{clave}: no quedan supuestos con gancho (añade más en ganchos.json).")
                    continue
                cosa, gancho = sups.pop(0)
                ident, tema = cosa["id"], cosa.get("tema", "")
            dur = generar(tipo, cosa, gancho, carpeta)
            if tipo == "supuesto" and dur > MAX_SUPUESTO:
                print(f"{clave}: el supuesto dura {dur:.0f} s (más de 3 min): se descarta y se prueba otro.")
                shutil.rmtree(carpeta)
                usados[ident] = "demasiado largo"
                continue
            with open(os.path.join(carpeta, "caption.txt"), "w", encoding="utf-8") as f:
                f.write(caption(tipo, cosa, gancho))
            guardar_json(os.path.join(carpeta, "meta.json"), {
                "fecha": dia.isoformat(), "franja": franja, "id": ident, "formato": "voz_" + tipo, "tema": tema,
                "convocatoria": cosa.get("convocatoria", "") if isinstance(cosa, dict) else "", "caso": "",
                "imagenes": [], "reel": "reel.mp4", "duracion": round(dur, 1)})
            usados[ident] = clave
            guardar_json(USADOS, usados)
            nuevas += 1
            print(f"{clave:<22} {tipo:<10} {dur:5.0f} s  {gancho[:70]}")
        dia += dt.timedelta(days=1)
    print(f"{nuevas} reels con voz nuevos. Quedan con gancho: {len(infr)} infracciones, {len(sups)} supuestos; "
          f"{len(fichas)} fichas.")
    return nuevas


def fijar_inicio(fecha):
    """Fija el primer dia del plan y quita de la cola lo antiguo de las franjas manana/mediodia/noche desde ese dia."""
    ini = dt.date.fromisoformat(fecha)
    guardar_json(CONFIG, {"inicio": ini.isoformat()})
    publicadas = leer_json(os.path.join(REPO, "estado", "publicadas.json"), {})
    quitadas = 0
    for d in sorted(os.listdir(COLA)):
        if d[:10] >= ini.isoformat() and not d.endswith("_tarde") and d not in publicadas:
            meta = leer_json(os.path.join(COLA, d, "meta.json"), {})
            if str(meta.get("formato", "")).startswith("voz_"):
                continue
            shutil.rmtree(os.path.join(COLA, d))
            quitadas += 1
    print(f"Plan con voz desde {ini}: {quitadas} publicaciones antiguas quitadas de la cola.")


if __name__ == "__main__":
    if sys.argv[1] == "inicio":
        fijar_inicio(sys.argv[2])
        programar()
    elif sys.argv[1] == "programar":
        programar()
