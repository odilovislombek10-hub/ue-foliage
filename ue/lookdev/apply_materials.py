"""LOOKDEV (in editor): bring tree / ground materials to the validated Zaliniy state (data/lookdev/materials_final.json).

!! SHARED LIBRARY EDIT !!  scope 'shared_library' = assets under /Game/SHABLON/MODEL (DARAXT trees, IZGIRIT,
export/mtl ...), 'shared_material' = other /Game/SHABLON materials (M_Grass, paving, asphalt). These folders are the
same on every project of the PC, so the change affects every project that uses them. 'project' = StarterContent water.

For every change: load the material; if the parameter already equals the target (tolerance 1e-3) -> skip;
otherwise copy <asset>.uasset -> <asset>.uasset.bak_YYYYMMDD (once), set the value (MaterialInstanceConstant:
instance parameter; base Material: default value of the parameter expression), update / recompile, save.
Then the one graph edit (dub_4m_03_Leaf_Mat1: Multiply by ScalarParameter SSS_Scale=0.3 on the SubsurfaceColor input)
unless a 'SSS_Scale' parameter already exists.
Log with old values (for undo): work/lookdev/materials_<date>.json.
ARGS: scope ('all' | 'shared_library' | 'shared_material' | 'project'), dry_run (False), graph (True), budget (s, 120)
Origin: apply_changes.py + calls #529, #558-#563, #578, #590, #595 of the Zaliniy session.
"""
import datetime
import json
import os
import sys
import time

_d = os.path.dirname(os.path.abspath(__file__))
while not os.path.exists(os.path.join(_d, 'config.example.json')):
    _d = os.path.dirname(_d)
sys.path.insert(0, os.path.join(_d, 'ue'))
import ue_common as U  # noqa: E402
import unreal  # noqa: E402

A = U.args(dict(scope='all', dry_run=False, graph=True, budget=120))
MEL = unreal.MaterialEditingLibrary
TOL = 1e-3


def _param_expr(mat, name):
    for e in MEL.get_material_expressions(mat) if hasattr(MEL, 'get_material_expressions') else []:
        try:
            if str(e.get_editor_property('parameter_name')) == name:
                return e
        except Exception:
            pass
    return None


def _same(a, b):
    if a is None:
        return False
    if isinstance(b, bool) or isinstance(a, bool):
        return bool(a) == bool(b)
    if isinstance(b, (list, tuple)):
        a = list(a); b = list(b)
        n = min(len(a), len(b), 3)          # rgb decides; alpha of tint vectors is unused
        return all(abs(float(a[i]) - float(b[i])) < TOL for i in range(n))
    return abs(float(a) - float(b)) < TOL


def _lc(v):
    v = [float(x) for x in (list(v) + [1.0])[:4]]
    return unreal.LinearColor(*v)


def get_val(m, typ, name):
    if isinstance(m, unreal.MaterialInstanceConstant):
        if typ == 'scalar':
            return MEL.get_material_instance_scalar_parameter_value(m, name)
        if typ == 'vector':
            o = MEL.get_material_instance_vector_parameter_value(m, name); return [o.r, o.g, o.b, o.a]
        return MEL.get_material_instance_static_switch_parameter_value(m, name)
    e = _param_expr(m, name)
    if e is None:
        return 'NOEXPR'
    o = e.get_editor_property('default_value')
    return [o.r, o.g, o.b, o.a] if typ == 'vector' else o


def set_val(m, typ, name, new):
    if isinstance(m, unreal.MaterialInstanceConstant):
        if typ == 'scalar':
            MEL.set_material_instance_scalar_parameter_value(m, name, float(new))
        elif typ == 'vector':
            MEL.set_material_instance_vector_parameter_value(m, name, _lc(new))
        else:
            MEL.set_material_instance_static_switch_parameter_value(m, name, bool(new))
    else:
        e = _param_expr(m, name)
        if typ == 'scalar':
            e.set_editor_property('default_value', float(new))
        elif typ == 'vector':
            e.set_editor_property('default_value', _lc(new))
        else:
            e.set_editor_property('default_value', bool(new))


