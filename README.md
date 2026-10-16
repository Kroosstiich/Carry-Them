# Carry Them

A Skyrim Special Edition mod: the player carries an NPC on their back. The reverse of
[Carry Me](https://www.nexusmods.com/skyrimspecialedition/mods/194011), where NPCs carry the player.

Download: [Carry Them on Nexus Mods](https://www.nexusmods.com/skyrimspecialedition/mods/195568).
This repository holds the source.

## Requirements (in game)

- SKSE64 and [Address Library for SKSE Plugins](https://www.nexusmods.com/skyrimspecialedition/mods/32444)
- [Piggyback](https://www.nexusmods.com/skyrimspecialedition/mods/186556) 1.2.2 or later
- [Offset Movement Animation](https://www.nexusmods.com/skyrimspecialedition/mods/110408), then a Pandora or Nemesis run
- [Open Animation Replacer](https://www.nexusmods.com/skyrimspecialedition/mods/92109)
- Optional: SkyUI and MCM Helper, for the settings menu

## How it works

- `Scripts/Source/CT_Control.psc`: all the logic. The power walks the target up behind the player
  with `Piggyback.ApproachAndAttach`, then holds it on the back (restrained, pose markers, no head
  tracking, no host collision). Jump sets it down.
- The poses are swapped in by Open Animation Replacer
  (`Data/meshes/actors/character/animations/OpenAnimationReplacer/CarryThem`): the rider plays one
  still pose under all its movement animations, the player plays a carrying pose layered by Offset
  Movement Animation.
- `CarryThem.esp` is not edited by hand: `tools/build_plugin.py` generates it from scratch.
- `Data/MCM/Config/CarryThem/config.json`: the optional MCM (MCM Helper). Its sliders write the
  `CT_OffsetX/Y/Z` and `CT_Rotation` globals, which can also be set from the console.

## Building

Windows, PowerShell 5.1, Python 3.12 and the Creation Kit's Papyrus compiler. Create
`local.paths.ps1` next to `build.ps1` (it is not tracked) with `SKYRIM_PATH`, `MO2_MODS_PATH`,
`PIGGYBACK_SOURCE` (Piggyback's `Scripts/Source`) and `MCM_SOURCE` (MCM Helper and SkyUI sources).

```powershell
.\build.ps1                     # compile the scripts, generate Data\CarryThem.esp
.\build.ps1 -Package 1.0.0      # also write release\CarryThem-1.0.0.zip
```

## License and permissions

The code (Papyrus scripts, plugin generator, build scripts, configuration files) is licensed under
**GPL-3.0-or-later**: see [LICENSE](LICENSE) and [COPYING.txt](COPYING.txt).

**The animations are not.** The `*.hkx` files under `Data/meshes` come from Carry Me and remain
Fflower's work, reused under Carry Me's permissions (see Credits below).

## Credits

- **Fflower**, author of [Carry Me](https://www.nexusmods.com/skyrimspecialedition/mods/194011):
  all the animations in `Data/meshes` come from Carry Me and belong to Fflower. Their reuse follows
  Carry Me's permissions: no Donation Points, no paid mods, no conversion to other games.
- Kroosstii: concept, direction, in-game testing, and the Piggyback framework.
- AI assistance: written with the help of Claude (Anthropic), which wrote the scripts and the plugin
  generator to my specifications and helped debug them.
- Ersh (Open Animation Replacer), Exit-9B (MCM Helper), the SkyUI team, the author of Offset
  Movement Animation, RSE - Shoulder Or Saddle (how to keep a passenger still), the SKSE team,
  meh321 (Address Library), Bethesda Game Studios.
