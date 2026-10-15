"""Publicar con la "API de Instagram con inicio de sesión de Instagram" (sin página de Facebook).

    python instagram_login.py configurar   # una vez: pide el token y lo guarda en GitHub
    python instagram_login.py renovar      # cada semana (actualizar_cola.bat): alarga el token 60 días

El token se pide sin mostrarlo en pantalla. Se guarda:
  - en GitHub, como secreto del repositorio (lo usa el publicador);
  - en este PC, cifrado con la protección de datos de Windows (DPAPI) de tu usuario,
    para poder renovarlo antes de que caduque. Solo tu usuario de Windows puede descifrarlo.
"""
import ctypes
import ctypes.wintypes as wt
import getpass
import json
import os
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

AQUI = os.path.dirname(os.path.abspath(__file__))
HOST = "https://graph.instagram.com"
ALMACEN = os.path.join(os.environ.get("LOCALAPPDATA", AQUI), "publicador-instagram",
                       "token_" + os.path.basename(os.path.dirname(AQUI)).replace(" ", "_") + ".bin")

with open(os.path.join(AQUI, "cuenta.txt"), encoding="utf-8") as _f:
    ESPERADA = _f.read().strip().lstrip("@").lower()


# ---------------------------------------------------------------- DPAPI (cifrado de Windows)

class _Blob(ctypes.Structure):
    _fields_ = [("cbData", wt.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]


def _dpapi(datos, cifrar):
    entrada = _Blob(len(datos), ctypes.cast(ctypes.create_string_buffer(datos, len(datos)), ctypes.POINTER(ctypes.c_char)))
    salida = _Blob()
    funcion = ctypes.windll.crypt32.CryptProtectData if cifrar else ctypes.windll.crypt32.CryptUnprotectData
    if not funcion(ctypes.byref(entrada), None, None, None, None, 0, ctypes.byref(salida)):
        raise OSError("No se pudo cifrar/descifrar el token con DPAPI")
    try:
        return ctypes.string_at(salida.pbData, salida.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(salida.pbData)


def guardar_local(token):
    os.makedirs(os.path.dirname(ALMACEN), exist_ok=True)
    with open(ALMACEN, "wb") as f:
        f.write(_dpapi(token.encode(), cifrar=True))


def leer_local():
    with open(ALMACEN, "rb") as f:
        return _dpapi(f.read(), cifrar=False).decode()


# ---------------------------------------------------------------- API y GitHub

def get(ruta, **params):
    url = f"{HOST}/{ruta}?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(url, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        try:
            msg = json.loads(e.read().decode(errors="replace")).get("error", {}).get("message", "")
        except ValueError:
            msg = ""
        sys.exit(f"Error de Instagram: {msg or e.code}")


def gh(*args, entrada=None):
    subprocess.run(["gh", *args], cwd=os.path.dirname(AQUI), input=entrada, check=True)


def cuenta_del_token(token):
    yo = get("me", fields="user_id,username", access_token=token)
    return str(yo.get("user_id") or yo.get("id")), yo.get("username", "")


def guardar_en_github(token, user_id):
    gh("secret", "set", "IG_USER_ID", entrada=user_id.encode())
    gh("secret", "set", "IG_ACCESS_TOKEN", entrada=token.encode())
    gh("variable", "set", "GRAPH_HOST", "--body", "graph.instagram.com")


# ---------------------------------------------------------------- comandos

def configurar():
    print(f"Configuración de @{ESPERADA} con inicio de sesión de Instagram\n")
    token = getpass.getpass("Token de Instagram (no se verá al escribir): ").strip()
    user_id, usuario = cuenta_del_token(token)
    print(f"El token es de @{usuario}.")
    if usuario.lower() != ESPERADA:
        sys.exit(f"Esta carpeta publica en @{ESPERADA}, no en @{usuario}. No se ha guardado nada.")
    token = _intentar_renovar(token) or token
    guardar_en_github(token, user_id)
    guardar_local(token)
    print(f"\nListo. @{usuario} configurada en GitHub y token guardado cifrado en este PC para renovarlo cada semana.")


def _intentar_renovar(token):
    """Devuelve el token renovado, o None si aun no se puede (los recien generados no se renuevan
    hasta pasadas 24 h; no es un error, la tarea semanal lo hara)."""
    url = f"{HOST}/refresh_access_token?" + urllib.parse.urlencode(
        {"grant_type": "ig_refresh_token", "access_token": token})
    try:
        with urllib.request.urlopen(url, timeout=60) as r:
            return json.load(r).get("access_token")
    except urllib.error.HTTPError:
        return None


def renovar():
    if not os.path.exists(ALMACEN):
        print("No hay token guardado en este PC: ejecuta primero 'python instagram_login.py configurar'.")
        return
    token = leer_local()
    respuesta = get("refresh_access_token", grant_type="ig_refresh_token", access_token=token)
    nuevo = respuesta.get("access_token")
    if not nuevo:
        sys.exit("Instagram no devolvió un token nuevo.")
    user_id, usuario = cuenta_del_token(nuevo)
    if usuario.lower() != ESPERADA:
        sys.exit(f"El token renovado es de @{usuario}, no de @{ESPERADA}. No se ha cambiado nada.")
    guardar_en_github(nuevo, user_id)
    guardar_local(nuevo)
    dias = int(respuesta.get("expires_in", 0)) // 86400
    print(f"Token de @{usuario} renovado: válido {dias} días más.")


if __name__ == "__main__":
    {"configurar": configurar, "renovar": renovar}.get(sys.argv[1] if len(sys.argv) > 1 else "", lambda: sys.exit(__doc__))()
