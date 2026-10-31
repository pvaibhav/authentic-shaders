# Authentic LCD shaders

Shaders and bezels that draw the Game Boy, Game Boy Pocket, Game Boy Light, Game Boy Color and Game Boy Advance screens as their reflective LCDs looked in room light. They come from the Authentic screen of [slot](https://github.com/pvaibhav/slot).

| Game Boy (RG35XX SP) | Game Boy Color (RG35XX SP) | Game Boy Advance (640x480, rendered) |
|---|---|---|
| ![Game Boy](screenshots/gb-rgsp.png) | ![Game Boy Color](screenshots/gbc-rgsp.png) | ![Game Boy Advance](screenshots/gba-640x480.png) |

## Frontends

- [NextUI](nextui/): shaders, presets and overlays in one `.pakz`. Download it from the [releases](../../releases).

## How it works

Each screen is two shader passes. The first runs once per game pixel. It works out each dot's ink and its share of the gaps between dots on a Game Boy, or each pixel's measured colour on the GBC and GBA. The second runs once per screen pixel and draws the dot grid, the dots' shadows and the GBC's sparkle. The bezel, its shadow and the glass reflection are drawn in advance into an overlay image.

- Game Boy, Pocket and Light use Harlequin's dmg-3x and gb-pocket-3x settings and palettes.
- GBC uses BGB's "GBC reality" colours, fitted to Pokefan531's measured ramp.
- GBA uses Pokefan531's 2026 measured ramp and colour matrix and the panel's tint from the Handheld Color Space Project. Brightness and contrast match the GBC.
- The bezels are cut from Harlequin's dmg-3x and gb-pocket-3x border art. The GBC and GBA use the Pocket's.

## Licence

GPL-3.0, like Harlequin's gameboy shader and border art (libretro glsl-shaders, `handheld/console-border`) that this ports.
