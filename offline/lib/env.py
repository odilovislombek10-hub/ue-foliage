"""Offline bootstrap: puts <repo>/common on sys.path, loads config (adds pylib to sys.path) and exposes SP = work dir.

Every offline script starts with:
    import os, sys; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lib'))
    import env
"""
import os
import sys

_d = os.path.dirname(os.path.abspath(__file__))
while not os.path.exists(os.path.join(_d, 'config.example.json')):
    _d = os.path.dirname(_d)
REPO = _d
for p in (os.path.join(REPO, 'common'), os.path.join(REPO, 'offline', 'lib')):
    if p not in sys.path:
        sys.path.insert(0, p)

import uefol_config as C  # noqa: E402  (loads config.json, inserts pylib into sys.path)

CFG = C.CFG
SP = C.WORK          # all intermediate rasters / json live here (name kept from the original session)
W, D = C.W, C.D
lot_level_name = C.lot_level_name

# '-h' / '--help' on any offline script prints its docstring before heavy data is loaded
if any(a in ('-h', '--help') for a in sys.argv[1:]):
    _m = sys.modules.get('__main__')
    print((getattr(_m, '__doc__', None) or 'no help').strip())
    sys.exit(0)
