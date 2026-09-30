# ue-foliage — Unreal Engine loyihasiga daraxt va butalarni avtomatik ekish

Bu repozitoriy Zaliniy loyihasida (UE 5.8, ArchViz Explorer) qilingan ko'kalamzorlashtirish ishini **boshqa
loyihada xuddi shunday takrorlash** uchun to'plangan. Hamma kompyuterlarda bir xil daraxt kutubxonasi bor:
`/Game/SHABLON/MODEL/DARAXT` (bir xil fayl nomlari, bir xil meshlar), shuning uchun daraxt o'lchamlari
(`data/tree_geo.json`), turlari va material tuzatishlari bu yerdan to'g'ridan-to'g'ri ishlatiladi.

Nima qiladi:

1. Ochiq leveldagi **gazon (maysa) meshlarini** topadi (grass materiali bo'yicha), 0,25 m to'rga chizadi.
2. Atrofni vertikal nurlar (line trace) bilan tasniflaydi: yo'l, yo'lak/brusschatka, bolalar maydonchasi, suv,
   bino, past to'siqlar — 1 m to'rda.
3. Hududni **lotlarga** bo'ladi (PDF bosh reja bo'lsa — undan, bo'lmasa yo'l tarmog'i bo'yicha avtomatik taklif),
   foydalanuvchi bilan birlashtirish ro'yxati kelishiladi (`lots.json`).
4. Har bir lotning maysa uchastkalarini (bed) ajratadi va **v6 ekish dvigateli** bilan dizayn qiladi:
   ko'cha qatorlari, bolalar maydonchasi soyasi, yo'lak bo'yi qatorlari, archa guruhlari, 3–4 turdan aralash
   daraxt to'dalari, daraxt tagida 2–4 xil butadan "yubka", tor tasmalarga buta guruhlari, bo'sh joylarni
   tuzatish sikli.
