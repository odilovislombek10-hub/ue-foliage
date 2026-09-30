# CLAUDE.md — ue-foliage operating instructions

You plant trees and shrubs into an Unreal Engine 5.8 project exactly the way it was done on the Zaliniy project,
using the shared tree library `/Game/SHABLON/MODEL/DARAXT` (identical on every PC of this user).
Talk to the user in **Uzbek (Latin)**. The user is an ArchViz professional and judges by eye: show screenshots,
do not argue with numbers.

## Before anything
1. Read `README.md` (pipeline, rules, safety) and `docs/research/client_rules_v6.md`.
2. Ask the user for: project root, persistent level to plant in, where the FOL_ sublevels should go, whether a
   PDF master plan with lots exists (which page/area), which lots/blocks are the current stage. Never guess the stage.
3. `config.example.json` -> `config.json`, fill in paths; install `pylib` (README "O'rnatish").
4. Check the editor is open and the MCP listener answers (`mcp__unreal__run_python` with `result='ping'`).
   If the editor is closed, start it with the project and wait until port 20251 answers.

## Run the pipeline (see the table in README)
Editor steps: `runpy.run_path(r'<repo>/ue/<script>.py', init_globals={'ARGS': {...}}, run_name='__main__').get('RESULT')`.
Offline steps: `"<UE>/Engine/Binaries/ThirdParty/Python3/Win64/python.exe" offline/<script>.py`.
Order: ue/01 -> ue/02 (repeat until done) -> check env_mats.json / extend material_classes -> offline/02_zones ->
[offline/03_plan_register] -> offline/04_lots propose -> **agree lots.json with the user** -> 04_lots apply ->
05_beds -> 06_engine -> 07_verify -> 08_preview -> ue/06 FTs -> ue/07 sublevels -> ue/08 plant (repeat) ->
09_camplan -> ue/09_shots lots.

## Verify every step visually
* Open (Read tool) every PNG a step writes: size_full.png, lots_proposed.png, lots_final.png, engine/preview/*.png,
  and the in-editor screenshots in `<Project>/Saved/Screenshots/WindowsEditor/`.
* After planting, shoot every lot (`ue/09_shots.py` action `lots`) and look for: empty lawn, one model repeated in a
  row, lone shrub balls, trees on paths/roads/roofs, trees floating or buried, bare playground edges.
* Screenshots are tick-driven: after starting a queue, wait (poll `action: status`) - never shoot right after moving
  the camera; never shoot while shaders compile. After any setting change use `settle` (>= 45-75 s + stable fps).
* A change is kept only if every shot of the fixed set improves (compare with `offline/tools/compare_sets.py`).

## Hard rules
* Keep the algorithms (engine, species library, client rules). Change parameters only after the user asks.
* Never `add_instances` into the persistent level; plant each FOL_ level opened as its own map (ue/08 does it).
* Never hold UObjects in `builtins` across `load_level`; never delete foreign `builtins` entries (MCP state);
  check the editor world is not None; never bulk-load DARAXT meshes (OOM crash).
* Back up every file before editing (`.bak_YYYYMMDD`, scripts do it); `Config/*.ini` only with the editor closed.
* Shared-library edits (FoliageTypes, `ue/lookdev/apply_materials.py`, `fix_textures.py`) affect every project on
  the PC: tell the user before running them; they are idempotent (skip what is already at target).
* No lawn/grass/flower models; trees and shrubs only. No renders / Movie Render Queue: the product is a packaged
  real-time build.
* Do not do work the user did not ask for. Report briefly in Uzbek what was done and show the images.

## Look-dev (only when asked)
`docs/LOOKDEV_QOLLANMA.md`: materials, textures, lighting/PPV, ini, test method; findings in `docs/TESTLAR_VA_XULOSALAR.md`.
