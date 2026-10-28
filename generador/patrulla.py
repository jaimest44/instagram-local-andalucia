"""«Supuesto de patrulla»: caso creíble de servicio de Policía Local, pregunta tipo examen y resolución
con datos del codificado (norma, artículo, calificación, multa, puntos, responsable y órgano).

    python patrulla.py muestra            # genera los carruseles de todos los casos en salida/patrulla
    python patrulla.py programar FECHA    # (cuando Jaime lo apruebe) los mete en cola

Las cifras de cada caso salen del codificado de la app; los relatos son ficticios.
"""
import json
import os
import sys

from PIL import ImageDraw

import carrusel as C

AQUI = os.path.dirname(os.path.abspath(__file__))

CASOS = [
    {
        "id": "movil", "titulo": "Móvil en la mano en plena avenida",
        "lugar": "Avda. de Andalucía", "hora": "08:15 h", "implicados": "Conductor, 34 años", "vehiculo": "Turismo",
        "relato": "Una patrulla observa a un conductor que circula a baja velocidad por la Avenida de Andalucía "
                  "mientras escribe un mensaje con el teléfono móvil sujeto en la mano. Le dan el alto y se identifica.",
        "pregunta": "¿Cómo se califica la infracción y qué sanción le corresponde?",
        "opciones": ["Leve: 80 € y sin puntos", "Grave: 200 € y 3 puntos", "Grave: 200 € y 6 puntos", "Muy grave: 500 € y 4 puntos"],
        "correcta": "B", "calificacion": "Grave",
        "precepto": "Art. 18.2 RGC (opc. 5B)", "multa": "200 € (100 € con pronto pago)", "puntos": "3 puntos",
        "responsable": "Conductor", "organo": "Alcalde (vía urbana)",
        "ojo": ["Llevar auriculares conectados al conducir también es grave y quita 3 puntos (art. 18.2, opc. 5C).",
                "El pronto pago reduce la multa a la mitad: 100 €.",
                "En vías urbanas sanciona el Alcalde, no la DGT."],
    },
    {
        "id": "alcohol", "titulo": "Control de alcoholemia de madrugada",
        "lugar": "Paseo Marítimo", "hora": "02:30 h", "implicados": "Conductor, 41 años", "vehiculo": "Turismo",
        "relato": "En un control preventivo, el conductor de un turismo realiza la prueba con un etilómetro homologado "
                  "y da 0,38 mg/l de alcohol en aire espirado. No presenta síntomas evidentes de embriaguez.",
        "pregunta": "¿Qué infracción comete y con qué consecuencias?",
        "opciones": ["Grave: 200 € y sin puntos", "Muy grave: 500 € y 4 puntos", "Muy grave: 1.000 € y 6 puntos",
                     "Delito contra la seguridad vial"],
        "correcta": "B", "calificacion": "Muy grave",
        "precepto": "Art. 20.1 RGC (opc. 5E)", "multa": "500 € (250 € con pronto pago)", "puntos": "4 puntos",
        "responsable": "Conductor", "organo": "Alcalde (vía urbana)",
        "ojo": ["Más de 0,50 mg/l en aire: 1.000 € y 6 puntos (opc. 5I).",
                "Más de 0,60 mg/l en aire ya es delito (art. 379.2 del Código Penal).",
                "Noveles y profesionales: el límite baja a 0,15 mg/l."],
    },
    {
        "id": "cinturon", "titulo": "Sin cinturón a la salida del colegio",
        "lugar": "C/ Real", "hora": "09:05 h", "implicados": "Conductora, 29 años", "vehiculo": "Turismo",
        "relato": "Durante la vigilancia de la entrada de un colegio, los agentes ven que la conductora de un turismo "
                  "circula sin el cinturón de seguridad abrochado.",
        "pregunta": "¿Qué sanción le corresponde a la conductora?",
        "opciones": ["Leve: 80 € y sin puntos", "Grave: 200 € y sin puntos", "Grave: 200 € y 4 puntos", "Muy grave: 500 € y 6 puntos"],
        "correcta": "C", "calificacion": "Grave",
        "precepto": "Art. 117.1 RGC (opc. 5E)", "multa": "200 € (100 € con pronto pago)", "puntos": "4 puntos",
        "responsable": "Conductora", "organo": "Alcalde (vía urbana)",
        "ojo": ["Si el que no lo lleva es un pasajero, la multa es para el pasajero y no hay puntos (opc. 5F).",
                "Es grave tanto no llevarlo como llevarlo mal abrochado.",
                "Pronto pago: 100 €."],
    },
    {
        "id": "drogas", "titulo": "Consumo de drogas en un parque",
        "lugar": "Parque municipal", "hora": "19:40 h", "implicados": "Varón, 22 años", "vehiculo": "—",
        "relato": "Una patrulla a pie sorprende a un joven fumando un porro en un banco del parque. En el registro "
                  "superficial le encuentran una pequeña bolsa con hachís para consumo propio.",
        "pregunta": "¿Cómo se califica la conducta según la LO 4/2015?",
        "opciones": ["No es infracción: es consumo propio", "Infracción leve: 100 a 600 €",
                     "Infracción grave: 601 a 30.000 €", "Delito contra la salud pública"],
        "correcta": "C", "calificacion": "Grave",
        "precepto": "Art. 36.16 LO 4/2015", "multa": "601 a 30.000 €", "puntos": "",
        "responsable": "Autor", "organo": "Delegado del Gobierno",
        "ojo": ["Aunque sea para consumo propio, en lugares públicos es infracción grave.",
                "Si hay indicios de venta a terceros, ya no es administrativo: delito del art. 368 CP.",
                "La sustancia se interviene y se levanta acta."],
    },
    {
        "id": "botellon", "titulo": "Menores bebiendo en la plaza",
        "lugar": "Plaza del Ayuntamiento", "hora": "23:50 h", "implicados": "Tres menores de 16 y 17 años", "vehiculo": "—",
        "relato": "Los agentes localizan a tres menores bebiendo alcohol en la plaza, fuera de cualquier establecimiento. "
                  "Les piden la documentación y comprueban su edad.",
        "pregunta": "Según la Ley 7/2006 de Andalucía, ¿qué infracción cometen?",
        "opciones": ["Leve: apercibimiento o hasta 300 €", "Grave: de 301 a 24.000 €",
                     "Muy grave: de 24.001 a 60.000 €", "Ninguna: los menores no son responsables"],
        "correcta": "A", "calificacion": "Leve",
        "precepto": "Art. 8.5 Ley 7/2006", "multa": "Apercibimiento o hasta 300 €", "puntos": "",
        "responsable": "Los menores (y sus representantes legales)", "organo": "Alcalde del municipio",
        "ojo": ["Regla de oro de la Ley 7/2006: graves = negocios, leves = personas.",
                "Vender bebidas para consumir en la calle por teléfono o mensajería es grave (art. 7.1).",
                "Prescripción: muy graves 4 años, graves 3 y leves 1."],
    },
    {
        "id": "itv", "titulo": "Control rutinario: la ITV",
        "lugar": "Ctra. de circunvalación", "hora": "11:20 h", "implicados": "Conductor y titular, 57 años", "vehiculo": "Furgoneta",
        "relato": "En un control de documentación, los agentes comprueban que la furgoneta lleva más de un año "
                  "sin pasar la inspección técnica periódica que le corresponde.",
        "pregunta": "¿Qué infracción se denuncia?",
        "opciones": ["Leve: 80 € y sin puntos", "Grave: 200 € y sin puntos", "Grave: 200 € y 4 puntos", "Muy grave: 500 € y sin puntos"],
        "correcta": "B", "calificacion": "Grave",
        "precepto": "Art. 10.1 RGVeh (opc. 5A)", "multa": "200 € (100 € con pronto pago)", "puntos": "",
        "responsable": "Titular / Conductor", "organo": "Alcalde (vía urbana)",
        "ojo": ["Circular con la ITV desfavorable y el plazo para subsanar vencido también es grave (opc. 5E).",
                "Con la ITV negativa el vehículo queda inhabilitado para circular (opc. 5F).",
                "La ITV no quita puntos del carné."],
    },
    {
        "id": "ppp", "titulo": "Perro peligroso sin bozal",
        "lugar": "Paseo del río", "hora": "20:10 h", "implicados": "Propietario, 38 años", "vehiculo": "—",
        "relato": "Un vecino avisa de un perro de raza potencialmente peligrosa que pasea suelto y sin bozal. "
                  "La patrulla localiza al dueño, que muestra su licencia en vigor.",
        "pregunta": "¿Qué infracción comete el propietario?",
        "opciones": ["Leve: hasta 300,51 €", "Grave: de 300,52 a 2.404,05 €",
                     "Muy grave: de 2.404,06 a 15.025,30 €", "Ninguna, porque tiene licencia"],
        "correcta": "B", "calificacion": "Grave",
        "precepto": "Art. 13.2.d Ley 50/1999", "multa": "300,52 a 2.404,05 €", "puntos": "",
        "responsable": "Propietario / tenedor", "organo": "Comunidad Autónoma / Municipio",
        "ojo": ["Tener el perro potencialmente peligroso sin licencia es muy grave (art. 13.1.b).",
                "En lugares públicos debe llevar bozal y estar sujeto con cadena.",
                "Tener licencia no exime de llevar bozal."],
    },
    {
        "id": "patinete", "titulo": "Patinete eléctrico sin casco",
        "lugar": "Carril bici, C/ Nueva", "hora": "18:30 h", "implicados": "Conductor, 19 años", "vehiculo": "Patinete eléctrico (VMP)",
        "relato": "Un joven circula con su patinete eléctrico por el carril bici sin llevar puesto el casco "
                  "de protección. Los agentes le dan el alto.",
        "pregunta": "¿Cómo se califica la infracción?",
        "opciones": ["No es infracción: el casco es opcional", "Leve: 80 €",
                     "Grave: 200 €", "Muy grave: 500 €"],
        "correcta": "C", "calificacion": "Grave",
        "precepto": "Art. 118.3 RGC (opc. 5D)", "multa": "200 € (100 € con pronto pago)", "puntos": "",
        "responsable": "Conductor", "organo": "Alcalde (vía urbana)",
        "ojo": ["De noche, sin luz ni elemento reflectante, también es grave (opc. 5E).",
                "Circular con un VMP por autopista o autovía es grave (art. 20.1 LSV).",
                "El VMP necesita su certificado de circulación (art. 22 RGVeh)."],
    },
]

