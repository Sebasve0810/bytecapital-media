"""render_carousel.py SRC_DIR OUT_DIR [BLOBDIR]
SRC_DIR contains project/canvas.json + project/*.dc.html (a Design canvas).
Renders each board in canvas order to OUT_DIR/NN.jpg (1080x1350)."""
import sys, os, re, json, html
from playwright.sync_api import sync_playwright
CH = '/opt/pw-browsers/chromium-1194/chrome-linux/chrome'
FONTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fonts')
src, out = sys.argv[1], sys.argv[2]
blobdir = sys.argv[3] if len(sys.argv) > 3 else None
os.makedirs(out, exist_ok=True)
canvas = json.load(open(os.path.join(src, 'project', 'canvas.json')))
order = canvas.get('order') or list(canvas['boards'].keys())
ff = ''.join(
    f"@font-face{{font-family:'Space Grotesk';font-weight:{w};src:url('file://{os.path.abspath(FONTS)}/space-grotesk-latin-{w}-normal.woff2') format('woff2')}}"
    f"@font-face{{font-family:'Space Grotesk';font-weight:{w};unicode-range:U+0100-024F;src:url('file://{os.path.abspath(FONTS)}/space-grotesk-latin-ext-{w}-normal.woff2') format('woff2')}}"
    for w in (300, 400, 500, 600, 700))
def prep(s):
    m = re.search(r"data-props='([^']*)'", s)
    accent = '#19E68C'
    if m:
        try:
            props = json.loads(html.unescape(m.group(1)))
            accent = props.get('accent', {}).get('default', accent) or accent
        except Exception:
            pass
    s = s.replace('{{accent}}', accent)
    s = re.sub(r'<script[^>]*support\.js[^>]*></script>', '', s)
    s = re.sub(r'<script type="text/x-dc".*?</script>', '', s, flags=re.S)
    s = re.sub(r'<link[^>]*fonts\.(googleapis|gstatic)\.com[^>]*>', '', s)
    s = s.replace('<x-dc>', '').replace('</x-dc>', '').replace('<helmet>', '').replace('</helmet>', '')
    s = s.replace('<style>', '<style>' + ff, 1) if '<style>' in s else s.replace('</head>', f'<style>{ff}</style></head>')
    s = s.replace('@bytecapital<', '@byte_capital<')
    if blobdir:
        s = re.sub(r'/_blob/([0-9a-f]{32})', lambda mm: 'file://' + os.path.join(os.path.abspath(blobdir), mm.group(1)), s)
    return s
with sync_playwright() as p:
    br = p.chromium.launch(executable_path=CH, args=['--no-sandbox', '--allow-file-access-from-files'])
    for i, name in enumerate(order, 1):
        b = canvas['boards'][name]
        pg = br.new_page(viewport={'width': b['w'], 'height': b['h']})
        tmp = os.path.join(out, f'.{i:02d}.html')
        open(tmp, 'w').write(prep(open(os.path.join(src, 'project', name)).read()))
        pg.goto('file://' + os.path.abspath(tmp)); pg.evaluate('document.fonts.ready'); pg.wait_for_timeout(300)
        bad = pg.evaluate("""() => [...document.querySelectorAll('img')].filter(i => !i.complete || i.naturalWidth === 0).length""")
        pg.screenshot(path=os.path.join(out, f'{i:02d}.jpg'), type='jpeg', quality=92)
        os.remove(tmp); pg.close()
        print(name, '->', f'{i:02d}.jpg', 'BROKEN_IMG' if bad else '')
    br.close()
