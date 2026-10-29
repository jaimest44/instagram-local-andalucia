"""Post extra: anuncio de los Esquemas visuales del temario de Policia Local (carrusel 4:5, 5 diapositivas).
    python anuncio_esquemas.py <carpeta_salida>
"""
import json
import os
import sys

GEN = r"D:/Movistar Cloud/40. TRABAJO/OPOSI S.L/LOCAL ANDALUCÍA/40. INSTAGRAM/generador"
sys.path.insert(0, GEN)
os.chdir(GEN)
from PIL import Image, ImageDraw, ImageFilter  # noqa: E402

import carrusel as C  # noqa: E402
import infografias as I  # noqa: E402

F = I.FICHAS
W, H, M = C.W, C.H, C.M


def ficha(rel):
    img, tema, _ = I.leer_ficha(os.path.join(F, rel))
    return img, tema


def marco(img, d, pieza, xy, borde=C.CIAN, r=16, grosor=6):
    x, y = xy
    d.rounded_rectangle((x - grosor, y - grosor, x + pieza.width + grosor, y + pieza.height + grosor), radius=r, fill=borde)
    img.paste(pieza, (x, y))


def girada(pieza, angulo):
    capa = Image.new("RGBA", (pieza.width + 16, pieza.height + 16), (0, 0, 0, 0))
    dc = ImageDraw.Draw(capa)
    dc.rounded_rectangle((0, 0, capa.width - 1, capa.height - 1), radius=14, fill=C.CIAN + (255,))
    capa.paste(pieza, (8, 8))
    return capa.rotate(angulo, expand=True, resample=Image.BICUBIC)


