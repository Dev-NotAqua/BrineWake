# 05 — Audio, VFX, Camera/Anim, Kits

## Audio (Audio Modulation buses: Music, Ambience, World, Ship, Weapons,
Foley, UI, Voice). 3-5 variants + pitch; pooled; low-pass underwater/below;
reverb caves/hold; distant booms delayed.
Ocean: lap, swell, storm, hull slap, wake, underwater. Ship: creak by roll,
sail flap/whump, ratchet, wheel creak+click, capstan, anchor chain+splash,
bell, lantern. Combat: load/boom/whistle/impact/leaks/flood/bail/sink.
Player/combat/loot/world/UI lists per v2 plan. Music: title, tavern loop,
sailing cues, voyage jingle, fort drums, storm drone, ghost theme. No combat
music, only hit sting. Shanties: 6-8 PD tunes, per-instrument stems, synced.

## VFX (Niagara, pooled, 3 tiers, chunky 2-3-tone puffs)
One manager `VFX.play(name,pos)`. Water: bow spray, wake, foam, splashes,
ripples, rain rings, rays, bubbles. Ship: flash+smoke+light, trail, splinters,
holes, leaks, hold water, billow, flag, anchor splash, sinking debris.
Combat/loot/weather/character/ambient/screen per v2 plan. No blood: slash arc,
hit star, bone burst + wisp.

## Camera/Anim
First-person default with body visible; third for emotes/sit/optional wheel.
Anims: locomotion, stations, tools, combat, 12 emotes, NPCs, skeletons, animals.

## Asset kits
A sloop · B items · C nature · D modular outpost · E shop dressing ·
F character parts · G sets (Sailor, Corsair, Tidewalker, Emberguard) ·
H NPCs · I loot · J enemies/creatures · K later ships/fort · L VFX/UI art.
