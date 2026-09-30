# Sinov usuli va xulosalar (Zaliniy, 2026-09-29/30)

## Tasdiqlangan sinov usuli

1. **Bitta o'zgarish — bitta sinov.** Har bir qiymat o'zgargach editor to'liq tinchlanguncha kutiladi:
   oddiy sozlamalarda kamida 45 s, Nanite puli / Lumen / HWRT sinovlarida 75–150 s, **va** kadr vaqti barqaror
   bo'lguncha (oxirgi 3 s o'rtachasi oldingi 3 s dan 15 % ichida). Buni `ue/shots_lib.py settle` qiladi:
   ```python
   runpy.run_path(r'<repo>/ue/09_shots.py', init_globals={'ARGS': {'action': 'settle',
       'steps': [['ST_a', {'r.Nanite.Streaming.QualityScale.MinQuality': 0.3}],
                 ['ST_b', {'r.Nanite.Streaming.QualityScale.MinQuality': 1.0}]],
       'min_wait': 75, 'max_wait': 200}}, run_name='__main__')
   ```
   Mijoz shikoyati: agent qiymatni o'zgartirib darhol rasm olgani uchun natijalar noto'g'ri chiqqan.
2. **Qat'iy kadrlar to'plami** (`ue/09_shots.py` `set`): 2 ta 90 m qiya aerial (zich hovlilar), 4 ta 1,65 m
   odam bo'yi, oxirida CineCameraActor orqali bosh kadr. Namuna: `data/examples/shotset.zaliniy.json`.
   Yuqoridan: `top` (150 / 400 / 800 m + CINE).
