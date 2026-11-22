#!/usr/bin/env python3
"""Сборка АгроДозор_Живая_Страница.html — самодостаточный файл.

Инлайнит в onepage.html: шрифты (woff2 → data URI), three.min.js,
3D-модель (model.json как JS-объект, model.bin как base64) и все <img src>.
Запуск: python3 build_standalone.py
"""
import base64
import json
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

SRC = 'onepage.html'
DST = 'АгроДозор_Живая_Страница.html'

with open(SRC, 'r', encoding='utf-8') as f:
    t = f.read()

# --- 1) шрифты ---
font_re = re.compile(r"url\('assets/fonts/([^']+\.woff2)'\)")
fonts = set(font_re.findall(t))
for fn in sorted(fonts):
    with open('assets/fonts/' + fn, 'rb') as f:
        b64 = base64.b64encode(f.read()).decode('ascii')
    t = t.replace("assets/fonts/%s" % fn, 'data:font/woff2;base64,' + b64)
print('fonts inlined:', len(fonts))

# --- 2) three.min.js ---
with open('assets/three.min.js', 'r', encoding='utf-8') as f:
    three = f.read()
assert '<script src="assets/three.min.js"></script>' in t
t = t.replace('<script src="assets/three.min.js"></script>', '<script>\n' + three + '\n</script>')
print('three.min.js inlined:', len(three), 'chars')

# --- 3) 3D-модель ---
with open('assets/3d/model.json', 'r', encoding='utf-8') as f:
    meta = json.load(f)
with open('assets/3d/model.bin', 'rb') as f:
    bin_b64 = base64.b64encode(f.read()).decode('ascii')
inject = ('<script>\nconst EMBEDDED_MODEL_META = ' + json.dumps(meta, ensure_ascii=False) + ';\n'
          + 'const EMBEDDED_MODEL_B64 = "' + bin_b64 + '";\n</script>\n')
lm = t.find('function loadMachine()')
script_start = t.rfind('<script>', 0, lm)
t = t[:script_start] + inject + t[script_start:]
old_fetch = """  Promise.all([
    fetch('assets/3d/model.json').then(function(r){ if (!r.ok) throw new Error('meta'); return r.json(); }),
    fetch('assets/3d/model.bin').then(function(r){ if (!r.ok) throw new Error('bin'); return r.arrayBuffer(); })
  ]).then(function(res){
    var meta = res[0], buf = res[1];"""
new_inline = """  Promise.resolve([EMBEDDED_MODEL_META, (function(){ var s = atob(EMBEDDED_MODEL_B64); var b = new Uint8Array(s.length); for (var i = 0; i < s.length; i++) b[i] = s.charCodeAt(i); return b.buffer; })()])
  .then(function(res){
    var meta = res[0], buf = res[1];"""
assert old_fetch in t, 'loadMachine fetch pattern not found'
t = t.replace(old_fetch, new_inline, 1)
print('model inlined: bin b64', len(bin_b64), 'chars')

# --- 4) все локальные <img> ---
img_re = re.compile(r'(?:src|srcset)="(assets/img/[^"]+)"')
imgs = set(img_re.findall(t))
mime = {'jpg': 'image/jpeg', 'jpeg': 'image/jpeg', 'png': 'image/png', 'webp': 'image/webp', 'svg': 'image/svg+xml'}
for fn in sorted(imgs):
    ext = fn.rsplit('.', 1)[-1].lower()
    with open(fn, 'rb') as f:
        b64 = base64.b64encode(f.read()).decode('ascii')
    t = t.replace('"%s"' % fn, '"data:%s;base64,%s"' % (mime.get(ext, 'application/octet-stream'), b64))
print('images inlined:', len(imgs))

left = re.findall(r'(?:src|href)="(assets/[^"]+)"', t)
print('remaining asset refs:', left if left else 'NONE')
with open(DST, 'w', encoding='utf-8') as f:
    f.write(t)
print('written', DST, '=', len(t), 'bytes')
