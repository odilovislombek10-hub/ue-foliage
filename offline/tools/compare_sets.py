"""Compare two shot sets side by side (A left, B right) + per-shot luminance / shadow colour numbers.

Usage:  python compare_sets.py <prefixA> <prefixB> [names...]
Reads <Project>/Saved/Screenshots/WindowsEditor/<prefix><name>.png for names (default: the 7-shot audit set
CINE TA TB EYE0..EYE3), writes work/compare/setcmp.png. Rule used on Zaliniy: keep a change only if EVERY shot
improves (no trade-offs). Origin: setcmp.py."""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'lib'))
import env  # noqa: E402
import numpy as np
from PIL import Image, ImageDraw
S = os.path.join(env.CFG['project_root'], 'Saved', 'Screenshots', 'WindowsEditor')
NAMES = ['CINE', 'TA', 'TB', 'EYE0', 'EYE1', 'EYE2', 'EYE3']


def stats(p):
    a = np.asarray(Image.open(p).convert('RGB').resize((960, 540))).astype(np.float32)
    L = 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]
    return dict(p5=int(np.percentile(L, 5)), p50=int(np.percentile(L, 50)), p95=int(np.percentile(L, 95)),
                sh=[int(x) for x in a[L < np.percentile(L, 15)].mean(0)])


if __name__ == '__main__':
    A, B = sys.argv[1], sys.argv[2]
    if len(sys.argv) > 3:
        NAMES = sys.argv[3:]
    W, H = 800, 450
    o = Image.new('RGB', (W * 2, H * len(NAMES)))
    d = ImageDraw.Draw(o)
    for i, n in enumerate(NAMES):
        for j, pre in enumerate((A, B)):
            p = os.path.join(S, pre + n + '.png')
            o.paste(Image.open(p).convert('RGB').resize((W, H)), (j * W, i * H))
            d.rectangle((j * W, i * H, j * W + 140, i * H + 14), fill='black'); d.text((j * W + 2, i * H + 1), pre + n, fill='white')
        print(n, A, stats(os.path.join(S, A + n + '.png')), B, stats(os.path.join(S, B + n + '.png')))
    o.save(env.W('compare', 'setcmp.png')); print('written', env.W('compare', 'setcmp.png'))
