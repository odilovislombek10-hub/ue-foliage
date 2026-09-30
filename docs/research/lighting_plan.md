# Integrated lighting / visualization plan (packaged real-time ArchViz Explorer)

Sources: render_audit, scene_state, uds, ue_lighting_pp, ppv, grading, atmosphere, rt_pathtracing, performance, composition, camera, archviz_realism, decisions.md.
Target look: <referens papka>/825e3a246161a4adddf5940f05e2e91a.jpg — bright lively ~13:00, warm sun, open cool shadows, gentle haze, yellow-olive greens. Seen from above.

## Phase L1 — level actors (Atrof_button; backup Atrof_button.umap.bak_20260929_light exists)
Ultra_Dynamic_Sky (exposure owner = UDS, per ppv.md option A):
- Time of Day 1300; Animate Time of Day False (moving sun rebuilds VSM cache every frame).
- Randomize Cloud Formation on Run False (repeatable image). Cloud Speed 0.35 → 0.15.
- Sun Source Angle Scale 1.0 → 0.5 (source angle 1.2° → ~0.6°: crisper, still soft).
- Sun Light Color (1, 0.97, 0.92) — atmosphere already warms; do not overdo.
- Cloud Shadows Intensity When Sunny 0.7 → 0.45.
- Exposure Metering Mode → Manual; tune Exposure Bias Day by eye/HDR visualizer so sunlit white facade ≈ 235–245 sRGB, never clipped.
- Sun Yaw / Sun Pitch: keep 13:00 on the clock; choose Sun Yaw so the sun is 40–120° to the side of the main aerial camera (decisions.md). Sun Pitch 30 (path tilt) gives ~57° elevation at 13:00 — try 40–45 for longer shadows.
- Sun directional light Indirect Lighting Intensity 2.0 → 1.0 (if UDS overwrites it, use the UDS variable).
Ultra_Dynamic_Weather manual state: Cloud Coverage 3.8 → 1.5, Fog 1.0 → 0.3, Wind Intensity 2.0 → 1.0 (less WPO/VSM invalidation). Season 1 (summer) unchanged.
Contact shadows on sun: length 0.03 (cheap depth under shrubs/benches).

New unbound PostProcessVolume "PPV_Master_Runtime", priority 10, NO exposure overrides:
- White balance Temp 6700 (verify direction: higher = warmer), Tint -0.02.
- Global Saturation (1, 0.90 on G via grading) → start simple: Global Saturation Y 0.93, Contrast Y 0.95, Gain (1.02,1.00,0.97); Shadows Gain (0.97,0.99,1.04), Shadows Offset (0.004,0.005,0.008); Highlights Saturation 0.90.
- Tonemapper defaults (slope 0.88, toe 0.55, shoulder 0.26, white clip 0.04); Blue Correction 0.6; Expand Gamut 0.8.
- Local exposure: highlight contrast 0.8, shadow contrast 0.85.
- Bloom 0.3 (threshold -1); Lens flare 0; Vignette 0.15; Chromatic aberration 0; Film grain 0; Motion blur 0.2 (runtime) — no DOF.
- Lumen: default quality; Scene View Distance ~60000 cm for aerials if cost allows.

## Phase L2 — config (needs editor restart; after approval, backups first)
- r.Tonemapper.Sharpen 2 → 0.8.  r.Lumen.TraceMeshSDF → r.Lumen.TraceMeshSDFs (typo).
- r.ReflectionCaptureResolution 2048 → 512.  Remove dead cvars (r.LightPropagationVolume, r.SkinCache.SceneMemoryLimitInMB, duplicate ExtendDefaultLuminanceRange, r.MSAACount).
- GlobalDefaultGameMode duplicate: confirm which one is intended (CLAUDE.md says BP_Explorer_GameMode_LN).
- r.PathTracing False (no stills) — optional, smaller package.
- Tiering (rt_pathtracing.md / performance.md): High tier (RTX 3090): HW Lumen + VSM sun + RT local lights; Medium (4060 Ti/5060 Ti): SW Lumen + VSM. Implement ApplyRenderTier in Lanessa (C++ change, full build) — later phase.

## Phase L3 — foliage performance (after v6 planting)
FoliageTypes: WPO disable distance 3000–5000 cm, shadow cache invalidation Rigid, Affect Distance Field Lighting off on shrubs, cull distances; r.Shadow.Virtual.Cache.MaxMaterialPositionInvalidationRange 5000; r.OptimizedWPO 1.

## Phase L4 — hero cameras (camera.md shots A–E, CineCameraPerspectiveTools, 35 mm, vertical correction 0.4) + composition checklist (composition.md).
