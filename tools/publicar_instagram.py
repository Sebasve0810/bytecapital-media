"""Publica en Instagram los carruseles que están en la cola del repositorio.

Lo corre el workflow .github/workflows/publicar-instagram.yml en las franjas del día.

Cola (la escribe el Publicador de Claude, este script nunca la modifica):
  cola/<id>.json  {"id", "titulo", "texto", "imagenes": [urls raw de GitHub], "historia": url 1080x1920, "encoladoEn"}
  Cada post publicado sube también una historia con `historia` (si falta, con la primera imagen).
Estado (lo escribe este script):
  estado/<id>.json  {"id", "estado", "intentos", "publicadaEn", "mediaId", "permalink", "ultimoError",
                     "historia": {"estado", "intentos", "mediaId", "ultimoError"}, ...}
  estado = publicada | error (se reintenta en la siguiente franja) | fallida (no se reintenta)
  Una historia que falla se reintenta en las franjas siguientes (hasta 3 intentos, máximo 24 horas);
  nunca cambia el estado del post.

Variables de entorno:
  IG_ACCESS_TOKEN   token de acceso (obligatorio)
  IG_USER_ID        id de la cuenta de Instagram (obligatorio con el inicio de sesión unificado;
                    si falta se usa /me, que solo sirve con tokens de usuario de Instagram)
  IG_API_BASE       por defecto https://graph.facebook.com/v26.0 (inicio de sesión unificado);
                    con tokens de usuario de Instagram: https://graph.instagram.com/v26.0
  MODO              publicar (por defecto) | prueba (no publica: valida token, imágenes y muestra el plan)
  MAX_POR_FRANJA    máximo de posts por ejecución (por defecto 5)
  SEPARACION_SEGUNDOS  espera entre un post y el siguiente (por defecto 60)
  FRANJAS           horas de publicación en Bogotá (por defecto 10:00,12:00,18:00)
  ESPERAR_FRANJA    1 = si la ejecución llega antes de una franja (hasta 20 min), espera a la hora exacta
  MAX_INTENTOS      intentos antes de marcar fallida (por defecto 3)
"""
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

BOGOTA = timezone(timedelta(hours=-5), "America/Bogota")
RAIZ = os.environ.get("REPO_ROOT", os.getcwd())
DIR_COLA = os.path.join(RAIZ, "cola")
DIR_ESTADO = os.path.join(RAIZ, "estado")
API = os.environ.get("IG_API_BASE", "https://graph.facebook.com/v26.0").rstrip("/")
TOKEN = os.environ.get("IG_ACCESS_TOKEN", "")
MODO = os.environ.get("MODO", "publicar").strip().lower()
MAX_POR_FRANJA = int(os.environ.get("MAX_POR_FRANJA", "5"))
SEPARACION = int(os.environ.get("SEPARACION_SEGUNDOS", "60"))
FRANJAS = [f.strip() for f in os.environ.get("FRANJAS", "10:00,12:00,18:00").split(",") if f.strip()]
ESPERAR_FRANJA = os.environ.get("ESPERAR_FRANJA", "0") == "1"
MAX_INTENTOS = int(os.environ.get("MAX_INTENTOS", "3"))
POLL_SEGUNDOS = int(os.environ.get("POLL_SEGUNDOS", "10"))
POLL_MAX_SEGUNDOS = int(os.environ.get("POLL_MAX_SEGUNDOS", "300"))

resumen = []


def log(msg):
    print(msg, flush=True)
    resumen.append(msg)


def ahora():
    return datetime.now(BOGOTA)


def iso(dt=None):
    return (dt or ahora()).isoformat(timespec="seconds")


class ErrorGraph(Exception):
    """Error que devuelve la API (respuesta clara: no hubo publicación)."""


class ErrorRed(Exception):
    """Fallo de red o respuesta inesperada (no se sabe qué pasó)."""


def llamar(metodo, ruta, datos=None, params=None, reintentos=2):
    url = ruta if ruta.startswith("http") else f"{API}/{ruta.lstrip('/')}"
    if params:
        url += ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    cuerpo = json.dumps(datos).encode() if datos is not None else None
    for intento in range(reintentos + 1):
        req = urllib.request.Request(url, data=cuerpo, method=metodo)
        req.add_header("Authorization", f"Bearer {TOKEN}")
        if cuerpo is not None:
            req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode() or "{}")
        except urllib.error.HTTPError as e:
            texto = e.read().decode(errors="replace")
            try:
                err = json.loads(texto).get("error", {})
                msg = f"{err.get('message', texto)} (code {err.get('code')}, subcode {err.get('error_subcode')})"
            except Exception:
                msg = texto[:300]
            if e.code >= 500 and intento < reintentos:
                time.sleep(5 * (intento + 1))
                continue
            if e.code >= 500:
                raise ErrorRed(f"HTTP {e.code}: {msg}")
            raise ErrorGraph(f"HTTP {e.code}: {msg}")
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            if intento < reintentos:
                time.sleep(5 * (intento + 1))
                continue
            raise ErrorRed(str(e))


