How to put this into Overleaf (project 6abd1570a170b73d0ef1e16a)

I cannot push directly to your Overleaf link (it needs your login, no API access).
Do this (30 seconds):

Option A — single file (recommended):
1. Open https://www.overleaf.com/project/6abd1570a170b73d0ef1e16a
2. If there is an existing main.tex, replace its contents.
   Otherwise: New File -> main.tex
3. Open this local file in Notepad:
   Documents\Unreal Projects\Brinewake2\Docs\Overleaf\main.tex
4. Copy ALL, paste into Overleaf's main.tex, press Recompile.
5. No other files or packages needed (article + amsmath + booktabs + hyperref + listings only).

Option B — upload:
1. In Overleaf: Menu -> Upload -> select main.tex from the Overleaf folder.
2. Recompile.

What was verified on your machine (2026-10-11):
- UE 5.8.3 (changelist 58210709) at C:\Program Files\Epic Games\UE_5.8
- Brinewake2.uproject (FileVersion 3, plugins: StateTree, GameplayStateTree, ModelContextProtocol, AllToolsets)
- 3 maps: Lvl_FirstPerson, Lvl_Horror, Lvl_Shooter
- Physics numbers in the doc are from your actual .cpp/.h + DefaultEngine.ini,
  not invented (capsule 34x96, air control 0.5, braking 1500, bullet 3000 cm/s,
  damage 25, force 100, blast 500 cm, horror 250/600/150 cm/s, NPC 100 HP).

Live-editor MCP check failed (connection reset = editor not running).
To enable live queries later: open Brinewake2 in UE 5.8, run
ModelContextProtocol.StartServer in the console, then retry.
