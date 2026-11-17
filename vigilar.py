#!/usr/bin/env python3
"""Revisa las apps y avisa por Telegram cuando una se cae o vuelve.
Guarda el ultimo estado en estado.json para avisar solo los cambios."""
import json, os, urllib.request, urllib.parse

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
]
TOKEN, CHAT = os.environ["TG_TOKEN"], os.environ["TG_CHAT"]

def arriba(url):
    for _ in range(2):  # reintenta una vez para no avisar por un tropiezo
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "vigilante-apps"})
            with urllib.request.urlopen(req, timeout=20) as r:
                if r.status < 400:
                    return True
        except Exception:
            pass
    return False

def avisar(texto):
    data = urllib.parse.urlencode({"chat_id": CHAT, "text": texto}).encode()
    urllib.request.urlopen(f"https://api.telegram.org/bot{TOKEN}/sendMessage", data=data, timeout=15)

antes = json.load(open("estado.json")) if os.path.exists("estado.json") else {}
ahora = {n: arriba(u) for n, u in APPS}
for n, u in APPS:
    if n in antes and antes[n] != ahora[n]:
        avisar(f"✅ {n} volvió\n{u}" if ahora[n] else f"🔴 {n} está CAÍDA\n{u}")
if os.environ.get("PRUEBA"):
    avisar("🛰️ Vigilante externo (GitHub) conectado.\n" + "\n".join(
        f"{'✅' if ahora[n] else '🔴'} {n}" for n, _ in APPS))
json.dump(ahora, open("estado.json", "w"), ensure_ascii=False, indent=1)
