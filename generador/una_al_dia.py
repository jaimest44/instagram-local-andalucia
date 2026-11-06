# 6/11/2026, Jaime: @localandalucia pasa a UNA publicacion al dia (11:00), solo supuestos oficiales resueltos en video y
# normas en video. Desde el 7/11: dias impares supuesto (SUP01..SUP16), dias pares norma (en el orden que ya tenian);
# cuando se acaban los supuestos, norma cada dia. Todo lo demas pendiente (mediodia, tarde, chuletas...) va a
# cola_pausada/ sin borrar nada. Registro para deshacer: estado/una_al_dia_6-11.json.
# Uso: python una_al_dia.py [--aplicar]
import datetime as dt, json, os, shutil, sys

REPO = r"D:/Movistar Cloud/40. TRABAJO/OPOSI S.L/LOCAL ANDALUCÍA/40. INSTAGRAM"
COLA, PAUSA = os.path.join(REPO, "cola"), os.path.join(REPO, "cola_pausada")
SRC = r"C:/Users/jaime/Downloads/INFOGRAFIA LEYES/VIDEOS_NORMAS/salida_supuestos/"
DESDE = dt.date(2026, 11, 7)
APLICAR = "--aplicar" in sys.argv

CTA = ("Regístrate gratis en app.localandalucia.com y haz tu primer test en 5 minutos (enlace en la bio). "
       "Este y más supuestos resueltos en vídeo, en el Plan Completo.")
SUP = [  # archivo, escena (gancho del caption), municipio y año, duracion
    ("SUP01_Adra2024_STOP_y_lesiones", "Un turismo se salta un STOP y choca con otro coche que tenía prioridad. Hay heridos.", "Adra 2024", 75),
    ("SUP02_Autocaravana_estacionada_o_acampada", "Una autocaravana en plena calle, con los calzos puestos. Un agente dice «mal estacionada». ¿Estacionada o acampada?", "Barbate 2023", 80),
    ("SUP03_Ciclista_de_noche_sin_reflectante", "Un ciclista de noche por carretera, con el reflectante gastado. ¿Qué tiene que llevar?", "Jerez de la Frontera 2023", 70),
    ("SUP04_Patinete_sin_casco", "Un patinete eléctrico sin casco. Al ver a la patrulla, se lo pone. ¿Es infracción?", "Huelma 2025", 63),
    ("SUP05_Patinete_de_noche_sin_luces", "Un patinete eléctrico de noche, sin luces ni reflectante. ¿Qué denuncias?", "Jaén 2026", 68),
    ("SUP06_Furgoneta_4200kg_permiso_B", "Una furgoneta de 4.200 kg y su conductor solo tiene el permiso B. ¿Puede llevarla?", "Rincón de la Victoria 2021", 85),
    ("SUP07_Patinete_atropella_en_la_acera", "Un patinete va por la acera y atropella a un peatón. ¿Es delito?", "Mairena del Alcor 2021", 88),
    ("SUP08_Nijar2024_triciclo_y_minimoto", "Un triciclo por la acera y una minimoto que huye. El de la moto tiene 19 años y nunca tuvo permiso. ¿Qué denuncias?", "Níjar 2024", 89),
    ("SUP09_Malaga2020_ciclista_paseo_maritimo", "Un ciclista en el paseo marítimo, con auriculares, sin casco y con signos de haber bebido.", "Málaga 2020", 90),
    ("SUP10_Polopos2025_cruce_con_semaforos", "Choque en un cruce con semáforos y cada conductor culpa al otro. ¿Quién tiene la culpa?", "Polopos y La Mamola 2025", 82),
    ("SUP11_Mijas2017_Rincon2019_semaforo_camion_moto", "Un turismo pasa en rojo, un camión y una moto. Cayó en dos exámenes distintos. ¿Qué ilícitos ves?", "Mijas 2017 y Rincón de la Victoria 2019", 97),
    ("SUP12_Motril2022_patinete_acera_movil_25kmh", "Un patinete por la acera, con el móvil en la mano y a más de 25 km/h. ¿Qué denuncias?", "Motril 2022", 71),
    ("SUP13_VilladelRio2025_rojo_huida_y_moto", "Un turismo se salta un rojo, choca y el conductor huye. Y aparece una moto sin ITV ni seguro.", "Villa del Río 2025", 93),
    ("SUP14_Andujar2023_patinete_menor_y_ciclomotor", "Un patinete con pasajero y un ciclomotor cuyo conductor dice «ya no soplo más». ¿Qué denuncias?", "Andújar 2023", 82),
    ("SUP15_Herrera2018_droga_menores_y_violencia", "Venta de droga a chicos de 15 y 16 años junto a un instituto, un rojo y una negativa a las pruebas. ¿Cuántos delitos ves?", "Herrera 2018", 91),
    ("SUP16_Almonte2018_tres_sujetos_y_bate", "Tres conductores con problemas y un agente agredido con un bate. ¿Qué harías tú?", "Almonte 2018", 106),
]


