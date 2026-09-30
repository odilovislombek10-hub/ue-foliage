"""Build docs/DARAXT_OZGARISHLAR.md: every tree material / texture change (old -> new, why, which species use it).

Inputs (all in data/lookdev/): materials_final.json, logs/applied_tex_first10.json + logs/applied_tex.json, tree_mats_zaliniy.json, lineup_mats_zaliniy.json.
Run:  "%UEPY%" offline/tools/make_tree_report.py
"""
import collections
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LD = os.path.join(ROOT, 'data', 'lookdev')
OUT = os.path.join(ROOT, 'docs', 'DARAXT_OZGARISHLAR.md')

# why each change stage was made (Uzbek), in the order they were applied on 2026-09-30
WHY = {
    'matchg_1': "Barg yorug'lik o'tkazishi (SSS) juda kuchli edi: (1,3; 1,4; 0,6) x 0,8 - toj soya tomoni yonib, "
                "sarg'ish ko'rinardi. (0,55; 0,65; 0,2) x 0,5 ga tushirildi; M_Base_Leaf da subsurface_Brightness 0,6.",
    'palette': "Turlar rangi bir-biridan uzoq edi (sariq-zaytun / ko'k-yashil / kulrang). Barg rangi parametrlari "
               "(Brightness, Contrast, Desaturation, EXP, Tint) referens palitrasiga yaqinlashtirildi.",
    'leafshading': "Barg soyalanishi: M_Base_Leaf / M_Base_Reed da 'Normal' (FlattenNormal Flatness) 0 edi, Normal "
                   "slotida esa haqiqiy normal xarita emas - toj ichi qop-qora chiqardi -> 1 (tekis). Yaltiroqlik "
                   "(roughness/specular) va SSS turlar bo'yicha tekislandi.",
    'tweak1': "Qator (lineup) tekshiruvidan keyin: 07_leaf juda sariq (Brightness 0,9), Corona_Proxy071 och-limon "
              "(ColorBrightness 1,2, Saturation 0,8).",
    'ground': "Yer palitrasi: maysa rangi va katta masshtabli dog'lar, yo'lak (bruschatka) iliq tosh rangi, asfalt, suv.",
    'grass2': "Maysa biroz to'qroq: BaseColor Tint (0,49; 0,71; 0,42).",
    'aud1': "Odam bo'yi auditi: yozda gilos gullari (Petal Mode 1 - faqat bahorda), quyoshli kunda ko'lmaklar o'chirildi, "
            "to'q sariq tanalar (Silver_Birch_Branch_Mat Desa/EXP), maysa soyasidagi ko'k tus (MV_Tint).",
    'graph': "Material grafigi o'zgartirildi.",
}
TEXKEYS = {
    'mips': "mipmap yoqildi (NoMipmaps -> FromTextureGroup)",
    'comp': "siqish EditorIcon -> Default",
    'stream': "never_stream o'chirildi (oqimda yuklanadi)",
    'pot': "2 ning darajasiga cho'zildi (mip va oqim uchun)",
    'cov': "alpha coverage 0,3333 (uzoqda barg yo'qolmasin)",
    'max': "maks. o'lcham 2048",
}


def fmt(v):
    if v is None:
        return '-'
    if isinstance(v, (list, tuple)):
        return '(' + ', '.join('%.3g' % x for x in v[:3]) + ')'
    if isinstance(v, bool):
        return str(v)
    if isinstance(v, (int, float)):
        return '%.4g' % v
    return str(v)


