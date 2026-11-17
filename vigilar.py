#!/usr/bin/env python3
"""Vigilante externo: revisa las apps desde GitHub y avisa por Telegram.

- Avisa cuando una app se cae o vuelve (con cuanto tiempo estuvo caida).
- Recuerda cada 30 min si sigue caida.
- Avisa si una app va lenta (> 10 s).
- Detecta paginas "vacias" (ej. "Site Not Found") aunque respondan 200.
- Una vez al dia: resumen, y aviso si el certificado HTTPS o el dominio
  vencen en menos de 15 dias.
Guarda todo en estado.json (el workflow lo sube al repo).
"""
import json, os, socket, ssl, time, urllib.request, urllib.parse, urllib.error
from datetime import datetime, timezone, timedelta

APPS = [
    ("Matrimonio", "https://boda.26092003.xyz"),
    ("Pizza", "https://pizza4estaciones.com"),
    ("AsistApp", "https://asistencia.26092003.xyz"),
    ("Sistema Escolar", "https://escuela.26092003.xyz"),
    ("Airtek", "https://samipirela26-creator.github.io/airtek-evaluaciones/"),
    ("Mi Carro", "https://mi-carro-sanuel.web.app"),
    ("SaaS", "https://miapp-saas-sanuel.web.app"),
    ("Mis Detallitos", "https://mis-detallitos.web.app"),
    ("Kamilux", "https://kamilux-store.web.app"),
    ("Nuestra Lista", "https://nuestra-lista-32720.web.app"),
]
# Dominios propios a los que vigilar el vencimiento (los .web.app/github.io no)
DOMINIOS = ["26092003.xyz", "pizza4estaciones.com"]
# Si la pagina contiene alguno de estos textos, se considera caida
TEXTOS_MALOS = ["Site Not Found", "Bad Gateway", "Service Unavailable",
                "Application error", "There isn't a GitHub Pages site here"]

LENTA_SEG = 10
RECORDAR_MIN = 30
AVISO_DIAS = 15
HORA_RESUMEN_VE = 8          # 8 am Venezuela (UTC-4)
VE = timezone(timedelta(hours=-4))

TOKEN, CHAT = os.environ["TG_TOKEN"], os.environ["TG_CHAT"]
AHORA = time.time()


def avisar(texto):
    data = urllib.parse.urlencode({"chat_id": CHAT, "text": texto}).encode()
    urllib.request.urlopen(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                           data=data, timeout=15)


def revisar(url):
    """Devuelve (arriba, segundos, motivo). Reintenta una vez."""
    motivo = ""
    for _ in range(2):
        t0 = time.time()
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "vigilante-apps"})
            with urllib.request.urlopen(req, timeout=25) as r:
                cuerpo = r.read(200_000).decode("utf-8", "ignore")
                seg = time.time() - t0
                malo = next((t for t in TEXTOS_MALOS if t in cuerpo), None)
                if malo:
                    motivo = f'muestra "{malo}"'
                    continue
                return True, seg, ""
        except urllib.error.HTTPError as e:
            motivo = f"error {e.code}"
        except Exception as e:
            motivo = type(e).__name__
    return False, None, motivo


