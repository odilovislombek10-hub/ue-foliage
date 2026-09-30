# DT2: why far trees look simplified (static analysis, 2026-09-30)

Client question: "Far trees look heavily simplified. Is it the mesh, the ini, or the render settings?"
Method: I read config files, logs, SP dumps, .uasset name tables and UE 5.8 source. I did not use the editor or MCP.

## Short answer
The main cause is the **mesh plus how Nanite works**: all trees are Nanite with 1 LOD, and their leaves are disjoint masked cards simplified with Preserve Area. The **ini/scalability is not the cause**: everything is at Epic, and none of the foliage/LOD cvars affect Nanite. Two things make it worse: (a) the leaf textures have no mipmaps, and (b) the Nanite streaming pool may be lowering quality automatically. (b) cannot be proven statically and needs one runtime check.

## 1. Config: effective values (editor session log 2026-09-29 20:53, all sg = 3 / Epic)
| cvar | value | where set | affects Nanite trees? |
|---|---|---|---|
| sg.* (all groups) | 3 (Epic) | engine default; no [ScalabilityGroups] in Saved/Config/WindowsEditor/GameUserSettings.ini | - |
| r.ViewDistanceScale | 1.0 | BaseScalability [ViewDistanceQuality@3] | only cull distances. FT CullDistance = (0,0), no per-component overrides in FOL_*.umap, so no effect |
| foliage.DensityScale / grass.DensityScale | 1.0 / 1.0 | [FoliageQuality@3] | no (FTs don't use density scaling) |
| foliage.LODDistanceScale | not set (commented out in BaseScalability), default 1 | - | no, Nanite ignores LOD screen sizes |
| r.StaticMeshLODDistanceScale, r.SkeletalMeshLODBias | default / 0 | - | no (1-LOD Nanite meshes) |
| r.Nanite.MaxPixelsPerEdge | 1 (engine default, NaniteCullRaster.cpp:134) | not set; confirmed in log 07:36 | **yes, this sets the LOD target** |
| r.Nanite.ViewMeshLODBias.Offset / .Min | 0 / -2 (DeferredShadingRenderer.cpp:387-392) | default | yes. With TSR the LOD scales by upscale factor; neutral at 100% |
| r.Nanite.Streaming.StreamingPoolSize | 1024 (engine default 512) | DefaultEngine.ini [SystemSettings] | **yes, see candidate 2** |
| r.Nanite.Streaming.QualityScale.Min/MaxPoolPercentage, MinQuality | 70 / 85 / 0.3 | engine default | **yes, see candidate 2** |
| r.Nanite.Foliage / r.Nanite.AllowVoxels | 0 / 0 (ReadOnly) | default | Voxelize is not available |
| r.Shadow.NaniteLODBias | 1 (default, ShadowSceneRenderer.cpp:49) | default | shadow geometry is one step coarser (minor) |
| r.ScreenPercentage | 100 | DefaultEngine [SystemSettings] (was 75 until today) | shading resolution of sub-pixel leaves |
| r.Streaming.PoolSize / MipBias | 2500 / 0 | DefaultScalability [TextureQuality@3] | OK |
| r.RayTracing.Enable | 0 (EnableOnDemand=1); r.RayTracing.Nanite.Mode=1 | DefaultEngine | fallback mesh not used for primary view |
| PerfIndexValues_ResolutionQuality | "50 71 75 75 100" | DefaultScalability | only applies if something calls `scalability N`/benchmark; the ini r.ScreenPercentage=100 (SystemSettingsIni priority) overrides it. Low risk |

Epic's BaseScalability.ini has no Nanite lines at any sg level. Nanite detail does **not** depend on scalability.

## 2. Log findings (Saved/Logs/ANIMA_Character.log + backups)
- No Nanite streaming warnings, no texture pool "over budget", no HLOD. Atrof_button.umap is not World Partition (no HLOD), and the FOL_* levels are ordinary streamed sublevels with no distance streaming volumes.
- Nanite pool quality scaling is **silent** (FQualityScalingManager, NaniteStreamingManager.cpp:478-509). It shows only in `stat NaniteStreaming` → "Quality Scale" / "Streaming Pool Percentage". So a clean log does not rule it out.
- Nanite builds in today's log run at about 26-46 bytes GPU per triangle (e.g. Pinus_Mugo 452k tris → 20.6 MB).
- One WPO warning: Crataegus_Prunifolia_min_02 (Nanite ISM with WPO, not supported in RT). Not related to simplification.

## 3. Mesh facts
- 91 DARAXT meshes (SP/tree_meta.json + .uasset name-table scan): all Nanite, ShapePreservation=PRESERVE_AREA, 1 LOD. `KeepPercentTriangles` and `TrimRelativeError` are **not serialized in any .uasset**, so they are at their defaults (1.0 / 0.0), which means no build-time trimming. FallbackTarget = RelativeError with FallbackRelativeError = 0.0 (full-detail fallback, 100%). The fallback is not used for the primary view with RT off, so it is irrelevant to the look (it only costs memory and disk).
- Leaves: about 75% of species are **masked cards** (M_Base_Leaf, M_Foliage_Masked, SpeedTree *_Leaf_Mat…). The 4 Corona_Proxy trees (the most instanced: MI_Plant_nn21/22, 6468 slots each) are opaque real leaf geometry.
- Heavy: Ash_tree_02 / N_Ash_tree_02 10.26 M tris (554 MB each on disk), Silver_Birch_02 5.0 M, Lagerstroemia 6.2 M. 24 meshes have **8 UV channels** (all stored in Nanite pages). DARAXT Nanite data ≈ 4.5 GB on disk.

## Ranked root-cause candidates

### 1. (Primary, certain) Nanite cluster-DAG simplification of disjoint leaf cards + Preserve Area. Source: mesh / Nanite design
Mechanism: Nanite's QEM edge-collapse simplifier (NaniteBuilder/Private/Cluster.cpp ~l.1030-1066) can only reduce an isolated leaf quad by collapsing it entirely. After each DAG level it calls `Simplifier.PreserveSurfaceArea()` (l.1065). This dilates the open boundary edges of the surviving cards so total area stays constant. At runtime Nanite picks the coarsest cluster whose error projects to < r.Nanite.MaxPixelsPerEdge (1 px). The error is purely geometric: alpha masks are not considered. The result is fewer leaves, each scaled up, with the same UVs. So distant crowns show big, clumpy, "low-poly" leaves and lose their fine silhouette. Epic's docs describe exactly this: "each disjoint part (a leaf…) has open edges… it eventually needs to start removing some of these disjoint elements completely… Preserve Area will redistribute that lost area… the effect is to scale each leaf up" (Working with Nanite-Enabled Content / Nanite docs). Epic also notes that card foliage with Nanite is not always a win, and 5.7+ introduced Nanite Foliage/voxels specifically because card aggregates break down at distance.
Fixes (cheapest first):
- a) `r.Nanite.ViewMeshLODBias.Offset -1` (runtime, main view only because TSR is on: LODScaleFactor = 2^1, clamped by Min -2). This gives an effective 0.5 px/edge for the main view but not for shadows. Cost: about 1.5-2x rasterized foliage triangles, estimated +0.5-2 ms GPU in wide aerials; more Nanite pages streamed (makes candidate 2 more likely). The alternative is `r.Nanite.MaxPixelsPerEdge 0.5` (already in Scripts/profile_lumen.py), which also refines VSM, so it costs more. Try it first in the console; if it helps, put it in DefaultEngine [SystemSettings].
- b) Opaque-geometry trees (Corona_Proxy071/072/22788/26394): `r.Nanite.AllowVoxels=1` (or the Nanite Foliage project setting) + Shape Preservation = Voxelize. Cost: editor restart, global shader recompile, Nanite rebuild of 4 meshes, repackage. Experimental. Do NOT use it on masked-card meshes: the voxelizer ignores opacity (see SP/agents/distant_trees.json).
- c) Masked-card hero species that are seen far away: replace or re-author them with denser, smaller real-geometry leaves (then 5.8 voxels work), or make them non-Nanite with authored LODs plus an impostor last LOD. Cost: high (content work).
- Do not raise MaxPixelsPerEdge above 1, and do not add a positive ViewMeshLODBias: both make this worse.

