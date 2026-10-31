# Authentic LCD shaders for NextUI

## Install

Download `Authentic-GB-GBC-GBA.pakz` from the [latest release](../../../releases/latest), copy it to the root of your SD card and start NextUI. It installs and removes files from earlier releases.

Then, in a game, once per console:

1. Open Options > Shaders > Shader preset and pick `authentic-dmg`, `authentic-pocket`, `authentic-light`, `authentic-gbc` or `authentic-gba`.
2. Open Options > Overlay and pick the same screen at your device's resolution, for example `authentic-gbc-720x480.png`.
3. Save the settings for the console.

The presets set Screen Scaling to Native, which the overlays are drawn for. They also turn off the core's colour correction and turn on its LCD ghosting (Gambatte, gpSP or mGBA).

Overlays come in 640x480, 720x480, 720x720, 1024x768 and 1280x720. On a 720x480 screen the GBA picture fills the screen, so its overlay only adds the glass. Versions without the bezel are in `Overlays/<console>/Authentic panel only`. Move one up a folder to use it.

The Game Boy shaders have two settings under Options > Shaders > Shader Settings. `DOT_SHADOW` sets how dark the dots' shadows are (1 matches dmg-3x). `DOT_SHADOW_OFFSET` sets how far down and left they fall, in game pixels (dmg-3x uses 0.5).

## Performance

Each number is the GPU time for NextUI's whole frame: both shader passes at Native scale, the copy to the screen and the overlay. It is the median of 5 runs on real game frames, measured with `bench/bench.c`. A plain copy through the same steps is shown for comparison. A frame at 60 Hz is 16.7 ms.

| Device (GPU, screen) | Plain copy | Game Boy | Pocket | Light | GBC | GBA |
|---|---|---|---|---|---|---|
| Anbernic RG35XX SP (Mali-G31, 720x480) | 0.83 ms | 2.23 ms | 2.45 ms | 2.34 ms | 2.64 ms | not measured |
| TrimUI Brick (PowerVR GE8300, 1024x768) | 2.77 ms (GB), 3.12 ms (GBA) | 4.65 ms | | | 5.67 ms | 4.99 ms |

## Building

```sh
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python src/build.py
```

This writes `build/dist/Authentic-GB-GBC-GBA.pakz`. `src/render.py` renders the shaders with desktop OpenGL for previews. `bench/bench.c` times a shader on the device. Build it for aarch64 and run it with no arguments for usage.