ICONOS = {"LUGAR": "pin", "HORA": "reloj", "IMPLICADOS": "persona", "VEHÍCULO": "coche"}


def icono(d, tipo, cx, cy, color):
    if tipo == "pin":
        d.ellipse((cx - 14, cy - 20, cx + 14, cy + 8), fill=color)
        d.polygon([(cx - 11, cy + 2), (cx + 11, cy + 2), (cx, cy + 22)], fill=color)
        d.ellipse((cx - 5, cy - 11, cx + 5, cy - 1), fill=C.FONDO)
    elif tipo == "reloj":
        d.ellipse((cx - 20, cy - 20, cx + 20, cy + 20), outline=color, width=5)
        d.line((cx, cy, cx, cy - 12), fill=color, width=4)
        d.line((cx, cy, cx + 10, cy + 4), fill=color, width=4)
    elif tipo == "persona":
        d.ellipse((cx - 9, cy - 20, cx + 9, cy - 2), fill=color)
        d.rounded_rectangle((cx - 17, cy + 1, cx + 17, cy + 21), radius=9, fill=color)
    else:
        d.rounded_rectangle((cx - 22, cy - 4, cx + 22, cy + 12), radius=5, fill=color)
        d.polygon([(cx - 13, cy - 4), (cx - 7, cy - 15), (cx + 9, cy - 15), (cx + 15, cy - 4)], fill=color)
        d.ellipse((cx - 16, cy + 7, cx - 6, cy + 17), fill=C.FONDO, outline=color, width=3)
        d.ellipse((cx + 6, cy + 7, cx + 16, cy + 17), fill=C.FONDO, outline=color, width=3)


