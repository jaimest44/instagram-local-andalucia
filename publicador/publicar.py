"""Publica en Instagram el carrusel del dia que esta en cola/AAAA-MM-DD.

Se ejecuta en GitHub Actions (ver .github/workflows/publicar.yml). Solo usa la libreria estandar.

Variables de entorno (secretos del repositorio):
    IG_USER_ID       id de la cuenta de Instagram profesional
    IG_ACCESS_TOKEN  token con permiso instagram_content_publish
Opcionales:
    GRAPH_HOST       graph.facebook.com (por defecto) o graph.instagram.com
    GRAPH_VERSION    v24.0 por defecto
    URL_BASE         de donde descarga Instagram las imagenes; por defecto el raw de GitHub

    python publicar.py              publica lo pendiente de hoy
    python publicar.py --comprobar  solo comprueba que el token funciona y que hay cola
    python publicar.py --simular    dice que publicaria, sin publicar
    python publicar.py --formato_facebook  dice si cada video de la cola ira a Facebook como Reel
                                           o como video normal (no usa el token ni publica nada)
    python publicar.py --probar_reel_facebook  sube el proximo Reel corto a la pagina de Facebook como
                                               BORRADOR (comprueba el permiso de Reels; no publica nada)

En la pagina de Facebook, los videos de 90 s o menos se publican como Reel; los mas largos, como video normal.
"""
import argparse
import datetime as dt
import json
import os
import re
import struct
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo

AQUI = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(AQUI, ".."))
COLA = os.path.join(REPO, "cola")
PUBLICADAS = os.path.join(REPO, "estado", "publicadas.json")

HOST = os.environ.get("GRAPH_HOST", "graph.facebook.com")
VERSION = os.environ.get("GRAPH_VERSION", "v24.0")
AVISO_COLA = 7  # avisa cuando queden menos dias preparados
HORA_PUBLICACION = dt.time(20, 30)  # hora de Madrid; antes de esta hora no se publica
# GitHub lanza los cron con horas de retraso: una ejecucion de madrugada aun publica el dia anterior
HORA_RECUPERACION = dt.time(6, 0)


class ErrorAPI(Exception):
    def __init__(self, mensaje="", codigo=None):
        super().__init__(mensaje)
        self.codigo = codigo  # HTTP status of the failed response, when there was one


def api(metodo, ruta, **params):
    params["access_token"] = os.environ["IG_ACCESS_TOKEN"]
    url = f"https://{HOST}/{VERSION}/{ruta}"
    datos = urllib.parse.urlencode(params).encode()
    if metodo == "GET":
        req = urllib.request.Request(url + "?" + datos.decode())
    else:
        req = urllib.request.Request(url, data=datos, method="POST")
    for intento in range(4):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            cuerpo = e.read().decode(errors="replace")
            try:
                err = json.loads(cuerpo).get("error", {})
            except ValueError:
                err = {}
            # errores transitorios: reintenta
            if e.code >= 500 or err.get("is_transient") or err.get("code") in (1, 2, 4, 17, 32, 613):
                time.sleep(10 * (intento + 1))
                continue
            # nunca imprimir el token
            raise ErrorAPI(f"{e.code} {err.get('message', cuerpo)[:400]}") from None
        except urllib.error.URLError:
            time.sleep(10 * (intento + 1))
    raise ErrorAPI(f"La API no responde tras varios intentos ({ruta})")


def esperar_contenedor(cid, maximo=180):
    inicio = time.time()
    while time.time() - inicio < maximo:
        estado = api("GET", cid, fields="status_code,status").get("status_code")
        if estado == "FINISHED":
            return
        if estado in ("ERROR", "EXPIRED"):
            raise ErrorAPI(f"El contenedor {cid} quedó en estado {estado}")
        time.sleep(5)
    raise ErrorAPI(f"El contenedor {cid} no terminó de procesarse")


def url_base():
    if os.environ.get("URL_BASE"):
        return os.environ["URL_BASE"].rstrip("/")
    repo = os.environ["GITHUB_REPOSITORY"]
    rama = os.environ.get("GITHUB_REF_NAME", "main")
    return f"https://raw.githubusercontent.com/{repo}/{rama}/cola"