def duracion(seg):
    m = int(seg // 60)
    if m < 60:
        return f"{m} min"
    h, m = divmod(m, 60)
    return f"{h} h {m} min" if h < 24 else f"{h // 24} d {h % 24} h"


def dias_certificado(url):
    host = urllib.parse.urlparse(url).hostname
    ctx = ssl.create_default_context()
    with socket.create_connection((host, 443), timeout=10) as s:
        with ctx.wrap_socket(s, server_hostname=host) as t:
            fin = ssl.cert_time_to_seconds(t.getpeercert()["notAfter"])
    return int((fin - AHORA) // 86400)


def dias_dominio(dominio):
    url = f"https://rdap.org/domain/{dominio}"
    req = urllib.request.Request(url, headers={"Accept": "application/rdap+json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        datos = json.load(r)
    for ev in datos.get("events", []):
        if ev.get("eventAction") == "expiration":
            fin = datetime.fromisoformat(ev["eventDate"].replace("Z", "+00:00"))
            return int((fin.timestamp() - AHORA) // 86400)
    return None


try:
    E = json.load(open("estado.json"))
except Exception:
    E = {}
if "apps" not in E:                       # formato viejo: {nombre: bool}
    E = {"apps": {n: {"arriba": v} for n, v in E.items() if isinstance(v, bool)}}
apps = E["apps"]

# ---------- caidas, vueltas, recordatorios y lentitud ----------
for nombre, url in APPS:
    arriba, seg, motivo = revisar(url)
    a = apps.setdefault(nombre, {"arriba": arriba})
    antes = a.get("arriba")
    if antes is not None and antes != arriba:
        if arriba:
            desde = a.get("caida_desde")
            extra = f" (estuvo caída {duracion(AHORA - desde)})" if desde else ""
            avisar(f"✅ {nombre} volvió{extra}\n{url}")
            a.pop("caida_desde", None); a.pop("recordado", None)
        else:
            a["caida_desde"] = a["recordado"] = AHORA
            avisar(f"🔴 {nombre} está CAÍDA ({motivo})\n{url}")
    elif not arriba and a.get("caida_desde"):
        if AHORA - a.get("recordado", 0) >= RECORDAR_MIN * 60:
            a["recordado"] = AHORA
            avisar(f"⏰ {nombre} sigue CAÍDA hace {duracion(AHORA - a['caida_desde'])} ({motivo})\n{url}")
    a["arriba"] = arriba

    lenta = bool(arriba and seg and seg > LENTA_SEG)
    if lenta and not a.get("lenta"):
        avisar(f"🐢 {nombre} está lenta: tardó {seg:.0f} s en responder\n{url}")
    elif not lenta and a.get("lenta") and arriba:
        avisar(f"⚡ {nombre} ya responde normal")
    a["lenta"] = lenta
    a["seg"] = round(seg, 1) if seg else None

# ---------- una vez al dia: resumen + certificados + dominios ----------
hoy = datetime.now(VE)
toca_diario = (hoy.hour >= HORA_RESUMEN_VE and E.get("ultimo_diario") != hoy.date().isoformat())
if toca_diario or os.environ.get("PRUEBA"):
    E["ultimo_diario"] = hoy.date().isoformat()
    problemas = []
    for nombre, url in APPS:
        try:
            d = dias_certificado(url)
            if d < AVISO_DIAS:
                problemas.append(f"🔒 Certificado de {nombre} vence en {d} días")
        except Exception as e:
            problemas.append(f"🔒 No pude leer el certificado de {nombre} ({type(e).__name__})")
    for dom in DOMINIOS:
        try:
            d = dias_dominio(dom)
            if d is not None and d < AVISO_DIAS:
                problemas.append(f"🌐 El dominio {dom} vence en {d} días. ¡Renuévalo!")
            E.setdefault("dominios", {})[dom] = d
        except Exception:
            pass
    ok = sum(1 for n, _ in APPS if apps[n]["arriba"])
    lineas = [f"{'✅' if apps[n]['arriba'] else '🔴'} {n}"
              + (f" · {apps[n]['seg']} s" if apps[n].get("seg") else "") for n, _ in APPS]
    titulo = "🛰️ Prueba del vigilante" if os.environ.get("PRUEBA") else "☀️ Resumen diario"
    doms = " · ".join(f"{k}: {v} d" for k, v in E.get("dominios", {}).items() if v is not None)
    avisar(f"{titulo}: {ok}/{len(APPS)} apps arriba\n" + "\n".join(lineas)
           + (f"\n\n🌐 Dominios vencen en: {doms}" if doms else "")
           + ("\n\n" + "\n".join(problemas) if problemas else "")
           + "\n\nSi un día no llega este resumen, el vigilante dejó de funcionar.")

json.dump(E, open("estado.json", "w"), ensure_ascii=False, indent=1)
