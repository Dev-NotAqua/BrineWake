# 06 — Milestones (Unreal) + Risks

M0 Folders, style guide, UI kit, 1 prop, audio buses, VFX manager.
Done: painted barrel matches guide in-engine.
M1 Ocean + grey sloop buoyancy + deck walk (2 clients, storm, no jitter,
`p.netshowcorrections` clean).
M2 Sloop art + sailing + ship SFX/VFX. Done: sail A→B as client.
M3 Rig + generator + creation screen + locomotion + camera.
M4 HUD, wheels, prompts, pause, settings, core tools (PC+pad+touch).
M5 Cannons, holes, flood, repair, sink. Done: fight ends in sinking, replicated.
M6 Gullrest + shops/chests/item DB/save. Done: buy hat, rejoin, kept.
M7 2 islands + treasure + map table + sell + Log v1. Done: 20-min loop solo.
M8 Melee/guns/skeletons/death/bounty. Done: clear captain.
M9 Front-end + sessions + chat/voice. Done: 3 crews on 1 server.
M10 Weather/day-night/shanties/polish. Done: night storm crossing.
M11 Trade/fish/banners/commendations/tutorial + islands. Done: First Tide unaided.
M12 Mobile perf (later), analytics, playtest. Slice = M0-M7.

## Risks
- Moving deck + replication jitter: test M1, fallback attach+predict.
- Custom modular rig scaling: prove M3 before clothing sets.
- Ship replication bandwidth: server-auth forces, minimal RPCs.
- Scope: keep to slice. Multiplayer co-op from start = 10x; lock 1 ship/4 players to M7.