def leer_json(ruta, defecto):
    try:
        with open(ruta, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return defecto


def pendientes(hoy, publicadas):
    if not os.path.isdir(COLA):
        return []
    dias = sorted(d for d in os.listdir(COLA) if os.path.isfile(os.path.join(COLA, d, "meta.json")))
    # la fecha son los 10 primeros caracteres ("2026-10-23_mediodia" es del dia 23)
    return [d for d in dias if d[:10] <= hoy.isoformat() and d not in publicadas]


# Dos publicaciones al dia: (sufijo de la carpeta en cola/, hora de Madrid a partir de la que se publica)
FRANJAS = [("_manana", dt.time(11, 0)), ("_mediodia", dt.time(14, 0)), ("_tarde", dt.time(18, 0)), ("", None)]  # None = HORA_PUBLICACION (noche)
# _manana: serie de esquemas visuales (martes y viernes); _tarde: videos propios (p. ej. supuestos en dibujos); solo se publica si hay carpeta ese dia


def franja_actual(ahora):
    """Sufijo de la franja que toca a esta hora, o None si aun no toca ninguna."""
    sufijo = None
    for suf, hora in FRANJAS:
        if ahora.time() >= (hora or HORA_PUBLICACION):
            sufijo = suf
    return sufijo


def comprobar_cuenta():
    """Para en seco si las credenciales son de otra cuenta que la de este repositorio (cuenta.txt)."""
    with open(os.path.join(AQUI, "cuenta.txt"), encoding="utf-8") as f:
        esperada = f.read().strip().lstrip("@").lower()
    real = api("GET", os.environ["IG_USER_ID"], fields="username").get("username", "")
    if real.lower() != esperada:
        raise ErrorAPI(f"Las credenciales guardadas son de @{real}, pero este repositorio publica en @{esperada}. "
                       f"No se publica nada. Repite publicador/configurar_token.py en la carpeta correcta.")
    return real


def publicar_reel(dia, meta, texto, base):
    """Publica el reel.mp4 de la carpeta como Reel (y lo comparte tambien en el feed)."""
    ig = os.environ["IG_USER_ID"]
    cont = api("POST", f"{ig}/media", media_type="REELS", video_url=f"{base}/{meta['reel']}",
               caption=texto, share_to_feed="true")
    esperar_contenedor(cont["id"], maximo=600)  # el video tarda mas en procesarse
    pub = api("POST", f"{ig}/media_publish", creation_id=cont["id"])
    info = api("GET", pub["id"], fields="permalink")
    return {"media_id": pub["id"], "permalink": info.get("permalink", ""), "tipo": "reel",
            "publicado": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "id_pregunta": meta.get("id")}


def publicar(dia):
    carpeta = os.path.join(COLA, dia)
    meta = leer_json(os.path.join(carpeta, "meta.json"), {})
    with open(os.path.join(carpeta, "caption.txt"), encoding="utf-8") as f:
        texto = f.read()
    ig = os.environ["IG_USER_ID"]
    base = f"{url_base()}/{dia}"
    comprobar_cuenta()
    if meta.get("reel"):
        return publicar_reel(dia, meta, texto, base)

    hijos = []
    for img in meta["imagenes"]:
        r = api("POST", f"{ig}/media", image_url=f"{base}/{img}", is_carousel_item="true")
        hijos.append(r["id"])
    for h in hijos:
        esperar_contenedor(h)
    carrusel = api("POST", f"{ig}/media", media_type="CAROUSEL", children=",".join(hijos), caption=texto)
    esperar_contenedor(carrusel["id"])
    pub = api("POST", f"{ig}/media_publish", creation_id=carrusel["id"])
    info = api("GET", pub["id"], fields="permalink")
    return {"media_id": pub["id"], "permalink": info.get("permalink", ""),
            "publicado": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "id_pregunta": meta.get("id")}


NECESARIOS = ["instagram_basic", "instagram_content_publish", "pages_read_engagement", "pages_show_list"]


def diagnosticar():
    """Lista los permisos del token guardado y dice cuales faltan para publicar."""
    token = os.environ["IG_ACCESS_TOKEN"]
    try:
        info = api("GET", "debug_token", input_token=token).get("data", {})
    except ErrorAPI as e:
        if "pages_read_engagement" in str(e):
            print("::error::El token guardado no tiene pages_read_engagement (ni puede consultarse a sí mismo). "
                  "Genera uno nuevo y vuelve a ejecutar publicador/configurar_token.py.")
        else:
            print(f"::error::No se pudo consultar el token: {e}")
        sys.exit(1)
    permisos = sorted(info.get("scopes", []))
    print(f"Tipo de token: {info.get('type')}  ·  válido: {info.get('is_valid')}  ·  "
          f"caduca: {'nunca' if not info.get('expires_at') else dt.datetime.fromtimestamp(info['expires_at'])}")
    print("Permisos concedidos:", ", ".join(permisos) or "(ninguno)")
    for g in info.get("granular_scopes", []):
        print(f"  {g.get('scope')}: {len(g.get('target_ids', []))} recursos")
    faltan = [p for p in NECESARIOS if p not in permisos]
    if faltan:
        print(f"::error::Al token le faltan permisos para publicar: {', '.join(faltan)}")
        sys.exit(1)
    print("Tiene todos los permisos necesarios para publicar.")


# ---------------------------------------------------------------- Facebook (pagina)

def _fb_enviar(req, intentos=3):
    """Send a Facebook request, retrying server errors. The token is never printed."""
    for intento in range(intentos):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            cuerpo = e.read().decode(errors="replace")
            e.close()
            if e.code >= 500 and intento < intentos - 1:
                time.sleep(10 * (intento + 1))
                continue
            try:
                j = json.loads(cuerpo)
                j = j if isinstance(j, dict) else {}
                # Graph errors come in "error"; rupload.facebook.com errors come in "debug_info"
                msg = (j.get("error") or j.get("debug_info") or {}).get("message", cuerpo)
            except ValueError:
                msg = cuerpo
            raise ErrorAPI(f"Facebook {e.code}: {msg[:300]}", codigo=e.code) from None


def fb_api(metodo, ruta, host="graph.facebook.com", **params):
    """Llamada a la API de Facebook con el token de la PAGINA (secreto FB_PAGE_TOKEN)."""
    params["access_token"] = os.environ["FB_PAGE_TOKEN"]
    url = f"https://{host}/{VERSION}/{ruta}"
    datos = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(url, data=datos, method="POST") if metodo == "POST" \
        else urllib.request.Request(url + "?" + datos.decode())
    return _fb_enviar(req)


def texto_facebook(texto):
    """En Facebook los enlaces se pueden pulsar: sobra "(enlace en la bio)" y se añade https y utm."""
    texto = texto.replace(" (enlace en la bio)", "").replace("(enlace en la bio)", "")
    return re.sub(r"(?<![/\w.])(app\.[a-z]+\.com)\b",
                  r"https://\1/?utm_source=facebook&utm_medium=post", texto)


# ---------------------------------------------------------------- Facebook: Reel or normal video

# Facebook Page Reels accept videos from 3 to 90 seconds (Meta "Reels Publishing API" guide).
FB_REEL_MIN_S = 3
FB_REEL_MAX_S = 90
FB_ESPERA_SUBIDA_S = 300  # how long to wait for Facebook to fetch the hosted file
FB_ESPERA_PUBLICADO_S = 300  # how long to wait for the Reel to show as published after "finish"


def _cajas_mp4(f, inicio, fin):
    """Yield (type, payload_start, box_end) for each ISO-BMFF box between inicio and fin."""
    pos = inicio
    while pos + 8 <= fin:
        f.seek(pos)
        cabecera = f.read(8)
        if len(cabecera) < 8:
            return
        tam, tipo = struct.unpack(">I4s", cabecera)
        datos = pos + 8
        if tam == 1:  # 64-bit size follows the type
            ext = f.read(8)
            if len(ext) < 8:
                return
            tam = struct.unpack(">Q", ext)[0]
            datos += 8
        elif tam == 0:  # box runs to the end of the file
            tam = fin - pos
        if tam < datos - pos:  # corrupt size: stop instead of looping forever
            return
        yield tipo, datos, pos + tam
        pos += tam


def duracion_mp4(ruta):
    """Duration in seconds from the mp4 'moov/mvhd' box (stdlib only), or None if it cannot be read."""
    try:
        with open(ruta, "rb") as f:
            for tipo, ini, fin in _cajas_mp4(f, 0, os.path.getsize(ruta)):
                if tipo != b"moov":
                    continue
                for tipo2, ini2, _ in _cajas_mp4(f, ini, fin):
                    if tipo2 != b"mvhd":
                        continue
                    f.seek(ini2)
                    version = f.read(4)[0]  # 1 byte version + 3 bytes flags
                    if version == 1:
                        _, _, escala, dur = struct.unpack(">QQIQ", f.read(28))
                        desconocida = 0xFFFFFFFFFFFFFFFF
                    else:
                        _, _, escala, dur = struct.unpack(">IIII", f.read(16))
                        desconocida = 0xFFFFFFFF
                    if not escala or not dur or dur == desconocida:
                        return None
                    return dur / escala
    except (OSError, struct.error, IndexError):
        return None
    return None


def duracion_video(carpeta, meta):
    """(seconds, source) of the day's video: exact from the file if possible, else the queue metadata."""
    if meta.get("reel"):
        segundos = duracion_mp4(os.path.join(carpeta, meta["reel"]))
        if segundos:
            return segundos, "archivo"
    for clave in ("duracion", "duracion_s"):  # plan_voz.py writes "duracion"; una_al_dia.py "duracion_s"
        valor = meta.get(clave)
        if isinstance(valor, (int, float)) and not isinstance(valor, bool) and valor > 0:
            return float(valor), "meta"
    return None, "desconocida"


def formato_facebook(segundos):
    """'reel' if the Page accepts it as a Reel (3-90 s), else 'video'. Unknown duration -> 'video'."""
    if segundos is not None and FB_REEL_MIN_S <= segundos <= FB_REEL_MAX_S:
        return "reel"
    return "video"


def plan_facebook(dia):
    """One line saying how the day's post would go to Facebook (no API call, no token)."""
    carpeta = os.path.join(COLA, dia)
    meta = leer_json(os.path.join(carpeta, "meta.json"), {})
    if not meta.get("reel"):
        return "Facebook: publicación con fotos"
    segundos, origen = duracion_video(carpeta, meta)
    dur = f"{segundos:.1f} s, según el {origen}" if segundos is not None else "duración desconocida"
    if formato_facebook(segundos) == "reel":
        return f"Facebook: Reel ({dur})"
    return f"Facebook: vídeo normal ({dur}; los Reels de página admiten de {FB_REEL_MIN_S} a {FB_REEL_MAX_S} s)"


class ReelRechazado(ErrorAPI):
    """Facebook rejected the Reel and its status says it is not public: a normal video cannot duplicate it."""


def fb_reel_publico(status):
    """True if the Reel status says it is already public on the Page (even if an error is also reported)."""
    st = status if isinstance(status, dict) else {}
    publicacion = st.get("publishing_phase") if isinstance(st.get("publishing_phase"), dict) else {}
    return publicacion.get("publish_status") == "published" or publicacion.get("status") in ("complete", "completed")


def fb_fase_reel(status):
    """Read the 'status' object of a Reel: ('error', why) | ('publicado'|'subido'|'esperando', '')."""
    st = status if isinstance(status, dict) else {}
    if st.get("video_status") in ("upload_failed", "error", "expired"):
        return "error", f"video_status={st['video_status']}"
    for fase in ("uploading_phase", "processing_phase", "publishing_phase"):
        datos = st.get(fase) if isinstance(st.get(fase), dict) else {}
        # processing/publishing report "error" (object); uploading_phase reports "errors" (list)
        error = datos.get("error") or datos.get("errors")
        if isinstance(error, list):
            error = error[0] if error else None
        if datos.get("status") == "error" or datos.get("publish_status") == "error" or error:
            detalle = error.get("message") if isinstance(error, dict) else None
            return "error", detalle or f"{fase} con error"
    if fb_reel_publico(st):
        return "publicado", ""
    subida = st.get("uploading_phase") if isinstance(st.get("uploading_phase"), dict) else {}
    if subida.get("status") in ("complete", "completed"):
        return "subido", ""
    return "esperando", ""


def fb_publicacion_sin_empezar(status):
    """True only if the status explicitly says publishing has not started and the Reel is not public."""
    st = status if isinstance(status, dict) else {}
    publicacion = st.get("publishing_phase") if isinstance(st.get("publishing_phase"), dict) else {}
    return publicacion.get("status") == "not_started" and not fb_reel_publico(st)


def fb_status_reel(video_id):
    """One GET /{video-id}?fields=status -> Facebook's 'status' object ({} if it is missing)."""
    status = fb_api("GET", video_id, fields="status").get("status")
    return status if isinstance(status, dict) else {}


def fb_leer_reel(video_id, status=None):
    """'esperando' | 'subido' | 'publicado' from the Reel status (read with one GET unless it is given).
    Raises ReelRechazado if Facebook reports an error and the Reel is not public, or plain ErrorAPI
    if it reports an error on a Reel that is already public (that one must never be sent again)."""
    if status is None:
        status = fb_status_reel(video_id)
    estado, detalle = fb_fase_reel(status)
    if estado == "error":
        if fb_reel_publico(status):
            raise ErrorAPI(f"Facebook informa de un error en el Reel {video_id}, pero ya está publicado: {detalle}")
        raise ReelRechazado(f"Facebook rechazó el Reel {video_id}: {detalle}")
    return estado


def fb_esperar_reel(video_id, objetivo, maximo):
    """Poll the Reel status until it reaches `objetivo` ('subido' or 'publicado').
    Errors are raised as in fb_leer_reel. On timeout returns the last state."""
    orden = {"esperando": 0, "subido": 1, "publicado": 2}
    inicio = time.monotonic()
    while True:
        estado = fb_leer_reel(video_id)
        if orden[estado] >= orden[objetivo] or time.monotonic() - inicio > maximo:
            return estado
        time.sleep(5)


def fb_preparar_reel(pagina, ruta_local, url_video):
    """Reel phases 1 and 2: open an upload session and send the mp4 to rupload.facebook.com.
    Sends the bytes of the local file (the Actions checkout has it); if it is missing, Facebook
    fetches the hosted copy from file_url. Nothing is published yet. Returns the video_id."""
    sesion = fb_api("POST", f"{pagina}/video_reels", upload_phase="start")
    video_id = sesion["video_id"]
    cabeceras = {"Authorization": f"OAuth {os.environ['FB_PAGE_TOKEN']}"}
    datos = None
    if ruta_local and os.path.isfile(ruta_local):
        with open(ruta_local, "rb") as f:
            datos = f.read()
        cabeceras.update({"offset": "0", "file_size": str(len(datos)),
                          "Content-Type": "application/octet-stream"})
    else:
        cabeceras["file_url"] = url_video  # no body: Facebook downloads the hosted file
    req = urllib.request.Request(f"https://rupload.facebook.com/video-upload/{VERSION}/{video_id}",
                                 data=datos, method="POST", headers=cabeceras)
    subida = _fb_enviar(req)
    if not subida.get("success"):
        raise ErrorAPI(f"Facebook no aceptó la subida del Reel {video_id}: {str(subida)[:200]}")
    if fb_esperar_reel(video_id, "subido", FB_ESPERA_SUBIDA_S) == "esperando":
        raise ErrorAPI(f"Facebook no terminó de recibir el Reel {video_id} en {FB_ESPERA_SUBIDA_S} s")
    return video_id


def fb_publicar_reel(pagina, video_id, texto):
    """Reel phase 3: publish it on the Page with the description. Returns the result for publicadas.json.
    Raises ReelRechazado only when it is certain that the Reel is not public and will not become public:
    Facebook's status says it was rejected, or Facebook refused the "finish" call itself (HTTP 4xx)
    and the status says publishing has not started."""
    try:
        fin = fb_api("POST", f"{pagina}/video_reels", upload_phase="finish", video_id=video_id,
                     video_state="PUBLISHED", description=texto)
        if not fin.get("success"):
            raise ErrorAPI(f"Facebook no publicó el Reel {video_id}: {str(fin)[:200]}")
    except ErrorAPI as e:
        # The finish call failed: ask for the status once. If it clearly says rejected and not public,
        # fb_leer_reel raises ReelRechazado; if it cannot be read, or the Reel is public, keep this error.
        try:
            status = fb_status_reel(video_id)
            fb_leer_reel(video_id, status)
        except ReelRechazado:
            raise
        except ErrorAPI:
            raise e from None
        # A 4xx means Facebook refused the request itself (for example, the token lacks the Reels
        # permission). If publishing has not even started, a normal video cannot duplicate it.
        # A 5xx (after retries), a 200 without success or a timeout stay as an error: it might still go out.
        if e.codigo is not None and 400 <= e.codigo < 500 and fb_publicacion_sin_empezar(status):
            raise ReelRechazado(f"Facebook no aceptó publicar el Reel {video_id} y no se ha empezado "
                                f"a publicar: {e}") from e
        raise e
    estado = fb_esperar_reel(video_id, "publicado", FB_ESPERA_PUBLICADO_S)
    resultado = {"video_id": video_id, "formato": "reel",
                 "estado": "publicado" if estado == "publicado" else "procesando"}
    if fin.get("post_id"):
        resultado["post_id"] = fin["post_id"]
    return resultado


def fb_video_normal(pagina, url_video, texto):
    """Normal Page video (what was always done): Facebook downloads it from file_url."""
    r = fb_api("POST", f"{pagina}/videos", host="graph-video.facebook.com", file_url=url_video, description=texto)
    return {"video_id": r.get("id"), "formato": "video"}


def publicar_video_facebook(pagina, carpeta, meta, url_video, texto):
    """90 s or less -> Page Reel; longer (or unknown) -> normal video.
    If the Reel is not published (it fails before "finish"; Facebook refuses "finish" with a 4xx and
    publishing has not started; or Facebook rejects it afterwards and its status says it is not public),
    it falls back to a normal video so the day is not lost."""
    segundos, _ = duracion_video(carpeta, meta)
    dur = round(segundos, 1) if segundos is not None else None
    if formato_facebook(segundos) == "video":
        return {**fb_video_normal(pagina, url_video, texto), "duracion_s": dur}
    try:
        video_id = fb_preparar_reel(pagina, os.path.join(carpeta, meta["reel"]), url_video)
    except Exception as e:  # noqa: BLE001 - nothing published yet, so a normal video is safe
        print(f"::warning::Facebook no aceptó el vídeo como Reel ({e}). Se publica como vídeo normal.")
        return {**fb_video_normal(pagina, url_video, texto), "duracion_s": dur, "reel_error": str(e)[:300]}
    # From here on the Reel may already be public: fall back only if Facebook says it rejected it and it
    # is not public (ReelRechazado). Any other error is raised, so it is never published twice.
    try:
        return {**fb_publicar_reel(pagina, video_id, texto), "duracion_s": dur}
    except ReelRechazado as e:
        print(f"::warning::Facebook no publicó el Reel tras pedir su publicación y no está publicado ({e}). "
              f"Se publica como vídeo normal.")
        return {**fb_video_normal(pagina, url_video, texto), "duracion_s": dur, "reel_error": str(e)[:300],
                "reel_video_id": video_id}


def es_reel_facebook(dia):
    """True if the day's post would go to the Facebook Page as a Reel (video of 3-90 s)."""
    carpeta = os.path.join(COLA, dia)
    meta = leer_json(os.path.join(carpeta, "meta.json"), {})
    return bool(meta.get("reel")) and formato_facebook(duracion_video(carpeta, meta)[0]) == "reel"


def probar_reel_facebook(dia):
    """The whole Page Reel flow, but "finish" asks for video_state=DRAFT: it checks that the Page token
    can make Reels without publishing anything. The draft stays unpublished in the Page's content
    (Meta Business Suite), where it can be deleted. Returns (video_id, state after finish)."""
    pagina = os.environ["FB_PAGE_ID"]
    carpeta = os.path.join(COLA, dia)
    meta = leer_json(os.path.join(carpeta, "meta.json"), {})
    video_id = fb_preparar_reel(pagina, os.path.join(carpeta, meta["reel"]), f"{url_base()}/{dia}/{meta['reel']}")
    fin = fb_api("POST", f"{pagina}/video_reels", upload_phase="finish", video_id=video_id,
                 video_state="DRAFT", description="Prueba del publicador: borrador, no publicar.")
    if not fin.get("success"):
        raise ErrorAPI(f"Facebook no aceptó el Reel {video_id} como borrador: {str(fin)[:200]}")
    return video_id, fb_leer_reel(video_id)  # raises if Facebook already reports an error


def publicar_facebook(dia):
    """Publica en la pagina de Facebook lo mismo que se acaba de publicar en Instagram.
    Devuelve None si esta cuenta no tiene Facebook configurado."""
    pagina = os.environ.get("FB_PAGE_ID")
    if not pagina or not os.environ.get("FB_PAGE_TOKEN"):
        return None
    carpeta = os.path.join(COLA, dia)
    meta = leer_json(os.path.join(carpeta, "meta.json"), {})
    with open(os.path.join(carpeta, "caption.txt"), encoding="utf-8") as f:
        texto = texto_facebook(f.read())
    base = f"{url_base()}/{dia}"
    if meta.get("reel"):
        return publicar_video_facebook(pagina, carpeta, meta, f"{base}/{meta['reel']}", texto)
    fotos = [fb_api("POST", f"{pagina}/photos", url=f"{base}/{img}", published="false")["id"]
             for img in meta["imagenes"]]
    r = fb_api("POST", f"{pagina}/feed", message=texto,
               attached_media=json.dumps([{"media_fbid": f} for f in fotos]))
    return {"post_id": r.get("id")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--comprobar", action="store_true")
    ap.add_argument("--simular", action="store_true")
    ap.add_argument("--ya", action="store_true", help="publica aunque no sea la hora")
    ap.add_argument("--diagnosticar", action="store_true", help="muestra los permisos del token (nunca el token)")
    ap.add_argument("--publicar_ahora", action="store_true",
                    help="publica YA la carpeta indicada en PROBAR_CARPETA (publicaciones puntuales)")
    ap.add_argument("--probar_reel", action="store_true",
                    help="Instagram descarga y procesa el proximo Reel de la cola, sin publicarlo")
    ap.add_argument("--formato_facebook", action="store_true",
                    help="dice si cada video de la cola ira a Facebook como Reel o como video normal (sin token)")
    ap.add_argument("--probar_reel_facebook", action="store_true",
                    help="sube el proximo Reel corto de la cola a la pagina de Facebook como BORRADOR, sin publicarlo")
    a = ap.parse_args()

    if a.formato_facebook:  # local check only: reads cola/, never calls the API
        hoy_str = dt.datetime.now(ZoneInfo("Europe/Madrid")).date().isoformat()
        hechas = leer_json(PUBLICADAS, {})
        dias = sorted(d for d in os.listdir(COLA) if d[:10] >= hoy_str and d not in hechas
                      and os.path.isfile(os.path.join(COLA, d, "meta.json"))) if os.path.isdir(COLA) else []
        for d in dias:
            print(f"{d:<22} {plan_facebook(d)}")
        print(f"{len(dias)} publicaciones pendientes revisadas. No se ha publicado nada.")
        return

    ahora = dt.datetime.now(ZoneInfo("Europe/Madrid"))
    hoy = ahora.date()
    de_madrugada = ahora.time() < HORA_RECUPERACION
    if de_madrugada:
        hoy -= dt.timedelta(days=1)  # el cron de anoche llego tarde: le toca al dia de ayer
    publicadas = leer_json(PUBLICADAS, {})
    cola = pendientes(hoy, publicadas)
    futuras = sorted({d[:10] for d in os.listdir(COLA) if d[:10] > hoy.isoformat()}) if os.path.isdir(COLA) else []
    print(f"Hoy {hoy}. Pendientes: {len(cola)}. Días preparados por delante: {len(futuras)}.")
    if len(futuras) < AVISO_COLA:
        print(f"::warning::Solo quedan {len(futuras)} días en cola. Ejecuta generar_cola.py en el PC.")

    if a.comprobar:
        print(f"Token correcto. Cuenta: @{comprobar_cuenta()}")
        if os.environ.get("FB_PAGE_ID") and os.environ.get("FB_PAGE_TOKEN"):
            pagina = fb_api("GET", os.environ["FB_PAGE_ID"], fields="name")
            print(f"Facebook correcto. Página: {pagina.get('name')}")
        else:
            print("Facebook: sin configurar (falta ejecutar publicador/configurar_facebook.py).")
        return
    if a.probar_reel:
        prox = os.environ.get("PROBAR_CARPETA") or next((d for d in sorted(os.listdir(COLA)) if d[:10] >= hoy.isoformat() and d not in publicadas
                     and leer_json(os.path.join(COLA, d, "meta.json"), {}).get("reel")), None)
        if not prox:
            print("No hay ningún Reel en la cola.")
            return
        comprobar_cuenta()
        url = f"{url_base()}/{prox}/{leer_json(os.path.join(COLA, prox, 'meta.json'), {}).get('reel', 'reel.mp4')}"
        cont = api("POST", f"{os.environ['IG_USER_ID']}/media", media_type="REELS", video_url=url,
                   caption="prueba", share_to_feed="true")
        try:
            esperar_contenedor(cont["id"], maximo=600)
        except ErrorAPI as e:
            print(f"::error::Instagram no aceptó el Reel de {prox}: {e}")
            sys.exit(1)
        print(f"Reel de {prox} aceptado y procesado por Instagram (NO se ha publicado).")
        return
    if a.probar_reel_facebook:  # never publishes: the Reel stays as a draft on the Page
        if not (os.environ.get("FB_PAGE_ID") and os.environ.get("FB_PAGE_TOKEN")):
            print("::error::Facebook no está configurado.")
            sys.exit(1)
        prox = os.environ.get("PROBAR_CARPETA") or next(
            (d for d in sorted(os.listdir(COLA)) if d[:10] >= hoy.isoformat() and d not in publicadas
             and es_reel_facebook(d)), None)
        if not prox:
            print("No hay ningún vídeo de 90 s o menos en la cola.")
            return
        if not os.path.isfile(os.path.join(COLA, prox, "meta.json")) or not es_reel_facebook(prox):
            print(f"::error::cola/{prox} no tiene un vídeo de {FB_REEL_MIN_S} a {FB_REEL_MAX_S} s.")
            sys.exit(1)
        try:
            video_id, estado = probar_reel_facebook(prox)
        except Exception as e:  # noqa: BLE001
            print(f"::error::Facebook no aceptó el Reel de {prox} ni siquiera como borrador: {e}")
            sys.exit(1)
        print(f"Reel de {prox} aceptado por Facebook como BORRADOR (video_id {video_id}, estado: {estado}). "
              f"NO se ha publicado; el borrador se puede borrar en Meta Business Suite.")
        return
    if a.diagnosticar:
        diagnosticar()
        return
    if a.publicar_ahora:  # publicacion puntual: la carpeta indicada, ya (lo lanza una tarea a su hora)
        dia = os.environ.get("PROBAR_CARPETA", "")
        if not dia or not os.path.isfile(os.path.join(COLA, dia, "meta.json")):
            print(f"::error::No existe la carpeta cola/{dia}.")
            sys.exit(1)
        if dia in publicadas:
            print(f"{dia} ya estaba publicada.")
            return
    else:
        if not cola:
            print("Nada que publicar hoy.")
            return
        # franja que toca: de madrugada, la noche de ayer (el cron llego tarde)
        sufijo = "" if de_madrugada else franja_actual(ahora)
        if sufijo is None:
            if not (a.ya or a.simular):
                print(f"Son las {ahora:%H:%M} en Madrid: la primera publicación es a las {FRANJAS[0][1]:%H:%M}.")
                return
            sufijo = FRANJAS[0][0]

        # solo la de esta franja y como mucho una por franja: las que fallaron se saltan
        dia = hoy.isoformat() + sufijo
        if dia not in cola:
            hecho = dia in publicadas
            print(f"Nada para {dia}" + (" (ya publicada)." if hecho else f" (hay {len(cola)} antiguas sin publicar que se saltan)."))
            return
        if a.simular:
            print(f"Publicaría {dia}: {url_base()}/{dia}")
            print(plan_facebook(dia))
            return
    meta_dia = leer_json(os.path.join(COLA, dia, "meta.json"), {})
    if meta_dia.get("solo_facebook"):  # p. ej. videos de mas de 3 min: no caben como Reel
        try:
            fb = publicar_facebook(dia)
        except ErrorAPI as e:
            print(f"::error::No se pudo publicar {dia} en Facebook: {e}")
            sys.exit(1)
        if not fb:
            print(f"::error::{dia} es solo para Facebook y Facebook no está configurado.")
            sys.exit(1)
        publicadas[dia] = {"tipo": "solo_facebook", "facebook": fb, "permalink": "",
                           "publicado": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                           "id_pregunta": meta_dia.get("id")}
        with open(PUBLICADAS, "w", encoding="utf-8") as f:
            json.dump(publicadas, f, ensure_ascii=False, indent=1, sort_keys=True)
        print(f"Publicado {dia} solo en Facebook: {fb}")
        return
    try:
        resultado = publicar(dia)
    except ErrorAPI as e:
        print(f"::error::No se pudo publicar {dia}: {e}")
        sys.exit(1)
    # Facebook: si falla, Instagram ya esta publicado; se avisa pero no se marca como error
    try:
        fb = publicar_facebook(dia)
        if fb:
            resultado["facebook"] = fb
            print(f"Publicado también en Facebook: {fb}")
    except Exception as e:  # noqa: BLE001
        resultado["facebook_error"] = str(e)[:300]
        print(f"::warning::Instagram OK, pero falló Facebook: {e}")
    publicadas[dia] = resultado
    os.makedirs(os.path.dirname(PUBLICADAS), exist_ok=True)
    with open(PUBLICADAS, "w", encoding="utf-8") as f:
        json.dump(publicadas, f, ensure_ascii=False, indent=1, sort_keys=True)
    print(f"Publicado {dia}: {resultado['permalink']}")


if __name__ == "__main__":
    main()