def slides():
    imgs = []
    ejemplos = {
        "ce": "Constitucion/CE_02_Derechos_Fundamentales.pdf",
        "cp": "Codigo_Penal/" + next(f for f in I.fichas_de("Codigo_Penal") if f.startswith("CP_L2_09")),
        "pl": "Ley_6-2023_Policias_Locales_Andalucia/" + I.fichas_de("Ley_6-2023_Policias_Locales_Andalucia")[0],
        "rgc": "RGCir_RD_1428-2003_Reglamento_General_Circulacion/" + I.fichas_de("RGCir_RD_1428-2003_Reglamento_General_Circulacion")[2],
        "l39": "Ley_39-2015_Procedimiento_Administrativo/" + I.fichas_de("Ley_39-2015_Procedimiento_Administrativo")[1],
        "vg": "Violencia_de_Genero_LO_1-2004_y_Ley_13-2007/" + I.fichas_de("Violencia_de_Genero_LO_1-2004_y_Ley_13-2007")[0],
    }
    f_ = {k: ficha(v)[0] for k, v in ejemplos.items()}

    # 1. portada: titular + abanico de fichas
    img, d = C.lienzo("NUEVO EN LA APP")
    y = C.TOP - 20
    for texto, color in (("EL TEMARIO DE", C.BLANCO), ("POLICÍA LOCAL", C.CIAN), ("EN ESQUEMAS", C.BLANCO), ("VISUALES.", C.BLANCO)):
        f, _, _ = C.ajustar(d, texto, C.TIT, W - 2 * M, 104, 100, 56, 1.0)
        d.text((M, y), texto, font=f, fill=color)
        y += 100
    C.pegatina(img, "+150 fichas · más de 70 leyes", (M - 6, y + 8), angulo=-3, tam=38)
    y += 120
    alto = C.LIMITE - y - 60
    for k, ang, x in (("cp", 7, 40), ("rgc", -6, 590), ("ce", 0, 300)):
        p = f_[k].crop((0, 0, 1080, int(1080 * 1.05)))
        p = p.resize((430, int(430 * p.height / p.width)), Image.LANCZOS)
        p = p.crop((0, 0, p.width, min(p.height, alto)))
        g = girada(p, ang)
        img.paste(g, (x, y + (0 if k == "ce" else 30)), g)
    d = ImageDraw.Draw(img)
    C.pie(d, "Desliza  >")
    imgs.append(img)

    # 2. asi es una ficha (Derechos fundamentales), parte de abajo difuminada
    img, d = C.lienzo("ASÍ ES UNA FICHA")
    y = C.TOP - 30
    corte = 0.38
    ej = I.difuminar(f_["ce"], corte)
    ancho = W - 2 * M
    ej = ej.resize((ancho, int(ancho * ej.height / ej.width)), Image.LANCZOS)
    alto = C.LIMITE - y - 10
    marco(img, d, ej.crop((0, 0, ancho, alto)), (M, y))
    cy = y + int(ej.height * corte) + 110
    if cy < y + alto - 120:
        I.candado(d, W // 2, cy, r=56)
        d.text((W // 2, cy + 100), "Completa, en la app", font=C.fuente(C.TIT, 58), fill=C.BLANCO, anchor="mm",
               stroke_width=6, stroke_fill=C.FONDO)
    C.pie(d, "Constitución · Derechos fundamentales")
    imgs.append(img)

    # 3. mosaico: de la Constitucion al trafico
    img, d = C.lienzo("DE LA CONSTITUCIÓN AL TRÁFICO")
    y0 = C.TOP - 20
    col, sep = 3, 22
    tw = (W - 2 * M - sep * (col - 1)) // col
    th = 320
    etiquetas = [("ce", "Constitución"), ("cp", "Código Penal"), ("pl", "Ley 6/2023 PL"),
                 ("l39", "Ley 39/2015"), ("rgc", "Circulación"), ("vg", "Violencia de género")]
    for i, (k, et) in enumerate(etiquetas):
        cx = M + (i % col) * (tw + sep)
        cy = y0 + (i // col) * (th + 80)
        p = f_[k].resize((tw, int(tw * f_[k].height / f_[k].width)), Image.LANCZOS).crop((0, 0, tw, th))
        marco(img, d, p, (cx, cy), r=12, grosor=4)
        d.text((cx + tw // 2, cy + th + 36), et, font=C.fuente(C.SEMI, 30), fill=C.BLANCO, anchor="mm")
    y = y0 + 2 * (th + 80) + 10
    f, l, t = C.ajustar(d, "Y así hasta más de 70 leyes.", C.TXT_SB, W - 2 * M, 60, 36, 26, 1.3)
    C.escribir(d, (M, y), l, f, t, C.CIAN, 1.3)
    C.pie(d, "Desliza  >")
    imgs.append(img)

    # 4. bloques del temario
    img, d = C.lienzo("TODOS LOS BLOQUES")
    y = C.TOP - 20
    bloques = [
        ("Constitución y Estatuto", "CE, Estatuto de Andalucía, TC, Poder Judicial, Defensor del Pueblo"),
        ("Administración y función pública", "Leyes 39 y 40/2015, LBRL, LAULA, padrón, TREBEP"),
        ("Policía Local y seguridad", "Ley 6/2023, Decreto 8/2026, LO 2/1986, Seguridad Ciudadana, armas"),
        ("Penal y procesal", "Código Penal (34 fichas), LECrim, detención, menores, víctima"),
        ("Tráfico y transporte", "Ley de Tráfico, Circulación, Conductores, Vehículos, LOTT, taxi y VTC"),
        ("Policía administrativa", "Consumo, comercio, espectáculos, urbanismo, medio ambiente, animales"),
        ("Igualdad y violencia de género", "LO 1/2004, LO 3/2007, LO 10/2022, LGTBI, deontología"),
    ]
    for tit, sub in bloques:
        alto = 118
        C.tarjeta(d, (M, y, W - M, y + alto), barra=C.CIAN)
        d.text((M + 40, y + 22), tit, font=C.fuente(C.TIT, 44), fill=C.BLANCO)
        f, l, t = C.ajustar(d, sub, C.TXT, W - 2 * M - 70, 40, 26, 20, 1.2)
        d.text((M + 40, y + 74), l[0], font=f, fill=C.TEXTO)
        y += alto + 14
    C.pie(d, "Desliza  >")
    imgs.append(img)

    # 5. cierre
    img, d = C.lienzo("ESQUEMAS VISUALES")
    y = C.TOP - 6
    for texto, color in (("CADA LEY,", C.BLANCO), ("DE UN VISTAZO", C.CIAN), ("Y DESDE EL MÓVIL.", C.BLANCO)):
        f, _, _ = C.ajustar(d, texto, C.TIT, W - 2 * M, 96, 90, 50, 1.0)
        d.text((M, y), texto, font=f, fill=color)
        y += 96
    y += 24
    items = ["Más de 150 fichas, ley a ley", "Cada parte de la ley en una hoja", "Cifras, plazos y multas clave",
             "Consejos y trampas de examen"]
    alto = 84 + len(items) * 52
    d.rounded_rectangle((M, y, W - M, y + alto), radius=26, fill=(255, 255, 255))
    d.text((M + 40, y + 28), "En la app tienes:", font=C.fuente(C.SEMI, 33), fill=C.NAVY_TXT)
    yy = y + 84
    for it in items:
        cx, cy = M + 56, yy + 18
        d.ellipse((cx - 16, cy - 16, cx + 16, cy + 16), fill=C.CIAN)
        d.line((cx - 8, cy, cx - 2, cy + 7, cx + 9, cy - 7), fill=C.NAVY_TXT, width=4)
        d.text((cx + 32, cy), it, font=C.fuente(C.TXT_SB, 31), fill=C.NAVY_TXT, anchor="lm")
        yy += 52
    y += alto + 26
    d.rounded_rectangle((M, y, W - M, y + 150), radius=30, fill=C.CIAN)
    d.text((W // 2, y + 38), "Regístrate en " + C.URL_APP, font=C.fuente(C.DISPLAY, 40), fill=C.NAVY_TXT, anchor="mm")
    d.text((W // 2, y + 96), I.RUTA_APP.replace("→", ">"), font=C.fuente(C.SEMI, 31), fill=C.NAVY_TXT, anchor="mm")
    C.pie(d, "Guárdalo y compártelo con quien prepare la oposición")
    imgs.append(img)
    return imgs


def texto():
    return "\n\n".join([
        "📚 Ya tienes el temario de Policía Local en esquemas visuales.",
        "Más de 150 fichas de más de 70 leyes: Constitución, Estatuto, Código Penal, LECrim, Ley 6/2023, "
        "tráfico, policía administrativa, igualdad… Cada ficha resume una parte de la ley en una hoja, "
        "con las cifras, los plazos y las trampas que más caen en el examen.",
        f"Las tienes en {C.URL_APP} → {I.RUTA_APP} (enlace en la bio).",
        "📌 Guárdalo y compártelo con quien esté preparando la oposición.",
        "#policialocal #oposicionesandalucia #esquemasvisuales",
    ])


if __name__ == "__main__":
    salida = sys.argv[1]
    os.makedirs(salida, exist_ok=True)
    nombres = []
    imgs = slides()
    for i, im in enumerate(imgs):
        C.puntos(im, i, len(imgs))
        n = f"{i + 1:02d}.jpg"
        im.save(os.path.join(salida, n), "JPEG", quality=90, optimize=True, progressive=True)
        nombres.append(n)
    open(os.path.join(salida, "caption.txt"), "w", encoding="utf-8").write(texto())
    meta = {"id": "anuncio-esquemas-visuales", "formato": "anuncio", "tema": "promo", "convocatoria": "",
            "caso": "", "imagenes": nombres}
    json.dump(meta, open(os.path.join(salida, "meta.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, sort_keys=True)
    print("ok", nombres)
