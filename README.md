# Byte Capital media

Imágenes públicas de los carruseles de Byte Capital (Instagram @byte_capital) y la publicación automática con GitHub Actions.

- `posts/<id-de-la-noticia>/NN.jpg`: láminas de cada carrusel, 1080×1350, en orden.
- `tools/render_carousel.py`: convierte un lienzo de diseño (`project/canvas.json` + `project/*.dc.html`) en JPG.
  Uso: `python3 tools/render_carousel.py <carpeta-del-lienzo> posts/<id>`
- `cola/<id>.json`: posts listos para publicar (los agrega el Publicador de Claude).
- `estado/<id>.json`: resultado de cada publicación (lo escribe GitHub Actions).
- `tools/publicar_instagram.py`: publica la cola con la API oficial de Instagram.
- `.github/workflows/publicar-instagram.yml`: corre a las **10:00, 12:00 y 18:00** (Bogotá) y publica hasta **5 posts** por franja, en orden de llegada.
- `.github/workflows/renovar-token-instagram.yml`: renueva el token de Instagram los días 1 y 15 de cada mes.

## Formato de la cola

`cola/<id>.json`:

```json
{
  "id": "2026-11-03-nvidia-resultados",
  "titulo": "Nvidia supera expectativas",
  "texto": "Descripción del post...\n\n#bytecapital #nvidia ...",
  "imagenes": [
    "https://raw.githubusercontent.com/Sebasve0810/bytecapital-media/main/posts/2026-11-03-nvidia-resultados/01.jpg"
  ],
  "encoladoEn": "2026-11-03T08:45:00-05:00"
}
```

`estado/<id>.json` queda con `estado` = `publicada` (con `permalink`), `error` (se reintenta en la siguiente franja, hasta 3 intentos) o `fallida` (no se reintenta; revisar `ultimoError`).

## Configuración (una sola vez)

### 1. Token de Instagram

1. Entra a [developers.facebook.com](https://developers.facebook.com/apps) con tu cuenta de Facebook y crea una app (**Crear app**). Elige el caso de uso de Instagram (administrar contenido en Instagram) y tipo **Negocio**.
2. Dentro de la app, ve a **Instagram → Configuración de la API con inicio de sesión de Instagram**.
3. En **Generar tokens de acceso**, pulsa **Agregar cuenta**, inicia sesión con @byte_capital y acepta los permisos (`instagram_business_basic` e `instagram_business_content_publish`).
4. Pulsa **Generar token** y cópialo. Es un token de larga duración (60 días); el workflow de renovación lo mantiene vivo.

Para publicar solo en tu propia cuenta, la app puede quedarse en modo desarrollo; no hace falta enviarla a revisión de Meta.

### 2. Secretos en GitHub

En este repositorio: **Settings → Secrets and variables → Actions → New repository secret**.

| Nombre | Valor |
|---|---|
| `IG_ACCESS_TOKEN` | El token del paso 1 |
| `GH_PAT` | Token de GitHub para que la renovación pueda actualizar `IG_ACCESS_TOKEN` (ver abajo) |
| `IG_USER_ID` | Opcional. Si no lo pones, se obtiene solo |

Para `GH_PAT`: [github.com/settings/personal-access-tokens](https://github.com/settings/personal-access-tokens) → **Generate new token** (fine-grained) → **Only select repositories**: `bytecapital-media` → **Repository permissions → Secrets: Read and write** → elige la mayor duración disponible → genera y copia.

### 3. Prueba

**Actions → Publicar en Instagram → Run workflow → modo `prueba`**. En el resumen debe salir `Cuenta: @byte_capital` y la lista de la cola. Ese modo no publica nada.

Luego, **Actions → Renovar token de Instagram → Run workflow** para comprobar la renovación (el token debe tener al menos 24 horas).

## Notas

- La API de Instagram admite hasta 50 publicaciones por día por cuenta; un carrusel cuenta como una.
- GitHub puede retrasar unos minutos las ejecuciones programadas. El workflow arranca 10 minutos antes y espera a la hora exacta.
- Si una ejecución falla, GitHub te avisa por correo.
