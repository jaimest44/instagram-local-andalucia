"""«Precio congelado» en el estilo de la infografia de la Ley 7/2006 (la que mejor ha funcionado): una pantalla 9:16
con texto grande, y un Reel de ~14 s en el que los bloques aparecen rapido. Sin voz (anuncio de pago: nada sin
licencia comercial). Quien se suscribe antes del 31/12/2026 mantiene 9,99 €/mes mientras siga suscrito; nunca se
dice el precio de 2027.

    python precio_infografia.py la    <carpeta de salida>
    python precio_infografia.py admin <carpeta de salida>
"""
import importlib.util
import os
import subprocess
import sys

from PIL import Image, ImageDraw

AQUI = os.path.dirname(os.path.abspath(__file__))
ADMIN = os.path.join(AQUI, "..", "..", "..", "ADMINISTRATIVO LOCAL ANDALUCIA", "40. INSTAGRAM", "generador")
marca, salida = sys.argv[1], sys.argv[2]
ruta_c = os.path.join(ADMIN if marca == "admin" else AQUI, "carrusel.py")
spec = importlib.util.spec_from_file_location("carrusel", ruta_c)
C = importlib.util.module_from_spec(spec)
sys.path.insert(0, os.path.dirname(ruta_c))
spec.loader.exec_module(C)

W, H, M = 1080, 1920, 68
ROJO, NARANJA, VERDE = (217, 64, 64), (226, 135, 0), (46, 160, 90)
INCLUYE = {"la": ["+15.000 preguntas de exámenes oficiales", "Supuestos prácticos resueltos", "Codificado de infracciones",
                  "Esquemas visuales de los 45 temas"],
           "admin": ["Exámenes oficiales de Ayuntamientos", "Cada pregunta justificada", "Supuestos prácticos resueltos",
                     "Esquemas visuales de los 41 temas"]}[marca]


def caja(d, x0, y0, x1, y1):
    d.rounded_rectangle((x0, y0, x1, y1), radius=26, fill=(24, 50, 84), outline=(58, 86, 124), width=2)


