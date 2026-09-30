# Vizual holat (look-dev) qo'llanmasi

Zaliniyda 2026-09-29/30 kunlari tasdiqlangan vizual holatni boshqa loyihada takrorlash: daraxt materiallari,
barg teksturalari, maysa/yo'lak/suv ranglari, yorug'lik va post-process, `DefaultEngine.ini`.
Hammasi skript + ma'lumot ko'rinishida; har bir skript **idempotent** (maqsad qiymatdagi narsaga tegmaydi) va
o'zgartirishdan oldin `.bak_YYYYMMDD` zaxira oladi.

## Nima qayerga ta'sir qiladi

| Qadam | Skript | Ta'sir doirasi |
|---|---|---|
| Daraxt / buta materiallari (128 o'zgarish) | `ue/lookdev/apply_materials.py` `scope='shared_library'` | **UMUMIY KUTUBXONA** `/Game/SHABLON/MODEL/...` — kompyuterdagi hamma loyiha |
| dub_4m_03 barg materiali grafigi | `apply_materials.py` (graph) | **UMUMIY KUTUBXONA** |
| Maysa, yo'lak, asfalt (14 o'zgarish) | `apply_materials.py` `scope='shared_material'` | **UMUMIY** `/Game/SHABLON/MATERIAL/...` |
| Suv rangi (M_Water_Lake) | `apply_materials.py` `scope='project'` | faqat shu loyiha (StarterContent) |
| 103 barg teksturasi (mipmap va h.k.) | `ue/lookdev/fix_textures.py` | **UMUMIY KUTUBXONA** |
| Yorug'lik, UDS, tuman, PPV, kamera | `ue/lookdev/apply_lighting.py` | faqat ochiq level (`.umap`) |
| Suv tekisligi CTX_Water_Plane | `ue/lookdev/water_plane.py` | faqat ochiq level (ixtiyoriy) |
| `DefaultEngine.ini` | `offline/update_ini.py` | faqat shu loyiha (editor yopiq holda) |

Agar kutubxona boshqa kompyuterdan allaqachon tuzatilgan holda nusxalangan bo'lsa, umumiy qadamlar hech narsa
qilmaydi (`already_ok`). Avval `dry_run` bilan tekshiring.

## Tartib