def main():
    mf = json.load(open(os.path.join(LD, 'materials_final.json'), encoding='utf-8'))['changes']
    tex = (json.load(open(os.path.join(LD, 'logs', 'applied_tex_first10.json'), encoding='utf-8')) +
           json.load(open(os.path.join(LD, 'logs', 'applied_tex.json'), encoding='utf-8')))
    use = json.load(open(os.path.join(LD, 'tree_mats_zaliniy.json'), encoding='utf-8'))
    line = json.load(open(os.path.join(LD, 'lineup_mats_zaliniy.json'), encoding='utf-8'))

    # material -> species that use it (from the lineup dump) and planted instance count (plan)
    mat2sp = collections.defaultdict(set)
    for sp, d in line.items():
        for m in d['materials']:
            mat2sp[m['mat'].split('.')[0]].add(sp.split('_', 1)[1] if '_' in sp else sp)
    mat_cnt = {r[5].split('.')[0]: r[4] for r in use}
    mat_master = {r[5].split('.')[0]: (r[1].split('.')[0], r[2]) for r in use}

    by = collections.OrderedDict()
    for c in mf:
        by.setdefault(c['material'], []).append(c)

    L = []
    L.append('# Daraxtlar ustidagi ish: materiallar va teksturalar (2026-09-30, Zaliniy)\n')
    L.append("Bu hujjat `offline/tools/make_tree_report.py` bilan `data/lookdev/` dagi loglardan avtomatik yasalgan. "
             "Hamma qiymatlar editorda qo'llanib, skrinshotlar bilan tekshirilgan. Qayta qo'llash: "
             "`ue/lookdev/apply_materials.py` va `ue/lookdev/fix_textures.py` (zaxira `.bak_` bilan, takror ishlatish xavfsiz).\n")
    L.append("**Diqqat:** `/Game/SHABLON/MODEL/...` dagi o'zgarishlar umumiy daraxt kutubxonasiga yoziladi - "
             "o'sha kompyuterdagi hamma loyihaga ta'sir qiladi.\n")
    L.append('## Topilgan muammolar va sabablari\n')
    for k in ('matchg_1', 'palette', 'leafshading', 'tweak1', 'aud1', 'ground', 'grass2'):
        L.append('- **%s** - %s' % (k, WHY[k]))
    L.append("- **Nok (dub_4m_03_Leaf_Mat1) grafigi** - yorug'lik o'tkazish (SubsurfaceColor) xom teksturadan olinardi, "
             "rangdan ~4 barobar kuchli (limon-sariq yaltirash). TextureSample va MF_Season_Leaf 'SubsurfaceColor' "
             "orasiga Multiply x ScalarParameter `SSS_Scale` = 0,3 qo'shildi.")
    L.append("- **Uzoqdagi daraxtlar** - 103 ta barg/po'stloq teksturasida mipmap yo'q edi (uzoqda uchqun, teshik, "
             "kulrang chet). Asosiy sabab esa Nanite oqim puli (1024 MB) to'lib, sifatni jimgina pasaytirishi edi: "
             "`r.Nanite.Streaming.StreamingPoolSize=1536`, `r.Nanite.Streaming.QualityScale.MinQuality=1.0` "
             "(docs/TESTLAR_VA_XULOSALAR.md).\n")
    L.append('Rasmlar: `docs/img/lineup_oldin.png` (tuzatishdan oldin 24 tur), `docs/img/lineup_keyin.png` (keyin), '
             '`docs/img/uzoq_daraxt_pool.png` (Nanite pul sinovi: chap yuqori - eski holat).\n')

    L.append('## Materiallar (%d ta material, %d ta o\'zgarish)\n' % (len(by), len(mf)))
    for mat, cs in by.items():
        master, shading = mat_master.get(mat, ('?', '?'))
        sp = ', '.join(sorted(mat2sp.get(mat, []))) or '-'
        L.append('### `%s`' % mat)
        L.append('- master: `%s` (%s); ekilgan nusxalar (reja): %s; turlar: %s; scope: %s' %
                 (master, shading, mat_cnt.get(mat, '-'), sp, cs[0].get('scope', '-')))
        L.append('\n| Parametr | Tur | Oldin | Keyin | Bosqich (sabab) |\n|---|---|---|---|---|')
        for c in cs:
            L.append('| %s | %s | %s | %s | %s |' % (c['param'], c['type'], fmt(c.get('original')), fmt(c.get('target')),
                                                    ', '.join(x.replace('applied_', '') for x in c.get('sources', []))))
        L.append('')

    L.append('## Grafik o\'zgarishi\n')
    L.append('| Material | Nima qilindi |\n|---|---|')
    L.append("| `/Game/SHABLON/MODEL/DARAXT/TXTR/dub_4m_03_Leaf_Mat1` | TextureSample -> Multiply(A) ; ScalarParameter "
             "`SSS_Scale`=0,3 -> Multiply(B) ; Multiply -> MF_Season_Leaf.SubsurfaceColor (ue/lookdev/apply_materials.py) |\n")

    L.append('## Teksturalar (%d ta)\n' % len(tex))
    L.append('| Tekstura | Vazifasi | Asl o\'lcham | O\'zgarishlar |\n|---|---|---|---|')
    for name, roles, w, h, ch in tex:
        L.append('| %s | %s | %dx%d | %s |' % (name, ', '.join(roles), w, h,
                                              '; '.join(TEXKEYS[k] for k in ch) or '-'))
    L.append('')
    open(OUT, 'w', encoding='utf-8').write('\n'.join(L))
    print('written', OUT, len(by), 'materials', len(tex), 'textures')


if __name__ == '__main__':
    main()
