"""Texto (caption) de cada publicacion de @localandalucia.

Reglas: la primera linea es lo unico que se ve antes del "... mas", asi que lleva el gancho.
Una sola peticion de accion, el enlace a la app y pocos hashtags (3-5) que describan el tema.
Sin rayas largas ni frases de relleno: tiene que sonar a persona, no a plantilla.
"""
import hashlib
import re

from datos import acortar, es_desarrollo

URL_APP = "app.localandalucia.com"

GANCHOS_TEST = [
    "¿Sabrías responder esta pregunta del examen de Policía Local de {conv}?",
    "Esta cayó en {conv}. ¿La aciertas sin mirar?",
    "Pregunta oficial de {conv}. Aquí falla mucha gente.",
    "Si opositas a Policía Local en Andalucía, esta te puede caer. Salió en {conv}.",
]
GANCHOS_SUPUESTO = [
    "Supuesto práctico real de {conv}. ¿Cómo actuarías?",
    "Este caso cayó en el examen de {conv}. ¿Lo tenías?",
    "Supuesto de {conv}: lee el caso y piensa la respuesta antes de deslizar.",
]
GANCHOS_INFRACCION = [
    "¿Leve, grave o muy grave? Infracción de {materia}.",
    "Te lo encuentras de servicio: ¿qué infracción es y cuánto cuesta?",
    "{materia}: ¿sabrías calificar esta infracción sin mirar el codificado?",
    "Una de las que hay que saber de memoria en {materia}. ¿Qué tipo es?",
]

PIDE_TEST = [
    "Deja tu respuesta en comentarios (A, B, C o D) y desliza para ver la solución con el artículo exacto.",
    "Responde en comentarios antes de deslizar. En la siguiente imagen tienes la solución y lo que dice la ley.",
]
PIDE_DESARROLLO = [
    "Escribe en comentarios cómo lo resolverías y desliza para comparar con la solución.",
]
PIDE_INFRACCION = [
    "Comenta leve, grave o muy grave y desliza para ver la cuantía, el responsable y el órgano competente.",
    "Responde en comentarios antes de deslizar. En la siguiente imagen tienes la calificación completa.",
]

CIERRES = [
    "Guárdalo para tu próximo repaso.\n\nMás test oficiales de Policía Local en Andalucía, corregidos y justificados, en {url} (enlace en la bio).",
    "Guárdalo y compártelo con quien esté opositando contigo.\n\nTest, supuestos y el codificado completo en {url} (enlace en la bio).",
    "Si te ha servido, guárdalo.\n\nPractica con exámenes reales de Policía Local en {url} (enlace en la bio).",
]
CIERRES_INFRACCION = [
    "Guárdalo para tu próximo servicio.\n\nEl codificado completo, con cuantías, puntos y órganos competentes, en {url} (enlace en la bio).",
    "Guárdalo y compártelo con tu compañero de patrulla.\n\nTodas las infracciones codificadas en {url} (enlace en la bio).",
]

TEMAS = [
    (r"tr[aá]fico|circulaci[oó]n|6/2015|1428/2003|conductor|veh[ií]culo", "#seguridadvial"),
    (r"c[oó]digo penal|10/1995|delito", "#codigopenal"),
    (r"enjuiciamiento criminal|lecrim|detenci", "#lecrim"),
    (r"seguridad ciudadana|4/2015", "#seguridadciudadana"),
    (r"constituci", "#constitucionespañola"),
    (r"6/2023|polic[ií]as locales", "#policialocalandalucia"),
    (r"2/1986|fuerzas y cuerpos", "#fuerzasycuerpos"),
    (r"39/2015|40/2015|procedimiento administrativo", "#derechoadministrativo"),
    (r"animal", "#proteccionanimal"),
    (r"extranjer", "#extranjeria"),
]
FIJOS = ["#policialocal", "#oposicionespolicia", "#oposicionesandalucia"]


def _elige(lista, semilla, n=0):
    h = int(hashlib.md5(f"{semilla}{n}".encode()).hexdigest(), 16)
    return lista[h % len(lista)]


def hashtags(p):
    texto = " ".join([p.get("norma", ""), p.get("tema", ""), p.get("pregunta", ""), p.get("materia", "")])
    tags = list(FIJOS)
    for patron, tag in TEMAS:
        if re.search(patron, texto, re.I):
            tags.append(tag)
            break
    tags.append({"infraccion": "#codificado", "corta": "#supuestopractico"}.get(p["tipo"], "#testoposiciones"))
    return " ".join(dict.fromkeys(tags))


def caption(p):
    sid = p["id"]
    if p["tipo"] == "infraccion":
        partes = [_elige(GANCHOS_INFRACCION, sid).format(materia=p["materia"].lower()),
                  acortar(_frase(p["texto"]), 400),
                  f"Norma: {acortar(p['norma'], 140)}",
                  _elige(PIDE_INFRACCION, sid, 1),
                  _elige(CIERRES_INFRACCION, sid, 2).format(url=URL_APP)]
    else:
        conv = p["convocatoria"]
        if es_desarrollo(p):
            gancho, pide = _elige(GANCHOS_SUPUESTO, sid), _elige(PIDE_DESARROLLO, sid, 1)
        elif p["tipo"] == "corta":
            gancho, pide = _elige(GANCHOS_SUPUESTO, sid), _elige(PIDE_TEST, sid, 1)
        else:
            gancho, pide = _elige(GANCHOS_TEST, sid), _elige(PIDE_TEST, sid, 1)
        partes = [gancho.format(conv=conv), acortar(p["pregunta"], 400)]
        if p["norma"]:
            partes.append(f"Norma: {acortar(p['norma'], 120)}")
        partes += [pide, _elige(CIERRES, sid, 2).format(url=URL_APP)]
    partes.append(hashtags(p))
    texto = "\n\n".join(partes)
    texto = texto.replace("—", ",").replace("–", "-")
    return texto[:2200]


def _frase(t):
    """Conducta tipificada en tipo frase (en el Excel viene en mayusculas)."""
    from carrusel import sin_mayusculas
    return sin_mayusculas(t)


if __name__ == "__main__":
    from datos import cargar, problemas
    for tipo in ("test", "corta", "infraccion"):
        p = next(x for x in cargar(tipo) if not problemas(x))
        print(f"----- {tipo}\n{caption(p)}\n")
