# Byte Capital media

Imágenes públicas de los carruseles de Byte Capital (Instagram @byte_capital) y la publicación automática con GitHub Actions.

- `posts/<id-de-la-noticia>/NN.jpg`: láminas de cada carrusel, 1080×1350, en orden.
- `posts/<id>/historia.jpg`: versión 1080×1920 de la portada para las historias (la crea `tools/render_historia.py posts/<id>`).
- `tools/render_carousel.py`: convierte un lienzo de diseño (`project/canvas.json` + `project/*.dc.html`) en JPG.
  Uso: `python3 tools/render_carousel.py <carpeta-del-lienzo> posts/<id>`
- `cola/<id>.json`: posts listos para publicar (los agrega el Publicador de Claude).
- `estado/<id>.json`: resultado de cada publicación (lo escribe GitHub Actions).
- `tools/publicar_instagram.py`: publica la cola con la API oficial de Instagram.
- `.github/workflows/publicar-instagram.yml`: corre a las **07:00, 10:00, 12:00 y 18:00** (Bogotá) y publica hasta **5 posts** por franja, de la noticia **más antigua a la más reciente** (campo `creadoEn`), y sube cada uno también a las **historias**.

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
  "historia": "https://raw.githubusercontent.com/Sebasve0810/bytecapital-media/main/posts/2026-11-03-nvidia-resultados/historia.jpg",
  "creadoEn": "2026-11-02T14:30:00Z",
  "encoladoEn": "2026-11-03T08:45:00-05:00"
}
```

`estado/<id>.json` queda con `estado` = `publicada` (con `permalink`), `error` (se reintenta en la siguiente franja, hasta 3 intentos) o `fallida` (no se reintenta; revisar `ultimoError`). El campo `historia` guarda el resultado de la historia: si falla, se reintenta en las franjas siguientes (hasta 3 veces en 24 horas) sin afectar al post. Si la cola no trae `historia`, se usa la primera imagen. La API no permite stickers ni enlaces en las historias.

## Configuración (una sola vez)

La cuenta @byte_capital usa el **inicio de sesión unificado** de Meta (no necesita página de Facebook): el token es de usuario del sistema y **no vence**, así que no hay que renovarlo.

### 1. Token de Instagram

1. En [developers.facebook.com/apps](https://developers.facebook.com/apps) abre la app **Byte Capital** (ya tiene un portfolio comercial y el caso de uso "Administrar mensajes y contenido en Instagram").
2. **Casos de uso → Personalizar → API setup with Unified login**: en el paso 1 crea una configuración con los permisos `instagram_basic` e `instagram_content_publish`.
3. **Roles de la app → Roles**: agrega a @byte_capital como **Evaluador de Instagram** y acepta la invitación en Instagram (Configuración → Apps y sitios web, o instagram.com/accounts/manage_access).
4. Vuelve al paso **2. Generar tokens de acceso**, pulsa **Generar token** junto a @byte_capital y cópialo.

La app puede quedarse en modo desarrollo; no hace falta enviarla a revisión de Meta.

### 2. Secretos en GitHub

En este repositorio: **Settings → Secrets and variables → Actions → New repository secret**.

| Nombre | Valor |
|---|---|
| `IG_ACCESS_TOKEN` | El token del paso 1 |
| `IG_USER_ID` | Opcional. El ID de la cuenta (17841424069892350) ya está en el workflow |

### 3. Prueba

**Actions → Publicar en Instagram → Run workflow → modo `prueba`**. En el resumen debe salir `Cuenta: @byte_capital` y la lista de la cola. Ese modo no publica nada.

## Notas

- La API de Instagram admite hasta 50 publicaciones por día por cuenta; un carrusel cuenta como una.
- GitHub puede retrasar unos minutos las ejecuciones programadas. El workflow arranca 10 minutos antes y espera a la hora exacta.
- Si una ejecución falla, GitHub te avisa por correo.
