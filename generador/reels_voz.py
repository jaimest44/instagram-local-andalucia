"""Reels con voz para @localandalucia (plan de captacion de noviembre 2026): sin cara, voz narrada.

Tres formatos:
    infraccion  ~25 s   escena -> «¿leve, grave o muy grave?» -> multa, puntos y QUIEN SANCIONA (codificado)
    chuleta     ~35 s   «3 trampas de <ley> que caen siempre» sobre la ficha de Esquemas visuales
    supuesto    1-3 min supuesto resuelto: la escena, la pregunta, 5 s para pensar y la solucion

    python reels_voz.py muestra infraccion "TRÁFICO COMPLETO - CODIFICADO.xlsx#65" "Vas conduciendo y coges el móvil para contestar un WhatsApp."
    python reels_voz.py muestra chuleta Codigo_Penal/CP_L2_09_Hurto_Robo_Usurpacion.pdf
    python reels_voz.py muestra supuesto "2022 - Armilla SP.xlsx#12"

Voz: Azure AI Speech (Alvaro, neuronal) si esta configurada con publicador/configurar_voz.py (clave cifrada
en este PC); si no, la voz de Windows (provisional). Se puede forzar con VOZ=windows o VOZ=azure.
"""
import io
import os
import re
import subprocess
import sys
import wave

from PIL import Image, ImageDraw

import carrusel as C
import datos
import infografias as I

AQUI = os.path.dirname(os.path.abspath(__file__))
W, H, M = 1080, 1920, 70
FPS = 30
sys.path.insert(0, os.path.join(AQUI, "..", "publicador"))
from configurar_voz import leer as leer_azure  # noqa: E402

AZURE = leer_azure()
VOZ = os.environ.get("VOZ", "azure" if AZURE else "windows")
VOZ_AZURE = "es-ES-AlvaroNeural"


# ---------------------------------------------------------------- voz

LECTURA = [  # lo que la voz lee mal tal cual
    (r"\bArts?\.\s*", "artículo "), (r"\bart\.\s*", "artículo "), (r"\bapdo\.\s*", "apartado "),
    (r"\bopc\.\s*\w+", ""), (r"\bLOPSC\b", "Ley de Seguridad Ciudadana"), (r"\bLO\b", "Ley Orgánica"),
    (r"\bRDL\b", "Real Decreto Legislativo"), (r"\bRD\b", "Real Decreto"), (r"\bCP\b", "Código Penal"),
    (r"\bRGCir\.?\b", "Reglamento General de Circulación"), (r"\bRGC\b", "Reglamento General de Circulación"),
    (r"\bLECrim\b", "Ley de Enjuiciamiento Criminal"), (r"\bITV\b", "i te uve"), (r"\bDGT\b", "de ge te"),
    (r"(\d+)/(\d{4})", r"\1 de \2"), (r"(\d+) ?€", r"\1 euros"), (r"mg/l", "miligramos por litro"),
    (r"km/h", "kilómetros por hora"), (r"\bnº\s*", "número "), (r"\bD\.\s", "don "), (r"[«»\"“”]", ""),
    (r"\s*\(([^)]*)\)", r", \1,"), (r"\s+", " "),
]


def para_leer(t):
    for a, b in LECTURA:
        t = re.sub(a, b, t)
    return t.strip()


def sintetizar(texto, ruta):
    """WAV mono con la frase leida."""
    texto = para_leer(texto)
    if VOZ == "azure":
        import urllib.request
        from xml.sax.saxutils import escape
        ssml = (f"<speak version='1.0' xml:lang='es-ES'><voice name='{VOZ_AZURE}'>"
                f"<prosody rate='+6%'>{escape(texto)}</prosody></voice></speak>").encode("utf-8")
        req = urllib.request.Request(
            f"https://{AZURE['region']}.tts.speech.microsoft.com/cognitiveservices/v1", data=ssml,
            headers={"Ocp-Apim-Subscription-Key": AZURE["clave"], "Content-Type": "application/ssml+xml",
                     "X-Microsoft-OutputFormat": "riff-24khz-16bit-mono-pcm", "User-Agent": "localandalucia-reels"})
        with urllib.request.urlopen(req, timeout=60) as r, open(ruta, "wb") as f:
            f.write(r.read())
    else:
        tmp = ruta + ".txt"
        open(tmp, "w", encoding="utf-8").write(texto)
        subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                        os.path.join(AQUI, "voz_windows.ps1"), "-TextoArchivo", tmp, "-Salida", ruta], check=True)
        os.remove(tmp)


def leer_wav(ruta):
    with wave.open(ruta) as w:
        return w.getparams(), w.readframes(w.getnframes())


