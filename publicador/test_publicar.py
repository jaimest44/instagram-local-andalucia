"""Tests for the Facebook part of publicar.py: Reel (90 s or less) or normal video.

Nothing here touches the network: urllib.request.urlopen is replaced by a fake that records each
request and answers like the Graph API would. The token is a dummy value.

    python -m unittest discover -s publicador -p "test_*.py" -v
"""
import io
import json
import os
import struct
import tempfile
import unittest
import urllib.error
import urllib.parse
from unittest import mock

import publicar


# ---------------------------------------------------------------- helpers

def caja(tipo, contenido):
    return struct.pack(">I4s", 8 + len(contenido), tipo) + contenido


def mp4(segundos, escala=1000, version=0, moov_al_final=False, mdat_grande=False):
    """Minimal ISO-BMFF file with ftyp, moov/mvhd and mdat (enough for duracion_mp4)."""
    dur = int(round(segundos * escala))
    if version == 1:
        mvhd = caja(b"mvhd", bytes([1, 0, 0, 0]) + struct.pack(">QQIQ", 0, 0, escala, dur) + bytes(80))
    else:
        mvhd = caja(b"mvhd", bytes([0, 0, 0, 0]) + struct.pack(">IIII", 0, 0, escala, dur) + bytes(80))
    moov = caja(b"moov", mvhd + caja(b"trak", bytes(16)))
    ftyp = caja(b"ftyp", b"isom" + bytes(4) + b"isomavc1")
    datos = bytes(64)
    if mdat_grande:  # 64-bit size field
        mdat = struct.pack(">I4sQ", 1, b"mdat", 16 + len(datos)) + datos
    else:
        mdat = caja(b"mdat", datos)
    return ftyp + (mdat + moov if moov_al_final else moov + mdat)


