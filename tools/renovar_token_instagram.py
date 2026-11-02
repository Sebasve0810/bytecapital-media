"""Renueva el token de larga duración de Instagram (dura 60 días) y lo escribe en un archivo.

Uso: IG_ACCESS_TOKEN=... python3 tools/renovar_token_instagram.py <archivo-de-salida>
El workflow renovar-token-instagram.yml guarda luego ese valor como secreto del repositorio.
"""
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

token = os.environ.get("IG_ACCESS_TOKEN", "")
if not token or len(sys.argv) < 2:
    print("::error::Falta IG_ACCESS_TOKEN o el archivo de salida")
    sys.exit(1)

url = "https://graph.instagram.com/refresh_access_token?" + urllib.parse.urlencode(
    {"grant_type": "ig_refresh_token", "access_token": token})
try:
    with urllib.request.urlopen(url, timeout=60) as r:
        datos = json.loads(r.read().decode())
except urllib.error.HTTPError as e:
    print(f"::error::Instagram rechazó la renovación (HTTP {e.code}): {e.read().decode(errors='replace')[:300]}")
    sys.exit(1)

nuevo = datos.get("access_token")
if not nuevo:
    print("::error::La respuesta no trae access_token")
    sys.exit(1)
print(f"::add-mask::{nuevo}")
with open(sys.argv[1], "w") as f:
    f.write(nuevo)
dias = int(datos.get("expires_in", 0)) // 86400
print(f"Token renovado; vence en {dias} días")