### 2. (Probable, must measure) Nanite streaming pool overcommit → automatic quality downscale. Source: ini
When pool use is > 85% for 2+ frames, the Nanite streamer multiplies a quality scale by 0.97 per frame, down to 0.3 (NaniteStreamingManager.cpp:106-130, 478-509). DeferredShadingRenderer.cpp:1654 divides the pixels-per-edge target by it, so at worst this is **3.3 px/edge**: exactly "far trees suddenly much coarser", and it is silent in the log. Distant trees also only get coarse pages when the pool is full. Evidence that the pool is tight: 1024 MB pool against ≈4.5 GB of tree Nanite data plus a dense city; 10 M-tri trees; 24 meshes carrying 8 UV sets; and the 2026-09-04 note in DefaultEngine.ini that distant leaves disappeared at 512 MB.
Test (1 minute, no restart): `stat NaniteStreaming` in the problem view. Look at Quality Scale < 1.0 or Pool Percentage > 85. Then compare with `r.Nanite.Streaming.QualityScale.MinQuality 1`.
Fixes: pool 1536 (the ini note says 2048 asserts: pool must be < max GPU allocation), which costs +512 MB VRAM. Strip unused UV channels on the 8-UV meshes (Ash_tree*, Silver_Birch*, N_* …) and rebuild Nanite; this shrinks page data and costs only rebuild time. Consider Trim Relative Error / Keep % Triangles on the 10 M / 5-6 M tri meshes, since detail that is never visible still costs pool.

