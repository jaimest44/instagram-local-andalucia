"""Guarda la clave de Azure AI Speech (voz de los reels) en este PC y prueba que funciona.

    python configurar_voz.py

La clave se pide sin mostrarla en pantalla y se guarda cifrada con la protección de datos de
Windows (DPAPI) de tu usuario, en %LOCALAPPDATA%\\publicador-instagram\\azure_voz.bin.
No va a GitHub: los reels se generan en este PC (actualizar_cola.bat).
"""
import getpass
import json
import os
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from instagram_login import _dpapi  # noqa: E402

ALMACEN = os.path.join(os.environ.get("LOCALAPPDATA", "."), "publicador-instagram", "azure_voz.bin")


def leer():
    """{'clave': ..., 'region': ...} o None si no esta configurada."""
    if not os.path.exists(ALMACEN):
        return None
    with open(ALMACEN, "rb") as f:
        return json.loads(_dpapi(f.read(), cifrar=False).decode())


def probar(clave, region):
    ssml = ("<speak version='1.0' xml:lang='es-ES'><voice name='es-ES-AlvaroNeural'>"
            "Prueba de la voz de los reels.</voice></speak>").encode("utf-8")
    req = urllib.request.Request(f"https://{region}.tts.speech.microsoft.com/cognitiveservices/v1", data=ssml,
                                 headers={"Ocp-Apim-Subscription-Key": clave, "Content-Type": "application/ssml+xml",
                                          "X-Microsoft-OutputFormat": "riff-24khz-16bit-mono-pcm",
                                          "User-Agent": "localandalucia-reels"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return len(r.read())


def configurar():
    print("Pega la CLAVE 1 de tu recurso de Voz de Azure (no se verá al escribir) y pulsa Enter:")
    clave = getpass.getpass("Clave: ").strip()
    region = input("Región (Ubicación/Región del recurso, p. ej. westeurope): ").strip().lower().replace(" ", "") or "westeurope"
    try:
        n = probar(clave, region)
    except urllib.error.HTTPError as e:
        print(f"\nAzure ha rechazado la clave ({e.code}). Revisa que sea la clave del recurso de Voz y la región correcta.")
        sys.exit(1)
    os.makedirs(os.path.dirname(ALMACEN), exist_ok=True)
    with open(ALMACEN, "wb") as f:
        f.write(_dpapi(json.dumps({"clave": clave, "region": region}).encode(), cifrar=True))
    print(f"\nListo: la voz de Azure funciona ({n} bytes de prueba) y la clave queda guardada en este PC.")


if __name__ == "__main__":
    configurar()
