"""Serie «Esquemas visuales»: enseña un trozo de una ficha de estudio (PDF A4) y difumina el resto,
con llamada a la app (Recursos → Supuestos → Esquemas visuales). Estilo de la infografía de la Ley 7/2006.

    python infografias.py programar 2026-10-30      # mete en cola la serie (martes y viernes a las 11:00)
    python infografias.py muestra Codigo_Penal/CP_L2_09_Hurto_Robo_Usurpacion.pdf reel

Formatos (se alternan): Reel 9:16 con barrido por la ficha, o carrusel 4:5 de 4 diapositivas.
"""
import datetime as dt
import json
import os
import re
import subprocess
import sys

import pymupdf
from PIL import Image, ImageDraw, ImageFilter

import carrusel as C

FICHAS = r"C:/Users/jaime/Downloads/INFOGRAFIA LEYES"
AQUI = os.path.dirname(os.path.abspath(__file__))
COLA = os.path.join(AQUI, "..", "cola")
ESTADO = os.path.join(AQUI, "..", "estado", "infografias_usadas.json")
RUTA_APP = "Recursos → Supuestos → Esquemas visuales"

# orden de la serie (de mas a menos preguntas de examen) y la ficha con la que empieza cada ley
LEYES = [
    ("Constitucion", "Constitución Española", "CE_02"),
    ("Codigo_Penal", "Código Penal", "CP_L2_09"),
    ("Ley_39-2015_Procedimiento_Administrativo", "Ley 39/2015", "L39-2015_02"),
    ("RGCir_RD_1428-2003_Reglamento_General_Circulacion", "Reglamento General de Circulación", "RGCir_03"),
    ("LBRL_Ley_7-1985_Regimen_Local", "Ley de Bases del Régimen Local", ""),
    ("LSV_RDL_6-2015_Trafico_y_Seguridad_Vial", "Ley de Tráfico y Seguridad Vial", "LSV_02"),
    ("LECrim_Ley_Enjuiciamiento_Criminal", "Ley de Enjuiciamiento Criminal", ""),
    ("LO_2-1986_Fuerzas_y_Cuerpos_de_Seguridad", "LO 2/1986 de Fuerzas y Cuerpos de Seguridad", ""),
    ("Estatuto_Autonomia_Andalucia", "Estatuto de Autonomía de Andalucía", ""),
    ("Ley_6-2023_Policias_Locales_Andalucia", "Ley 6/2023 de Policías Locales", ""),
    ("Decreto_8-2026_Ingreso_Policia_Local", "Decreto 8/2026 de ingreso", ""),
    ("Emergencias_Ley_2-2002_y_Proteccion_Civil_Ley_17-2015", "Emergencias y Protección Civil", ""),
    ("TREBEP_RDL_5-2015", "TREBEP", ""),
    ("RD_137-1993_Reglamento_de_Armas", "Reglamento de Armas", ""),
    ("Violencia_de_Genero_LO_1-2004_y_Ley_13-2007", "Violencia de género", ""),
]


# ---------------------------------------------------------------- lectura de la ficha

def fichas_de(carpeta):
    d = os.path.join(FICHAS, carpeta)
    return sorted(f for f in os.listdir(d) if f.lower().endswith(".pdf") and "complet" not in f.lower())


