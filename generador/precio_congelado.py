"""Reel 9:16 con voz: «9,99 €/mes congelado si te suscribes antes del 31/12/2026» (para las dos cuentas y Meta Ads).
Quien se suscribe antes de 2027 mantiene 9,99 €/mes mientras siga suscrito. Nunca se dice el precio de 2027.

    python precio_congelado.py la    <carpeta de salida>
    python precio_congelado.py admin <carpeta de salida>
"""
import importlib.util
import json
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
ADMIN = os.path.join(AQUI, "..", "..", "..", "ADMINISTRATIVO LOCAL ANDALUCIA", "40. INSTAGRAM", "generador")

marca, salida = sys.argv[1], sys.argv[2]
if marca == "admin":  # mismo motor de video, con la marca (logo, colores, URL) de Administrativo
    sys.path.insert(0, ADMIN)
    spec = importlib.util.spec_from_file_location("carrusel", os.path.join(ADMIN, "carrusel.py"))
    modulo = importlib.util.module_from_spec(spec)
    sys.modules["carrusel"] = modulo
    spec.loader.exec_module(modulo)
    sys.path.remove(ADMIN)
sys.path.insert(0, AQUI)
import reels_voz as R  # noqa: E402

C = R.C
W, M = R.W, R.M


def escenas():
    esc = []
    img, d = R.base("PRECIO DE LANZAMIENTO")
    y = R.texto_grande(d, 470, "TU PRECIO, CONGELADO", C.BLANCO, alto=170, maximo=150)
    y = R.texto_grande(d, y + 20, "9,99 €/MES", C.CIAN, alto=340, maximo=320, minimo=140, fuente=C.DISPLAY, inter=1.0)
    y = R.texto_grande(d, y + 30, "MIENTRAS SIGAS SUSCRITO", C.BLANCO, alto=150, maximo=120)
    C.pegatina(img, "Solo hasta el 31 de diciembre", (M - 6, y + 70), angulo=-3, tam=62)
    R.texto_grande(d, y + 320, "Regístrate gratis y pruébala antes de pagar", C.TEXTO, alto=150, maximo=54, minimo=40, fuente=C.SEMI)
    esc.append(R.Escena(img, "Nueve con noventa y nueve al mes, congelado mientras sigas suscrito. "
                             "Solo si te suscribes antes del 31 de diciembre.", pausa=0.5))

    img, d = R.base("CÓMO FUNCIONA")
    y = R.texto_grande(d, 380, "ASÍ FUNCIONA EL PRECIO CONGELADO", C.BLANCO, alto=260, maximo=110) + 50
    pasos = ["Te suscribes al Plan Completo antes del 31/12/2026.",
             "Pagas 9,99 € al mes.",
             "En 2027 el precio sube… pero tú sigues pagando 9,99 € mientras mantengas tu suscripción."]
    for i, p in enumerate(pasos, 1):
        f, l, t = C.ajustar(d, p, C.TXT_SB, W - 2 * M - 170, 360, 62, 40, 1.3)
        alto = max(200, len(l) * int(t * 1.3) + 80)
        C.tarjeta(d, (M, y, W - M, y + alto))
        d.ellipse((M + 34, y + alto // 2 - 44, M + 122, y + alto // 2 + 44), fill=C.AMBAR)
        d.text((M + 78, y + alto // 2), str(i), font=C.fuente(C.DISPLAY, 56), fill=C.NAVY_TXT, anchor="mm")
        C.escribir(d, (M + 150, y + (alto - len(l) * int(t * 1.3)) // 2), l, f, t, C.BLANCO, 1.3)
        y += alto + 26
    esc.append(R.Escena(img, "Te suscribes antes del 31 de diciembre y pagas nueve con noventa y nueve al mes. "
                             "En 2027 el precio sube, pero tú sigues pagando lo mismo mientras mantengas tu suscripción.",
                        pausa=0.6))

    img, d = R.base("QUÉ INCLUYE")
    y = R.texto_grande(d, 420, "TODO PARA APROBAR, EN EL MÓVIL", C.BLANCO, alto=300, maximo=140)
    y += 80
    for item in C.LISTA_CTA[:3]:
        cx, cy = M + 30, y + 40
        d.ellipse((cx - 28, cy - 28, cx + 28, cy + 28), fill=C.CIAN)
        d.line((cx - 13, cy, cx - 3, cy + 12, cx + 15, cy - 12), fill=C.NAVY_TXT, width=7)
        f, l, t = C.ajustar(d, item, C.TXT_SB, W - 2 * M - 90, 150, 60, 40, 1.2)
        C.escribir(d, (cx + 60, cy - len(l) * int(t * 1.2) // 2), l, f, t, C.BLANCO, 1.2)
        y += max(150, len(l) * int(t * 1.2) + 80)
    esc.append(R.Escena(img, "Exámenes oficiales resueltos, supuestos prácticos y mucho más, en el móvil.", pausa=0.5))

    img, d = R.base("PRUÉBALA GRATIS")
    y = R.texto_grande(d, 460, "REGÍSTRATE GRATIS Y PRUÉBALA ANTES DE PAGAR.", C.BLANCO, alto=620, maximo=140)
    y = R.boton_app(d, y + 60)
    R.texto_grande(d, y + 70, "9,99 €/mes congelado si te suscribes antes del 31/12", C.CIAN, alto=160, maximo=60, minimo=40, fuente=C.SEMI)
    R.pie(d, "Precio congelado mientras sigas suscrito")
    esc.append(R.Escena(img, "Regístrate gratis y pruébala antes de pagar. Enlace en la bio.", pausa=1.4))
    return esc


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
    dur = R.montar(escenas(), os.path.join(salida, "reel.mp4"), os.path.join(salida, "_trabajo"))
    import shutil
    shutil.rmtree(os.path.join(salida, "_trabajo"), ignore_errors=True)
    open(os.path.join(salida, "caption.txt"), "w", encoding="utf-8").write(caption())
    print(f"{salida}: {dur:.1f} s")
