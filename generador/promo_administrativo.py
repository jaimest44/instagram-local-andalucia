"""Post puntual de @localandalucia presentando la cuenta hermana @administrativo_local_andalucia.

    python promo_administrativo.py 2026-10-25     # lo deja en la cola como publicacion de la noche de ese dia

Si ese dia ya tenia un carrusel, ese carrusel vuelve a quedar disponible para otro dia.
"""
import json
import os
import sys

from PIL import Image

import carrusel as C

AQUI = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(AQUI, ".."))
ADMIN = os.path.abspath(os.path.join(REPO, "..", "..", "ADMINISTRATIVO LOCAL ANDALUCIA", "40. INSTAGRAM"))

CAPTION = """¿Opositas también a Administrativo de Ayuntamiento? 👀

Muchos opositores a Policía Local se presentan además a las plazas de Administrativo y Auxiliar de los Ayuntamientos andaluces. Para ellos hemos abierto @administrativo_local_andalucia.

Cada día, dos preguntas reales de exámenes oficiales de Ayuntamientos de Andalucía, con la solución y el artículo exacto.

Síguela y compártela con quien esté preparando Administrativo 🙌

La app para Administrativo: app.administrativolocal.com

#oposicionesandalucia #administrativo #policialocal #oposiciones #ayuntamiento"""


def slide_portada():
    img, d = C.lienzo("NUEVA CUENTA")
    y = C.TOP + 20
    for texto, color in (("¿OPOSITAS", C.BLANCO), ("TAMBIÉN A", C.BLANCO), ("ADMINISTRATIVO?", C.CIAN)):
        f, _, _ = C.ajustar(d, texto, C.TIT, C.W - 2 * C.M, 110, 96, 50, 1.0)
        d.text((C.M, y), texto, font=f, fill=color)
        y += 108
    y += 30
    sub = ("Hemos abierto @administrativo_local_andalucia: preguntas reales de exámenes de "
           "Ayuntamientos andaluces, cada día, con la solución y el artículo.")
    f2, l2, t2 = C.ajustar(d, sub, C.TXT, C.W - 2 * C.M, 200, 38, 26, 1.35)
    y = C.escribir(d, (C.M, y), l2, f2, t2, C.TEXTO, 1.35) + 40
    # muestra de un post real de la cuenta de Administrativo
    muestra = sorted(x for x in os.listdir(os.path.join(ADMIN, "cola")) if len(x) == 10)[0]
    prev = Image.open(os.path.join(ADMIN, "cola", muestra, "01.jpg")).convert("RGB")
    alto = C.LIMITE - y - 10
    prev = prev.resize((int(prev.width * alto / prev.height), alto), Image.LANCZOS)
    x = (C.W - prev.width) // 2
    d.rounded_rectangle((x - 8, y - 8, x + prev.width + 8, y + alto + 8), radius=18, fill=C.CIAN)
    img.paste(prev, (x, y))
    C.pie(d, "Desliza  →")
    return img


def slide_cta():
    img, d = C.lienzo("NUEVA CUENTA")
    y = C.TOP + 40
    for texto, color in (("SÍGUELA EN", C.BLANCO), ("@ADMINISTRATIVO_", C.CIAN), ("LOCAL_ANDALUCIA", C.CIAN)):
        f, _, _ = C.ajustar(d, texto, C.TIT, C.W - 2 * C.M, 110, 92, 46, 1.0)
        d.text((C.M, y), texto, font=f, fill=color)
        y += 104
    y += 40
    puntos = ["2 preguntas oficiales al día", "Supuestos prácticos resueltos",
              "Exámenes de Cádiz, Sevilla, Granada, Málaga, Córdoba…", "Y compártela con quien prepare Administrativo"]
    f3 = C.fuente(C.TXT_SB, 36)
    for p in puntos:
        d.ellipse((C.M, y + 14, C.M + 18, y + 32), fill=C.CIAN)
        lineas = C.envolver(d, p, f3, C.W - 2 * C.M - 50)
        y = C.escribir(d, (C.M + 40, y), lineas, f3, 36, C.BLANCO, 1.3) + 26
    C.pie(d, "Enlace a la app de Administrativo en el texto")
    return img


def main():
    fecha = sys.argv[1]
    carpeta = os.path.join(REPO, "cola", fecha)
    usadas_p = os.path.join(REPO, "estado", "usadas.json")
    usadas = json.load(open(usadas_p, encoding="utf-8"))
    viejo = os.path.join(carpeta, "meta.json")
    if os.path.exists(viejo):  # el carrusel que habia ese dia vuelve a estar disponible
        meta_vieja = json.load(open(viejo, encoding="utf-8"))
        usadas.pop(meta_vieja.get("id"), None)
        for f in os.listdir(carpeta):
            os.remove(os.path.join(carpeta, f))
    os.makedirs(carpeta, exist_ok=True)
    imgs = [slide_portada(), slide_cta()]
    nombres = []
    for i, img in enumerate(imgs, 1):
        C.puntos(img, i - 1, len(imgs))
        n = f"{i:02d}.jpg"
        img.save(os.path.join(carpeta, n), "JPEG", quality=90, optimize=True, progressive=True)
        nombres.append(n)
    open(os.path.join(carpeta, "caption.txt"), "w", encoding="utf-8").write(CAPTION)
    meta = {"fecha": fecha, "franja": "noche", "id": f"promo-administrativo-{fecha}", "formato": "promo",
            "convocatoria": "", "tema": "promo", "caso": "", "imagenes": nombres}
    json.dump(meta, open(os.path.join(carpeta, "meta.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump(usadas, open(usadas_p, "w", encoding="utf-8"), ensure_ascii=False, indent=1, sort_keys=True)
    print(carpeta)


if __name__ == "__main__":
    main()
