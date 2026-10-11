# 02 — Outposts, factions and the Blender asset library

Sea of Thieves is the art benchmark only. Names, factions and activities below are Brinewake's own.
Status: proposal written 2026-10-11, to be confirmed by the owner before systems are built.

## Factions (one building each at every outpost)

| Faction | Place | Asset | What they pay for | Twist |
|---|---|---|---|---|
| Deepfinders | canvas salvage tent on the beach | `SM_BW_SalvageTent` | wreck salvage | you dive for it: breath, depth and currents matter, no digging for chests |
| Saltmarket Guild | awning stall on the pier | `SM_BW_MarketStall` | cargo runs | goods spoil or soak; price drops with every wave over the deck |
| Lantern Wardens | leaning watch hut on a tall deck | `SM_BW_WardenHut` | putting out "drowned lights" | night and storm jobs; the storm cell is the dungeon |
| Keelwrights | open yard on stilts | `SM_BW_Keelwright` | hull work | repairs and hull upgrades need timber you bring in |
| (neutral) | alehouse | `SM_BW_Alehouse` | crew up, rumours | rumours point at live events on the map |
| (neutral) | lookout | `SM_BW_Tower` | spot sails and weather | |

Outpost name for the first island: **Gullrest**.

## Ships
Sloop (1 to 2) and brigantine (2 to 3) first. Menu wording stays plain: "Crew", "Charts", "Voyage", "Ledger".

## Blender asset library (build order)
Everything is modelled by `Tools\mcp\bw_kit.py` / `bw_outpost.py`, exported as FBX, imported, then placed as instances.

1. Rock kit: `SM_BW_Slab_01..12` (worn slabs: tall, squat, wedge, plate, pillar, split), `SM_BW_Boulder_A/B`.
2. Outpost: the six buildings above, `SM_BW_Dock` (straight), dock corner, dock end, mooring post, ladder.
3. Dressing: palms A/B/C, bush, fern, barrel, crate, lantern post, banner pole, bench, rowboat, net rack, anchor.
4. Ships: sloop hull, brigantine hull, mast, sail, wheel, cannon, capstan.
5. Characters: pirate body, six outfits, swim / row / haul animations (needs a rig; not started).
6. Island parts: terrain per island, grass and vine detail, waterfall ribbons.

Done so far: 1 (first ten slabs), 2 (buildings and straight dock), part of 3, part of 6.