def caption(escena, conv):
    return (f"🚨 {escena}\n\n"
            "¿Qué harías tú? Escríbelo en comentarios antes de ver la solución 👇\n\n"
            f"Supuesto oficial de {conv}, resuelto paso a paso.\n\n"
            f"{CTA}\n\n"
            "📌 Guárdalo y envíaselo a tu compañero de opos.\n\n"
            "#policialocal #oposicionesandalucia #supuestopractico")


def fecha_de(nombre):
    return dt.date.fromisoformat(nombre[:10])


def main():
    pend = sorted(n for n in os.listdir(COLA) if n[:4].isdigit() and fecha_de(n) >= DESDE)
    normas, pausar = [], []
    for n in pend:
        meta = json.load(open(os.path.join(COLA, n, "meta.json"), encoding="utf-8"))
        (normas if n.endswith("_manana") and meta.get("formato") == "video_norma" else pausar).append((n, meta.get("formato")))
    # nuevo calendario
    plan, d, s, k = [], DESDE, 0, 0
    while s < len(SUP) or k < len(normas):
        if d.day % 2 == 1 and s < len(SUP):
            plan.append((d, "sup", SUP[s])); s += 1
        elif k < len(normas):
            plan.append((d, "norma", normas[k][0])); k += 1
        elif s < len(SUP):
            plan.append((d, "sup", SUP[s])); s += 1
        d += dt.timedelta(days=1)
    print(f"a pausar: {len(pausar)}  ({', '.join(sorted(set(f for _, f in pausar)))})")
    for n, f in pausar: print("  PAUSA", n, f)
    print(f"normas: {len(normas)} | supuestos: {len(SUP)} | ultimo dia: {plan[-1][0]}")
    for d, t, x in plan: print(" ", d, d.strftime("%a"), "SUPUESTO " + x[0] if t == "sup" else "norma    " + x)
    if not APLICAR:
        return print("(simulacion: no se ha cambiado nada)")
    reg = {"at": dt.datetime.now().isoformat(), "pausadas": [], "movidas": [], "nuevas": []}
    ruta_reg = os.path.join(REPO, "estado", "una_al_dia_6-11.json")
    if os.path.exists(ruta_reg): raise SystemExit("ya aplicado")
    for n, _ in pausar:
        dest = os.path.join(PAUSA, n)
        if os.path.exists(dest): raise SystemExit("ya existe en cola_pausada: " + n)
        shutil.move(os.path.join(COLA, n), dest); reg["pausadas"].append(n)
    tmp = os.path.join(REPO, "_tmp_normas"); os.makedirs(tmp)
    for n, _ in normas: shutil.move(os.path.join(COLA, n), os.path.join(tmp, n))
    for d, t, x in plan:
        nombre = f"{d.isoformat()}_manana"; dest = os.path.join(COLA, nombre)
        if t == "norma":
            shutil.move(os.path.join(tmp, x), dest)
            mp = os.path.join(dest, "meta.json"); meta = json.load(open(mp, encoding="utf-8"))
            meta["fecha"] = d.isoformat(); json.dump(meta, open(mp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            reg["movidas"].append([x, nombre])
        else:
            key, escena, conv, dur = x
            os.makedirs(dest)
            shutil.copy2(SRC + key + ".mp4", os.path.join(dest, "reel.mp4"))
            open(os.path.join(dest, "caption.txt"), "w", encoding="utf-8").write(caption(escena, conv))
            meta = {"caso": "", "convocatoria": conv, "duracion_s": dur, "fecha": d.isoformat(), "formato": "video_supuesto",
                    "franja": "manana", "id": "supuesto-" + key, "imagenes": [], "reel": "reel.mp4",
                    "serie": "Supuestos oficiales resueltos en vídeo", "tema": conv}
            json.dump(meta, open(os.path.join(dest, "meta.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            reg["nuevas"].append(nombre)
    os.rmdir(tmp)
    json.dump(reg, open(ruta_reg, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("hecho; registro en", ruta_reg)


main()