class Respuesta(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()


class GraphFalso:
    """Fake urlopen: records each request and answers like Facebook would."""

    def __init__(self, reel_falla_en=None, estados=None):
        self.peticiones = []
        self.reel_falla_en = reel_falla_en  # "start" | "upload" | "finish" | None
        self.estados = list(estados or [
            {"video_status": "upload_complete", "uploading_phase": {"status": "complete"}},
            {"video_status": "ready", "uploading_phase": {"status": "complete"},
             "processing_phase": {"status": "complete"},
             "publishing_phase": {"status": "complete", "publish_status": "published"}},
        ])

    def __call__(self, req, timeout=None):
        url = req.full_url
        binario = url.startswith("https://rupload.facebook.com/")  # rupload body is the raw mp4
        params = dict(urllib.parse.parse_qsl(req.data.decode())) if req.data and not binario else {}
        if "?" in url:
            params.update(urllib.parse.parse_qsl(url.split("?", 1)[1]))
        cabeceras = {k.lower(): v for k, v in req.header_items()}
        self.peticiones.append({"metodo": req.get_method(), "url": url.split("?")[0], "params": params,
                                "cabeceras": cabeceras, "cuerpo": req.data})
        ruta = urllib.parse.urlparse(url).path
        if ruta.endswith("/video_reels") and params.get("upload_phase") == "start":
            if self.reel_falla_en == "start":
                raise self.error(400, {"error": {"message": "Reels no disponibles"}})
            return self.ok({"video_id": "111", "upload_url": "https://rupload.facebook.com/video-upload/111"})
        if url.startswith("https://rupload.facebook.com/"):
            if self.reel_falla_en == "upload":
                raise self.error(400, {"debug_info": {"retriable": False, "message": "file_url no válido"}})
            return self.ok({"success": True})
        if ruta.endswith("/111") and params.get("fields") == "status":
            return self.ok({"status": self.estados.pop(0) if len(self.estados) > 1 else self.estados[0],
                            "id": "111"})
        if ruta.endswith("/video_reels") and params.get("upload_phase") == "finish":
            if self.reel_falla_en == "finish":
                raise self.error(400, {"error": {"message": "No se pudo publicar el vídeo"}})
            return self.ok({"success": True, "post_id": "999"})
        if ruta.endswith("/videos"):
            return self.ok({"id": "222"})
        if ruta.endswith("/photos"):
            return self.ok({"id": "333"})
        if ruta.endswith("/feed"):
            return self.ok({"id": "pagina_444"})
        raise AssertionError(f"Petición inesperada: {req.get_method()} {url}")

    @staticmethod
    def ok(datos):
        return Respuesta(json.dumps(datos).encode())

    @staticmethod
    def error(codigo, datos):
        return urllib.error.HTTPError("https://x", codigo, "error", {}, io.BytesIO(json.dumps(datos).encode()))

    def rutas(self):
        return [urllib.parse.urlparse(p["url"]).path for p in self.peticiones]


# ---------------------------------------------------------------- what decides Reel or video

class DecideReelOVideo(unittest.TestCase):
    def test_limites(self):
        self.assertEqual(publicar.formato_facebook(3), "reel")
        self.assertEqual(publicar.formato_facebook(45.2), "reel")
        self.assertEqual(publicar.formato_facebook(90), "reel")
        self.assertEqual(publicar.formato_facebook(90.01), "video")
        self.assertEqual(publicar.formato_facebook(164.3), "video")
        self.assertEqual(publicar.formato_facebook(2.9), "video")
        self.assertEqual(publicar.formato_facebook(None), "video")  # unknown: keep the old behaviour


class DuracionMp4(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)

    def escribir(self, nombre, datos):
        ruta = os.path.join(self.dir.name, nombre)
        with open(ruta, "wb") as f:
            f.write(datos)
        return ruta

    def test_mvhd_version_0(self):
        self.assertAlmostEqual(publicar.duracion_mp4(self.escribir("a.mp4", mp4(62.77))), 62.77, places=2)

    def test_mvhd_version_1_y_moov_al_final_con_mdat_de_64_bits(self):
        ruta = self.escribir("b.mp4", mp4(164.33, escala=90000, version=1, moov_al_final=True, mdat_grande=True))
        self.assertAlmostEqual(publicar.duracion_mp4(ruta), 164.33, places=2)

    def test_archivo_roto_o_inexistente(self):
        self.assertIsNone(publicar.duracion_mp4(self.escribir("roto.mp4", b"esto no es un mp4")))
        self.assertIsNone(publicar.duracion_mp4(self.escribir("vacio.mp4", b"")))
        self.assertIsNone(publicar.duracion_mp4(os.path.join(self.dir.name, "no_existe.mp4")))

    def test_el_archivo_manda_sobre_la_meta(self):
        self.escribir("reel.mp4", mp4(91.37))
        meta = {"reel": "reel.mp4", "duracion_s": 90}  # hand-written value, rounded down
        self.assertEqual(publicar.duracion_video(self.dir.name, meta), (91.37, "archivo"))

    def test_sin_archivo_usa_la_meta(self):
        self.assertEqual(publicar.duracion_video(self.dir.name, {"reel": "x.mp4", "duracion": 43.2}), (43.2, "meta"))
        self.assertEqual(publicar.duracion_video(self.dir.name, {"reel": "x.mp4", "duracion_s": 106}), (106.0, "meta"))
        self.assertEqual(publicar.duracion_video(self.dir.name, {"reel": "x.mp4"}), (None, "desconocida"))


class EstadoDelReel(unittest.TestCase):
    def test_estados(self):
        self.assertEqual(publicar.fb_fase_reel({"video_status": "uploading",
                                                "uploading_phase": {"status": "in_progress"}}), ("esperando", ""))
        self.assertEqual(publicar.fb_fase_reel({"uploading_phase": {"status": "complete"}}), ("subido", ""))
        self.assertEqual(publicar.fb_fase_reel({"publishing_phase": {"status": "complete",
                                                                     "publish_status": "published"}}),
                         ("publicado", ""))
        self.assertEqual(publicar.fb_fase_reel(None), ("esperando", ""))

    def test_error_de_procesado_del_ejemplo_de_meta(self):
        st = {"video_status": "processing", "uploading_phase": {"status": "complete"},
              "processing_phase": {"status": "not_started",
                                   "error": {"message": "Resolution too low. Video must have a minimum "
                                                        "resolution of 540p."}},
              "publishing_phase": {"status": "not_started"}}
        estado, detalle = publicar.fb_fase_reel(st)
        self.assertEqual(estado, "error")
        self.assertIn("540p", detalle)
        self.assertEqual(publicar.fb_fase_reel({"video_status": "upload_failed"})[0], "error")

    def test_errores_de_subida_en_lista(self):
        st = {"uploading_phase": {"status": "in_progress",
                                  "errors": [{"code": 1363040, "message": "File is not a video"}]}}
        self.assertEqual(publicar.fb_fase_reel(st), ("error", "File is not a video"))
        self.assertEqual(publicar.fb_fase_reel({"uploading_phase": {"status": "completed", "errors": []}}),
                         ("subido", ""))

    def test_reel_publico(self):
        self.assertTrue(publicar.fb_reel_publico({"publishing_phase": {"publish_status": "published"}}))
        self.assertTrue(publicar.fb_reel_publico({"publishing_phase": {"status": "complete"}}))
        self.assertFalse(publicar.fb_reel_publico({"video_status": "error"}))
        self.assertFalse(publicar.fb_reel_publico({"publishing_phase": {"status": "error", "publish_status": "error"}}))
        self.assertFalse(publicar.fb_reel_publico({"publishing_phase": {"status": "not_started"}}))
        self.assertFalse(publicar.fb_reel_publico(None))


# ---------------------------------------------------------------- full Facebook flow, with a fake API

class PublicarFacebook(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        for parche in (
            mock.patch.object(publicar, "COLA", self.dir.name),
            mock.patch.object(publicar, "VERSION", "v24.0"),
            mock.patch.dict(os.environ, {"FB_PAGE_ID": "PAGINA", "FB_PAGE_TOKEN": "token-de-prueba",
                                         "URL_BASE": "https://ejemplo.test/cola"}),
            mock.patch.object(publicar.time, "sleep", lambda s: None),
            mock.patch("builtins.print"),
        ):
            parche.start()
            self.addCleanup(parche.stop)

    def dia(self, nombre, segundos=None, meta_extra=None, fotos=False):
        carpeta = os.path.join(self.dir.name, nombre)
        os.makedirs(carpeta)
        meta = {"imagenes": ["01.jpg", "02.jpg"]} if fotos else {"imagenes": [], "reel": "reel.mp4"}
        meta.update(meta_extra or {})
        with open(os.path.join(carpeta, "meta.json"), "w", encoding="utf-8") as f:
            json.dump(meta, f)
        with open(os.path.join(carpeta, "caption.txt"), "w", encoding="utf-8") as f:
            f.write("🚨 Supuesto resuelto. Regístrate en app.localandalucia.com (enlace en la bio)")
        if segundos is not None:
            with open(os.path.join(carpeta, "reel.mp4"), "wb") as f:
                f.write(mp4(segundos))
        return nombre

    def publicar(self, dia, api):
        with mock.patch.object(publicar.urllib.request, "urlopen", api):
            return publicar.publicar_facebook(dia)

    def test_video_corto_sale_como_reel(self):
        api = GraphFalso()
        r = self.publicar(self.dia("2026-11-13_manana", 62.77), api)
        self.assertEqual(r, {"video_id": "111", "formato": "reel", "estado": "publicado", "post_id": "999",
                             "duracion_s": 62.8})
        self.assertNotIn("/v24.0/PAGINA/videos", api.rutas())  # no normal video
        inicio, subida = api.peticiones[0], api.peticiones[1]
        self.assertEqual(inicio["url"], "https://graph.facebook.com/v24.0/PAGINA/video_reels")
        self.assertEqual(inicio["params"]["upload_phase"], "start")
        self.assertEqual(subida["url"], "https://rupload.facebook.com/video-upload/v24.0/111")
        self.assertEqual(subida["metodo"], "POST")
        self.assertEqual(subida["cabeceras"]["authorization"], "OAuth token-de-prueba")
        # the local mp4 is sent as the body (Meta's "local file" upload), not fetched from a URL
        with open(os.path.join(self.dir.name, "2026-11-13_manana", "reel.mp4"), "rb") as f:
            contenido = f.read()
        self.assertEqual(subida["cuerpo"], contenido)
        self.assertEqual(subida["cabeceras"]["offset"], "0")
        self.assertEqual(subida["cabeceras"]["file_size"], str(len(contenido)))
        self.assertEqual(subida["cabeceras"]["content-type"], "application/octet-stream")
        self.assertNotIn("file_url", subida["cabeceras"])
        fin = [p for p in api.peticiones if p["params"].get("upload_phase") == "finish"]
        self.assertEqual(len(fin), 1)
        self.assertEqual(fin[0]["params"]["video_state"], "PUBLISHED")
        self.assertEqual(fin[0]["params"]["video_id"], "111")
        # Facebook text: clickable link with utm, without "(enlace en la bio)"
        self.assertIn("https://app.localandalucia.com/?utm_source=facebook", fin[0]["params"]["description"])
        self.assertNotIn("enlace en la bio", fin[0]["params"]["description"])
        # the finish call is only sent once the upload is complete
        self.assertLess(api.rutas().index("/v24.0/111"), api.peticiones.index(fin[0]))

    def test_justo_90_segundos_es_reel(self):
        r = self.publicar(self.dia("d90", 90.0), GraphFalso())
        self.assertEqual(r["formato"], "reel")

    def test_video_largo_sigue_como_video_normal(self):
        api = GraphFalso()
        r = self.publicar(self.dia("2026-11-14_manana", 164.33), api)
        self.assertEqual(r, {"video_id": "222", "formato": "video", "duracion_s": 164.3})
        self.assertEqual(len(api.peticiones), 1)
        p = api.peticiones[0]
        self.assertEqual(p["url"], "https://graph-video.facebook.com/v24.0/PAGINA/videos")
        self.assertEqual(p["params"]["file_url"], "https://ejemplo.test/cola/2026-11-14_manana/reel.mp4")

    def test_sin_archivo_usa_la_duracion_de_la_meta(self):
        api = GraphFalso()
        r = self.publicar(self.dia("sin_mp4", None, {"duracion_s": 106}), api)
        self.assertEqual(r["formato"], "video")
        api = GraphFalso()
        r = self.publicar(self.dia("sin_mp4_corto", None, {"duracion": 43.2}), api)
        self.assertEqual(r["formato"], "reel")
        # no local file: Facebook fetches the hosted copy (file_url header, empty body)
        subida = api.peticiones[1]
        self.assertTrue(subida["url"].startswith("https://rupload.facebook.com/video-upload/v24.0/"))
        self.assertEqual(subida["cabeceras"]["file_url"], "https://ejemplo.test/cola/sin_mp4_corto/reel.mp4")
        self.assertIsNone(subida["cuerpo"])

    def test_duracion_desconocida_va_como_video_normal(self):
        r = self.publicar(self.dia("sin_nada", None), GraphFalso())
        self.assertEqual(r, {"video_id": "222", "formato": "video", "duracion_s": None})

    def test_si_el_reel_falla_antes_de_publicar_va_como_video_normal(self):
        for fallo in ("start", "upload"):
            with self.subTest(fallo=fallo):
                api = GraphFalso(reel_falla_en=fallo)
                r = self.publicar(self.dia(f"falla_{fallo}", 45), api)
                self.assertEqual(r["formato"], "video")
                self.assertEqual(r["video_id"], "222")
                self.assertIn("reel_error", r)
                self.assertNotIn("finish", [p["params"].get("upload_phase") for p in api.peticiones])

    def test_si_facebook_rechaza_el_video_al_procesarlo_va_como_video_normal(self):
        api = GraphFalso(estados=[{"video_status": "processing", "uploading_phase": {"status": "complete"},
                                   "processing_phase": {"status": "error",
                                                        "error": {"message": "Resolution too low"}}}])
        r = self.publicar(self.dia("baja_resolucion", 30), api)
        self.assertEqual(r["formato"], "video")
        self.assertIn("Resolution too low", r["reel_error"])

    def comprobar_reserva_tras_finish(self, api, r, texto_error):
        """The Reel was rejected after "finish": exactly one finish, then one normal video."""
        self.assertEqual(r["formato"], "video")
        self.assertEqual(r["video_id"], "222")
        self.assertEqual(r["reel_video_id"], "111")
        self.assertIn(texto_error, r["reel_error"])
        fases = [p["params"].get("upload_phase") for p in api.peticiones]
        self.assertEqual(fases.count("finish"), 1)
        self.assertEqual(api.rutas().count("/v24.0/PAGINA/videos"), 1)
        self.assertLess(fases.index("finish"), api.rutas().index("/v24.0/PAGINA/videos"))

    def test_rechazo_despues_del_finish_va_como_video_normal(self):
        # Facebook accepts "finish" and rejects the Reel while processing it: it is not public,
        # so a normal video cannot duplicate it and the day is not lost
        subido = {"video_status": "upload_complete", "uploading_phase": {"status": "complete"}}
        rechazos = {
            "video_status_error": ({"video_status": "error", "uploading_phase": {"status": "complete"}},
                                   "video_status=error"),
            "processing_phase": ({"video_status": "processing", "uploading_phase": {"status": "complete"},
                                  "processing_phase": {"status": "error",
                                                       "error": {"message": "Video too long for Reels"}},
                                  "publishing_phase": {"status": "not_started"}}, "Video too long"),
            "publish_status_error": ({"uploading_phase": {"status": "complete"},
                                      "publishing_phase": {"status": "error", "publish_status": "error"}},
                                     "publishing_phase con error"),
        }
        for nombre, (rechazo, texto_error) in rechazos.items():
            with self.subTest(rechazo=nombre):
                api = GraphFalso(estados=[subido, rechazo])
                r = self.publicar(self.dia(f"rechazo_{nombre}", 89.8), api)
                self.comprobar_reserva_tras_finish(api, r, texto_error)

    def test_finish_falla_y_facebook_dice_que_lo_rechazo(self):
        estados = [{"uploading_phase": {"status": "complete"}},
                   {"video_status": "error", "uploading_phase": {"status": "complete"}}]
        api = GraphFalso(reel_falla_en="finish", estados=estados)
        r = self.publicar(self.dia("finish_rechazado", 45), api)
        self.comprobar_reserva_tras_finish(api, r, "video_status=error")

    def test_finish_falla_sin_rechazo_claro_no_duplica(self):
        # the status shows no error: the Reel could still go public, so only the error is reported
        api = GraphFalso(reel_falla_en="finish", estados=[{"uploading_phase": {"status": "complete"}}])
        with self.assertRaises(publicar.ErrorAPI) as ctx:
            self.publicar(self.dia("finish_dudoso", 45), api)
        self.assertNotIsInstance(ctx.exception, publicar.ReelRechazado)
        self.assertIn("No se pudo publicar el vídeo", str(ctx.exception))
        self.assertNotIn("/v24.0/PAGINA/videos", api.rutas())

    def test_error_con_el_reel_ya_publicado_no_duplica(self):
        # an error on a Reel whose status says it is public: reported, never a second (normal) video
        estados = [{"uploading_phase": {"status": "complete"}},
                   {"video_status": "error", "uploading_phase": {"status": "complete"},
                    "publishing_phase": {"status": "complete", "publish_status": "published"}}]
        api = GraphFalso(estados=estados)
        with self.assertRaises(publicar.ErrorAPI) as ctx:
            self.publicar(self.dia("falla_ya_publicado", 30), api)
        self.assertNotIsInstance(ctx.exception, publicar.ReelRechazado)
        self.assertNotIn("/v24.0/PAGINA/videos", api.rutas())

    def test_si_tarda_en_publicarse_no_duplica(self):
        # still processing when the wait ends: it may go public later, so no normal video
        api = GraphFalso(estados=[{"uploading_phase": {"status": "complete"}}])
        with mock.patch.object(publicar, "FB_ESPERA_PUBLICADO_S", -1):
            r = self.publicar(self.dia("lento", 30), api)
        self.assertEqual(r["formato"], "reel")
        self.assertEqual(r["estado"], "procesando")
        self.assertNotIn("/v24.0/PAGINA/videos", api.rutas())

    def test_las_fotos_no_cambian(self):
        api = GraphFalso()
        r = self.publicar(self.dia("carrusel", fotos=True), api)
        self.assertEqual(r, {"post_id": "pagina_444"})
        self.assertEqual(api.rutas(), ["/v24.0/PAGINA/photos", "/v24.0/PAGINA/photos", "/v24.0/PAGINA/feed"])

    def test_sin_facebook_configurado_no_hace_nada(self):
        with mock.patch.dict(os.environ, {"FB_PAGE_ID": ""}):
            api = GraphFalso()
            self.assertIsNone(self.publicar(self.dia("sin_fb", 30), api))
            self.assertEqual(api.peticiones, [])

    def test_plan_facebook(self):
        self.dia("corto", 62.77)
        self.dia("largo", 164.33)
        self.dia("fotos", fotos=True)
        self.assertEqual(publicar.plan_facebook("corto"), "Facebook: Reel (62.8 s, según el archivo)")
        self.assertTrue(publicar.plan_facebook("largo").startswith("Facebook: vídeo normal (164.3 s"))
        self.assertEqual(publicar.plan_facebook("fotos"), "Facebook: publicación con fotos")


if __name__ == "__main__":
    unittest.main()