### 3. (Certain, contributes to the "broken/simplified" read) Leaf textures without mipmaps. Source: textures
Of 177 textures used by foliage MIs, 100 are TMGS_NO_MIPMAPS (64% of slot-instance usage, 173k/269k; SP/agents/dt/mic_tex.json), and 53 are never_stream. Far crowns sample mip0, which gives salt-and-pepper aliasing, thinned alpha-test coverage and grey fringes. Together with candidate 1 this reads as crude, low-detail trees. Fix: MipGen FromTextureGroup, proper compression, `do_scale_mips_for_alpha_coverage=True` with threshold 0.3333 in the opacity channel, and stretch NPOT textures to power of two. Cost: texture rebuild only; net VRAM saving.

### 4. (Minor) r.Shadow.NaniteLODBias = 1 (default)
Shadow geometry is one LOD step coarser than the view, so distant canopy shadows are blobbier. Setting it to 0 costs VSM raster time (about +10-30% shadow depth cost on foliage). Low priority.

### 5. (Minor / already fixed) Screen percentage 75 → 100 (fixed today)
With TSR, Nanite geometry LOD is compensated through ViewMeshLODBias, but shading of sub-pixel leaves was coarser. Verify that the packaged kiosk does not call `scalability 3` / a settings BP. If it does, PerfIndexValues_ResolutionQuality[3] = 75, but the [SystemSettings] r.ScreenPercentage=100 still has priority.

### Not causes (ruled out)
foliage.LODDistanceScale, r.StaticMeshLODDistanceScale, r.ViewDistanceScale, foliage.DensityScale, FT cull distances (0), HLOD (none), fallback mesh (RT off; Nanite.Mode=1 anyway), KeepPercentTriangles/TrimRelativeError (defaults), and the texture streaming pool (2500 MB, no over-budget message).

## Recommended order
1. `stat NaniteStreaming` in the far view → decides whether candidate 2 is real (1 min).
2. Console `r.Nanite.ViewMeshLODBias.Offset -1` (and compare `r.Nanite.MaxPixelsPerEdge 0.5`); screenshot A/B, `stat gpu`.
3. Texture mips/alpha coverage (batches, back up .uasset files first).
4. Pool 1536 + strip extra UV channels if step 1 shows a Quality Scale < 1.
5. Voxelize the 4 Corona proxies (restart) only after 1-4.

Sources: Epic "Working with Nanite-Enabled Content" (https://dev.epicgames.com/documentation/unreal-engine/working-with-naniteenabled-content), "Nanite Virtualized Geometry" (https://dev.epicgames.com/documentation/en-us/unreal-engine/nanite-virtualized-geometry-in-unreal-engine), "Nanite Foliage" (https://dev.epicgames.com/documentation/en-us/unreal-engine/nanite-foliage), shinsoj "Notes on foliage in Unreal 5" (https://medium.com/@shinsoj/notes-on-foliage-in-unreal-5-3522b6eb159f). Engine: NaniteBuilder/Private/Cluster.cpp:1065, Engine/Private/Rendering/NaniteStreamingManager.cpp:57,106-130,478-509, Renderer/Private/DeferredShadingRenderer.cpp:381-392,1636-1654, Renderer/Private/Nanite/NaniteCullRaster.cpp:134, Shadows/ShadowSceneRenderer.cpp:49, Engine/Private/Scalability.cpp:532-551.
