# Byte Capital media

Imágenes públicas de los carruseles de Byte Capital (Instagram), para que Metricool pueda leerlas.

- `posts/<id-de-la-noticia>/NN.jpg`: láminas de cada carrusel, 1080×1350, en orden.
- `tools/render_carousel.py`: convierte un lienzo de diseño (`project/canvas.json` + `project/*.dc.html`) en JPG.
  Uso: `python3 tools/render_carousel.py <carpeta-del-lienzo> posts/<id>`
