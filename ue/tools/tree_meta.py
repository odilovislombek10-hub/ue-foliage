"""TOOL (in editor): static-mesh audit of the whole tree library -> work/tree_meta.json.

Only needed when the DARAXT library changes (data/tree_meta.json is the audit of the shared library).
Chunked (ARGS budget s); call until done == of. Loads meshes one by one (never bulk-load DARAXT: OOM).
Fields: lods, tris, verts, nanite settings, size_m, uv channels, collision, material slots with base material,
blend mode, two-sided, shading model, WPO. Origin: tree_meta.py of the Zaliniy session.
"""
import os
import sys

_d = os.path.dirname(os.path.abspath(__file__))
while not os.path.exists(os.path.join(_d, 'config.example.json')):
    _d = os.path.dirname(_d)
sys.path.insert(0, os.path.join(_d, 'ue'))
import ue_common as U  # noqa: E402
import builtins, json, time  # noqa: E402
import unreal  # noqa: E402

OUT = U.W('tree_meta.json')
ses = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
ar = unreal.AssetRegistryHelpers.get_asset_registry()
store = builtins.__dict__.setdefault('_uefol_tmeta', {})   # plain dicts only


def safe(f, d=None):
    try:
        return f()
    except Exception as e:
        return d if d is not None else 'ERR:' + str(e)[:60]


def base_mat(m):
    b = m; s = 0
    while isinstance(b, unreal.MaterialInstance) and s < 20:
        p = b.get_editor_property('parent')
        if not p:
            break
        b = p; s += 1
    return b


def mat_info(m):
    if not m:
        return None
    b = base_mat(m)
    d = dict(name=m.get_name(), path=m.get_path_name().split('.')[0], base=b.get_path_name().split('.')[0])
    if isinstance(b, unreal.Material):
        d['blend'] = str(safe(lambda: m.get_blend_mode() if hasattr(m, 'get_blend_mode') else b.get_editor_property('blend_mode'))).split('.')[-1].split(':')[0]
        d['two_sided'] = bool(safe(lambda: b.get_editor_property('two_sided'), False))
        d['shading'] = str(safe(lambda: b.get_editor_property('shading_model'))).split('.')[-1].split(':')[0]
        d['wpo'] = bool(safe(lambda: unreal.MaterialEditingLibrary.get_material_property_input_node(b, unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET) is not None, False))
        d['usage_ism'] = bool(safe(lambda: b.get_editor_property('used_with_instanced_static_meshes'), False))
        d['usage_nanite'] = bool(safe(lambda: b.get_editor_property('used_with_nanite'), False))
        # instance overrides of blend/two-sided
        if isinstance(m, unreal.MaterialInstanceConstant):
            bpo = safe(lambda: m.get_editor_property('base_property_overrides'))
            if not isinstance(bpo, str):
                if safe(lambda: bpo.get_editor_property('override_blend_mode'), False):
                    d['blend'] = str(bpo.get_editor_property('blend_mode')).split('.')[-1].split(':')[0] + '*'
                if safe(lambda: bpo.get_editor_property('override_two_sided'), False):
                    d['two_sided'] = bool(bpo.get_editor_property('two_sided'))
    return d


def meta(sm):
    b = sm.get_bounding_box()
    mn, mx = b.min, b.max
    ns = sm.get_editor_property('nanite_settings')
    lods = sm.get_num_lods()
    bs = sm.get_editor_property('body_setup')
    d = dict(
        path=sm.get_path_name().split('.')[0],
        lods=lods,
        tris=[safe(lambda i=i: sm.get_num_triangles(i), -1) for i in range(lods)],
        verts=[ses.get_number_verts(sm, i) for i in range(lods)],
        nanite=bool(ns.enabled),
        nanite_preserve_area=bool(safe(lambda: ns.get_editor_property('preserve_area'), False)),
        nanite_shape=str(safe(lambda: ns.get_editor_property('shape_preservation'))).split('.')[-1].split(':')[0],
        nanite_pct=safe(lambda: round(ns.get_editor_property('keep_percent_triangles'), 3)),
        nanite_fallback_pct=safe(lambda: round(ns.get_editor_property('fallback_percent_triangles'), 3)),
        size_m=[round((mx.x - mn.x) / 100, 2), round((mx.y - mn.y) / 100, 2), round((mx.z - mn.z) / 100, 2)],
        min_cm=[round(mn.x), round(mn.y), round(mn.z)], max_cm=[round(mx.x), round(mx.y), round(mx.z)],
        uvch=ses.get_num_uv_channels(sm, 0),
        lm_res=sm.get_editor_property('light_map_resolution'),
        lm_uv=sm.get_editor_property('light_map_coordinate_index'),
        simple_coll=ses.get_simple_collision_count(sm),
        coll_trace=str(safe(lambda: bs.get_editor_property('collision_trace_flag'))).split('.')[-1].split(':')[0] if bs else None,
        coll_profile=str(safe(lambda: bs.get_editor_property('default_instance').get_editor_property('collision_profile_name'))) if bs else None,
        nsec=sm.get_num_sections(0),
        mats=[mat_info(s.material_interface) for s in sm.static_materials],
        slot_names=[str(s.material_slot_name) for s in sm.static_materials],
        lod_screen=safe(lambda: [round(x, 3) for x in ses.get_lod_screen_sizes(sm)]),
        auto_lod=safe(lambda: sm.get_editor_property('auto_compute_lod_screen_size'), None),
        disk_kb=None,
    )
    return d


def run(budget=100):
    t0 = time.time()
    assets = [a for a in ar.get_assets_by_path(U.CFG['tree_library_root'], recursive=True)
              if str(a.asset_class_path.asset_name) == 'StaticMesh']
    for a in assets:
        k = str(a.package_name)
        if k in store:
            continue
        if time.time() - t0 > budget:
            break
        sm = unreal.load_asset(k)
        try:
            store[k] = meta(sm)
        except Exception as e:
            store[k] = dict(err=repr(e)[:200])
    json.dump(store, open(OUT, 'w'), indent=0)
    return dict(done=len(store), of=len(assets), sec=round(time.time() - t0, 1))


if __name__ == '__main__':
    A = U.args(dict(budget=100))
    RESULT = run(A['budget'])
    print(RESULT)
