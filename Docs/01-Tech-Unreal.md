# 01 — Tech (Unreal 5.8)

Base: C++ First Person (user created) — keep, add Third Person mesh visible in
first person (real body visible). EnhancedInput from day one.

## Plugins to enable
ModelContextProtocol, AllToolsets, Water, Buoyancy, CommonUI, EnhancedInput,
GameplayTags, EOS / OnlineSubsystemEOS.

## Server modules (C++ UGameInstanceSubsystem + GameState)
Ship, Wave (shared Gerstner params, server time), Crew/Session, Voyage,
Loot, Combat, Shop/DataAssets, Save.

## Client controllers (PlayerController + Components)
Ocean, Camera, Input, UI, Audio, VFX.

## Ocean / Ship
- Water plugin ocean, custom Gerstner material params replicated from server.
- Ship: single server-auth replicated Pawn, Chaos physics + Buoyancy sample
  points on hull. Client predicts, `p.netshowcorrections 1` must stay clean.
- Deck walking: attach characters to ship, test 2 clients in storm, no jitter.

## Item DB / Save / Strings
- Item DB: DataAssets drive shops, chests, Pirate Log.
- Save: local profile + EOS, cosmetics/gold/rep/counters/stats/settings/flags,
  session-locked. No pay-to-win.
- Strings: StringTable for localisation.

## Perf target
60fps mid PC first (Scalability tiers for Niagara/audio). Phones later.
World Partition + HLOD + ISM for islands/outpost. No Tick-heavy loops.