5. Natijani tekshiradi (masofalar, aralashlik, bo'sh maysa qolmagani), yuqoridan ko'rinish rasmlarini chizadi.
6. Editor ichida: FoliageType assetlarini yaratadi, **har bir lot uchun alohida `FOL_*` streaming level**
   qo'shadi va har biriga daraxtlarni ekadi.
7. Skrinshotlar bilan vizual tekshiradi (daraxt ekrandan keyin kutib, Nanite/tekstura yuklanib bo'lgach).
8. Ixtiyoriy: Zaliniyda tasdiqlangan **vizual holat** (daraxt materiallari, teksturalar, yorug'lik, PPV, ini)
   — `docs/LOOKDEV_QOLLANMA.md`.
   Daraxtlar bo'yicha har bir material va tekstura o'zgarishi (oldin -> keyin, sabab, qaysi turlar):
   `docs/DARAXT_OZGARISHLAR.md` (rasmlar `docs/img/`).

Zaliniy natijasi: 23 ta lot (1-bosqich), 839 ta maysa uchastkasi, 24 416 ta o'simlik (5 635 daraxt), 54 xil model.
Bu repodagi offline qism Zaliniy ma'lumotlarida sinab ko'rildi: 23 levelning hammasi asl natija bilan
**bir xil** chiqdi.

---

## Talablar

| Nima | Izoh |
|---|---|
| Unreal Engine 5.8 | `C:\Program Files\Epic Games\UE_5.8` |
| Daraxt kutubxonasi | `/Game/SHABLON/MODEL/DARAXT` — Zaliniydagi bilan bir xil (boshqa joyda bo'lsa `config.tree_library_root`) |
| Python Editor Script Plugin | editorda yoqilgan bo'lishi kerak |
| MCP listener | loyihada `Content/Python/init_unreal.py` editor ochilganda 127.0.0.1:20251 da MCP serverni ishga tushiradi; Claude `mcp__unreal__run_python` orqali ishlaydi. MCP bo'lmasa — editor konsolida `py "<fayl>"` |
| Python kutubxonalari | UE bilan kelgan python orqali `pylib/` papkasiga: numpy, opencv-python-headless, scipy, scikit-image, pillow (+ matplotlib, pymupdf) |
| RAM | 32 GB+ (katta sahna + og'ir Nanite daraxtlar); skriptlar bo'sh xotira kam bo'lsa to'xtaydi |

UE bilan kelgan python:

```
"C:\Program Files\Epic Games\UE_5.8\UE_5.8\Engine\Binaries\ThirdParty\Python3\Win64\python.exe"
```

Quyida uni qisqacha `UEPY` deb yozamiz.

## O'rnatish

```bat
git clone https://github.com/odilovislombek10-hub/ue-foliage.git
cd ue-foliage
"%UEPY%" -m pip install --target pylib -r requirements.txt
copy config.example.json config.json
```

`config.json` ni tahrirlang (hamma yo'llar shu yerda, skriptlarda qattiq yozilgan yo'l yo'q):

| Kalit | Ma'nosi |
|---|---|
| `project_root` | yangi UE loyiha papkasi (`.uproject` turgan joy) |
| `work_dir` | oraliq fayllar va natijalar papkasi (bir necha GB bo'lishi mumkin; repodan tashqarida) |
| `pylib` | bo'sh = `<repo>/pylib` |
| `persistent_level` | daraxtlar qo'shiladigan asosiy level, masalan `/Game/LEVEL/Zaliniy/Atrof_button` |
| `foliage_level_folder`, `foliage_level_prefix` | `FOL_*` sublevellar papkasi va prefiksi |
| `streaming_class`, `streaming_initially_loaded/visible` | sublevel turi (Zaliniyda `LevelStreamingDynamic`) |
| `tree_library_root`, `foliage_type_folder` | daraxt kutubxonasi va `FT_*` assetlari papkasi |
| `grass_materials` | gazonni aniqlaydigan materiallar (to'liq yo'l `...M_Grass.M_Grass`) |
| `material_classes` | nur tekkan material NOMI bo'yicha sinf: grass / road / paving / playground / water |
| `ground_z_cm` | yer sathi (Zaliniy: -202 sm); bino = yerdan 3 m baland, past to'siq = 0,3 m |
| `lots` | yo'l tarmog'i bo'yicha bloklash va bo'lish parametrlari |
| `plan_pdf` | PDF bosh rejadan lot olish (ixtiyoriy) |
| `mpc_seasons` | skrinshotdan oldin daraxtlarni yozga qo'yadigan MPC (UDS `UDW Seasons`) |
| `screenshots` | CineCamera nomi, o'lcham, kutish vaqtlari |

Boshqa kompyuterda `CLAUDE.md` ni o'sha Claude o'qiydi — u bosqichma-bosqich yo'riqnoma.

---

## Skriptni editorda ishga tushirish

`ue/` dagi hamma skriptlar editor ichida ishlaydi. MCP orqali (Claude `mcp__unreal__run_python`):

```python
import runpy
result = runpy.run_path(r'D:/git/ue-foliage/ue/01_export_grass.py',
                        init_globals={'ARGS': {}}, run_name='__main__').get('RESULT')
```

`ARGS` — skript parametrlari (har bir skript boshidagi izohda yozilgan). Editor konsolidan:
`py "D:/git/ue-foliage/ue/01_export_grass.py" budget=60`.

`offline/` dagi skriptlar editorsiz, `UEPY` bilan ishlaydi: `"%UEPY%" offline\02_zones.py`.
Har biri `--help` bilan o'z yo'riqnomasini chiqaradi.

---

## Bosqichma-bosqich

Hamma fayllar `work_dir` ichida. ✎ = foydalanuvchi bilan kelishiladigan qo'lda qadam.

| # | Qayerda | Buyruq | Kiradi | Chiqadi |
|---|---|---|---|---|
| 1 | editor | `ue/01_export_grass.py` | ochiq persistent level | `label025.npy`, `grid.json`, `islands_raw.json`, `grass_comps.json` |
| 2 | editor | `ue/02_trace_classes.py` (`done: true` bo'lguncha qayta chaqiring) | grid, label | `cls1.npy`, `z1.npy`, `env_mats.json` |
| 2a | ✎ | `env_mats.json` ni o'qing: yo'l/yo'lak/maydoncha materiallari `config.material_classes` da bormi? Yo'q bo'lsa qo'shing va 2 ni `ARGS={'reset': True}` bilan qayta ishlating | | |
| 3 | offline | `offline/02_zones.py` | 1–2 natijalari | `cls1_fixed.npy`, `islands.json`, `size1.npy`, `size_full.png` |
| 4 | offline (ixtiyoriy) | `offline/03_plan_register.py render / regions / label / compare / align` | PDF reja | `lotUE.npy`, `reg2lot.json`, `plan2ue_affine.npy`, overlay rasmlar |
| 5 | offline | `offline/04_lots.py propose` | | `group3.npy`, `lots_proposed.png/json`, `lots.json` shabloni |
| 5a | ✎ | foydalanuvchi bilan `lots.json`: qaysi guruhlar bitta lot, qaysilar hozirgi bosqich, palitralar, parklar | | |
| 6 | offline | `offline/04_lots.py apply` | `lots.json` | `group4.npy`, `lots_resolved.json`, `lots_final.png` |
| 7 | offline | `offline/05_beds.py` | | `beds_lab025.npy`, `beds_st1.json` |
| 8 | offline | `offline/06_engine.py` (yoki `06_engine.py FOL_20_21` — bitta lot) | | `engine/xf_v6.json`, `meta_v6.pkl` |
| 9 | offline | `offline/07_verify.py` | | `engine/verify_v6.json` — `clearance_violations` bo'sh, `unresolved_patches` ≈ 0 |
| 10 | offline | `offline/08_preview.py v6` | | `engine/preview/*.png` — ✎ ko'rib chiqing |
| 11 | editor | `ue/06_create_foliage_types.py` (`left: []` bo'lguncha) | xf | `FT_*` assetlar |
| 12 | editor | `ue/07_create_sublevels.py` | xf | `FOL_*` levellar persistent levelga qo'shiladi, saqlanadi |
| 13 | editor | `ue/08_plant_levels.py` (`left: []` bo'lguncha, har chaqiriqda 4 level) | xf | har bir `FOL_*` ga ekilgan, saqlangan |
| 14 | offline | `offline/09_camplan.py` | xf | `shots/lot_shots.json` |
| 15 | editor | `ue/09_shots.py` `ARGS={'action':'lots'}` | | `Saved/Screenshots/WindowsEditor/LOT_*.png` — ✎ ko'rib chiqing |

### Yagona archviz dizayn nazorati

`06_engine.py` ichidagi archviz pass alohida qo'lda ishlatiladigan skript emas. U har bir generatsiyada avtomatik ravishda:

- kesishgan offset konturlari sabab daraxt qatorlari ikki marta ekilishini real markaz oralig'i bilan to'xtatadi;
- fasadlarda uzluksiz hedge emas, 2–4 turli butadan ritmik qatlamli massalar va ochiq intervallar yaratadi;
- daraxti kam lawn uchun avval struktura daraxti, daraxti ko'p/uzun/fasad bed uchun avval buta kompozitsiyasi qo'yadi;
- path topilmagan daraxt guruhlarini ham gazon chetiga yo'naltirilgan underplant bilan tugatadi.

Chegaralar `config.engine.archviz` da. `07_verify.py` natijasidagi `archviz_design` lot/bed kesimida qator oralig'i,
aloqasiz daraxt zichligi, daraxt taglari, katta bo'shliqlar va fasad massalarini tekshiradi. `08_preview.py` verify fayli
bo'lsa muammoli bed konturini avtomatik belgilaydi: `G` bo'sh kompozitsiya, `C` daraxt crowding, `U` underplant,
`F` fasad, `D` ortiqcha daraxt zichligi. Ishlab chiqarish tartibi doim `06 → 07 → 08 → vizual ko'rik`.

### Lot fayli `lots.json`

```json
{
 "merge": [["LOT_20", "LOT_21"], ["LOT_12", "KV_34"], ["KV_58", "KV_59"]],
 "spill_pairs":  [["LOT_38", "LOT_37"]],
 "absorb_pairs": [["38+38-1", "LOT_37"]],
 "stage": "auto",
 "palettes": {"20+21": "sage", "LOT_4": "deep"},
 "parks": ["LOT_128"]
}
```

* `merge` — `lots_proposed.png` dagi nomlar; bitta ro'yxat = bitta lot = bitta `FOL_` level.
  Yangi nom: qismlar `+` bilan, `LOT_` tushib qoladi, `KV_` → `K` (`12+K34` → `FOL_12_K34`).
* `spill_pairs` — reja chizig'i yo'ldan oshib ketgan ozgina bo'laklarni qo'shni lotga qaytaradi.
* `absorb_pairs` — yo'l bilan ajralgan blokda `dst` ko'pchilik bo'lsa, `src` ning shu blokdagi qismi `dst` ga.
* `stage` — hozir ekiladigan lotlar: `"auto"` (PDF lotlari bor guruhlar), `"all"` yoki nomlar ro'yxati.
* `palettes` — `fresh | sage | deep | blossom` (quyida); yozilmaganlari g'arbdan sharqqa navbat bilan beriladi.
* `parks` — ommaviy parklar: katta uchastkada bitta ataylab ochiq maydon qoldirishga ruxsat.

Zaliniydagi to'liq namuna: `data/examples/lots.zaliniy.json` (foydalanuvchining birlashtirish ro'yxati).

---

## Mijozning ekish qoidalari (majburiy)

Bular dvigatelda allaqachon bor; o'zgartirmang. Batafsil: `docs/research/client_rules_v6.md`, `standards.md`.

1. **Bo'sh maysa qolmasin.** Har bir uchastka dizayn bilan ekiladi; hovlilarda daraxt tojlari + butalar
   maysaning ≥ 60–70 % ini qoplaydi. 30 m² dan katta, eng yaqin o'simlikdan 4 m dan uzoq bo'sh joy qolsa —
   tuzatish sikli daraxt yoki buta guruhi qo'shadi (faqat parklarda bitta ataylab ochiq maydon).
2. **Hech qachon bitta model qatorda takrorlanmaydi.** Qatorlar va guruhlar 3–4 mos turdan aralash; har bir nusxa
   tasodifiy buriladi (yaw 0–360°, daraxtga 0–1,5° qiyalik) va masshtabi ±8–15 % o'zgaradi.
3. **Daraxt tagida butalar:** 2–4 xil butadan qatlamli "yubka" (orqa baland K, o'rta E, oldingi past F),
   yo'lak tomonga qaragan; butalar maysada yolg'iz sharcha bo'lib turmaydi (1–2 tadan qolgan guruhlar o'chiriladi).
4. **Bino, maydoncha, yo'lak yonida ham dizayn:** bo'sh emas. Bolalar maydonchasining janub va g'arb tomoniga
   soya daraxtlari (7,5 m oraliq), qolgan tomonlarga siyrakroq; maydonchadan 2,5 m, archa 15 m; zaharli
   oleandr maydonchadan ≥ 10 m.
5. **Ko'cha qatorlari:** keng chetga (≥ 5 m) katta daraxtlar aralashmasi 9 m oraliqda, tor chetga (3–5 m)
   ustunsimon teraklar 5,5 m oraliqda; bitta ko'cha hamma lotda bir xil o'qiladi.
6. **Archalar** o'z guruhlarida (faqat `deep` palitrada), och yashil bargli daraxtlardan 8 m uzoqda;
   to'q (D) va sariq-yashil (Y) tonlar 8 m ichida yonma-yon qo'yilmaydi.
7. **Gazon va gul modellari ekilmaydi** (Calamagrostis va h.k.). Faqat daraxt va butalar.
8. **Kutubxonadan to'liq foydalanish:** palitra tekshiruvidan o'tgan hamma daraxt va butalar (`offline/lib/species6.py`,
   55+ model). Ishlatilmaydiganlar: materiali yo'q (Ash_tree_02, MWLW lindens), doim sariq Autumn_hornbeam_02_01,
   yalang'och sakura 0301/0303, ko'chat dub 3 m / dub_4m_03, Silver_Birch_03.
9. **Masofalar:** maysa chetidan tanagacha L 2,5 / M 1,8 / S 1,2 / P 1,3 / C 2,0 m; fasaddan L 6 / M 4,5 / S 3 /
   P 4 / C 5 m; yo'ldan L,M 2 / S 1,8 / P 1,5 / C 3 m; buta toji yo'lakka chiqmaydi.
10. **Har bir lot alohida streaming level** (`FOL_<lot>`): katta sahnani qism-qism yuklash oson bo'ladi.
11. Unumdorlik: ko'p mayda o'simlik o'rniga kamroq, kattaroq, yaxshi kompozitsiya (skirtli daraxtlar ≥ 9 m oraliq).

Palitralar (har bir lotga bitta, qo'shnilar almashadi): `fresh` (grab, shumtol, och-sariq shumtol),
`sage` (shumtol, keng bargli), `deep` (to'q bargli, qayin, archalar bilan), `blossom` (gullaydigan olcha, lagerstremiya).
Rollar: L katta soya daraxti, M o'rta, S kichik/aksent, P ustunsimon, C archa, K baland buta, E dumaloq buta, F past buta.

---

## Xavfsizlik qoidalari (Zaliniyda qimmatga tushgan saboqlar)

1. **`add_instances` ni persistent levelda ishlatmang.** `InstancedFoliageActor.add_instances()` doim editor
   dunyosining PersistentLevel iga yozadi. Shuning uchun `08_plant_levels.py` har bir `FOL_*` ni alohida xarita
   qilib ochadi, ekadi, saqlaydi, keyin persistent levelni qaytadan ochadi.
2. **`builtins` da UObject havolasini saqlamang** (aktor, komponent, dunyo, asset) va `load_level` qilmang —
   UE "Old World not cleaned up by GC" deb yiqiladi. Skriptlar faqat oddiy ma'lumot (raqam, JSON, numpy) saqlaydi,
   `load_level` dan oldin o'z havolalarini tozalaydi.
3. **MCP ning `builtins` dagi nomlarini hech qachon o'chirmang** — listener o'z holatini shu yerda saqlaydi.
   Skriptlar faqat o'z nomlarini (`_uefol*` va eski sessiya nomlari) tozalaydi.
4. **Editor dunyosi `None` emasligini tekshiring** (xarita yuklanayotganda `None`). Har bir skript tekshiradi.
5. **DARAXT meshlarini ommaviy yuklamang** — xotira tugab UE yiqilgan. Skriptlar bittalab yuklaydi, har 5 tadan
   keyin GC qiladi, bo'sh RAM kam bo'lsa to'xtaydi.
6. **Skrinshotdan oldin kuting:** kamera qo'yilgandan keyin kamida 5–15 s (Nanite, tekstura, Lumen yuklansin);
   sozlama o'zgartirilgandan keyin 45–75 s va kadr vaqti barqarorlashguncha (`settle`). Shader kompilyatsiyasi
   tugamaguncha (ShaderCompileWorker jarayonlari bor ekan) rasm olmang.
7. **Uzoqdagi daraxtlar uchun `DefaultEngine.ini`:** `r.Nanite.Streaming.StreamingPoolSize=1536` (2048 emas —
   assert beradi) va `r.Nanite.Streaming.QualityScale.MinQuality=1.0` — `offline/update_ini.py`.
8. **Fayllarni o'zgartirishdan oldin sanali zaxira:** `.bak_YYYYMMDD` (skriptlar o'zi qiladi; mavjud zaxira
   ustidan yozilmaydi).
9. **Umumiy kutubxona:** `FoliageTypes` va `docs/LOOKDEV_QOLLANMA.md` dagi material/tekstura tuzatishlari
   `/Game/SHABLON/...` ichida — kompyuterdagi hamma loyihaga ta'sir qiladi.

---

## Muammolar va yechimlar

| Belgisi | Sababi / yechimi |
|---|---|
| `01` "no grass triangles found" | `config.grass_materials` noto'g'ri yoki persistent level ochilmagan. `grass_comps.json` ni tekshiring |
| `02` juda sekin | 1 m to'r, gazondan 20 m atrof. `raster.near_grass_m` ni kamaytiring; chaqiriqlarni takrorlang (holat saqlanadi) |
| `size_full.png` da yo'llar maysaga o'xshaydi | `env_mats.json` dagi material nomlarini `material_classes` ga qo'shing, 02 ni `reset` bilan qayta ishlating |
| Bino tomida daraxtlar | `raster.roof_z_cm` (tom gazonlari tashlanadi); dvigatel bino maskasidagi "podium" uchastkalarni ekmaydi |
| Daraxtlar havoda / yer ostida | `ground_z_cm` noto'g'ri yoki joy traceda topilmagan; `z1.npy` dagi qiymatlarni tekshiring |
| `04 apply` "unknown group names" | `lots.json` dagi nomlar `lots_proposed.json` dagidek bo'lsin |
| Lot chegarasi yo'ldan oshgan | `spill_pairs` / `absorb_pairs` qo'shing |
| Lot bo'sh qolgan | `07_verify.py` → `empty_patches_gt30m2_far4m`, `unresolved_patches`; `08_preview.py` rasmlari |
| `08_plant_levels` "load failed" | avval `07_create_sublevels.py`; level nomi `lots_resolved.json` dagi bilan bir xil bo'lsin |
| PIE / paketda daraxt ko'rinmaydi | Levels oynasida `FOL_*` → Streaming Method / Initially Loaded; `streaming_initially_loaded=true` |
| UE yiqildi (Old World ...) | builtins da UObject qolgan — editorni qayta oching, faqat shu skriptlar bilan ishlang |
| UE yiqildi (xotira) | ko'p og'ir mesh yuklangan — editorni qayta oching, `budget` / `batch` ni kichraytiring |
| Uzoqdagi daraxtlar soddalashib ketadi | `offline/update_ini.py` (pool 1536 + MinQuality 1.0), editorni qayta oching; `docs/TESTLAR_VA_XULOSALAR.md` |
| Rasm juda erta olingan (xira, past sifat) | `screenshots.wait_s` ni oshiring, `settle` dan foydalaning |

---

## Repozitoriy tuzilmasi

```
config.example.json         hamma sozlamalar (config.json ga nusxa oling)
requirements.txt            pylib uchun kutubxonalar
common/uefol_config.py      config o'quvchi (editor va offline uchun umumiy)
ue/                         EDITOR ichida (MCP run_python yoki `py`)
  ue_common.py              xavfsizlik yordamchilari (world tekshiruvi, builtins tozalash, zaxira, saqlash)
  01_export_grass.py        gazon meshlari -> 0,25 m raster
  02_trace_classes.py       atrof sinflari (line trace, bo'laklab)
  06_create_foliage_types.py  FT_* assetlar
  07_create_sublevels.py    FOL_* streaming levellar
  08_plant_levels.py        ekish (har bir levelni alohida ochib)
  09_shots.py, shots_lib.py skrinshotlar (lot, audit to'plami, cine, settle)
  tools/                    kutubxona o'lchovi (tree_meta.py, measure_trees.py) - faqat yangi meshlar uchun
  lookdev/                  vizual holat: materiallar, teksturalar, yorug'lik, suv tekisligi, daraxtlar qatori
offline/                    UE python bilan, editorsiz
  02_zones.py 03_plan_register.py 04_lots.py 05_beds.py 06_engine.py 07_verify.py 08_preview.py 09_camplan.py
  update_ini.py             DefaultEngine.ini (editor yopiq)
  lib/                      lsite, geom, species6 (o'simlik kutubxonasi), metrics6, lotsplit, env
  tools/                    rasm solishtirish (compare_sets, treecmp, compare_panel, imgaudit)
data/                       tree_geo.json, tree_tags.json, tree_meta.json (umumiy kutubxona o'lchovlari)
  lookdev/                  materials_final.json, tex_roles.json, lighting_state.json, ini_settings.json, logs/
  examples/                 Zaliniy namunalari: lots, plan_labels, shotset, yangi meshlar ro'yxati
docs/                       LOOKDEV_QOLLANMA.md, TESTLAR_VA_XULOSALAR.md, research/ (mijoz qoidalari, qarorlar)
```