1. Editor yopiq: `"%UEPY%" offline\update_ini.py --dry-run`, keyin `offline\update_ini.py`
   (12 GB+ videokarta bo'lsa `--high-tier`). Editorni oching.
2. Persistent levelni oching. MCP orqali:
   ```python
   import runpy
   R = r'D:/git/ue-foliage/ue/lookdev/'
   result = runpy.run_path(R + 'apply_materials.py', init_globals={'ARGS': {'dry_run': True}}, run_name='__main__').get('RESULT')
   ```
   Natijani ko'ring, keyin `{'scope': 'shared_library'}`, `{'scope': 'shared_material'}`, `{'scope': 'project'}`
   (har biri `budget` ichida tugamasa — qayta chaqiring).
3. `fix_textures.py` — `{'dry_run': True}` bilan nechta tekstura qolganini ko'ring, keyin `left: 0` bo'lguncha
   `{'batch': 10}` bilan chaqiring (tekstura qayta siqilishi sekin).
4. `apply_lighting.py` — `{'dry_run': True}`, keyin `{}`. U UDS/UDW konstruktor skriptlarini qayta ishlatadi va
   levelni zaxiradan keyin saqlaydi. **Sun Yaw 120 va ekspozitsiya 2.1 Zaliniy kamerasiga moslangan** —
   yangi loyihada kadr bo'yicha tekshiring (`docs/research/decisions.md`: quyosh kameraga nisbatan 40–120° yonda).
5. Ixtiyoriy: `water_plane.py` (sahna tashqarisidagi bo'sh ko'k maydon o'rniga suv).
6. Tekshiruv: `ue/09_shots.py` `{'action': 'set'}` (7 kadr) va `{'action': 'cine'}`; natijani
   `offline/tools/compare_sets.py` bilan oldingisi bilan solishtiring (`docs/TESTLAR_VA_XULOSALAR.md`).

## Tasdiqlangan qiymatlar

### Daraxt materiallari (`data/lookdev/materials_final.json`, manba jurnallari `data/lookdev/logs/`)

Qo'llash tartibi (oxirgi qiymat yutadi): `matchg_1` → `applied_palette` → `applied_leafshading` → `applied_tweak1`
→ `applied_ground` → `applied_grass2` → `applied_aud1`. Jurnal qatori: `[material, parametr, eski, yangi]`.

* **SSS (barg orqali o'tgan nur):** M_Foliage_Masked / M_Foliage_Opaque_SSS instanslarida SubsurfaceTint
  (1,3; 1,4; 0,6) → (0,55; 0,65; 0,2), SubsurfaceAmount 0,5 (keyin leaf-shading ba'zilarida 0,7);
  M_Base_Leaf `subsurface_Brightness` > 0,7 → 0,6 (keyin 0,45). Sabab: tojalarning soya tomoni "yonib" turardi.
* **Palitra:** 23 barg materialida Brightness / Contrass / saturatsiya bir-biriga yaqinlashtirildi (turlar
  sariq, ko'k-yashil, kulrang bo'lib alohida turardi).
* **Leaf shading:** eng ko'p ekilgan Ashetree_00 (3512 dona) va teraklarda noto'g'ri ulangan barg normali —
  `Normal = 1` (tekis), 11 material; tojaning ichi qop-qora edi.
* **tweak1:** Ashetree_03 Brightness 0,9; MI_Plant_nn21 ColorBrightness 1,2, ColorSaturation 0,8.
* **aud1:** sakura Petal_2 `Petal Mode` 1 (yozda oq gullar ko'rinmaydi), Silver_Birch_Branch_Mat Desa 0,35 / EXP 0,8,
  Bruschatka_13/14 ko'lmak balandligi 0 (quyoshli kunda ko'lmak yo'q), Bruschatka_14 tint (0,9; 0,9; 0,95).
* **dub_4m_03_Leaf_Mat1 grafigi:** MF_Season_Leaf funksiyasining `SubsurfaceColor` kirishiga keladigan tekstura
  `Multiply(tekstura, ScalarParameter SSS_Scale = 0,3)` orqali o'tkaziladi (nok barglari limon-sariq yaltirardi).
  `SSS_Scale` parametri bo'lsa — qadam o'tkazib yuboriladi.

### Maysa, yo'lak, asfalt, suv

* M_Grass: BaseColor Tint (0,49; 0,71; 0,42), `Do MacroVary` = true, MV_NoisePower 1, MV_DetailIntensity 0,
  MV_PatchMult 0, MV_LargeScale 8e-5, MV_Tint_Lo (0,62; 0,72; 0,60), MV_Tint_Hi (1,15; 1,08; 0,85), MV_TintAmount 0,8.
* M_Bruschatka_09 tint (0,66; 0,62; 0,55) — iliq tosh; M_Asphalt_base_Inst tint (0,85; 0,84; 0,80).
* StarterContent M_Water_Lake Color (0,17; 0,21; 0,195) — to'q feruza.

### Teksturalar (`data/lookdev/tex_roles.json`, natija `logs/applied_tex.json`)

NoMipmaps → FromTextureGroup; TC_EDITOR_ICON → DEFAULT; never_stream → false; 2 ning darajasi bo'lmagan o'lcham →
stretch; shaffoflik/niqob xaritalarida alpha coverage (0,3333), 4k niqoblar 2048 gacha. 103 tekstura.
Sabab: uzoqdagi tojalarda uchqun, teshik va kulrang chet.

### Yorug'lik va post-process (`data/lookdev/lighting_state.json`)

* UDS: soat 13:00, vaqt animatsiyasi yo'q, bulut shakli tasodifiy emas, bulut tezligi 0,15, quyosh rangi
  (1; 0,99; 0,96), quyosh manba burchagi x0,5, Sun Yaw 120, bulut soyasi 0,45, **UDS ekspozitsiyasi o'chiq**
  (ekspozitsiya PPV da), osmon yorug'ligi 0,7, kunduzgi osmon rangi (1,12; 1,05; 0,85), tuman zichligi 0,0015,
  pasayishi 0,2, tuman ranglari ko'paytmasi (1; 0,88; 0,68), Mie 1,0, Saturation 1,0.
* UDW qo'lda ob-havo: bulut 1,5, tuman 0,05, shamol 1,0.
* UDS `Sun`: bilvosita yorug'lik 1,4, kontakt soya uzunligi 0,02. SkyAtmosphere aerial perspective 0.
* `PPV_Master_Runtime` (chegarasiz, prioritet 10): **qo'lda ekspozitsiya, bias 2,1**, oq balans 6500 / tint -0,02,
  gain (1,02; 1; 0,97), soya gain (1,02; 1,03; 0,90), soya saturatsiyasi 1,12, blue correction 0,6,
  expand gamut 0,8, local exposure highlight 0,8 / shadow 0,6, Lumen skylight leaking 0,1,
  Lumen final gather quality 2, bloom 0,3, vignette 0,15, lens flare / grain / fringe 0, motion blur 0,2.
* **CineCameraActor bazaviy holatda** — o'zida PP qiymati yo'q. Oldin kameraga qo'yilgan ekspozitsiya 1,75,
  soya kontrasti 0,9, skylight leaking 0,03 soyalarni qop-qora qilgan edi (mijoz talabi bilan tozalandi).

### `DefaultEngine.ini` (`data/lookdev/ini_settings.json`)

| Kalit | Qiymat | Sabab |
|---|---|---|
| `r.Tonemapper.Sharpen` | 1 | 2 da barglar atrofida oq chiziq |
| `r.Nanite.Streaming.StreamingPoolSize` | 1536 | 1024 da pul to'lib Nanite daraxt sifatini jimgina pasaytirardi; **2048 emas — assert** |
| `r.Nanite.Streaming.QualityScale.MinQuality` | 1.0 | uzoqdagi daraxtlar vaqt o'tib soddalashishining asosiy sababi |
| `r.ScreenPercentage` | 100 | 75 da mayda barglar yarim o'lchamda chizilardi |
| `r.TSR.ThinGeometryDetection` | 1 | yupqa shox/barglarda TSR uchquni |
| `r.Lumen.ScreenProbeGather.ShortRangeAO.FoliageOcclusionStrength` | 1.0 | toja ichida chuqurlik |
| (yuqori tier) `r.RayTracing.Enable`, `r.Lumen.HardwareRayTracing` | 1 | faqat 12 GB+ VRAM; Zaliniyda `Scripts/profile_lumen.py` profilida, 8 GB 4060 Ti uchun ini da o'chiq |

## Orqaga qaytarish

* Materiallar: `work/lookdev/materials_<sana>.json` da eski qiymatlar bor; yoki editor yopiq holda
  `<asset>.uasset.bak_<sana>` ni asl nomiga nusxalang.
* Teksturalar: `.uasset.bak_<sana>`.
* Level: `<level>.umap.bak_<sana>`. ini: `DefaultEngine.ini.bak_<sana>`.
