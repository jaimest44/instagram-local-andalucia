"""«Comenta y te lo envío»: a quien comenta una palabra clave en una publicación de los últimos 7 días
le manda por mensaje privado el enlace de la app (respuesta privada de Instagram: una por comentario).

Se ejecuta en GitHub Actions (ver .github/workflows/responder.yml). Configuración en respuestas.json;
lo ya contestado queda en estado/respondidos.json.

    python responder.py            contesta lo pendiente
    python responder.py --simular  dice a quién contestaría, sin enviar nada
"""
import argparse
import datetime as dt
import json
import os
import re
import sys
import unicodedata

from publicar import ErrorAPI, REPO, api, leer_json

AQUI = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.path.join(AQUI, "respuestas.json")
RESPONDIDOS = os.path.join(REPO, "estado", "respondidos.json")
VENTANA = dt.timedelta(days=7)  # Instagram solo deja responder en privado a comentarios de menos de 7 días


def normalizar(texto):
    sin_tildes = "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")
    return re.sub(r"[^A-Z0-9 ]+", " ", sin_tildes.upper())


def palabra_clave(texto, palabras):
    """La primera palabra clave que aparece como palabra suelta en el comentario, o None."""
    trozos = normalizar(texto).split()
    return next((p for p in palabras if normalizar(p).strip() in trozos), None)


def fecha(iso):
    return dt.datetime.strptime(iso[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=dt.timezone.utc)


def guardar(respondidos):
    with open(RESPONDIDOS, "w", encoding="utf-8") as f:
        json.dump(respondidos, f, ensure_ascii=False, indent=1, sort_keys=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--simular", action="store_true")
    a = ap.parse_args()

    config = leer_json(CONFIG, {})
    if not config.get("activo"):
        a.simular = True  # hasta activarlo en respuestas.json, solo se mira
    respondidos = leer_json(RESPONDIDOS, {})
    yo = os.environ["IG_USER_ID"]
    cuenta = api("GET", "me", fields="user_id,username")
    mi_usuario = cuenta.get("username", "").lower()
    ahora = dt.datetime.now(dt.timezone.utc)

    medios = api("GET", "me/media", fields="id,timestamp,caption", limit=30).get("data", [])
    recientes = [m for m in medios if ahora - fecha(m["timestamp"]) < VENTANA]
    vistos = enviados = 0
    for m in recientes:
        comentarios = api("GET", f"{m['id']}/comments", fields="id,text,timestamp,username", limit=50).get("data", [])
        for c in comentarios:
            vistos += 1
            if c["id"] in respondidos or c.get("username", "").lower() == mi_usuario:
                continue
            if ahora - fecha(c["timestamp"]) >= VENTANA:
                continue
            clave = palabra_clave(c.get("text", ""), config["palabras"])
            if not clave:
                continue
            texto = config["palabras"][clave]
            if a.simular:
                print(f"Contestaría a un comentario con «{clave}» en {m['id']} ({c['timestamp'][:16]})")
                continue
            try:
                api("POST", f"{yo}/messages", recipient=json.dumps({"comment_id": c["id"]}),
                    message=json.dumps({"text": texto}, ensure_ascii=False))
            except ErrorAPI as e:
                print(f"No se pudo contestar el comentario {c['id']}: {e}", file=sys.stderr)
                respondidos[c["id"]] = "error " + ahora.isoformat()[:16]
                continue
            respondidos[c["id"]] = ahora.isoformat()[:16]
            enviados += 1
            if config.get("respuesta_publica"):
                try:
                    api("POST", f"{c['id']}/replies", message=config["respuesta_publica"])
                except ErrorAPI as e:
                    print(f"Mensaje enviado, pero no la respuesta pública en {c['id']}: {e}", file=sys.stderr)
    if not a.simular:
        guardar(respondidos)
    print(f"{len(recientes)} publicaciones de los últimos 7 días, {vistos} comentarios leídos, {enviados} mensajes enviados.")


if __name__ == "__main__":
    main()