# ---------------------------------------------------------------- dibujo

def base(kicker):
    img = C.fondo_base(W, H)
    d = ImageDraw.Draw(img)
    lg = C.logo()
    lg = lg.resize((int(lg.width * 84 / lg.height), 84), Image.LANCZOS)
    img.paste(lg, (M, 60), lg)
    fk = C.fuente(C.SEMI, 32)
    x = M
    for c in kicker:
        d.text((x, 200), c, font=fk, fill=C.AMBAR)
        x += d.textlength(c, font=fk) + 6
    d.line((M, 252, M + 120, 252), fill=C.AMBAR, width=4)
    return img, d


def texto_grande(d, y, texto, color=C.BLANCO, alto=520, maximo=96, minimo=52, fuente=C.TIT, inter=1.08):
    f, l, t = C.ajustar(d, texto, fuente, W - 2 * M, alto, maximo, minimo, inter)
    return C.escribir(d, (M, y), l, f, t, color, inter)


def tarjeta_texto(d, y, texto, titulo=None, barra=C.CIAN, alto_max=700, maximo=40, minimo=28):
    f, l, t = C.ajustar(d, texto, C.TXT, W - 2 * M - 80, alto_max, maximo, minimo, 1.35)
    extra = 70 if titulo else 40
    alto = len(l) * int(t * 1.35) + extra + 40
    C.tarjeta(d, (M, y, W - M, y + alto), barra=barra)
    if titulo:
        d.text((M + 40, y + 26), titulo, font=C.fuente(C.SEMI, 34), fill=barra)
    C.escribir(d, (M + 40, y + extra), l, f, t, C.TEXTO, 1.35)
    return y + alto


