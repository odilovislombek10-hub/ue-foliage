"""LOOKDEV (offline, EDITOR CLOSED): write the validated render cvars into <project>/Config/DefaultEngine.ini.

Usage:  python update_ini.py [--high-tier] [--dry-run] [--ini path/to/DefaultEngine.ini]
Settings: data/lookdev/ini_settings.json ('base' always; 'high_tier' only with --high-tier = GPUs with >= 12 GB VRAM).
Each key is set inside its section: an existing 'key=value' line in that section is replaced, otherwise the line is
appended at the end of the section (section created if missing), with a '; uefol <date>: <why>' comment.
A dated backup DefaultEngine.ini.bak_YYYYMMDD is made first (never overwritten). Restart the editor afterwards.
Project-level change (not the shared tree library).
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lib'))
import env  # noqa: E402
import argparse  # noqa: E402
import datetime  # noqa: E402
import json  # noqa: E402
import re  # noqa: E402
import shutil  # noqa: E402


def set_key(lines, section, key, value, why, stamp):
    hdr = '[%s]' % section
    try:
        s = next(i for i, l in enumerate(lines) if l.strip() == hdr)
    except StopIteration:
        lines += ['', hdr]
        s = len(lines) - 1
    e = next((i for i in range(s + 1, len(lines)) if lines[i].startswith('[')), len(lines))
    pat = re.compile(r'^\s*' + re.escape(key) + r'\s*=')
    for i in range(s + 1, e):
        if pat.match(lines[i]):
            old = lines[i].split('=', 1)[1].strip()
            if old == value:
                return 'same'
            lines[i] = '%s=%s' % (key, value)
            return 'replaced %s -> %s' % (old, value)
    while e > s + 1 and not lines[e - 1].strip():
        e -= 1
    lines[e:e] = ['; uefol %s: %s' % (stamp, why), '%s=%s' % (key, value)]
    return 'added'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--high-tier', action='store_true')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--ini', default=os.path.join(env.CFG['project_root'], 'Config', 'DefaultEngine.ini'))
    a = ap.parse_args()
    S = json.load(open(env.D('lookdev', 'ini_settings.json'), encoding='utf-8'))
    items = S['base'] + (S['high_tier'] if a.high_tier else [])
    raw = open(a.ini, encoding='utf-8-sig').read()
    lines = raw.splitlines()
    stamp = datetime.date.today().strftime('%Y-%m-%d')
    rep = [(it['section'], it['key'], set_key(lines, it['section'], it['key'], it['value'], it['why'], stamp)) for it in items]
    for r in rep:
        print('%-36s %-62s %s' % r)
    if a.dry_run:
        print('dry run - nothing written'); return
    if all(r[2] == 'same' for r in rep):
        print('already up to date'); return
    b = a.ini + '.bak_' + datetime.date.today().strftime('%Y%m%d')
    if not os.path.exists(b):
        shutil.copy2(a.ini, b); print('backup', b)
    open(a.ini, 'w', encoding='utf-8', newline='\r\n').write('\n'.join(lines) + '\n')
    print('written', a.ini, '- restart the editor')


if __name__ == '__main__':
    main()