def graph_edit(g, log):
    m = unreal.load_asset(g['material'])
    if m is None:
        log.append((g['material'], 'GRAPH', 'MISSING')); return
    if _param_expr(m, g['parameter']) is not None:
        log.append((g['material'], 'GRAPH', 'already done')); return
    if A['dry_run']:
        log.append((g['material'], 'GRAPH', 'would edit')); return
    U.backup_asset(m)
    fc = MEL.get_material_property_input_node(m, unreal.MaterialProperty.MP_SUBSURFACE_COLOR)
    if fc is None:
        log.append((g['material'], 'GRAPH', 'no node on SubsurfaceColor - skipped')); return
    ins = MEL.get_inputs_for_material_expression(m, fc)
    idx = 3
    try:
        names = [str(n) for n in MEL.get_material_expression_input_names(fc)]
        if g['function_input'] in names:
            idx = names.index(g['function_input'])
    except Exception:
        pass
    tex = ins[idx]
    if tex is None:
        log.append((g['material'], 'GRAPH', 'input %d empty - skipped' % idx)); return
    outname = ''
    if hasattr(MEL, 'get_input_node_output_name_for_material_expression'):
        try:
            outname = MEL.get_input_node_output_name_for_material_expression(fc, tex) or ''
        except Exception:
            outname = ''
    (mx, my), (px, py) = g['node_pos']
    mul = MEL.create_material_expression(m, unreal.MaterialExpressionMultiply, mx, my)
    sp = MEL.create_material_expression(m, unreal.MaterialExpressionScalarParameter, px, py)
    sp.set_editor_property('parameter_name', g['parameter']); sp.set_editor_property('default_value', float(g['default']))
    ok1 = MEL.connect_material_expressions(tex, outname, mul, 'A')
    ok2 = MEL.connect_material_expressions(sp, '', mul, 'B')
    ok3 = MEL.connect_material_expressions(mul, '', fc, g['function_input'])
    MEL.recompile_material(m)
    unreal.EditorAssetLibrary.save_loaded_asset(m)
    log.append((g['material'], 'GRAPH', 'edited', [ok1, ok2, ok3]))


def main():
    U.editor_world()
    D = json.load(open(U.D('lookdev', 'materials_final.json')))
    ch = [c for c in D['changes'] if A['scope'] == 'all' or c['scope'] == A['scope']]
    log, touched, skipped, t0 = [], {}, 0, time.time()
    for c in ch:
        if time.time() - t0 > float(A['budget']):
            log.append(('BUDGET', 'stopped - call again')); break
        m = unreal.load_asset(c['material'])
        if m is None:
            log.append((c['material'], c['param'], 'MISSING')); continue
        old = get_val(m, c['type'], c['param'])
        if old == 'NOEXPR':
            log.append((c['material'], c['param'], 'NOEXPR')); continue
        if _same(old, c['target']):
            skipped += 1; continue
        if A['dry_run']:
            log.append((c['material'], c['param'], old, c['target'], 'dry')); continue
        U.backup_asset(m)
        set_val(m, c['type'], c['param'], c['target'])
        touched[c['material']] = m
        log.append((c['material'], c['param'], old, c['target']))
    for p, m in touched.items():
        if isinstance(m, unreal.MaterialInstanceConstant):
            MEL.update_material_instance(m)
        else:
            MEL.recompile_material(m)
        unreal.EditorAssetLibrary.save_loaded_asset(m)
    if A['graph'] and A['scope'] in ('all', 'shared_library'):
        for g in D.get('graph_edits', []):
            graph_edit(g, log)
    out = U.W('lookdev', 'materials_%s.json' % datetime.date.today().strftime('%Y%m%d'))
    prev = json.load(open(out)) if os.path.exists(out) else []
    json.dump(prev + log, open(out, 'w'), indent=1, default=str)
    touched.clear()
    return dict(changes=len(ch), set=len([l for l in log if len(l) == 4]), already_ok=skipped,
                problems=[l for l in log if len(l) == 3 and l[2] in ('MISSING', 'NOEXPR')], log=out)


if __name__ == '__main__':
    RESULT = main()
    print(RESULT)