def parte(d, y, caso):
    """Tarjeta tipo parte de intervencion con los datos del servicio."""
    filas = [("LUGAR", caso["lugar"]), ("HORA", caso["hora"]), ("IMPLICADOS", caso["implicados"]),
             ("VEHÍCULO", caso["vehiculo"])]
    alto = 70 + len(filas) * 92
    C.tarjeta(d, (C.M, y, C.W - C.M, y + alto), barra=C.AMBAR)
    d.text((C.M + 36, y + 22), "PARTE DE INTERVENCIÓN", font=C.fuente(C.SEMI, 26), fill=C.AMBAR)
    yy = y + 70
    for k, v in filas:
        icono(d, ICONOS[k], C.M + 66, yy + 34, C.CIAN)
        d.text((C.M + 110, yy + 6), k, font=C.fuente(C.SEMI, 22), fill=C.GRIS)
        d.text((C.M + 110, yy + 34), v, font=C.fuente(C.TXT_SB, 34), fill=C.BLANCO)
        yy += 92
    return y + alto


def diapositivas(caso):
    W, M = C.W, C.M
    imgs = []
    # 1. portada con el parte
    img, d = C.lienzo("SUPUESTO DE PATRULLA")
    f, l, t = C.ajustar(d, caso["titulo"].upper(), C.TIT, W - 2 * M, 200, 92, 54, 1.0)
    y = C.escribir(d, (M, C.TOP - 10), l, f, t, C.BLANCO, 1.0) + 30
    y = parte(d, y, caso) + 36
    C.pegatina(img, "¿Qué harías tú? Desliza", (M - 6, min(y, C.LIMITE - 70)), angulo=-3, tam=36)
    imgs.append(img)
    # 2. relato + pregunta + opciones
    img, d = C.lienzo("SUPUESTO DE PATRULLA")
    f, l, t = C.ajustar(d, caso["relato"], C.TXT, W - 2 * M - 72, 300, 32, 24, 1.38)
    y = C.caja_texto(d, C.TOP - 20, l, f, t, C.TEXTO, titulo="LOS HECHOS", barra=C.CIAN) + 26
    f, l, t = C.ajustar(d, caso["pregunta"], C.TIT, W - 2 * M, 130, 48, 32, 1.15)
    y = C.escribir(d, (M, y), l, f, t, C.BLANCO, 1.15) + 18
    alto = min(118, (C.LIMITE + 10 - y - 14 * 3) // 4)
    for letra, texto in zip("ABCD", caso["opciones"]):
        C.tarjeta_opcion(d, (M, y, W - M, y + alto), letra, texto)
        y += alto + 14
    C.pegatina(img, "Comenta tu respuesta", (M - 6, C.H - 128), angulo=-2.5, tam=32)
    imgs.append(img)
    # 3. resolucion
    img, d = C.lienzo("RESOLUCIÓN")
    color = C.GRAVEDAD.get(caso["calificacion"].lower(), C.CIAN)
    d.text((M, C.TOP - 18), "SOLUCIÓN: " + caso["correcta"], font=C.fuente(C.TIT, 72), fill=C.BLANCO)
    fcal = C.fuente(C.DISPLAY, 42)
    tw = d.textlength(caso["calificacion"].upper(), font=fcal)
    d.rounded_rectangle((M, C.TOP + 78, M + tw + 64, C.TOP + 150), radius=36, fill=color)
    d.text((M + 32, C.TOP + 114), caso["calificacion"].upper(), font=fcal, fill=C.NAVY_TXT, anchor="lm")
    y = C.TOP + 182
    filas = [("PRECEPTO", caso["precepto"]), ("MULTA", caso["multa"]), ("PUNTOS", caso["puntos"] or "No resta puntos"),
             ("RESPONSABLE", caso["responsable"]), ("QUIÉN SANCIONA", caso["organo"])]
    fv = C.fuente(C.TXT_SB, 32)
    bloques = [(k, C.envolver(d, v, fv, W - 2 * M - 72)[:2]) for k, v in filas]
    alto = sum(32 + len(ls) * 42 + 18 for _, ls in bloques) + 36
    C.tarjeta(d, (M, y, W - M, y + alto), barra=color)
    yy = y + 26
    for k, ls in bloques:
        d.text((M + 36, yy), k, font=C.fuente(C.SEMI, 23), fill=C.CIAN)
        yy = C.escribir(d, (M + 36, yy + 30), ls, fv, 32, C.BLANCO, 1.3) + 16
    C.pie(d, "Fuente: codificado de infracciones · Guárdalo")
    imgs.append(img)
    # 4. ojo en el examen
    img, d = C.lienzo("OJO EN EL EXAMEN")
    y = C.TOP - 10
    for i, punto in enumerate(caso["ojo"], 1):
        f, l, t = C.ajustar(d, punto, C.TXT_SB, W - 2 * M - 150, 230, 38, 26, 1.32)
        alto = max(130, len(l) * int(t * 1.32) + 56)
        C.tarjeta(d, (M, y, W - M, y + alto))
        d.ellipse((M + 30, y + alto // 2 - 34, M + 98, y + alto // 2 + 34), fill=C.AMBAR)
        d.text((M + 64, y + alto // 2), str(i), font=C.fuente(C.DISPLAY, 44), fill=C.NAVY_TXT, anchor="mm")
        C.escribir(d, (M + 126, y + (alto - len(l) * int(t * 1.32)) // 2), l, f, t, C.BLANCO, 1.32)
        y += alto + 22
    C.pie(d, "Así es como lo preguntan en el examen")
    imgs.append(img)
    # 5. cierre
    imgs.append(C.slide_cta({"tipo": "infraccion", "convocatoria": ""}))  # «Todo el codificado en tu bolsillo»
    return imgs


def texto(caso):
    return "\n\n".join([
        f"🚔 Supuesto de patrulla: {caso['titulo'].lower()}.",
        caso["relato"],
        f"❓ {caso['pregunta']} Comenta A, B, C o D y desliza para ver la solución con el artículo, la multa y quién sanciona.",
        "Practica cientos de supuestos y el codificado completo en app.localandalucia.com (enlace en la bio). "
        "Plan completo a 9,99 €/mes, precio congelado.",
        "#policialocal #oposicionesandalucia #supuestopractico",
    ])


def generar(caso, salida):
    os.makedirs(salida, exist_ok=True)
    nombres = []
    imgs = diapositivas(caso)
    for i, im in enumerate(imgs):
        C.puntos(im, i, len(imgs))
        n = f"{i + 1:02d}.jpg"
        im.save(os.path.join(salida, n), "JPEG", quality=90, optimize=True, progressive=True)
        nombres.append(n)
    with open(os.path.join(salida, "caption.txt"), "w", encoding="utf-8") as f:
        f.write(texto(caso))
    return nombres


if __name__ == "__main__":
    if sys.argv[1] == "muestra":
        for caso in CASOS:
            print(caso["id"], generar(caso, os.path.join(AQUI, "..", "salida", "patrulla", caso["id"])))