def etiqueta(d, x, y, texto, color=C.CIAN, tam=30):
    f = C.fuente(C.DISPLAY, tam)
    w = d.textlength(texto, font=f)
    d.rounded_rectangle((x, y, x + w + 24, y + tam + 18), radius=8, fill=color)
    d.text((x + 12, y + (tam + 18) // 2), texto, font=f, fill=C.NAVY_TXT, anchor="lm")
    return x + w + 24


def dibujar():
    """Imagen final y, en orden de aparicion, las cajas (y0, y1) de cada bloque."""
    img = C.fondo_base(W, H)
    d = ImageDraw.Draw(img)
    bloques = []

    # cabecera: logo + pastilla
    lg = C.logo()
    lg = lg.resize((int(lg.width * 110 / lg.height), 110), Image.LANCZOS)
    img.paste(lg, (M, 70), lg)
    f = C.fuente(C.SEMI, 32)
    ancho = sum(d.textlength(c, font=f) for c in C.MARCA) + 3 * (len(C.MARCA) - 1) + 60
    d.rounded_rectangle((W - M - ancho, 100, W - M, 160), radius=30, outline=C.CIAN, width=3)
    C.texto_espaciado(d, W - M - ancho / 2, 113, C.MARCA, f, C.CIAN, 3)
    fk = C.fuente(C.SEMI, 38)
    x = M
    for c in "PRECIO DE LANZAMIENTO · 2026":
        d.text((x, 212), c, font=fk, fill=C.AMBAR)
        x += d.textlength(c, font=fk) + 9

    # el precio, enorme
    fp = C.fuente(C.DISPLAY, 250)
    d.text((M - 6, 250), "9,99", font=fp, fill=C.BLANCO)
    xp = M - 6 + d.textlength("9,99", font=fp) + 18
    d.text((xp, 290), "€", font=C.fuente(C.DISPLAY, 150), fill=C.CIAN)
    d.text((xp, 440), "/MES", font=C.fuente(C.DISPLAY, 70), fill=C.CIAN)
    d.text((M, 540), "congelado · ", font=C.fuente(C.TXT_SB, 46), fill=C.TEXTO)
    xx = M + d.textlength("congelado · ", font=C.fuente(C.TXT_SB, 46))
    d.text((xx, 540), "mientras sigas suscrito", font=C.fuente(C.TXT_B, 46), fill=C.BLANCO)
    bloques.append((0, 610))
    C.pegatina(img, "Solo si te suscribes antes del 31/12", (M - 4, 630), angulo=-3, tam=46)
    d = ImageDraw.Draw(img)
    bloques.append((610, 760))

    # como funciona: tres filas como la tabla de multas
    y0 = 790
    caja(d, M, y0, W - M, y0 + 330)
    etiqueta(d, M + 30, y0 + 26, "PASO A PASO")
    d.text((M + 260, y0 + 50), "CÓMO FUNCIONA", font=C.fuente(C.SEMI, 40), fill=C.CIAN, anchor="lm")
    filas = [(VERDE, "ANTES 31/12", "Te suscribes por 9,99 €/mes"), (NARANJA, "EN 2027", "El precio sube para los nuevos"),
             (C.CIAN, "TÚ", "Sigues pagando 9,99 €/mes")]
    y = y0 + 100
    for color, et, texto in filas:
        d.rounded_rectangle((M + 30, y, W - M - 30, y + 62), radius=12, fill=(255, 255, 255))
        d.rounded_rectangle((M + 30, y, M + 290, y + 62), radius=12, fill=color)
        d.rectangle((M + 270, y, M + 290, y + 62), fill=color)
        d.text((M + 160, y + 31), et, font=C.fuente(C.DISPLAY, 32), fill=C.BLANCO if color != C.CIAN else C.NAVY_TXT, anchor="mm")
        fx, _, _ = C.ajustar(d, texto, C.DISPLAY, W - 2 * M - 300 - 40, 50, 38, 26, 1.0)
        d.text((M + 315, y + 31), texto, font=fx, fill=C.NAVY_TXT, anchor="lm")
        y += 74
    bloques.append((y0, y0 + 330))

    # dos cajas: que incluye / sin riesgo
    y0 = 1150
    mitad = W // 2
    caja(d, M, y0, mitad - 12, y0 + 330)
    caja(d, mitad + 12, y0, W - M, y0 + 330)
    etiqueta(d, M + 26, y0 + 24, "INCLUYE", tam=28)
    yy = y0 + 92
    for it in INCLUYE:
        d.ellipse((M + 26, yy + 4, M + 58, yy + 36), fill=C.CIAN)
        d.line((M + 34, yy + 20, M + 41, yy + 27, M + 51, yy + 13), fill=C.NAVY_TXT, width=4)
        fx, lx, tx = C.ajustar(d, it, C.TXT_SB, mitad - 12 - M - 100, 56, 26, 20, 1.12)
        C.escribir(d, (M + 72, yy), lx, fx, tx, C.BLANCO, 1.12)
        yy += max(52, len(lx) * int(tx * 1.12) + 14)
    etiqueta(d, mitad + 38, y0 + 24, "SIN RIESGO", tam=28)
    d.text((mitad + 38, y0 + 100), "Regístrate", font=C.fuente(C.DISPLAY, 58), fill=C.AMBAR)
    d.text((mitad + 38, y0 + 166), "gratis", font=C.fuente(C.DISPLAY, 58), fill=C.AMBAR)
    fx, lx, tx = C.ajustar(d, "y prueba la app antes de pagar.", C.TXT_SB, W - M - mitad - 70, 90, 32, 22, 1.2)
    C.escribir(d, (mitad + 38, y0 + 236), lx, fx, tx, C.TEXTO, 1.15)
    bloques.append((y0, y0 + 330))

    # regla de oro
    y0 = 1510
    d.text((M, y0), "REGLA DE ORO", font=C.fuente(C.SEMI, 40), fill=C.CIAN)
    y0 += 60
    d.rounded_rectangle((M, y0, W - M, y0 + 110), radius=22, fill=(44, 52, 40))
    f1 = C.fuente(C.DISPLAY, 46)
    t1 = "ANTES DEL 31/12 = "
    d.text((M + 30, y0 + 55), t1, font=f1, fill=C.AMBAR, anchor="lm")
    d.text((M + 30 + d.textlength(t1, font=f1), y0 + 55), "9,99 € congelado", font=f1, fill=C.BLANCO, anchor="lm")
    bloques.append((1500, y0 + 110))

    # boton
    y0 = 1715
    d.rounded_rectangle((M, y0, W - M, y0 + 150), radius=30, fill=C.CIAN)
    d.text((W // 2, y0 + 42), "Regístrate gratis en", font=C.fuente(C.SEMI, 36), fill=C.NAVY_TXT, anchor="mm")
    fu, _, _ = C.ajustar(d, C.URL_APP + "  >", C.DISPLAY, W - 2 * M - 60, 80, 66, 40, 1.0)
    d.text((W // 2, y0 + 102), C.URL_APP + "  >", font=fu, fill=C.NAVY_TXT, anchor="mm")
    bloques.append((y0, y0 + 150))
    d.text((W // 2, 1890), "Envíaselo a tu compañero de opos", font=C.fuente(C.TXT_SB, 30), fill=(185, 200, 221), anchor="mm")
    return img, bloques


def reel(img, bloques, destino, fps=30):
    """Los bloques entran uno a uno (0,45 s cada uno, deslizandose) y la imagen completa se queda ~9 s."""
    import imageio_ffmpeg
    fondo = C.fondo_base(W, H)
    entrada = [0.0, 0.35, 0.9, 1.5, 2.1, 2.7]  # el precio esta desde el primer fotograma
    total = 14
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    proc = subprocess.Popen([ff, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                             "-r", str(fps), "-i", "-", "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
                             "-c:v", "libx264", "-profile:v", "high", "-pix_fmt", "yuv420p", "-crf", "20",
                             "-c:a", "aac", "-b:a", "96k", "-t", str(total), "-shortest", "-movflags", "+faststart", destino],
                            stdin=subprocess.PIPE)
    for k in range(total * fps):
        t = k / fps
        fr = fondo.copy()
        for (y0, y1), t0 in zip(bloques, entrada):
            if t < t0:
                continue
            a = 1.0 if t0 == 0 else min(1.0, (t - t0) / 0.3)  # el precio, entero desde el primer fotograma
            desliz = int(60 * (1 - a) ** 2)
            trozo = img.crop((0, y0, W, y1))
            fr.paste(trozo if a >= 1 else Image.blend(fondo.crop((0, y0 + desliz, W, y1 + desliz)), trozo, a), (0, y0 + desliz))
        if t >= entrada[-1] + 0.3:
            fr = img.copy()
        proc.stdin.write(fr.tobytes())
    proc.stdin.close()
    proc.wait()


def caption():
    return "\n\n".join([
        "⏳ 9,99 €/mes congelado: solo si te suscribes antes del 31 de diciembre.",
        "Quien se suscriba al Plan Completo antes del 31/12/2026 paga 9,99 €/mes y mantiene ese precio también en 2027 "
        "y después, mientras siga suscrito. En 2027 el precio sube para los nuevos.",
        f"Regístrate gratis en {C.URL_APP} y prueba la app antes de pagar (enlace en la bio).",
        "📌 Envíaselo a tu compañero de opos.",
        "#oposicionesandalucia #oposiciones #preciocongelado",
    ])


if __name__ == "__main__":
    os.makedirs(salida, exist_ok=True)
    img, bloques = dibujar()
    img.save(os.path.join(salida, "precio_congelado_9x16.png"))
    reel(img, bloques, os.path.join(salida, "reel.mp4"))
    open(os.path.join(salida, "caption.txt"), "w", encoding="utf-8").write(caption())
    print("ok", salida)