def boton_app(d, y, linea1="Regístrate gratis en"):
    d.rounded_rectangle((M, y, W - M, y + 170), radius=34, fill=C.CIAN)
    d.text((W // 2, y + 50), linea1, font=C.fuente(C.SEMI, 38), fill=C.NAVY_TXT, anchor="mm")
    d.text((W // 2, y + 115), C.URL_APP, font=C.fuente(C.DISPLAY, 64), fill=C.NAVY_TXT, anchor="mm")
    return y + 170


def pie(d, texto):
    d.text((W // 2, H - 150), texto, font=C.fuente(C.TXT_SB, 34), fill=(185, 200, 221), anchor="mm")


# ---------------------------------------------------------------- montaje

class Escena:
    """Una imagen (o una funcion t -> imagen) con la frase que se lee mientras se ve."""

    def __init__(self, imagen, voz="", pausa=0.6, minimo=0.0, animada=None):
        self.imagen, self.voz, self.pausa, self.minimo, self.animada = imagen, voz, pausa, minimo, animada


def montar(escenas, destino, trabajo):
    import imageio_ffmpeg
    os.makedirs(trabajo, exist_ok=True)
    params, pcm, duraciones = None, [], []
    for i, e in enumerate(escenas):
        datos_voz = b""
        if e.voz:
            ruta = os.path.join(trabajo, f"voz_{i:02d}.wav")
            sintetizar(e.voz, ruta)
            p, datos_voz = leer_wav(ruta)
            params = params or p
        dur = max(e.minimo, (len(datos_voz) / (params.sampwidth * params.nchannels * params.framerate) if datos_voz else 0) + e.pausa)
        bytes_seg = params.sampwidth * params.nchannels * params.framerate if params else 0
        if params:
            datos_voz += b"\x00" * (int(dur * bytes_seg) - len(datos_voz))
            datos_voz = datos_voz[:int(dur * bytes_seg) // params.sampwidth * params.sampwidth]
        pcm.append(datos_voz)
        duraciones.append(dur)
    audio = os.path.join(trabajo, "voz.wav")
    with wave.open(audio, "wb") as w:
        w.setparams(params)
        w.writeframes(b"".join(pcm))

    total = sum(duraciones)
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    proc = subprocess.Popen([ff, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                             "-r", str(FPS), "-i", "-", "-i", audio, "-c:v", "libx264", "-profile:v", "high",
                             "-pix_fmt", "yuv420p", "-crf", "26", "-c:a", "aac", "-b:a", "96k", "-ar", "48000",
                             "-shortest", "-movflags", "+faststart", destino], stdin=subprocess.PIPE)
    hecho = 0.0
    for e, dur in zip(escenas, duraciones):
        quieta = None
        for k in range(int(round(dur * FPS))):
            t = k / FPS
            if e.animada:
                img = e.animada(t, dur)
            else:
                if quieta is None:
                    quieta = e.imagen
                # entrada suave: la escena sube 40 px en los primeros 0,3 s
                desliz = int(40 * max(0, 1 - t / 0.3) ** 2)
                if desliz:
                    img = C.fondo_base(W, H)
                    img.paste(quieta.crop((0, 0, W, H - desliz)), (0, desliz))
                else:
                    img = quieta
            img = img.copy()
            dd = ImageDraw.Draw(img)
            dd.rectangle((0, H - 12, int(W * (hecho + t) / total), H), fill=C.CIAN)  # barra de progreso
            proc.stdin.write(img.tobytes())
        hecho += dur
    proc.stdin.close()
    proc.wait()
    if proc.returncode:
        raise RuntimeError("ffmpeg falló al montar el reel")
    return total


def cuenta_atras(texto, segundos, kicker):
    fondo, d = base(kicker)
    texto_grande(d, 460, texto, C.BLANCO, alto=420, maximo=140)
    fondo_lim = fondo.copy()

    def cuadro(t, dur):
        img = fondo_lim.copy()
        dd = ImageDraw.Draw(img)
        n = max(1, segundos - int(t))
        cx, cy = W // 2, 1250
        dd.ellipse((cx - 170, cy - 170, cx + 170, cy + 170), outline=C.CIAN, width=10)
        frac = (t % 1)
        dd.arc((cx - 170, cy - 170, cx + 170, cy + 170), start=-90, end=-90 + int(360 * (1 - frac)), fill=C.AMBAR, width=14)
        dd.text((cx, cy), str(n), font=C.fuente(C.DISPLAY, 210), fill=C.BLANCO, anchor="mm")
        return img
    return cuadro


# ---------------------------------------------------------------- formato 1: infraccion

def reel_infraccion(inf, gancho, destino):
    grav = inf["gravedad"].lower()
    color = C.GRAVEDAD.get(grav, C.CIAN)
    multa = C.cuantia_legible(inf["cuantia"])
    m = re.match(r"^(.*?) \((.*) con pronto pago\)$", multa)
    multa_corta, pronto = (m.group(1), m.group(2)) if m else (multa, "")
    referencia = re.sub(r"\s*opc\.\s*\w+", "", inf["referencia"])  # la opcion del codificado es interna
    esc = []

    img, d = base("¿CUÁNTO TE CAE?")
    y = texto_grande(d, 480, gancho, C.BLANCO, alto=700, maximo=132, minimo=70)
    C.pegatina(img, "¿Multa? ¿Puntos? ¿Quién sanciona?", (M - 6, y + 60), angulo=-3, tam=50)
    esc.append(Escena(img, gancho + " ¿Sabes cuánto te cae?", pausa=0.5))

    esc.append(Escena(None, "¿Leve, grave o muy grave? Piénsalo.", pausa=0, minimo=3.2,
                      animada=cuenta_atras("¿LEVE, GRAVE O MUY GRAVE?", 3, "PIÉNSALO")))

    img, d = base("LA RESPUESTA")
    y = 400
    d.rounded_rectangle((M, y, M + 560, y + 136), radius=68, fill=color)
    d.text((M + 280, y + 68), grav.upper(), font=C.fuente(C.DISPLAY, 76), fill=C.NAVY_TXT, anchor="mm")
    y += 200
    d.text((M, y), "MULTA", font=C.fuente(C.SEMI, 44), fill=C.GRIS)
    y = texto_grande(d, y + 56, multa_corta, C.CIAN, alto=330, maximo=210, minimo=90, fuente=C.DISPLAY, inter=1.0)
    if pronto:
        d.text((M, y), f"{pronto} con pronto pago", font=C.fuente(C.SEMI, 46), fill=C.TEXTO)
        y += 70
    if inf.get("puntos"):
        d.text((M, y + 10), f"y {inf['puntos']} puntos del carné", font=C.fuente(C.TIT, 92), fill=C.BLANCO)
        y += 130
    y += 40
    y = tarjeta_texto(d, y, inf["organo"], titulo="QUIÉN SANCIONA", barra=C.AMBAR, maximo=72) + 24
    tarjeta_texto(d, y, f"{inf['norma_media']} · {referencia}", titulo="DÓNDE LO DICE", maximo=46)
    voz = f"Es una infracción {grav}. " + (f"Multa de {multa}." if multa[:1].isdigit() else f"Sanción: {multa}.")
    if inf.get("puntos"):
        voz += f" Y te quitan {inf['puntos']} puntos."
    voz += f" ¿Y quién sanciona? {inf.get('organo_voz', inf['organo'])}. Lo dice {inf['norma_media']}, {referencia}."
    esc.append(Escena(img, voz, pausa=0.8))

    img, d = base("CODIFICADO DE INFRACCIONES")
    y = texto_grande(d, 460, "MÁS DE 2.400 INFRACCIONES CON SU MULTA Y QUIÉN SANCIONA.", C.BLANCO, alto=640, maximo=130)
    y = boton_app(d, y + 80)
    pie(d, "Envíaselo a tu compañero de opos")
    esc.append(Escena(img, "Tienes más de dos mil cuatrocientas infracciones, con su multa y quién sanciona, en la app. "
                           "Envíaselo a tu compañero de opos.", pausa=1.2))
    return montar(esc, destino, destino + "_trabajo")


# ---------------------------------------------------------------- formato 2: chuleta de ley

def consejos_ficha(ruta):
    import pymupdf
    lineas = [l.strip() for l in pymupdf.open(ruta)[0].get_text().splitlines() if l.strip()]
    out = []
    try:
        i = next(k for k, l in enumerate(lineas) if "TRAMPAS DE EXAMEN" in l.upper()) + 1
    except StopIteration:
        return out
    for l in lineas[i:]:
        if l.upper().startswith(("FUENTE", "MATERIAL DE ESTUDIO", "OPOSICIÓN")):
            break
        if re.match(r"^[^\w\s(¿¡«\"'+\-–]", l):
            out.append([re.sub(r"^[^\wÁÉÍÓÚÑ¿¡«\"(]+", "", l).strip(), ""])
        elif out:
            out[-1][1] += " " + l
    return [(I_limpiar(a), I_limpiar(b)) for a, b in out if a and b]


def I_limpiar(t):
    t = re.sub(r"\s+", " ", t).strip()
    return re.sub(r"(\w)([–-]) (\w)", lambda m: m.group(1) + (m.group(2) if m.group(1).isdigit() else "") + m.group(3), t)


def de(t):
    """«de el Código Penal» -> «del Código Penal»."""
    return re.sub(r"\b(de|DE) (el|EL) ", lambda m: ("del " if m.group(1) == "de" else "DEL "), t)


def reel_chuleta(carpeta_ley, pdf, ley, destino):
    ruta = os.path.join(I.FICHAS, carpeta_ley, pdf)
    ficha, tema, _ = I.leer_ficha(ruta)
    trampas = consejos_ficha(ruta)[:3]
    n = len(trampas)
    doc = ficha.resize((W - 80, int((W - 80) * ficha.height / ficha.width)))
    esc = []

    img, d = base(f"CHULETA · {ley.upper()}")
    y = texto_grande(d, 330, de(f"{n} TRAMPAS DE {ley.upper()} QUE CAEN EN EL EXAMEN"), C.BLANCO, alto=470, maximo=112)
    y = texto_grande(d, y + 10, tema, C.CIAN, alto=120, maximo=50, minimo=34, fuente=C.SEMI, inter=1.15)
    trozo = doc.crop((0, 0, doc.width, min(doc.height, H - y - 260)))
    d.rounded_rectangle((34, y + 34, W - 34, y + 40 + trozo.height + 6), radius=18, fill=C.CIAN)
    img.paste(trozo, (40, y + 40))
    esc.append(Escena(img, de(f"{n} trampas de {ley} que caen en el examen. Guárdalo."), pausa=0.4))

    for k, (tit, cuerpo) in enumerate(trampas, 1):
        img, d = base(f"TRAMPA {k} DE {n}")
        # la ficha de fondo, a la altura de la seccion de consejos (abajo), atenuada
        fondo = doc.crop((0, 0, doc.width, min(doc.height, H - 420))).point(lambda v: int(v * 0.30))
        img.paste(fondo, (40, 300))
        d = ImageDraw.Draw(img)
        y = texto_grande(d, 420, tit, C.CIAN, alto=420, maximo=130, minimo=60)
        tarjeta_texto(d, y + 50, cuerpo, maximo=62, minimo=36, alto_max=760)
        esc.append(Escena(img, f"Trampa {k}. {tit}. {cuerpo}", pausa=0.7))

    img, d = base("ESQUEMAS VISUALES")
    trozo = I.difuminar(ficha, 0.0).resize((W - 80, int((W - 80) * ficha.height / ficha.width))).crop((0, 0, W - 80, 700))
    img.paste(trozo, (40, 300))
    d = ImageDraw.Draw(img)
    I.candado(d, W // 2, 650, r=80)
    y = texto_grande(d, 1040, "LA FICHA COMPLETA Y LOS 45 TEMAS, EN LA APP", C.BLANCO, alto=250, maximo=86)
    boton_app(d, y + 40)
    pie(d, "Recursos > Supuestos > Esquemas visuales")
    esc.append(Escena(img, "La ficha completa, y las de los cuarenta y cinco temas, están en la app. Guárdalo para repasar.", pausa=1.2))
    return montar(esc, destino, destino + "_trabajo")


# ---------------------------------------------------------------- formato 3: supuesto resuelto

def frases(t):
    return [f.strip() for f in re.split(r"(?<=[.!?])\s+", re.sub(r"\s+", " ", t)) if f.strip()]


def trocear(t, maximo):
    """Frases agrupadas en bloques de <= maximo caracteres (una pantalla cada uno)."""
    bloques, actual = [], ""
    for f in frases(t):
        if actual and len(actual) + len(f) > maximo:
            bloques.append(actual)
            actual = f
        else:
            actual = (actual + " " + f).strip()
    if actual:
        bloques.append(actual)
    return bloques


def reel_supuesto(p, destino, gancho=None):
    """gancho: escena corta que abre el video (la escribe Claude por tandas); si no hay, la primera frase."""
    conv = p.get("convocatoria", "")
    fr = frases(p["enunciado"])
    if gancho:
        resto = p["enunciado"]
    else:
        gancho, resto = fr[0], " ".join(fr[1:])
    esc = []

    img, d = base("SUPUESTO PRÁCTICO" + (f" · {conv.upper()}" if conv else ""))
    y = texto_grande(d, 360, "¿QUÉ HARÍAS TÚ?", C.CIAN, alto=140, maximo=120)
    y = texto_grande(d, y + 30, gancho, C.BLANCO, alto=820, maximo=110, minimo=56, inter=1.1)
    C.pegatina(img, "Supuesto real de examen", (M - 6, min(y + 50, H - 330)), angulo=-3, tam=40)
    esc.append(Escena(img, gancho, pausa=0.5))

    for b in trocear(resto, 330):
        img, d = base("EL CASO")
        tarjeta_texto(d, 380, b, maximo=60, minimo=38, alto_max=1250)
        esc.append(Escena(img, b, pausa=0.4))

    img, d = base("LA PREGUNTA")
    texto_grande(d, 420, p["pregunta"], C.CIAN, alto=1000, maximo=110, minimo=56, inter=1.1)
    esc.append(Escena(img, p["pregunta"], pausa=0.3))

    esc.append(Escena(None, "Pausa el vídeo y piénsalo.", pausa=0, minimo=5.2,
                      animada=cuenta_atras("PAUSA EL VÍDEO Y PIÉNSALO", 5, "TU TURNO")))

    for i, b in enumerate(trocear(p["justificacion"], 360)):
        img, d = base("LA SOLUCIÓN" if i == 0 else "LA SOLUCIÓN (SIGUE)")
        tarjeta_texto(d, 380, b, barra=C.VERDE, maximo=60, minimo=38, alto_max=1250)
        esc.append(Escena(img, ("La solución. " if i == 0 else "") + b, pausa=0.4))

    img, d = base("SUPUESTOS RESUELTOS")
    y = texto_grande(d, 460, "MÁS DE 1.400 SUPUESTOS DE EXAMEN RESUELTOS PASO A PASO.", C.BLANCO, alto=640, maximo=130)
    y = boton_app(d, y + 80)
    pie(d, "Envíaselo a tu compañero de opos")
    esc.append(Escena(img, "Tienes más de mil cuatrocientos supuestos de examen resueltos en la app. "
                           "Envíaselo a tu compañero de opos.", pausa=1.2))
    return montar(esc, destino, destino + "_trabajo")


# ---------------------------------------------------------------- muestras

if __name__ == "__main__":
    if sys.argv[1] == "muestra":
        tipo = sys.argv[2]
        salida = os.path.join(AQUI, "..", "salida", f"muestra_voz_{tipo}.mp4")
        if tipo == "infraccion":
            inf = next(i for i in datos.cargar_infracciones() if i["id"].endswith(sys.argv[3]))
            dur = reel_infraccion(inf, sys.argv[4], salida)
        elif tipo == "chuleta":
            carpeta, pdf = sys.argv[3].split("/")
            ley = next((l for c, l, _ in I.LEYES if c == carpeta), carpeta)
            dur = reel_chuleta(carpeta, pdf, ley, salida)
        else:
            p = next(x for x in datos.cargar("corta") if x["id"].endswith(sys.argv[3]))
            dur = reel_supuesto(p, salida, sys.argv[4] if len(sys.argv) > 4 else None)
        print(f"{salida}: {dur:.1f} s")