def leer_json(ruta):
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)


def guardar_estado(est):
    os.makedirs(DIR_ESTADO, exist_ok=True)
    est["actualizadoEn"] = iso()
    with open(os.path.join(DIR_ESTADO, f"{est['id']}.json"), "w", encoding="utf-8") as f:
        json.dump(est, f, ensure_ascii=False, indent=2)
        f.write("\n")


def pendientes():
    if not os.path.isdir(DIR_COLA):
        return []
    lista = []
    for nombre in sorted(os.listdir(DIR_COLA)):
        if not nombre.endswith(".json"):
            continue
        try:
            post = leer_json(os.path.join(DIR_COLA, nombre))
        except Exception as e:
            log(f"⚠️ {nombre}: JSON inválido ({e}), se omite")
            continue
        post.setdefault("id", nombre[:-5])
        ruta_est = os.path.join(DIR_ESTADO, f"{post['id']}.json")
        est = leer_json(ruta_est) if os.path.exists(ruta_est) else None
        if est and est.get("estado") in ("publicada", "fallida"):
            continue
        if est and est.get("estado") == "error" and est.get("intentos", 0) >= MAX_INTENTOS:
            continue
        lista.append((post, est or {"id": post["id"], "intentos": 0}))
    lista.sort(key=lambda pe: (pe[0].get("encoladoEn", ""), pe[0]["id"]))
    return lista


def historias_pendientes():
    """Posts ya publicados cuya historia falló y aún tiene intentos (solo de las últimas 24 horas)."""
    lista = []
    if not os.path.isdir(DIR_ESTADO):
        return lista
    limite = ahora() - timedelta(hours=24)
    for nombre in sorted(os.listdir(DIR_ESTADO)):
        if not nombre.endswith(".json"):
            continue
        est = leer_json(os.path.join(DIR_ESTADO, nombre))
        h = est.get("historia")
        if est.get("estado") != "publicada" or not isinstance(h, dict) or h.get("estado") != "error":
            continue
        if h.get("intentos", 0) >= MAX_INTENTOS:
            continue
        try:
            if datetime.fromisoformat(est.get("publicadaEn", "")) < limite:
                continue
        except ValueError:
            continue
        ruta_cola = os.path.join(DIR_COLA, nombre)
        if os.path.exists(ruta_cola):
            lista.append((leer_json(ruta_cola), est))
    return lista


def url_historia(post):
    return post.get("historia") or post["imagenes"][0]


def url_responde(url):
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=30) as r:
            if r.status != 200:
                return f"la imagen {url} responde {r.status}"
    except Exception as e:
        return f"la imagen {url} no responde ({e})"
    return None


def validar(post):
    imgs = post.get("imagenes") or []
    texto = post.get("texto") or ""
    if not 1 <= len(imgs) <= 20:
        return f"debe tener entre 1 y 20 imágenes (tiene {len(imgs)})"
    if len(texto) > 2200:
        return f"el texto supera 2.200 caracteres ({len(texto)})"
    if texto.count("#") > 30:
        return "el texto tiene más de 30 hashtags"
    for url in imgs:
        problema = url_responde(url)
        if problema:
            return problema
    return None


def esperar_contenedor(cid):
    limite = time.time() + POLL_MAX_SEGUNDOS
    while True:
        st = llamar("GET", cid, params={"fields": "status_code"}).get("status_code")
        if st == "FINISHED":
            return
        if st in ("ERROR", "EXPIRED"):
            raise ErrorGraph(f"el contenedor {cid} quedó en {st}")
        if time.time() > limite:
            raise ErrorGraph(f"el contenedor {cid} no terminó de procesar (estado {st})")
        time.sleep(POLL_SEGUNDOS)


def publicar(uid, post):
    imgs, texto = post["imagenes"], post.get("texto", "")
    if len(imgs) == 1:
        cid = llamar("POST", f"{uid}/media", {"image_url": imgs[0], "caption": texto})["id"]
    else:
        hijos = [llamar("POST", f"{uid}/media", {"image_url": u, "is_carousel_item": True})["id"] for u in imgs]
        cid = llamar("POST", f"{uid}/media",
                     {"media_type": "CAROUSEL", "children": ",".join(hijos), "caption": texto})["id"]
    esperar_contenedor(cid)
    try:
        media_id = llamar("POST", f"{uid}/media_publish", {"creation_id": cid}, reintentos=0)["id"]
    except ErrorRed as e:
        # No se sabe si quedó publicado: no reintentar para no duplicar.
        raise ErrorRed(f"no se sabe si se publicó ({e}); revísalo en Instagram") from e
    permalink = ""
    try:
        permalink = llamar("GET", media_id, params={"fields": "permalink"}).get("permalink", "")
    except Exception:
        pass
    return media_id, permalink


