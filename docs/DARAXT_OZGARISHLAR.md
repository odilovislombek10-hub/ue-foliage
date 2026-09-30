# Daraxtlar ustidagi ish: materiallar va teksturalar (2026-09-30, Zaliniy)

Bu hujjat `offline/tools/make_tree_report.py` bilan `data/lookdev/` dagi loglardan avtomatik yasalgan. Hamma qiymatlar editorda qo'llanib, skrinshotlar bilan tekshirilgan. Qayta qo'llash: `ue/lookdev/apply_materials.py` va `ue/lookdev/fix_textures.py` (zaxira `.bak_` bilan, takror ishlatish xavfsiz).

**Diqqat:** `/Game/SHABLON/MODEL/...` dagi o'zgarishlar umumiy daraxt kutubxonasiga yoziladi - o'sha kompyuterdagi hamma loyihaga ta'sir qiladi.

## Topilgan muammolar va sabablari

- **matchg_1** - Barg yorug'lik o'tkazishi (SSS) juda kuchli edi: (1,3; 1,4; 0,6) x 0,8 - toj soya tomoni yonib, sarg'ish ko'rinardi. (0,55; 0,65; 0,2) x 0,5 ga tushirildi; M_Base_Leaf da subsurface_Brightness 0,6.
- **palette** - Turlar rangi bir-biridan uzoq edi (sariq-zaytun / ko'k-yashil / kulrang). Barg rangi parametrlari (Brightness, Contrast, Desaturation, EXP, Tint) referens palitrasiga yaqinlashtirildi.
- **leafshading** - Barg soyalanishi: M_Base_Leaf / M_Base_Reed da 'Normal' (FlattenNormal Flatness) 0 edi, Normal slotida esa haqiqiy normal xarita emas - toj ichi qop-qora chiqardi -> 1 (tekis). Yaltiroqlik (roughness/specular) va SSS turlar bo'yicha tekislandi.
- **tweak1** - Qator (lineup) tekshiruvidan keyin: 07_leaf juda sariq (Brightness 0,9), Corona_Proxy071 och-limon (ColorBrightness 1,2, Saturation 0,8).
- **aud1** - Odam bo'yi auditi: yozda gilos gullari (Petal Mode 1 - faqat bahorda), quyoshli kunda ko'lmaklar o'chirildi, to'q sariq tanalar (Silver_Birch_Branch_Mat Desa/EXP), maysa soyasidagi ko'k tus (MV_Tint).
- **ground** - Yer palitrasi: maysa rangi va katta masshtabli dog'lar, yo'lak (bruschatka) iliq tosh rangi, asfalt, suv.
- **grass2** - Maysa biroz to'qroq: BaseColor Tint (0,49; 0,71; 0,42).
- **Nok (dub_4m_03_Leaf_Mat1) grafigi** - yorug'lik o'tkazish (SubsurfaceColor) xom teksturadan olinardi, rangdan ~4 barobar kuchli (limon-sariq yaltirash). TextureSample va MF_Season_Leaf 'SubsurfaceColor' orasiga Multiply x ScalarParameter `SSS_Scale` = 0,3 qo'shildi.
- **Uzoqdagi daraxtlar** - 103 ta barg/po'stloq teksturasida mipmap yo'q edi (uzoqda uchqun, teshik, kulrang chet). Asosiy sabab esa Nanite oqim puli (1024 MB) to'lib, sifatni jimgina pasaytirishi edi: `r.Nanite.Streaming.StreamingPoolSize=1536`, `r.Nanite.Streaming.QualityScale.MinQuality=1.0` (docs/TESTLAR_VA_XULOSALAR.md).

Rasmlar: `docs/img/lineup_oldin.png` (tuzatishdan oldin 24 tur), `docs/img/lineup_keyin.png` (keyin), `docs/img/uzoq_daraxt_pool.png` (Nanite pul sinovi: chap yuqori - eski holat).

## Materiallar (55 ta material, 143 ta o'zgarish)

### `/Game/SHABLON/MODEL/export/mtl/MI_Plant_nn21`
- master: `M_Foliage_Opaque_SSS` (MSM_TWO_SIDED_FOLIAGE); ekilgan nusxalar (reja): 6468; turlar: Corona_Proxy071; scope: shared_library

| Parametr | Tur | Oldin | Keyin | Bosqich (sabab) |
|---|---|---|---|---|
| SubsurfaceTint | vector | (1.3, 1.4, 0.6) | (0.55, 0.65, 0.2) | matchg_1 |
| SubsurfaceAmount | scalar | - | 0.5 | matchg_1 |
| ColorBrightness | scalar | 1.6 | 1.2 | tweak1 |
| ColorSaturation | scalar | 0.9 | 0.8 | tweak1 |

### `/Game/SHABLON/MODEL/export/mtl/MI_Plant_nn22`
- master: `M_Foliage_Opaque_SSS` (MSM_TWO_SIDED_FOLIAGE); ekilgan nusxalar (reja): 6468; turlar: Corona_Proxy071; scope: shared_library

| Parametr | Tur | Oldin | Keyin | Bosqich (sabab) |
|---|---|---|---|---|
| SubsurfaceTint | vector | (1.3, 1.4, 0.6) | (0.55, 0.65, 0.2) | matchg_1 |
| SubsurfaceAmount | scalar | - | 0.5 | matchg_1 |

### `/Game/SHABLON/MODEL/IZGIRIT/TXTR/Material/Ashetree_00`
- master: `M_Base_Leaf` (MSM_TWO_SIDED_FOLIAGE); ekilgan nusxalar (reja): 3512; turlar: Ash-tree_0202_15_5m_, Ash-tree_05_21_2m_; scope: shared_library

| Parametr | Tur | Oldin | Keyin | Bosqich (sabab) |
|---|---|---|---|---|
| subsurface_Brightness | scalar | 1.55 | 0.6 | matchg_1 |
| Brightness | scalar | 0.8 | 1.05 | palette |
| Contrass | scalar | 1.2 | 1.1 | palette |
| Normal | scalar | 0 | 1 | leafshading |

### `/Game/SHABLON/MODEL/export/mtl/MI_Pandora_Land_Grey_Box_Westringia_Fruticosa_Coastal_Rosemary04_ID3`
- master: `M_Foliage_Masked` (MSM_TWO_SIDED_FOLIAGE); ekilgan nusxalar (reja): 2804; turlar: -; scope: shared_library

| Parametr | Tur | Oldin | Keyin | Bosqich (sabab) |
|---|---|---|---|---|
| SubsurfaceTint | vector | (1.3, 1.4, 0.6) | (0.55, 0.65, 0.2) | matchg_1 |
| SubsurfaceAmount | scalar | - | 0.5 | matchg_1 |

### `/Game/SHABLON/MODEL/export/mtl/MI_Pandora_Land_Grey_Box_Westringia_Fruticosa_Coastal_Rosemary_Flower04_ID3`
- master: `M_Foliage_Masked` (MSM_TWO_SIDED_FOLIAGE); ekilgan nusxalar (reja): 2624; turlar: -; scope: shared_library

| Parametr | Tur | Oldin | Keyin | Bosqich (sabab) |
|---|---|---|---|---|
| SubsurfaceTint | vector | (1.3, 1.4, 0.6) | (0.55, 0.65, 0.2) | matchg_1 |
| SubsurfaceAmount | scalar | - | 0.5 | matchg_1 |

### `/Game/SHABLON/MODEL/export/mtl/MI_Pandora_Land_Montra_Olive_Tree_Version7_1_ID3`
- master: `M_Foliage_Masked` (MSM_TWO_SIDED_FOLIAGE); ekilgan nusxalar (reja): 2593; turlar: Montra_Olive_Tree_Version7_1; scope: shared_library

| Parametr | Tur | Oldin | Keyin | Bosqich (sabab) |
|---|---|---|---|---|
| SubsurfaceTint | vector | (1.3, 1.4, 0.6) | (0.55, 0.65, 0.2) | matchg_1 |
| SubsurfaceAmount | scalar | - | 0.7 | matchg_1, leafshading |

### `/Game/SHABLON/MODEL/export/mtl/MI_Leaf`
- master: `M_Foliage_Masked` (MSM_TWO_SIDED_FOLIAGE); ekilgan nusxalar (reja): 1600; turlar: -; scope: shared_library

| Parametr | Tur | Oldin | Keyin | Bosqich (sabab) |
|---|---|---|---|---|
| SubsurfaceTint | vector | (1.3, 1.4, 0.6) | (0.55, 0.65, 0.2) | matchg_1 |
| SubsurfaceAmount | scalar | - | 0.5 | matchg_1 |

### `/Game/SHABLON/MODEL/export/mtl/MI_RH_Estate_Footed_Buxus_Leaves_1_Front`
- master: `M_Foliage_Opaque_SSS` (MSM_TWO_SIDED_FOLIAGE); ekilgan nusxalar (reja): 1439; turlar: -; scope: shared_library

| Parametr | Tur | Oldin | Keyin | Bosqich (sabab) |
|---|---|---|---|---|
| SubsurfaceTint | vector | (1.3, 1.4, 0.6) | (0.55, 0.65, 0.2) | matchg_1 |
| SubsurfaceAmount | scalar | - | 0.5 | matchg_1 |

### `/Game/SHABLON/MODEL/export/mtl/MI_Taiwa_Leaf_Mat`
- master: `M_Foliage_Masked` (MSM_TWO_SIDED_FOLIAGE); ekilgan nusxalar (reja): 1370; turlar: TSH-Tree002; scope: shared_library

| Parametr | Tur | Oldin | Keyin | Bosqich (sabab) |
|---|---|---|---|---|
| SubsurfaceTint | vector | (1.3, 1.4, 0.6) | (0.55, 0.65, 0.2) | matchg_1 |
| SubsurfaceAmount | scalar | - | 0.7 | matchg_1, leafshading |
| ColorSaturation | scalar | 0.9 | 1.15 | palette |
| ColorBrightness | scalar | 0.42 | 0.38 | palette |

### `/Game/SHABLON/MODEL/export/mtl/MI_Taiwa_Leaf_v2_Mat`
- master: `M_Foliage_Masked` (MSM_TWO_SIDED_FOLIAGE); ekilgan nusxalar (reja): 1370; turlar: TSH-Tree002; scope: shared_library

| Parametr | Tur | Oldin | Keyin | Bosqich (sabab) |
|---|---|---|---|---|
| SubsurfaceTint | vector | (1.3, 1.4, 0.6) | (0.55, 0.65, 0.2) | matchg_1 |
| SubsurfaceAmount | scalar | - | 0.7 | matchg_1, leafshading |
| ColorSaturation | scalar | 0.9 | 1.15 | palette |
| ColorBrightness | scalar | 0.4 | 0.36 | palette |

### `/Game/SHABLON/MODEL/export/mtl/MI_Taiwa_Leaf_v3_Mat`
- master: `M_Foliage_Masked` (MSM_TWO_SIDED_FOLIAGE); ekilgan nusxalar (reja): 1370; turlar: TSH-Tree002; scope: shared_library

| Parametr | Tur | Oldin | Keyin | Bosqich (sabab) |
|---|---|---|---|---|
| SubsurfaceTint | vector | (1.3, 1.4, 0.6) | (0.55, 0.65, 0.2) | matchg_1 |
| SubsurfaceAmount | scalar | - | 0.7 | matchg_1, leafshading |
| ColorSaturation | scalar | 0.9 | 1.15 | palette |
| ColorBrightness | scalar | 0.38 | 0.35 | palette |

### `/Game/SHABLON/MODEL/IZGIRIT/TXTR/Material/M_Populus_pyramidalis_02`
- master: `M_Base_Leaf` (MSM_TWO_SIDED_FOLIAGE); ekilgan nusxalar (reja): 1119; turlar: 18m_Terak_01, 18m_Terak_02, leaf; scope: shared_library

| Parametr | Tur | Oldin | Keyin | Bosqich (sabab) |
|---|---|---|---|---|
| subsurface_Brightness | scalar | 1.5 | 0.6 | matchg_1 |
| Brightness | scalar | 0.95 | 1.4 | palette |
| Contrass | scalar | 1.2 | 1.1 | palette |
| Desaturation | scalar | 0.1097 | 0.05 | palette |
| Normal | scalar | 0.3 | 1 | leafshading |

### `/Game/SHABLON/MODEL/IZGIRIT/TXTR/Material/M_Populus_pyramidalis_03`
- master: `M_Base_Leaf` (MSM_TWO_SIDED_FOLIAGE); ekilgan nusxalar (reja): 1119; turlar: 18m_Terak_01, 18m_Terak_02, leaf; scope: shared_library

| Parametr | Tur | Oldin | Keyin | Bosqich (sabab) |
|---|---|---|---|---|
| subsurface_Brightness | scalar | 1.5 | 0.6 | matchg_1 |
| Brightness | scalar | 0.7541 | 0.96 | palette |
| Contrass | scalar | 1.2 | 1.1 | palette |
| Desaturation | scalar | 0.1097 | 0.15 | palette |
| Normal | scalar | 0.3 | 1 | leafshading |

### `/Game/SHABLON/MODEL/IZGIRIT/TXTR/Material/M_Populus_pyramidalis_01`
- master: `M_Base_Leaf` (MSM_TWO_SIDED_FOLIAGE); ekilgan nusxalar (reja): 1048; turlar: 18m_Terak_01, 18m_Terak_02; scope: shared_library

| Parametr | Tur | Oldin | Keyin | Bosqich (sabab) |
|---|---|---|---|---|
| subsurface_Brightness | scalar | 1.5 | 0.6 | matchg_1 |
| Brightness | scalar | 0.905 | 1.28 | palette |
| Contrass | scalar | 1.2 | 1.1 | palette |
| Desaturation | scalar | 0.1097 | 0.05 | palette |
| Normal | scalar | 0.3 | 1 | leafshading |

### `/Game/SHABLON/MODEL/export/mtl/MI_Leaf_Front_7_Mat`
- master: `M_Foliage_Masked` (MSM_TWO_SIDED_FOLIAGE); ekilgan nusxalar (reja): 621; turlar: -; scope: shared_library

| Parametr | Tur | Oldin | Keyin | Bosqich (sabab) |
|---|---|---|---|---|
| SubsurfaceTint | vector | (1.3, 1.4, 0.6) | (0.55, 0.65, 0.2) | matchg_1 |
| SubsurfaceAmount | scalar | - | 0.5 | matchg_1 |

### `/Game/SHABLON/MODEL/export/mtl/MI_MT_PM_V66_Spiraea_japonica_01_Leaf_01`
- master: `M_Foliage_Masked` (MSM_TWO_SIDED_FOLIAGE); ekilgan nusxalar (reja): 471; turlar: -; scope: shared_library

| Parametr | Tur | Oldin | Keyin | Bosqich (sabab) |
|---|---|---|---|---|
| SubsurfaceTint | vector | (1.3, 1.4, 0.6) | (0.55, 0.65, 0.2) | matchg_1 |
| SubsurfaceAmount | scalar | - | 0.5 | matchg_1 |

### `/Game/SHABLON/MODEL/export/mtl/MI_Pandora_Land_Lavandula_Pedunculata_Atlantica_Stoechas_Subpedunculata02_ID4`
- master: `M_Foliage_Masked` (MSM_TWO_SIDED_FOLIAGE); ekilgan nusxalar (reja): 327; turlar: -; scope: shared_library

| Parametr | Tur | Oldin | Keyin | Bosqich (sabab) |
|---|---|---|---|---|
| SubsurfaceTint | vector | (1.3, 1.4, 0.6) | (0.55, 0.65, 0.2) | matchg_1 |
| SubsurfaceAmount | scalar | - | 0.5 | matchg_1 |

### `/Game/SHABLON/MODEL/export/mtl/MI_Pandora_Land_Lavandula_Pedunculata_Atlantica_Stoechas_Subpedunculata04_ID4`
- master: `M_Foliage_Masked` (MSM_TWO_SIDED_FOLIAGE); ekilgan nusxalar (reja): 288; turlar: -; scope: shared_library

| Parametr | Tur | Oldin | Keyin | Bosqich (sabab) |
|---|---|---|---|---|
| SubsurfaceTint | vector | (1.3, 1.4, 0.6) | (0.55, 0.65, 0.2) | matchg_1 |
| SubsurfaceAmount | scalar | - | 0.5 | matchg_1 |

### `/Game/SHABLON/MODEL/export/mtl/MI_Pandora_Land_Lavandula_Pedunculata_Atlantica_Stoechas_Subpedunculata03_ID4`
- master: `M_Foliage_Masked` (MSM_TWO_SIDED_FOLIAGE); ekilgan nusxalar (reja): 264; turlar: -; scope: shared_library

| Parametr | Tur | Oldin | Keyin | Bosqich (sabab) |
|---|---|---|---|---|
| SubsurfaceTint | vector | (1.3, 1.4, 0.6) | (0.55, 0.65, 0.2) | matchg_1 |
| SubsurfaceAmount | scalar | - | 0.5 | matchg_1 |

### `/Game/SHABLON/MODEL/export/mtl/MI_Pandora_Land_Grey_Box_Westringia_Fruticosa_Coastal_Rosemary_Flower_Version02_2_ID3`
- master: `M_Foliage_Masked` (MSM_TWO_SIDED_FOLIAGE); ekilgan nusxalar (reja): 234; turlar: -; scope: shared_library

| Parametr | Tur | Oldin | Keyin | Bosqich (sabab) |
|---|---|---|---|---|
| SubsurfaceTint | vector | (1.3, 1.4, 0.6) | (0.55, 0.65, 0.2) | matchg_1 |
| SubsurfaceAmount | scalar | - | 0.5 | matchg_1 |

### `/Game/SHABLON/MODEL/IZGIRIT/TXTR/Material/M_Anelanchier_01`
- master: `M_Base_Leaf` (MSM_TWO_SIDED_FOLIAGE); ekilgan nusxalar (reja): 114; turlar: 3m_Irga_02; scope: shared_library

| Parametr | Tur | Oldin | Keyin | Bosqich (sabab) |
|---|---|---|---|---|
| subsurface_Brightness | scalar | 1.5 | 0.6 | matchg_1 |
| Brightness | scalar | 0.7541 | 0.8 | palette |
| Desaturation | scalar | 0.1097 | 0.25 | palette |
| Normal | scalar | 0.4017 | 1 | leafshading |

### `/Game/SHABLON/MODEL/IZGIRIT/TXTR/Material/Ashetree_1`
- master: `M_Base_Leaf` (MSM_TWO_SIDED_FOLIAGE); ekilgan nusxalar (reja): 105; turlar: Ash_tree_1; scope: shared_library

| Parametr | Tur | Oldin | Keyin | Bosqich (sabab) |
|---|---|---|---|---|
| subsurface_Brightness | scalar | 1.2 | 0.45 | matchg_1, leafshading |
| Brightness | scalar | 0.6 | 0.72 | palette |
| Desaturation | scalar | 0.25 | 0.3 | palette |
| Normal | scalar | 0 | 1 | leafshading |

### `/Game/SHABLON/MODEL/IZGIRIT/TXTR/Material/Ashetree_2`
- master: `M_Base_Leaf` (MSM_TWO_SIDED_FOLIAGE); ekilgan nusxalar (reja): 105; turlar: Ash_tree_1; scope: shared_library

| Parametr | Tur | Oldin | Keyin | Bosqich (sabab) |
|---|---|---|---|---|
| subsurface_Brightness | scalar | 0.8 | 0.45 | matchg_1, leafshading |
| Brightness | scalar | 0.6 | 0.72 | palette |
| Desaturation | scalar | 0.25 | 0.3 | palette |
| Normal | scalar | 0 | 1 | leafshading |

### `/Game/SHABLON/MODEL/IZGIRIT/TXTR/Material/Ashetree_3`
- master: `M_Base_Leaf` (MSM_TWO_SIDED_FOLIAGE); ekilgan nusxalar (reja): 105; turlar: Ash_tree_1; scope: shared_library

| Parametr | Tur | Oldin | Keyin | Bosqich (sabab) |
|---|---|---|---|---|
| subsurface_Brightness | scalar | 1 | 0.45 | matchg_1, leafshading |
| Brightness | scalar | 0.6 | 0.72 | palette |
| Desaturation | scalar | 0.25 | 0.3 | palette |
| Normal | scalar | 0 | 1 | leafshading |

### `/Game/SHABLON/MODEL/IZGIRIT/TXTR/Material/Ashetree_03`
- master: `M_Base_Leaf` (MSM_TWO_SIDED_FOLIAGE); ekilgan nusxalar (reja): 71; turlar: leaf; scope: shared_library

| Parametr | Tur | Oldin | Keyin | Bosqich (sabab) |
|---|---|---|---|---|
| subsurface_Brightness | scalar | 1 | 0.6 | matchg_1 |
| Brightness | scalar | 0.8 | 0.9 | palette, tweak1 |
| Contrass | scalar | 1.2 | 1.1 | palette |
| Normal | scalar | 0 | 1 | leafshading |

### `/Game/SHABLON/MODEL/export/mtl/MI_palnt`
- master: `M_Foliage_Masked` (MSM_TWO_SIDED_FOLIAGE); ekilgan nusxalar (reja): 57; turlar: -; scope: shared_library

| Parametr | Tur | Oldin | Keyin | Bosqich (sabab) |
|---|---|---|---|---|
| SubsurfaceTint | vector | (1.3, 1.4, 0.6) | (0.55, 0.65, 0.2) | matchg_1 |
| SubsurfaceAmount | scalar | - | 0.5 | matchg_1 |

### `/Game/SHABLON/MODEL/export/mtl/MI_Material_3_Mat_2Sided`
- master: `M_Foliage_Masked` (MSM_TWO_SIDED_FOLIAGE); ekilgan nusxalar (reja): 52; turlar: Corona_Proxy137; scope: shared_library

| Parametr | Tur | Oldin | Keyin | Bosqich (sabab) |
|---|---|---|---|---|
| SubsurfaceTint | vector | (1.3, 1.4, 0.6) | (0.55, 0.65, 0.2) | matchg_1 |
| SubsurfaceAmount | scalar | - | 0.7 | matchg_1, leafshading |
| ColorTint | vector | (1, 1, 1) | (1.08, 1, 0.8) | palette |

### `/Game/SHABLON/MODEL/export/mtl/MI_FicusBenjamina_leaf_01_diffuse_Copy_Mat`
- master: `M_Foliage_Masked` (MSM_TWO_SIDED_FOLIAGE); ekilgan nusxalar (reja): 7; turlar: -; scope: shared_library

| Parametr | Tur | Oldin | Keyin | Bosqich (sabab) |
|---|---|---|---|---|
| SubsurfaceTint | vector | (1.3, 1.4, 0.6) | (0.55, 0.65, 0.2) | matchg_1 |
| SubsurfaceAmount | scalar | - | 0.5 | matchg_1 |

### `/Game/SHABLON/MODEL/export/mtl/MI_FicusBenjamina_leaf_01_diffuse_Copy_Copy_Mat`
- master: `M_Foliage_Masked` (MSM_TWO_SIDED_FOLIAGE); ekilgan nusxalar (reja): 4; turlar: -; scope: shared_library

| Parametr | Tur | Oldin | Keyin | Bosqich (sabab) |
|---|---|---|---|---|
| SubsurfaceTint | vector | (1.3, 1.4, 0.6) | (0.55, 0.65, 0.2) | matchg_1 |
| SubsurfaceAmount | scalar | - | 0.5 | matchg_1 |

### `/Game/SHABLON/MODEL/export/mtl/MI_FicusBenjamina_leaf_01_diffuse_Mat`
- master: `M_Foliage_Masked` (MSM_TWO_SIDED_FOLIAGE); ekilgan nusxalar (reja): 1; turlar: -; scope: shared_library

| Parametr | Tur | Oldin | Keyin | Bosqich (sabab) |
|---|---|---|---|---|
| SubsurfaceTint | vector | (1.3, 1.4, 0.6) | (0.55, 0.65, 0.2) | matchg_1 |
| SubsurfaceAmount | scalar | - | 0.5 | matchg_1 |

### `/Game/SHABLON/MODEL/DARAXT/TXTR/Speed_tree/Silver_Birch_Large/Silver_Birch_02_Leaf_Mat`
- master: `Silver_Birch_02_Leaf_Mat` (MSM_TWO_SIDED_FOLIAGE); ekilgan nusxalar (reja): 48; turlar: Silver_Birch_02; scope: shared_library

| Parametr | Tur | Oldin | Keyin | Bosqich (sabab) |
|---|---|---|---|---|
| Brightness | scalar | 1 | 1.05 | palette |
| desaturation | scalar | 0.3 | 0.15 | palette |

### `/Game/SHABLON/MODEL/DARAXT/TXTR/Speed_tree/Sample_Broadleaf_Forest2/Sample_Broadleaf_Forest2_Leaf_Mat`
- master: `Sample_Broadleaf_Forest2_Leaf_Mat` (MSM_TWO_SIDED_FOLIAGE); ekilgan nusxalar (reja): 192; turlar: Sample_Broadleaf_Forest2; scope: shared_library

| Parametr | Tur | Oldin | Keyin | Bosqich (sabab) |
|---|---|---|---|---|
| Brightness | scalar | 0.7 | 0.55 | palette |
| contrast | scalar | 1.5 | 1.25 | palette |
| desaturation | scalar | 0.4 | 0.2 | palette |
| scontrast | scalar | 1.3 | 2.6 | leafshading |

### `/Game/SHABLON/MODEL/DARAXT/TXTR/Speed_tree/Sample_Broadleaf_Forest3/Sample_Broadleaf_Forest3_Leaf_Mat`
- master: `Sample_Broadleaf_Forest3_Leaf_Mat` (MSM_TWO_SIDED_FOLIAGE); ekilgan nusxalar (reja): 495; turlar: Sample_Broadleaf_Forest3; scope: shared_library

| Parametr | Tur | Oldin | Keyin | Bosqich (sabab) |
|---|---|---|---|---|
| Brightness | scalar | 1 | 0.52 | palette |
| contrast | scalar | 1.8 | 1.25 | palette |
| desaturation | scalar | 0.4 | 0.2 | palette |
| scontrast | scalar | 1.3 | 2.6 | leafshading |

### `/Game/SHABLON/MODEL/DARAXT/TXTR/Speed_tree/Ashe_Tree/Ash_tree_Leaf_Mat`
- master: `Ash_tree_Leaf_Mat` (MSM_TWO_SIDED_FOLIAGE); ekilgan nusxalar (reja): 421; turlar: Ash_tree; scope: shared_library

| Parametr | Tur | Oldin | Keyin | Bosqich (sabab) |
|---|---|---|---|---|
| Brightness | scalar | 0.8 | 0.72 | palette |
| desaturation | scalar | 0.3 | 0.25 | palette |

### `/Game/SHABLON/MODEL/DARAXT/TXTR/NEW_TREE_1_Inst5`
- master: `NEW_TREE_1` (MSM_DEFAULT_LIT); ekilgan nusxalar (reja): 44; turlar: leaf_MatSG; scope: shared_library

| Parametr | Tur | Oldin | Keyin | Bosqich (sabab) |
|---|---|---|---|---|
| EXP | scalar | 0.264 | 0.34 | palette |
| Desa | scalar | 0.184 | 0.25 | palette |
| Specular | scalar | 0 | 0.3 | leafshading |
| Rouhnes | scalar | 1 | 3 | leafshading |

### `/Game/SHABLON/MODEL/DARAXT/TXTR/NEW_TREE_1_Inst`
- master: `NEW_TREE_1` (MSM_DEFAULT_LIT); ekilgan nusxalar (reja): 134; turlar: Lagerstroemia_speciosa; scope: shared_library

| Parametr | Tur | Oldin | Keyin | Bosqich (sabab) |
|---|---|---|---|---|
| EXP | scalar | 0.272 | 0.36 | palette |
| Desa | scalar | -0.6037 | -0.3 | palette |
| Specular | scalar | 0 | 0.3 | leafshading |

### `/Game/SHABLON/MODEL/DARAXT/TXTR/dub_4m_03_Leaf_Mat1_Inst`
- master: `dub_4m_03_Leaf_Mat1` (MSM_TWO_SIDED_FOLIAGE); ekilgan nusxalar (reja): 2340; turlar: Autumn_pear_tree_02_02; scope: shared_library

| Parametr | Tur | Oldin | Keyin | Bosqich (sabab) |
|---|---|---|---|---|
| EXP | scalar | 0.224 | 0.23 | palette |
| Desa | scalar | -0.02411 | 0.1 | palette |

### `/Game/SHABLON/MODEL/DARAXT/yangi/TEXTURA/MI_Leaf_1a`
- master: `M_Auto_Foliage` (MSM_TWO_SIDED_FOLIAGE); ekilgan nusxalar (reja): 356; turlar: Autumn_hornbeam_02_02; scope: shared_library

| Parametr | Tur | Oldin | Keyin | Bosqich (sabab) |
|---|---|---|---|---|
| Tint | vector | (1, 1, 1) | (0.72, 0.76, 1) | palette |
| RoughnessConst | scalar | 0.42 | 0.65 | leafshading |

### `/Game/SHABLON/MODEL/DARAXT/yangi/TEXTURA/MI_Leaf_2a`
- master: `M_Auto_Foliage` (MSM_TWO_SIDED_FOLIAGE); ekilgan nusxalar (reja): 356; turlar: Autumn_hornbeam_02_02; scope: shared_library

| Parametr | Tur | Oldin | Keyin | Bosqich (sabab) |
|---|---|---|---|---|
| Tint | vector | (1, 1, 1) | (0.55, 0.7, 1) | palette |
| RoughnessConst | scalar | 0.47 | 0.65 | leafshading |

### `/Game/SHABLON/MODEL/DARAXT/yangi/TEXTURA/MI_Leaf_3a`
- master: `M_Auto_Foliage` (MSM_TWO_SIDED_FOLIAGE); ekilgan nusxalar (reja): 356; turlar: Autumn_hornbeam_02_02; scope: shared_library

| Parametr | Tur | Oldin | Keyin | Bosqich (sabab) |
|---|---|---|---|---|
| Tint | vector | (1, 1, 1) | (0.55, 0.7, 1) | palette |
| RoughnessConst | scalar | 0.5 | 0.65 | leafshading |

### `/Game/SHABLON/MODEL/IZGIRIT/TXTR/Material/M_Anelanchier_03`
- master: `M_Base_Leaf` (MSM_TWO_SIDED_FOLIAGE); ekilgan nusxalar (reja): 1105; turlar: 18m_Terak_01, 18m_Terak_02, 3m_Irga_02; scope: shared_library

| Parametr | Tur | Oldin | Keyin | Bosqich (sabab) |
|---|---|---|---|---|
| Normal | scalar | 0 | 1 | leafshading |

### `/Game/SHABLON/MODEL/IZGIRIT/TXTR/Material/M_Philotheca_Myoporoides_Leaf`
- master: `M_Base_Reed` (MSM_TWO_SIDED_FOLIAGE); ekilgan nusxalar (reja): 878; turlar: Ash-tree_0202_15_5m_, Ash-tree_05_21_2m_; scope: shared_library

| Parametr | Tur | Oldin | Keyin | Bosqich (sabab) |
|---|---|---|---|---|
| Normal | scalar | 0.5059 | 1 | leafshading |

### `/Game/SHABLON/MODEL/DARAXT/TXTR/Speed_tree/Silver_Birch_Small/Silver_Birch_Medium_6m_01_Leaf_Mat`
- master: `Silver_Birch_Medium_6m_01_Leaf_Mat` (MSM_SUBSURFACE); ekilgan nusxalar (reja): 99; turlar: Silver_Birch_Medium_6m_01; scope: shared_library

| Parametr | Tur | Oldin | Keyin | Bosqich (sabab) |
|---|---|---|---|---|
| subsurdace | scalar | 1 | 0.6 | leafshading |

### `/Game/SHABLON/MODEL/DARAXT/sakura/Materials/Leaf01_2`
- master: `Leaf01` (MSM_TWO_SIDED_FOLIAGE); ekilgan nusxalar (reja): 201; turlar: Cherry_flowering_0302_Cerasus_; scope: shared_library

| Parametr | Tur | Oldin | Keyin | Bosqich (sabab) |
|---|---|---|---|---|
| Reflection_Glossiness (10) | scalar | 0.83 | 0.45 | leafshading |

### `/Game/SHABLON/MODEL/DARAXT/yangi/TEXTURA/MI_Twigs`
- master: `M_Auto_Opaque` (MSM_DEFAULT_LIT); ekilgan nusxalar (reja): 356; turlar: Autumn_hornbeam_02_02; scope: shared_library

| Parametr | Tur | Oldin | Keyin | Bosqich (sabab) |
|---|---|---|---|---|
| RoughnessConst | scalar | 0 | 0.8 | leafshading |

### `/Game/SHABLON/MODEL/DARAXT/TXTR/NEW_TREE_1_Inst2`
- master: `NEW_TREE_1` (MSM_DEFAULT_LIT); ekilgan nusxalar (reja): 228; turlar: -; scope: shared_library

| Parametr | Tur | Oldin | Keyin | Bosqich (sabab) |
|---|---|---|---|---|
| Specular | scalar | 0 | 0.3 | leafshading |
| Rouhnes | scalar | 1 | 3 | leafshading |

### `/Game/SHABLON/MODEL/DARAXT/TXTR/NEW_TREE_1_Inst1`
- master: `NEW_TREE_1` (MSM_DEFAULT_LIT); ekilgan nusxalar (reja): 670; turlar: Lagerstroemia_speciosa; scope: shared_library

| Parametr | Tur | Oldin | Keyin | Bosqich (sabab) |
|---|---|---|---|---|
| Specular | scalar | 0 | 0.3 | leafshading |

### `/Game/SHABLON/MATERIAL/GAZON/M_Grass`
- master: `?` (?); ekilgan nusxalar (reja): -; turlar: -; scope: shared_material

| Parametr | Tur | Oldin | Keyin | Bosqich (sabab) |
|---|---|---|---|---|
| BaseColor Tint | vector | (0.6, 0.8, 0.42) | (0.49, 0.71, 0.42) | ground, grass2 |
| Do MacroVary | switch | False | True | ground |
| MV_NoisePower | scalar | 4 | 1 | ground |
| MV_DetailIntensity | scalar | 1 | 0 | ground |
| MV_PatchMult | scalar | 1 | 0 | ground |
| MV_LargeScale | scalar | 1.5e-05 | 8e-05 | ground, aud1 |
| MV_Tint_Hi | vector | (0.604, 0.742, 0.823) | (1.15, 1.08, 0.85) | ground, aud1 |
| MV_Tint_Lo | vector | (0.0344, 0.0423, 0.0469) | (0.62, 0.72, 0.6) | ground, aud1 |
| MV_TintAmount | scalar | 1 | 0.8 | ground, aud1 |

### `/Game/SHABLON/MATERIAL/BRUSCHATKA/M_Bruschatka_09`
- master: `?` (?); ekilgan nusxalar (reja): -; turlar: -; scope: shared_material

| Parametr | Tur | Oldin | Keyin | Bosqich (sabab) |
|---|---|---|---|---|
| BaseColor_Tint | vector | (1, 1, 1) | (0.66, 0.62, 0.55) | ground |

### `/Game/SHABLON/MATERIAL/ASFALT/M_Asphalt_base_Inst`
- master: `?` (?); ekilgan nusxalar (reja): -; turlar: -; scope: shared_material

| Parametr | Tur | Oldin | Keyin | Bosqich (sabab) |
|---|---|---|---|---|
| BaseColor Tint | vector | (1, 1, 1) | (0.85, 0.84, 0.8) | ground |

### `/Game/StarterContent/Materials/M_Water_Lake`
- master: `?` (?); ekilgan nusxalar (reja): -; turlar: -; scope: project

| Parametr | Tur | Oldin | Keyin | Bosqich (sabab) |
|---|---|---|---|---|
| Color | vector | (0.302, 0.353, 0.439) | (0.17, 0.21, 0.195) | ground |

### `/Game/SHABLON/MODEL/DARAXT/sakura/Materials/Petal_2`
- master: `Petal` (MSM_TWO_SIDED_FOLIAGE); ekilgan nusxalar (reja): 201; turlar: Cherry_flowering_0302_Cerasus_; scope: shared_library

| Parametr | Tur | Oldin | Keyin | Bosqich (sabab) |
|---|---|---|---|---|
| Petal Mode | scalar | 0 | 1 | aud1 |

### `/Game/SHABLON/MATERIAL/BRUSCHATKA/M_Bruschatka_13`
- master: `?` (?); ekilgan nusxalar (reja): -; turlar: -; scope: shared_material

| Parametr | Tur | Oldin | Keyin | Bosqich (sabab) |
|---|---|---|---|---|
| Puddle Height MFPD | scalar | 0.25 | 0 | aud1 |

### `/Game/SHABLON/MATERIAL/BRUSCHATKA/M_Bruschatka_14`
- master: `?` (?); ekilgan nusxalar (reja): -; turlar: -; scope: shared_material

| Parametr | Tur | Oldin | Keyin | Bosqich (sabab) |
|---|---|---|---|---|
| Puddle Height MFPD | scalar | 0.25 | 0 | aud1 |
| BaseColor_Tint | vector | (1, 1, 1) | (0.9, 0.9, 0.95) | aud1 |

### `/Game/SHABLON/MODEL/DARAXT/TXTR/Silver_Birch_Branch_Mat`
- master: `Silver_Birch_Branch_Mat` (MSM_DEFAULT_LIT); ekilgan nusxalar (reja): 233; turlar: Silver_Birch_Medium_6m_02, dub_4m_02; scope: shared_library

| Parametr | Tur | Oldin | Keyin | Bosqich (sabab) |
|---|---|---|---|---|
| Desa | scalar | 0 | 0.35 | aud1 |
| EXP | scalar | 1 | 0.8 | aud1 |

## Grafik o'zgarishi

| Material | Nima qilindi |
|---|---|
| `/Game/SHABLON/MODEL/DARAXT/TXTR/dub_4m_03_Leaf_Mat1` | TextureSample -> Multiply(A) ; ScalarParameter `SSS_Scale`=0,3 -> Multiply(B) ; Multiply -> MF_Season_Leaf.SubsurfaceColor (ue/lookdev/apply_materials.py) |

## Teksturalar (103 ta)

| Tekstura | Vazifasi | Asl o'lcham | O'zgarishlar |
|---|---|---|---|
| Green_jk3 | BaseColor, Glossiness, Transmission | 2880x1035 | mipmap yoqildi (NoMipmaps -> FromTextureGroup); 2 ning darajasiga cho'zildi (mip va oqim uchun) |
| Green_jk1 | BaseColor, Glossiness, Transmission | 2880x1035 | mipmap yoqildi (NoMipmaps -> FromTextureGroup); 2 ning darajasiga cho'zildi (mip va oqim uchun) |
| Ash-tree_leaf_diff | Diffuse, Roughness, Subsurface | 640x1200 | mipmap yoqildi (NoMipmaps -> FromTextureGroup); never_stream o'chirildi (oqimda yuklanadi); 2 ning darajasiga cho'zildi (mip va oqim uchun) |
| Ash-tree_leaf_opac | Mask | 640x1200 | mipmap yoqildi (NoMipmaps -> FromTextureGroup); never_stream o'chirildi (oqimda yuklanadi); 2 ning darajasiga cho'zildi (mip va oqim uchun); alpha coverage 0,3333 (uzoqda barg yo'qolmasin) |
| Poplar_leaf_bump | Normal, Roughness | 441x442 | mipmap yoqildi (NoMipmaps -> FromTextureGroup); siqish EditorIcon -> Default; never_stream o'chirildi (oqimda yuklanadi); 2 ning darajasiga cho'zildi (mip va oqim uchun) |
| Grey_Box_Westringia_Fruticosa_Coastal_Rosemary_Branch | BaseColor | 380x4096 | mipmap yoqildi (NoMipmaps -> FromTextureGroup); 2 ning darajasiga cho'zildi (mip va oqim uchun) |
| Grey_Box_Westringia_Fruticosa_Coastal_Rosemary_Branch_Normal | Normal | 380x4096 | mipmap yoqildi (NoMipmaps -> FromTextureGroup); 2 ning darajasiga cho'zildi (mip va oqim uchun) |
| Grey_Box_Westringia_Fruticosa_Coastal_Rosemary_Branch_Gloss | Glossiness | 380x4096 | mipmap yoqildi (NoMipmaps -> FromTextureGroup); 2 ning darajasiga cho'zildi (mip va oqim uchun) |
| Grey_Box_Westringia_Fruticosa_Coastal_Rosemary_Leaf_Opacity | Opacity | 4096x4096 | mipmap yoqildi (NoMipmaps -> FromTextureGroup); never_stream o'chirildi (oqimda yuklanadi); alpha coverage 0,3333 (uzoqda barg yo'qolmasin); maks. o'lcham 2048 |
| Grey_Box_Westringia_Fruticosa_Coastal_Rosemary_Flower_Opacity | Opacity | 4096x4096 | mipmap yoqildi (NoMipmaps -> FromTextureGroup); never_stream o'chirildi (oqimda yuklanadi); alpha coverage 0,3333 (uzoqda barg yo'qolmasin); maks. o'lcham 2048 |
| Montra_Olive_Tree_Leaf_Opacity | Opacity | 4096x4096 | mipmap yoqildi (NoMipmaps -> FromTextureGroup); never_stream o'chirildi (oqimda yuklanadi); alpha coverage 0,3333 (uzoqda barg yo'qolmasin); maks. o'lcham 2048 |
| Poplar_trunk_diffuse | Diffuse | 1048x3968 | mipmap yoqildi (NoMipmaps -> FromTextureGroup); never_stream o'chirildi (oqimda yuklanadi); 2 ning darajasiga cho'zildi (mip va oqim uchun) |
| Poplar_trunk_normal | Normal | 1048x3968 | mipmap yoqildi (NoMipmaps -> FromTextureGroup); never_stream o'chirildi (oqimda yuklanadi); 2 ning darajasiga cho'zildi (mip va oqim uchun) |
| Poplar_trunk_displace | Roughness | 1048x3968 | mipmap yoqildi (NoMipmaps -> FromTextureGroup); never_stream o'chirildi (oqimda yuklanadi); 2 ning darajasiga cho'zildi (mip va oqim uchun) |
| Oak_bark_diff_02 | Diffuse | 2747x6760 | siqish EditorIcon -> Default; never_stream o'chirildi (oqimda yuklanadi); 2 ning darajasiga cho'zildi (mip va oqim uchun) |
| Oak_bark_Normal_02 | Normal | 2747x6760 | never_stream o'chirildi (oqimda yuklanadi); 2 ning darajasiga cho'zildi (mip va oqim uchun) |
| Oak_bark_Displ_02 | Roughness | 2747x6760 | siqish EditorIcon -> Default; never_stream o'chirildi (oqimda yuklanadi); 2 ning darajasiga cho'zildi (mip va oqim uchun) |
| Elm_leaf_01_diff | BaseColor | 800x1340 | mipmap yoqildi (NoMipmaps -> FromTextureGroup); 2 ning darajasiga cho'zildi (mip va oqim uchun) |
| Elm_leaf_01_bump | Normal | 800x1340 | mipmap yoqildi (NoMipmaps -> FromTextureGroup); 2 ning darajasiga cho'zildi (mip va oqim uchun) |
| Elm_leaf_01_opac | Opacity | 800x1340 | mipmap yoqildi (NoMipmaps -> FromTextureGroup); never_stream o'chirildi (oqimda yuklanadi); 2 ning darajasiga cho'zildi (mip va oqim uchun); alpha coverage 0,3333 (uzoqda barg yo'qolmasin) |
| Elm_leaf_01_trans | Transmission | 800x1340 | mipmap yoqildi (NoMipmaps -> FromTextureGroup); 2 ning darajasiga cho'zildi (mip va oqim uchun) |
| RH_Estate_Footed_Trunk_Diff | BaseColor | 150x2000 | mipmap yoqildi (NoMipmaps -> FromTextureGroup); 2 ning darajasiga cho'zildi (mip va oqim uchun) |
| RH_Estate_Footed_Leaf_Diff | BaseColor | 409x856 | mipmap yoqildi (NoMipmaps -> FromTextureGroup); 2 ning darajasiga cho'zildi (mip va oqim uchun) |
| Taiwa_Leaf | BaseColor | 164x512 | mipmap yoqildi (NoMipmaps -> FromTextureGroup); 2 ning darajasiga cho'zildi (mip va oqim uchun) |
| Taiwa_Leaf_Normal | Normal | 164x512 | mipmap yoqildi (NoMipmaps -> FromTextureGroup); 2 ning darajasiga cho'zildi (mip va oqim uchun) |
| Taiwa_Leaf_Opacity | Opacity | 164x512 | mipmap yoqildi (NoMipmaps -> FromTextureGroup); never_stream o'chirildi (oqimda yuklanadi); 2 ning darajasiga cho'zildi (mip va oqim uchun); alpha coverage 0,3333 (uzoqda barg yo'qolmasin) |
| Taiwa_Leaf_v2 | BaseColor | 164x512 | mipmap yoqildi (NoMipmaps -> FromTextureGroup); 2 ning darajasiga cho'zildi (mip va oqim uchun) |
| Taiwa_Leaf_v3 | BaseColor | 164x512 | mipmap yoqildi (NoMipmaps -> FromTextureGroup); 2 ning darajasiga cho'zildi (mip va oqim uchun) |
| Poplar_leaf_diffuse_02 | Diffuse, Subsurface | 441x442 | mipmap yoqildi (NoMipmaps -> FromTextureGroup); siqish EditorIcon -> Default; never_stream o'chirildi (oqimda yuklanadi); 2 ning darajasiga cho'zildi (mip va oqim uchun) |
| Poplar_leaf_opacity | Mask | 441x442 | mipmap yoqildi (NoMipmaps -> FromTextureGroup); siqish EditorIcon -> Default; never_stream o'chirildi (oqimda yuklanadi); 2 ning darajasiga cho'zildi (mip va oqim uchun); alpha coverage 0,3333 (uzoqda barg yo'qolmasin) |
| Poplar_leaf_diffuse_03 | Diffuse, Subsurface | 441x442 | mipmap yoqildi (NoMipmaps -> FromTextureGroup); siqish EditorIcon -> Default; never_stream o'chirildi (oqimda yuklanadi); 2 ning darajasiga cho'zildi (mip va oqim uchun) |
| Amelanchier_stem_01_diff | Diffuse, Normal, Roughness, Subsurface | 52x298 | mipmap yoqildi (NoMipmaps -> FromTextureGroup); siqish EditorIcon -> Default; never_stream o'chirildi (oqimda yuklanadi); 2 ning darajasiga cho'zildi (mip va oqim uchun) |
| Poplar_leaf_diffuse_01 | Diffuse, Subsurface | 441x442 | mipmap yoqildi (NoMipmaps -> FromTextureGroup); siqish EditorIcon -> Default; never_stream o'chirildi (oqimda yuklanadi); 2 ning darajasiga cho'zildi (mip va oqim uchun) |
| MT_PM_V66_Perovskia_atriplicifolia_01_Stem_01_albedo | BaseColor | 193x2352 | mipmap yoqildi (NoMipmaps -> FromTextureGroup); 2 ning darajasiga cho'zildi (mip va oqim uchun) |
| MT_PM_V66_Perovskia_atriplicifolia_01_Stem_01_normal | Normal | 193x2352 | mipmap yoqildi (NoMipmaps -> FromTextureGroup); 2 ning darajasiga cho'zildi (mip va oqim uchun) |
| MT_PM_V66_Perovskia_atriplicifolia_01_Stem_01_glossiness | Glossiness | 193x2352 | mipmap yoqildi (NoMipmaps -> FromTextureGroup); 2 ning darajasiga cho'zildi (mip va oqim uchun) |
| MT_PM_V66_Perovskia_atriplicifolia_01_Leaf_01_albedo | BaseColor | 3256x3256 | mipmap yoqildi (NoMipmaps -> FromTextureGroup); 2 ning darajasiga cho'zildi (mip va oqim uchun) |
| MT_PM_V66_Perovskia_atriplicifolia_01_Leaf_01_normal | Normal | 3256x3256 | mipmap yoqildi (NoMipmaps -> FromTextureGroup); 2 ning darajasiga cho'zildi (mip va oqim uchun) |
| MT_PM_V66_Perovskia_atriplicifolia_01_Leaf_01_opacity | Opacity | 3256x3256 | mipmap yoqildi (NoMipmaps -> FromTextureGroup); never_stream o'chirildi (oqimda yuklanadi); 2 ning darajasiga cho'zildi (mip va oqim uchun); alpha coverage 0,3333 (uzoqda barg yo'qolmasin) |
| MT_PM_V66_Perovskia_atriplicifolia_01_Leaf_01_glossiness | Glossiness | 3256x3256 | mipmap yoqildi (NoMipmaps -> FromTextureGroup); 2 ning darajasiga cho'zildi (mip va oqim uchun) |
| MT_PM_V66_Perovskia_atriplicifolia_01_Leaf_01_translucency | Transmission | 3256x3256 | mipmap yoqildi (NoMipmaps -> FromTextureGroup); 2 ning darajasiga cho'zildi (mip va oqim uchun) |
| MT_PM_V66_Perovskia_atriplicifolia_01_Stalk_01_albedo | BaseColor | 221x370 | mipmap yoqildi (NoMipmaps -> FromTextureGroup); 2 ning darajasiga cho'zildi (mip va oqim uchun) |
| MT_PM_V66_Perovskia_atriplicifolia_01_Stalk_01_normal | Normal | 221x370 | mipmap yoqildi (NoMipmaps -> FromTextureGroup); 2 ning darajasiga cho'zildi (mip va oqim uchun) |
| MT_PM_V66_Perovskia_atriplicifolia_01_Stalk_01_glossiness | Glossiness | 221x370 | mipmap yoqildi (NoMipmaps -> FromTextureGroup); 2 ning darajasiga cho'zildi (mip va oqim uchun) |
| MT_PM_V66_Perovskia_atriplicifolia_01_Flower_01_albedo | BaseColor | 590x1095 | mipmap yoqildi (NoMipmaps -> FromTextureGroup); 2 ning darajasiga cho'zildi (mip va oqim uchun) |
| MT_PM_V66_Perovskia_atriplicifolia_01_Flower_01_normal | Normal | 590x1095 | mipmap yoqildi (NoMipmaps -> FromTextureGroup); 2 ning darajasiga cho'zildi (mip va oqim uchun) |
| MT_PM_V66_Perovskia_atriplicifolia_01_Flower_01_opacity | Opacity | 590x1095 | mipmap yoqildi (NoMipmaps -> FromTextureGroup); never_stream o'chirildi (oqimda yuklanadi); 2 ning darajasiga cho'zildi (mip va oqim uchun); alpha coverage 0,3333 (uzoqda barg yo'qolmasin) |
| MT_PM_V66_Perovskia_atriplicifolia_01_Flower_01_glossiness | Glossiness | 590x1095 | mipmap yoqildi (NoMipmaps -> FromTextureGroup); 2 ning darajasiga cho'zildi (mip va oqim uchun) |
| MT_PM_V66_Perovskia_atriplicifolia_01_Flower_01_translucency | Transmission | 590x1095 | mipmap yoqildi (NoMipmaps -> FromTextureGroup); 2 ning darajasiga cho'zildi (mip va oqim uchun) |
| Phuctraining_Tropicalleaf_2_R | texture | 618x1600 | mipmap yoqildi (NoMipmaps -> FromTextureGroup); siqish EditorIcon -> Default; never_stream o'chirildi (oqimda yuklanadi); 2 ning darajasiga cho'zildi (mip va oqim uchun) |
| 12eawdaw31 | Diffuse | 2000x2000 | mipmap yoqildi (NoMipmaps -> FromTextureGroup); never_stream o'chirildi (oqimda yuklanadi); 2 ning darajasiga cho'zildi (mip va oqim uchun) |
| 12eawdaw32 | Normal, Roughness | 2000x2000 | mipmap yoqildi (NoMipmaps -> FromTextureGroup); never_stream o'chirildi (oqimda yuklanadi); 2 ning darajasiga cho'zildi (mip va oqim uchun) |
| Lavandula_Pedunculata_Atlantica_Stoechas_Subpedunculata_Branch | BaseColor | 626x4096 | mipmap yoqildi (NoMipmaps -> FromTextureGroup); 2 ning darajasiga cho'zildi (mip va oqim uchun) |
| Lavandula_Pedunculata_Atlantica_Stoechas_Subpedunculata_Branch_Normal | Normal | 626x4096 | mipmap yoqildi (NoMipmaps -> FromTextureGroup); 2 ning darajasiga cho'zildi (mip va oqim uchun) |
| Smooth_Wild_Hydrangea_Arborescens_Annabelle_Trunk | Glossiness | 380x4096 | mipmap yoqildi (NoMipmaps -> FromTextureGroup); 2 ning darajasiga cho'zildi (mip va oqim uchun) |
| Leaf_Front_7 | BaseColor | 164x512 | mipmap yoqildi (NoMipmaps -> FromTextureGroup); 2 ning darajasiga cho'zildi (mip va oqim uchun) |
| Leaf_Front_7_Normal | Normal | 164x512 | mipmap yoqildi (NoMipmaps -> FromTextureGroup); 2 ning darajasiga cho'zildi (mip va oqim uchun) |
| Leaf_Front_7_Opacity | Opacity | 164x512 | mipmap yoqildi (NoMipmaps -> FromTextureGroup); never_stream o'chirildi (oqimda yuklanadi); 2 ning darajasiga cho'zildi (mip va oqim uchun); alpha coverage 0,3333 (uzoqda barg yo'qolmasin) |
| Leaf_Front_7_Gloss | Glossiness | 164x512 | mipmap yoqildi (NoMipmaps -> FromTextureGroup); 2 ning darajasiga cho'zildi (mip va oqim uchun) |
| Leaf_Front_7_SubsurfaceColor | Transmission | 164x512 | mipmap yoqildi (NoMipmaps -> FromTextureGroup); 2 ning darajasiga cho'zildi (mip va oqim uchun) |
| T73_bark_s | Diffuse | 1200x7000 | mipmap yoqildi (NoMipmaps -> FromTextureGroup); never_stream o'chirildi (oqimda yuklanadi); 2 ning darajasiga cho'zildi (mip va oqim uchun) |
| T73_bark_s_normal | Normal | 1200x7000 | mipmap yoqildi (NoMipmaps -> FromTextureGroup); never_stream o'chirildi (oqimda yuklanadi); 2 ning darajasiga cho'zildi (mip va oqim uchun) |
| MT_PM_V66_Spiraea_japonica_01_Stem_01_albedo | BaseColor | 130x3748 | mipmap yoqildi (NoMipmaps -> FromTextureGroup); 2 ning darajasiga cho'zildi (mip va oqim uchun) |
| MT_PM_V66_Spiraea_japonica_01_Stem_01_normal | Normal | 130x3748 | mipmap yoqildi (NoMipmaps -> FromTextureGroup); 2 ning darajasiga cho'zildi (mip va oqim uchun) |
| MT_PM_V66_Spiraea_japonica_01_Stem_01_glossiness | Glossiness | 130x3748 | mipmap yoqildi (NoMipmaps -> FromTextureGroup); 2 ning darajasiga cho'zildi (mip va oqim uchun) |
| MT_PM_V66_Spiraea_japonica_01_Leaf_01_opacity | Opacity | 4096x4096 | mipmap yoqildi (NoMipmaps -> FromTextureGroup); never_stream o'chirildi (oqimda yuklanadi); alpha coverage 0,3333 (uzoqda barg yo'qolmasin); maks. o'lcham 2048 |
| MT_PM_V66_Spiraea_japonica_01_Petiole_01_albedo | BaseColor | 200x1703 | mipmap yoqildi (NoMipmaps -> FromTextureGroup); 2 ning darajasiga cho'zildi (mip va oqim uchun) |
| MT_PM_V66_Spiraea_japonica_01_Petiole_01_normal | Normal | 200x1703 | mipmap yoqildi (NoMipmaps -> FromTextureGroup); 2 ning darajasiga cho'zildi (mip va oqim uchun) |
| MT_PM_V66_Spiraea_japonica_01_Petiole_01_glossiness | Glossiness | 200x1703 | mipmap yoqildi (NoMipmaps -> FromTextureGroup); 2 ning darajasiga cho'zildi (mip va oqim uchun) |
| MT_PM_V66_Spiraea_japonica_01_Flower_01_opacity | Opacity | 4096x4096 | mipmap yoqildi (NoMipmaps -> FromTextureGroup); never_stream o'chirildi (oqimda yuklanadi); alpha coverage 0,3333 (uzoqda barg yo'qolmasin); maks. o'lcham 2048 |
| MT_PM_V66_Spiraea_japonica_01_Stamen_01_albedo | BaseColor | 200x1262 | mipmap yoqildi (NoMipmaps -> FromTextureGroup); 2 ning darajasiga cho'zildi (mip va oqim uchun) |
| MT_PM_V66_Spiraea_japonica_01_Stamen_01_normal | Normal | 200x1262 | mipmap yoqildi (NoMipmaps -> FromTextureGroup); 2 ning darajasiga cho'zildi (mip va oqim uchun) |
| MT_PM_V66_Spiraea_japonica_01_Stamen_01_glossiness | Glossiness | 200x1262 | mipmap yoqildi (NoMipmaps -> FromTextureGroup); 2 ning darajasiga cho'zildi (mip va oqim uchun) |
| awafaw31swda1 | Diffuse, Roughness | 2000x2000 | mipmap yoqildi (NoMipmaps -> FromTextureGroup); never_stream o'chirildi (oqimda yuklanadi); 2 ning darajasiga cho'zildi (mip va oqim uchun) |
| awafaw31swda2 | Normal | 2000x2000 | mipmap yoqildi (NoMipmaps -> FromTextureGroup); never_stream o'chirildi (oqimda yuklanadi); 2 ning darajasiga cho'zildi (mip va oqim uchun) |
| Lavandula_Pedunculata_Atlantica_Stoechas_Subpedunculata_Leaf_Opacity | Opacity | 4096x4096 | mipmap yoqildi (NoMipmaps -> FromTextureGroup); never_stream o'chirildi (oqimda yuklanadi); alpha coverage 0,3333 (uzoqda barg yo'qolmasin); maks. o'lcham 2048 |
| Lavandula_Pedunculata_Atlantica_Stoechas_Subpedunculata_Flower_Opacity | Opacity | 4096x4096 | mipmap yoqildi (NoMipmaps -> FromTextureGroup); never_stream o'chirildi (oqimda yuklanadi); alpha coverage 0,3333 (uzoqda barg yo'qolmasin); maks. o'lcham 2048 |
| edawwdaw31 | Diffuse, Roughness | 2000x2000 | mipmap yoqildi (NoMipmaps -> FromTextureGroup); never_stream o'chirildi (oqimda yuklanadi); 2 ning darajasiga cho'zildi (mip va oqim uchun) |
| edawwdaw33 | Normal | 2000x2000 | mipmap yoqildi (NoMipmaps -> FromTextureGroup); never_stream o'chirildi (oqimda yuklanadi); 2 ning darajasiga cho'zildi (mip va oqim uchun) |
| edawwdaw32 | Opacity | 2000x2000 | mipmap yoqildi (NoMipmaps -> FromTextureGroup); never_stream o'chirildi (oqimda yuklanadi); 2 ning darajasiga cho'zildi (mip va oqim uchun); alpha coverage 0,3333 (uzoqda barg yo'qolmasin) |
| awdfaw31wadaw2 | Diffuse | 2000x2000 | mipmap yoqildi (NoMipmaps -> FromTextureGroup); never_stream o'chirildi (oqimda yuklanadi); 2 ning darajasiga cho'zildi (mip va oqim uchun) |
| awdfaw31wadaw3 | Normal, Roughness | 2000x2000 | mipmap yoqildi (NoMipmaps -> FromTextureGroup); never_stream o'chirildi (oqimda yuklanadi); 2 ning darajasiga cho'zildi (mip va oqim uchun) |
| awdfaw31wadaw1 | Opacity | 2000x2000 | mipmap yoqildi (NoMipmaps -> FromTextureGroup); never_stream o'chirildi (oqimda yuklanadi); 2 ning darajasiga cho'zildi (mip va oqim uchun); alpha coverage 0,3333 (uzoqda barg yo'qolmasin) |
| Ash_p1 | Diffuse, Roughness, Subsurface | 667x1000 | mipmap yoqildi (NoMipmaps -> FromTextureGroup); siqish EditorIcon -> Default; never_stream o'chirildi (oqimda yuklanadi); 2 ning darajasiga cho'zildi (mip va oqim uchun) |
| Ash_pop | Mask | 667x1000 | mipmap yoqildi (NoMipmaps -> FromTextureGroup); siqish EditorIcon -> Default; never_stream o'chirildi (oqimda yuklanadi); 2 ning darajasiga cho'zildi (mip va oqim uchun); alpha coverage 0,3333 (uzoqda barg yo'qolmasin) |
| Physocarpus_leaf_05_diff | Diffuse, Normal, Subsurface | 600x720 | mipmap yoqildi (NoMipmaps -> FromTextureGroup); never_stream o'chirildi (oqimda yuklanadi); 2 ning darajasiga cho'zildi (mip va oqim uchun) |
| Physocarpus_leaf_01_opac | Mask | 600x720 | mipmap yoqildi (NoMipmaps -> FromTextureGroup); never_stream o'chirildi (oqimda yuklanadi); 2 ning darajasiga cho'zildi (mip va oqim uchun); alpha coverage 0,3333 (uzoqda barg yo'qolmasin) |
| Leaf | BaseColor | 164x512 | mipmap yoqildi (NoMipmaps -> FromTextureGroup); 2 ning darajasiga cho'zildi (mip va oqim uchun) |
| 01_Leaf_Normal | Normal | 164x512 | mipmap yoqildi (NoMipmaps -> FromTextureGroup); 2 ning darajasiga cho'zildi (mip va oqim uchun) |
| 01_Leaf_Opacity | Opacity | 164x512 | mipmap yoqildi (NoMipmaps -> FromTextureGroup); never_stream o'chirildi (oqimda yuklanadi); 2 ning darajasiga cho'zildi (mip va oqim uchun); alpha coverage 0,3333 (uzoqda barg yo'qolmasin) |
| Material_3_Opacity | Opacity | 512x512 | mipmap yoqildi (NoMipmaps -> FromTextureGroup); never_stream o'chirildi (oqimda yuklanadi); alpha coverage 0,3333 (uzoqda barg yo'qolmasin) |
| awdawdawtue1 | Diffuse, Roughness | 2000x2000 | mipmap yoqildi (NoMipmaps -> FromTextureGroup); never_stream o'chirildi (oqimda yuklanadi); 2 ning darajasiga cho'zildi (mip va oqim uchun) |
| awdawdawtue3 | Normal | 2000x2000 | mipmap yoqildi (NoMipmaps -> FromTextureGroup); never_stream o'chirildi (oqimda yuklanadi); 2 ning darajasiga cho'zildi (mip va oqim uchun) |
| awdawdawtue2 | Opacity | 2000x2000 | mipmap yoqildi (NoMipmaps -> FromTextureGroup); never_stream o'chirildi (oqimda yuklanadi); 2 ning darajasiga cho'zildi (mip va oqim uchun); alpha coverage 0,3333 (uzoqda barg yo'qolmasin) |
| aweawdasaw1 | Diffuse | 2000x2000 | mipmap yoqildi (NoMipmaps -> FromTextureGroup); never_stream o'chirildi (oqimda yuklanadi); 2 ning darajasiga cho'zildi (mip va oqim uchun) |
| aweawdasaw2 | Normal, Roughness | 2000x2000 | mipmap yoqildi (NoMipmaps -> FromTextureGroup); never_stream o'chirildi (oqimda yuklanadi); 2 ning darajasiga cho'zildi (mip va oqim uchun) |
| FicusBenjamina_leaf_01_diffuse_Copy | BaseColor | 762x1522 | mipmap yoqildi (NoMipmaps -> FromTextureGroup); 2 ning darajasiga cho'zildi (mip va oqim uchun) |
| FicusBenjamina_leaf_01_diffuse_Normal | Normal | 800x1510 | mipmap yoqildi (NoMipmaps -> FromTextureGroup); 2 ning darajasiga cho'zildi (mip va oqim uchun) |
| FicusBenjamina_leaf_01_diffuse_Copy_Opacity | Opacity | 800x1510 | mipmap yoqildi (NoMipmaps -> FromTextureGroup); never_stream o'chirildi (oqimda yuklanadi); 2 ning darajasiga cho'zildi (mip va oqim uchun); alpha coverage 0,3333 (uzoqda barg yo'qolmasin) |
| FicusBenjamina_leaf_01_diffuse_Copy_Copy | BaseColor | 600x1249 | mipmap yoqildi (NoMipmaps -> FromTextureGroup); 2 ning darajasiga cho'zildi (mip va oqim uchun) |
| FicusBenjamina_leaf_01_diffuse_Copy_Copy_Opacity | Opacity | 800x1510 | mipmap yoqildi (NoMipmaps -> FromTextureGroup); never_stream o'chirildi (oqimda yuklanadi); 2 ning darajasiga cho'zildi (mip va oqim uchun); alpha coverage 0,3333 (uzoqda barg yo'qolmasin) |
| FicusBenjamina_leaf_01_diffuse | BaseColor | 800x1510 | mipmap yoqildi (NoMipmaps -> FromTextureGroup); 2 ning darajasiga cho'zildi (mip va oqim uchun) |
| FicusBenjamina_leaf_01_diffuse_Opacity | Opacity | 800x1510 | mipmap yoqildi (NoMipmaps -> FromTextureGroup); never_stream o'chirildi (oqimda yuklanadi); 2 ning darajasiga cho'zildi (mip va oqim uchun); alpha coverage 0,3333 (uzoqda barg yo'qolmasin) |