3. **Qoida: o'zgarish faqat hamma kadrda yaxshilansa qoladi** (biri yaxshilanib, boshqasi buzilsa — rad).
   Solishtirish: `offline/tools/compare_sets.py A_ B_` (yonma-yon panel + yorug'lik p5/p50/p95, soya rangi),
   `imgaudit.py` (referens va render raqamlari), `compare_panel.py` (dE2000 hududlar bo'yicha),
   `treecmp.py` (toja rang polosalari referensga nisbatan).
4. **Turlar bo'yicha tekshiruv:** `ue/lookdev/lineup.py` — har bir daraxt turi suv tekisligida alohida, bir xil
   yorug'likda (TS_ kadrlar) + barcha material parametrlarining dampi (`lineup_mats.json`). Material o'zgarishi
   avval shu qatorda, keyin sahnada tekshiriladi. Sinovdan keyin `remove` (levelga saqlab qo'ymang).
5. Rasmni har doim **ko'z bilan** ham ko'ring (Read tool); raqamlar yordamchi. Mijoz: "bular vizualni ko'rib
   tuzatiladigan narsalar, raqam bilan taxmin qilinmaydi".
6. Diagnostika (stat, Nanite/Lumen vizualizatsiya) kadr olishdan oldin o'chiq bo'lsin.

## Xulosalar

### Uzoqdagi daraxtlar soddalashib ketishi
* **Asosiy sabab — Nanite oqim puli.** 1024 MB pul daraxtlar uchun kichik (DARAXT Nanite ma'lumoti ~4,5 GB,
  10 M uchburchakli meshlar bor). Pul 85 % dan oshsa, dvigatel sifat koeffitsientini har kadrda 0,97 ga
  ko'paytirib 0,3 gacha tushiradi — **logga hech narsa yozmaydi**, faqat `stat NaniteStreaming` da ko'rinadi.
  Shuning uchun daraxtlar avval yaxshi ko'rinib, bir necha soniyadan keyin soddalashardi.
* **Yechim:** `r.Nanite.Streaming.StreamingPoolSize=1536` + `r.Nanite.Streaming.QualityScale.MinQuality=1.0`.
  150 va 300 s ushlab turilgan kadrlarda sifat tushmadi; FPS 65–73, VRAM 21,7 / 24 GB.
  8 GB kartada pul 1536 tor bo'lishi mumkin. **2048 qo'ymang — assert** (pul maksimal GPU ajratmasidan kichik bo'lishi shart).
* `r.Nanite.ViewMeshLODBias.Offset -1`: 74 → 70 FPS, tojalar biroz detalliroq, lekin farq juda kichik;
  saqlanmadi. `-2` ham sinaldi. Qolgan soddalashuv — mesh tuzilishida: barglar alohida kartochkalar,
  Nanite uzoqda ularning bir qismini olib tashlab qolganini kattalashtiradi (Preserve Area), niqobni hisobga olmaydi.
  Og'irroq yechimlar (qaror kutilmoqda): eng ko'p ekilgan 3–5 turni Nanite qayta qurish (Preserve Area o'chiq /
  Keep Triangle %), opaque bargli 4 ta Corona_Proxy daraxti uchun Nanite Voxel, 8 UV kanalli meshlarni tozalash.
  Batafsil: `docs/research/distant_trees_analysis.md`.
* Barg teksturalarida mipmap yo'qligi (103 ta) uzoqda uchqun va teshik berardi — `fix_textures.py`.
* `r.ScreenPercentage` 75 → 100: mayda barglar to'liq o'lchamda chiziladi.

### Yorug'lik, soya, rang
* **HWRT Lumen** (`r.RayTracing.Enable 1`, `r.Lumen.HardwareRayTracing 1`) daraxt tagida tabiiy okklyuziya beradi,
  path tracingga eng yaqin. Lekin **Lumen yig'ilishi davomida tojalar sekin qorayib boradi** — natijani faqat
  tinchlangandan keyin baholang. Faqat 12 GB+ VRAM; 8 GB kartalarda ini da o'chiq, profil orqali yoqiladi.
* `FoliageOcclusionStrength` 1,0 / 0,7 / 0,4 va HWRT 0 bilan solishtirildi (FO_ kadrlar); 1,0 qoldi.
* Soyalarning qop-qoraligi CineCameraActor ning o'z PP qiymatlaridan edi (ekspozitsiya 1,75, soya kontrasti 0,9,
  skylight leaking 0,03). Kamera bazaviy holatga qaytarildi; umumiy PPV: local exposure shadow 0,6, leaking 0,1.
* Ekspozitsiya: mijoz "exposure compensation 10–10,5" degan (qo'lda rejim), sahna juda yorqin bo'lib ketdi;
  UDS ekspozitsiyasi o'chirilib, PPV da qo'lda bias 3,4 → 3,1 → 1,8 → 1,95 → **2,1** ga kelindi.
* Aerial perspective 0,3 → 0: uzoq plan sovuq-ko'k tuman bo'lib qolardi; tuman iliq rangga (1; 0,88; 0,68),
  zichlik 0,0015. Natija (TOPU_02): kontrast 19 → 24, soyadagi ko'klik B/G 1,11 → 1,03. Referensgacha hali farq bor
  (kontrast 54, soya B/G 0,62) — asosan uzoqdagi yassi daraxtlar va sovuq palitradan.
* Oldingi agentning material o'zgarishlari (kuchli sariq SSS) soya tomonini yondirgan edi — `.bak_20260929` dan
  tiklandi, keyin `materials_final.json` dagi o'zgarishlar kiritildi.

### Ekish
* v5 dagi "ochiq maysa xonasi" mantiqi juda ko'p bo'sh joy qoldirdi → v6 da qoplash maqsadi 66 % (parklarda 55 %)
  va bo'sh joylarni tuzatish sikli. v6 tekshiruvi: 24 416 o'simlik, masofa buzilishlari 0; qolgan 30 m² dan katta
  bo'sh joylar — bino maskasidagi "podium" (yer z yo'q) va parkdagi ataylab qoldirilgan ochiq maydonlar
  (bitta hal qilinmagan: FOL_33, 32 m²).
* Bitta turdagi quti-sharcha (boxwood) butalar xunuk ko'rindi → 10 ta buta kombinatsiyasi (2–4 tur, 3 qatlam).
* Uzun tasmalar ba'zi joyda ekilmay qolgan (fragment roll-back xatosi) → v6 da roll-back yo'q, qator
  bo'shliqlari ±1,5 m siljitish yoki kichikroq sinf bilan to'ldiriladi.

### Editor bilan ishlash
* `builtins` da aktor havolasi bilan `load_level` → "Old World not cleaned up" crash.
* DARAXT meshlarini ommaviy yuklash → xotira tugab crash.
* `add_instances` doim PersistentLevel ga yozadi → har bir FOL levelni alohida ochib ekish.
* Skrinshot navbatlari tick orqali; Python chaqiruvi davomida editor chizmaydi.