def publicar_historia(uid, post, est):
    """Sube la historia del post. Nunca cambia el estado del post; guarda el resultado en est['historia']."""
    h = est.get("historia") if isinstance(est.get("historia"), dict) else {}
    h["intentos"] = h.get("intentos", 0) + 1
    url = url_historia(post)
    try:
        problema = url_responde(url)
        if problema:
            raise ErrorGraph(problema)
        cid = llamar("POST", f"{uid}/media", {"image_url": url, "media_type": "STORIES"})["id"]
        esperar_contenedor(cid)
        try:
            h["mediaId"] = llamar("POST", f"{uid}/media_publish", {"creation_id": cid}, reintentos=0)["id"]
        except ErrorRed as e:
            h["intentos"] = MAX_INTENTOS  # no reintentar para no duplicar la historia
            raise ErrorRed(f"no se sabe si se publicó ({e}); revísala en Instagram") from e
        h.update({"estado": "publicada", "publicadaEn": iso(), "ultimoError": ""})
        ok = True
    except (ErrorGraph, ErrorRed) as e:
        h.update({"estado": "error", "ultimoError": str(e)})
        ok = False
    est["historia"] = h
    guardar_estado(est)
    if ok:
        log(f"   ↳ historia publicada")
    else:
        log(f"   ↳ ❌ historia de {post['id']}: {h['ultimoError']} (intento {h['intentos']})")
    return ok


def esperar_hasta_franja():
    t = ahora()
    for f in FRANJAS:
        h, m = map(int, f.split(":"))
        franja = t.replace(hour=h, minute=m, second=0, microsecond=0)
        falta = (franja - t).total_seconds()
        if 0 < falta <= 20 * 60:
            print(f"Esperando {int(falta)} s hasta la franja de las {f}", flush=True)
            time.sleep(falta)
            return


def escribir_resumen():
    ruta = os.environ.get("GITHUB_STEP_SUMMARY")
    if ruta:
        with open(ruta, "a", encoding="utf-8") as f:
            f.write("## Publicación en Instagram\n\n" + "\n".join(f"- {l}" for l in resumen) + "\n")


def main():
    if not TOKEN:
        log("❌ Falta el secreto IG_ACCESS_TOKEN")
        return 1
    uid = os.environ.get("IG_USER_ID", "").strip()
    try:
        if uid:
            # Inicio de sesión unificado (graph.facebook.com): el token es de usuario del sistema,
            # así que "me" no devuelve la cuenta de Instagram; se consulta por su id.
            me = llamar("GET", uid, params={"fields": "username"})
        else:
            # Inicio de sesión de Instagram (graph.instagram.com): "me" es la cuenta.
            me = llamar("GET", "me", params={"fields": "user_id,username"})
            uid = me.get("user_id") or me.get("id")
    except Exception as e:
        log(f"❌ El token o el ID de la cuenta no funcionan: {e}")
        return 1
    log(f"Cuenta: @{me.get('username', '?')} (id {uid}) · modo {MODO}")

    lista = pendientes()
    reintentos_historia = historias_pendientes()
    if not lista and not reintentos_historia:
        log("Sin posts en cola")
        return 0
    tanda = lista[:MAX_POR_FRANJA]
    log(f"En cola: {len(lista)} · se procesan {len(tanda)} (máximo {MAX_POR_FRANJA} por franja)")

    if MODO == "prueba":
        for post, _ in tanda:
            problema = validar(post) or url_responde(url_historia(post))
            log(f"{'✅' if not problema else '❌'} {post['id']}: {len(post.get('imagenes', []))} imagen(es)"
                + (" + historia" if post.get("historia") else " + historia con la portada")
                + (f" · {problema}" if problema else ""))
        return 0

    if ESPERAR_FRANJA:
        esperar_hasta_franja()

    fallos = 0
    for post, est in reintentos_historia:
        log(f"Reintentando la historia de {post['id']}")
        if not publicar_historia(uid, post, est):
            fallos += 1
    for i, (post, est) in enumerate(tanda):
        if i > 0 and SEPARACION > 0:
            time.sleep(SEPARACION)
        est["intentos"] = est.get("intentos", 0) + 1
        problema = validar(post)
        try:
            if problema:
                raise ErrorGraph(problema)
            media_id, permalink = publicar(uid, post)
        except ErrorGraph as e:
            fallos += 1
            est["estado"] = "fallida" if est["intentos"] >= MAX_INTENTOS else "error"
            est["ultimoError"] = str(e)
            guardar_estado(est)
            log(f"❌ {post['id']}: {e} (intento {est['intentos']}, queda {est['estado']})")
            continue
        except ErrorRed as e:
            fallos += 1
            est["estado"] = "fallida"
            est["ultimoError"] = str(e)
            guardar_estado(est)
            log(f"❌ {post['id']}: {e}")
            continue
        est.update({"estado": "publicada", "publicadaEn": iso(), "mediaId": media_id,
                    "permalink": permalink, "ultimoError": ""})
        guardar_estado(est)
        log(f"✅ {post['id']} publicado {permalink}")
        if not publicar_historia(uid, post, est):
            fallos += 1
    return 1 if fallos else 0


if __name__ == "__main__":
    codigo = main()
    escribir_resumen()
    sys.exit(codigo)
