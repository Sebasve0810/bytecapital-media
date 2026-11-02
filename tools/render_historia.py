"""render_historia.py POST_DIR
Crea POST_DIR/historia.jpg (1080x1920) para las historias de Instagram a partir de la portada POST_DIR/01.jpg:
fondo negro con cuadrícula, etiqueta "NUEVO POST" en verde, la portada al centro y "@byte_capital" abajo.
Respeta las zonas seguras de las historias (unos 250 px arriba y abajo)."""
import glob
import os
import sys
from playwright.sync_api import sync_playwright

CH = (sorted(glob.glob('/opt/pw-browsers/chromium-*/chrome-linux*/chrome')) or [None])[-1]
FONTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fonts')
post = os.path.abspath(sys.argv[1])
portada = os.path.join(post, '01.jpg')
if not os.path.exists(portada):
    sys.exit(f'No existe {portada}')

ff = ''.join(
    f"@font-face{{font-family:'SG';font-weight:{w};src:url('file://{FONTS}/space-grotesk-latin-{w}-normal.woff2') format('woff2')}}"
    for w in (500, 700))
html = f"""<!doctype html><html><head><meta charset="utf-8"><style>{ff}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{width:1080px;height:1920px;background:#0D0D0D;font-family:'SG',sans-serif;color:#fff;position:relative;overflow:hidden}}
.grid{{position:absolute;inset:0;opacity:.5;background-image:linear-gradient(#1c1c1c 1px,transparent 1px),linear-gradient(90deg,#1c1c1c 1px,transparent 1px);background-size:40px 40px}}
.glow{{position:absolute;width:760px;height:760px;left:160px;top:560px;border-radius:50%;background:#19E68C;filter:blur(160px);opacity:.22}}
.kicker{{position:absolute;top:262px;left:0;right:0;text-align:center}}
.kicker span{{display:inline-block;background:#19E68C;color:#0D0D0D;font-weight:700;font-size:40px;letter-spacing:.16em;padding:14px 34px;border-radius:999px}}
.portada{{position:absolute;top:372px;left:60px;width:960px;height:1200px;border-radius:28px;overflow:hidden;border:3px solid #2A2A2A;box-shadow:0 30px 80px rgba(0,0,0,.6)}}
.portada img{{width:100%;height:100%;object-fit:cover;display:block}}
.pie{{position:absolute;top:1606px;left:0;right:0;text-align:center}}
.pie .a{{font-weight:500;font-size:38px;color:#bdbdbd}}
.pie .b{{font-weight:700;font-size:46px;letter-spacing:.06em;margin-top:10px}}
.pie .b em{{font-style:normal;color:#19E68C}}
</style></head><body><div class="grid"></div><div class="glow"></div>
<div class="kicker"><span>NUEVO POST</span></div>
<div class="portada"><img src="file://{portada}"></div>
<div class="pie"><div class="a">Míralo completo en el perfil</div><div class="b"><em>@</em>byte_capital</div></div>
</body></html>"""

tmp = os.path.join(post, '.historia.html')
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(html)
with sync_playwright() as p:
    br = p.chromium.launch(executable_path=CH, args=['--no-sandbox', '--allow-file-access-from-files'])
    pg = br.new_page(viewport={'width': 1080, 'height': 1920})
    pg.goto('file://' + tmp)
    pg.evaluate('document.fonts.ready')
    pg.wait_for_timeout(300)
    if pg.evaluate("() => { const i = document.querySelector('img'); return !i.complete || i.naturalWidth === 0 }"):
        print('BROKEN_IMG')
    pg.screenshot(path=os.path.join(post, 'historia.jpg'), type='jpeg', quality=92)
    br.close()
os.remove(tmp)
print('historia.jpg lista')