def leer_ficha(ruta):
    """Imagen de la pagina, tema (titulo de la cabecera) y el primer consejo de examen."""
    doc = pymupdf.open(ruta)
    p = doc[0]
    w = p.rect.width
    spans = [s for b in p.get_text("dict")["blocks"] for l in b.get("lines", []) for s in l["spans"]
             if s["bbox"][1] < 80 and s["bbox"][0] < w * 0.8 and s["text"].strip()]
    grande = max(spans, key=lambda s: s["size"])
    linea = sorted([s for s in spans if abs(s["bbox"][3] - grande["bbox"][3]) < 5], key=lambda s: s["bbox"][0])
    titulo = re.sub(r"\s+", " ", "".join(s["text"] for s in linea)).strip()
    tema = [x.strip() for x in titulo.split("·") if x.strip()][-1]

    lineas = [l.strip() for l in p.get_text().splitlines() if l.strip()]
    consejo = None
    try:
        i = next(k for k, l in enumerate(lineas) if "TRAMPAS DE EXAMEN" in l.upper())
        tit = re.sub(r"^[^\wÁÉÍÓÚÑ¿¡«\"(]+", "", lineas[i + 1]).strip()  # quita el icono, no las comillas
        cuerpo = []
        for l in lineas[i + 2:]:
            if re.match(r"^[^\w\s(¿¡«\"'+\-–]", l):  # siguiente consejo (empieza por icono)
                break
            cuerpo.append(l)
        texto = re.sub(r"\s+", " ", " ".join(cuerpo))
        # palabras partidas al final de linea: "6– 18" -> "6–18", "consi- derar" -> "considerar"
        texto = re.sub(r"(\w)([–-]) (\w)", lambda m: m.group(1) + (m.group(2) if m.group(1).isdigit() else "") + m.group(3), texto)
        consejo = (tit, texto)
    except (StopIteration, IndexError):
        pass

    zoom = 2160 / w  # el doble de 1080 de ancho, para que quede nitida al reducir
    pix = p.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom))
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples).resize((1080, int(1080 * pix.height / pix.width)), Image.LANCZOS)
    return img, tema, consejo


def difuminar(img, desde):
    """Deja nitida la parte de arriba (hasta 'desde', fraccion de alto) y difumina el resto."""
    y = int(img.height * desde)
    out = img.copy()
    borroso = img.crop((0, y, img.width, img.height)).filter(ImageFilter.GaussianBlur(14))
    velo = Image.new("RGB", borroso.size, C.FONDO)
    out.paste(Image.blend(borroso, velo, 0.25), (0, y))
    # transicion suave entre lo nitido y lo difuminado
    trans = 60
    for i in range(trans):
        a = i / trans
        fila_n = img.crop((0, y - trans + i, img.width, y - trans + i + 1))
        fila_b = Image.blend(fila_n.filter(ImageFilter.GaussianBlur(4)), Image.new("RGB", fila_n.size, C.FONDO), 0.25 * a)
        out.paste(Image.blend(fila_n, fila_b, a), (0, y - trans + i))
    return out


def candado(d, cx, cy, r=62):
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=C.FONDO, outline=C.CIAN, width=5)
    d.rounded_rectangle((cx - 26, cy - 6, cx + 26, cy + 34), radius=7, fill=C.AMBAR)
    d.arc((cx - 18, cy - 36, cx + 18, cy + 6), start=180, end=360, fill=C.AMBAR, width=8)
    d.ellipse((cx - 5, cy + 8, cx + 5, cy + 18), fill=C.FONDO)


def tarjeta_cierre(img, d, y, ley, alto_total=None):
    """Tarjeta blanca + boton cian: las fichas de todas las leyes en la app."""
    items = ["Supuestos prácticos resueltos", "Consejos y trampas de examen", "Cifras, plazos y multas clave",
             "Más de 160 fichas, ley a ley"]
    alto = 84 + len(items) * 52
    d.rounded_rectangle((C.M, y, C.W - C.M, y + alto), radius=26, fill=(255, 255, 255))
    d.text((C.M + 40, y + 28), "La ficha completa incluye:", font=C.fuente(C.SEMI, 33), fill=C.NAVY_TXT)
    yy = y + 84
    for it in items:
        cx, cy = C.M + 56, yy + 18
        d.ellipse((cx - 16, cy - 16, cx + 16, cy + 16), fill=C.CIAN)
        d.line((cx - 8, cy, cx - 2, cy + 7, cx + 9, cy - 7), fill=C.NAVY_TXT, width=4)
        d.text((cx + 32, cy), it, font=C.fuente(C.TXT_SB, 31), fill=C.NAVY_TXT, anchor="lm")
        yy += 52
    y += alto + 26
    d.rounded_rectangle((C.M, y, C.W - C.M, y + 150), radius=30, fill=C.CIAN)
    d.text((C.W // 2, y + 38), "Regístrate en " + C.URL_APP, font=C.fuente(C.DISPLAY, 40), fill=C.NAVY_TXT, anchor="mm")
    d.text((C.W // 2, y + 96), RUTA_APP.replace("→", ">"), font=C.fuente(C.SEMI, 31), fill=C.NAVY_TXT, anchor="mm")
    return y + 150


# ---------------------------------------------------------------- carrusel (4 diapositivas 4:5)

def carrusel(ficha, tema, ley, salida, consejo=None):
    os.makedirs(salida, exist_ok=True)
    W, H, M = C.W, C.H, C.M
    corte = 0.42
    nitida = ficha.crop((0, 0, ficha.width, int(ficha.height * corte)))
    dif = difuminar(ficha, corte)
    imgs = []

    # 1. portada
    img, d = C.lienzo("ESQUEMA VISUAL")
    y = C.TOP - 10
    f, l, t = C.ajustar(d, ley.upper(), C.TIT, W - 2 * M, 200, 96, 56, 1.0)
    y = C.escribir(d, (M, y), l, f, t, C.CIAN, 1.0) + 8
    f, l, t = C.ajustar(d, tema, C.TIT, W - 2 * M, 150, 60, 36, 1.1)
    y = C.escribir(d, (M, y), l, f, t, C.BLANCO, 1.1) + 26
    C.pegatina(img, "Lo que más cae en el examen", (M - 6, y), angulo=-3, tam=36)
    y += 110
    prev = nitida.resize((W - 2 * M, int((W - 2 * M) * nitida.height / nitida.width)), Image.LANCZOS)
    alto = min(prev.height, C.LIMITE - y)
    d.rounded_rectangle((M - 6, y - 6, W - M + 6, y + alto + 6), radius=18, fill=C.CIAN)
    img.paste(prev.crop((0, 0, prev.width, alto)), (M, y))
    C.pie(d, "Desliza para ver la ficha  >")
    imgs.append(img)

    # 2. la parte nitida, grande
    img, d = C.lienzo("LO QUE MÁS CAE")
    y = C.TOP - 20
    zona = nitida.resize((W - 2 * M, int((W - 2 * M) * nitida.height / nitida.width)), Image.LANCZOS)
    alto = min(zona.height, C.LIMITE - y)
    img.paste(zona.crop((0, 0, zona.width, alto)), (M, y))
    y += alto + 30
    if consejo and C.LIMITE - y > 180:  # el consejo de examen de la ficha, en una tarjeta
        f, l, t = C.ajustar(d, consejo[1], C.TXT, W - 2 * M - 72, C.LIMITE - y - 110, 32, 22, 1.35)
        C.caja_texto(d, y, l, f, t, C.TEXTO, titulo="TRUCO DE EXAMEN · " + consejo[0].upper(), barra=C.AMBAR)
    C.pie(d, "Guárdalo para repasar")
    imgs.append(img)

    # 3. el resto, difuminado con candado
    img, d = C.lienzo("Y HAY MÁS…")
    y = C.TOP - 20
    resto = dif.crop((0, int(dif.height * (corte - 0.06)), dif.width, dif.height))
    resto = resto.resize((W - 2 * M, int((W - 2 * M) * resto.height / resto.width)), Image.LANCZOS)
    alto = min(resto.height, C.LIMITE - y)
    img.paste(resto.crop((0, 0, resto.width, alto)), (M, y))
    d = ImageDraw.Draw(img)
    cy = y + alto // 2 - 60
    candado(d, W // 2, cy)
    f = C.fuente(C.TIT, 64)
    d.text((W // 2, cy + 120), "ESTO ES SOLO UN ADELANTO", font=f, fill=C.BLANCO, anchor="mm",
           stroke_width=6, stroke_fill=C.FONDO)
    d.text((W // 2, cy + 185), "La ficha completa está en la app", font=C.fuente(C.SEMI, 38), fill=C.CIAN,
           anchor="mm", stroke_width=5, stroke_fill=C.FONDO)
    C.pie(d, "Desliza  >")
    imgs.append(img)

    # 4. cierre
    img, d = C.lienzo("ESQUEMAS VISUALES")
    y = C.TOP - 6
    for texto, color in (("LAS FICHAS DE", C.BLANCO), ("TODAS LAS LEYES,", C.CIAN), ("EN LA APP.", C.BLANCO)):
        f, _, _ = C.ajustar(d, texto, C.TIT, W - 2 * M, 96, 90, 50, 1.0)
        d.text((M, y), texto, font=f, fill=color)
        y += 96
    tarjeta_cierre(img, d, y + 24, ley)
    C.pie(d, "Guárdalo y compártelo con quien prepare la oposición")
    imgs.append(img)

    nombres = []
    for i, im in enumerate(imgs):
        C.puntos(im, i, len(imgs))
        n = f"{i + 1:02d}.jpg"
        im.save(os.path.join(salida, n), "JPEG", quality=90, optimize=True, progressive=True)
        nombres.append(n)
    return nombres


# ---------------------------------------------------------------- reel (9:16, ~15 s)

def reel(ficha, tema, ley, salida, fps=30):
    """Barrido lento por la ficha (nitida arriba, difuminada abajo) y tarjeta final."""
    import imageio_ffmpeg
    os.makedirs(salida, exist_ok=True)
    W, H, M = 1080, 1920, C.M
    corte = 0.45
    dif = difuminar(ficha, corte)
    ancho = W - 2 * 40
    doc = dif.resize((ancho, int(ancho * dif.height / dif.width)), Image.LANCZOS)

    base = C.fondo_base(W, H)
    d = ImageDraw.Draw(base)
    lg = C.logo()
    lg = lg.resize((int(lg.width * 84 / lg.height), 84), Image.LANCZOS)
    base.paste(lg, (M, 56), lg)
    fk = C.fuente(C.SEMI, 30)
    x = M
    for c in "ESQUEMA VISUAL · " + ley.upper():
        d.text((x, 172), c, font=fk, fill=C.AMBAR)
        x += d.textlength(c, font=fk) + 5
    f, l, t = C.ajustar(d, tema, C.TIT, W - 2 * M, 150, 72, 44, 1.05)
    C.escribir(d, (M, 222), l, f, t, C.BLANCO, 1.05)
    ventana_y, ventana_h = 410, 1330  # zona por la que pasa la ficha
    recorrido = max(0, doc.height - ventana_h)

    seg_barrido, seg_cierre = 10, 5
    total = seg_barrido + seg_cierre
    cierre = None
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    destino = os.path.join(salida, "reel.mp4")
    proc = subprocess.Popen([ff, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                             "-s", f"{W}x{H}", "-r", str(fps), "-i", "-",
                             "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
                             "-c:v", "libx264", "-profile:v", "high", "-pix_fmt", "yuv420p", "-crf", "21",
                             "-c:a", "aac", "-b:a", "96k", "-t", str(total), "-shortest",
                             "-movflags", "+faststart", destino], stdin=subprocess.PIPE)
    for n in range(total * fps):
        s = n / fps
        if s < seg_barrido:
            # 1 s quieto arriba, barrido suave hasta abajo, 1 s quieto
            k = min(1, max(0, (s - 1) / (seg_barrido - 2)))
            k = k * k * (3 - 2 * k)
            off = int(recorrido * k)
            frame = base.copy()
            frame.paste(doc.crop((0, off, doc.width, off + ventana_h)), (40, ventana_y))
            if s > seg_barrido - 3.5:  # al llegar a lo difuminado aparece el candado
                fd = ImageDraw.Draw(frame)
                cy = ventana_y + ventana_h // 2
                candado(fd, W // 2, cy - 40, r=70)
                fd.text((W // 2, cy + 80), "ESTO ES SOLO UN ADELANTO", font=C.fuente(C.TIT, 70), fill=C.BLANCO,
                        anchor="mm", stroke_width=7, stroke_fill=C.FONDO)
                fd.text((W // 2, cy + 150), "La ficha completa, en la app", font=C.fuente(C.SEMI, 42), fill=C.CIAN,
                        anchor="mm", stroke_width=6, stroke_fill=C.FONDO)
        else:
            if cierre is None:
                cierre = C.fondo_base(W, H)
                cd = ImageDraw.Draw(cierre)
                cierre.paste(lg, (M, 56), lg)
                y = 300
                for texto, color in (("LAS FICHAS DE", C.BLANCO), ("TODAS LAS LEYES,", C.CIAN), ("EN LA APP.", C.BLANCO)):
                    f, _, _ = C.ajustar(cd, texto, C.TIT, W - 2 * M, 130, 120, 60, 1.0)
                    cd.text((M, y), texto, font=f, fill=color)
                    y += 128
                tarjeta_cierre(cierre, cd, y + 40, ley)
                cd.text((W // 2, H - 140), "Guárdalo y compártelo con quien prepare la oposición",
                        font=C.fuente(C.TXT_SB, 30), fill=(185, 200, 221), anchor="mm")
            frame = cierre
        proc.stdin.write(frame.tobytes())
    proc.stdin.close()
    proc.wait()
    if proc.returncode:
        raise RuntimeError("ffmpeg falló al crear el reel")
    return destino


# ---------------------------------------------------------------- texto y programacion

def caption(ley, tema, consejo):
    gancho = f"🧠 {consejo[0]}\n{consejo[1]}" if consejo else f"Lo que más cae del {ley} en el examen de Policía Local."
    if len(gancho) > 330:
        gancho = gancho[:330].rsplit(" ", 1)[0] + "…"
    return "\n\n".join([
        gancho,
        f"Esto es solo un trozo de la ficha de estudio de {ley}: «{tema}».",
        "Las fichas completas de todas las leyes, con supuestos resueltos y trampas de examen, están en "
        f"{C.URL_APP} → {RUTA_APP}.",
        "📌 Guárdalo y compártelo con quien esté preparando la oposición.",
        "#policialocal #oposicionesandalucia #esquemasvisuales",
    ])


def generar_post(carpeta_ley, ley, pdf, formato, salida):
    ficha, tema, consejo = leer_ficha(os.path.join(FICHAS, carpeta_ley, pdf))
    os.makedirs(salida, exist_ok=True)
    meta = {"id": f"infografia-{carpeta_ley}-{pdf}", "formato": "infografia_" + formato, "tema": "infografia",
            "convocatoria": "", "caso": "", "ley": ley, "ficha": pdf, "imagenes": []}
    if formato == "reel":
        reel(ficha, tema, ley, salida)
        meta["reel"] = "reel.mp4"
    else:
        meta["imagenes"] = carrusel(ficha, tema, ley, salida, consejo)
    with open(os.path.join(salida, "caption.txt"), "w", encoding="utf-8") as f:
        f.write(caption(ley, tema, consejo))
    return meta, tema


def programar(inicio):
    """Una ficha por ley en el orden de LEYES, martes y viernes a las 11:00, alternando Reel y carrusel."""
    usadas = json.load(open(ESTADO, encoding="utf-8")) if os.path.exists(ESTADO) else {}
    dia = dt.date.fromisoformat(inicio)
    n = 0
    for carpeta_ley, ley, preferida in LEYES:
        fichas = [f for f in fichas_de(carpeta_ley) if f"{carpeta_ley}/{f}" not in usadas]
        if not fichas:
            continue
        pdf = next((f for f in fichas if preferida and f.startswith(preferida)), fichas[0])
        while dia.weekday() not in (1, 4):  # martes y viernes
            dia += dt.timedelta(days=1)
        clave = dia.isoformat() + "_manana"
        salida = os.path.join(COLA, clave)
        formato = "reel" if n % 2 == 0 else "carrusel"
        meta, tema = generar_post(carpeta_ley, ley, pdf, formato, salida)
        meta.update({"fecha": dia.isoformat(), "franja": "manana"})
        json.dump(meta, open(os.path.join(salida, "meta.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, sort_keys=True)
        usadas[f"{carpeta_ley}/{pdf}"] = clave
        print(f"{dia:%a %d/%m} 11:00  {formato:<8} {ley} · {tema}")
        n += 1
        dia += dt.timedelta(days=1)
    json.dump(usadas, open(ESTADO, "w", encoding="utf-8"), ensure_ascii=False, indent=1, sort_keys=True)


if __name__ == "__main__":
    if sys.argv[1] == "programar":
        programar(sys.argv[2])
    elif sys.argv[1] == "muestra":
        carpeta_ley, pdf = sys.argv[2].split("/")
        ley = next(l for c, l, _ in LEYES if c == carpeta_ley)
        destino = os.path.join(AQUI, "..", "salida", "muestra_infografia_" + sys.argv[3])
        print(generar_post(carpeta_ley, ley, pdf, sys.argv[3], destino))
