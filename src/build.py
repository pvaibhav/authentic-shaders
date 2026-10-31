"""Builds Authentic-GB-GBC-GBA.pakz: the shaders, a preset per screen, and the overlays
(panel, bezel and glass) for every NextUI screen size, named by size so each device picks its
own."""
import io
import os
import shutil
import zipfile

from PIL import Image

from authentic import panel_srgb
from overlay import overlay
from shaders import passes

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Screen: the core tags whose overlay folders get its overlays. GBA plays on gpSP (GBA) or,
# as an extra, mGBA (MGBA).
SCREENS = {
    "dmg": ("GB",),
    "pocket": ("GB",),
    "light": ("GB",),
    "gbc": ("GBC",),
    "gba": ("GBA", "MGBA"),
}

# Each core's settings for the presets: its own colour correction off, as the shaders bring
# the screen's colours, and the LCD's slow response on. Each core ignores the other's keys.
GAMBATTE = ["gambatte_gbc_color_correction = disabled", "gambatte_mix_frames = lcd_ghosting"]
CORE = {
    "dmg": GAMBATTE + ["gambatte_gb_colorization = internal", "gambatte_gb_internal_palette = GBC - Grayscale"],
    "gbc": GAMBATTE,
    "gba": [
        "gpsp_color_correction = disabled",
        "gpsp_frame_mixing = enabled",
        "mgba_color_correction = OFF",
        "mgba_interframe_blending = lcd_ghosting",
    ],
}
CORE["pocket"] = CORE["light"] = CORE["dmg"]

# NextUI's screens: the H700 handhelds, the TrimUI Brick, the TrimUI Smart Pro.
SIZES = [(640, 480), (720, 480), (720, 720), (1024, 768), (1280, 720)]

# The panel without the bezel, kept out of the overlay menu, which lists files only.
PANEL_DIR = "Authentic panel only"

README = """Authentic LCD shaders for Game Boy, Game Boy Color and Game Boy Advance, from slot.

In game, once per device:
  1. Menu > Options > Shaders > Shader preset, then one of
       authentic-dmg      Game Boy
       authentic-pocket   Game Boy Pocket
       authentic-light    Game Boy Light
       authentic-gbc      Game Boy Color
       authentic-gba      Game Boy Advance (gpSP or mGBA)
  2. Menu > Options > Overlay, then the same screen at this device's size,
     e.g. authentic-dmg-720x480.png. It holds the lit panel around the picture,
     the bezel and its shadow, and the glass. On a 3:2 screen (720x480) the
     GBA's picture fills it, and its overlay is the glass alone.
  3. Save the settings for the console.

Each preset sets Screen Scaling to Native, which the overlays are drawn for.

For the panel without the bezel, move the overlay you want up from
Overlays/GB/Authentic panel only/ (or GBC, GBA, MGBA) into the folder above it.

Shader settings (Menu > Options > Shaders > Shader Settings, Game Boy only):
  DOT_SHADOW          how dark the dots' shadows fall, 0 to 3; 1 is Harlequin's dmg-3x
  DOT_SHADOW_OFFSET   how far down and left they fall, in game pixels; dmg-3x has 0.5

The bezels are Harlequin's dmg-3x and gb-pocket-3x border art (libretro
glsl-shaders, handheld/console-border, GPL-3.0, like the shaders it ports):
its lens, window, glass and power light. The GBC and GBA use the Pocket's.

The Game Boy presets have the core draw in greys (GBC - Grayscale); the shader
lays the model's colours over them, so leave the palette alone.
"""

# Earlier releases' files, which this one replaces.
OLD = [f"Shaders/glsl/authentic-{m}.glsl" for m in ("gb", "dmg", "pocket", "light", "gbc")] + [
    "Shaders/authentic-gb.cfg", "Shaders/authentic-screen.txt",
] + [
    f"Shaders/authentic-{p}-{mode}.cfg"
    for p in ("gb-dmg", "gb-pocket", "gb-light", "gbc") for mode in ("native", "aspect")
] + [
    f"Overlays/{tag}/authentic-{m}{suffix}.png"
    for tag, ms in (("GB", ("dmg", "pocket", "light")), ("GBC", ("gbc",)))
    for m in ms for suffix in ("-native", "-aspect", "", "-panel")
]

POST_INSTALL = """#!/bin/sh
# Authentic GB/GBC/GBA: remove earlier releases' files, which this one replaces, and NextUI's
# compiled copies of the shaders, which it keys by file name and would otherwise keep using.
SD=/mnt/SDCARD
for f in {old}; do
	rm -f "$SD/$f"
done
rm -f "$SD"/.shadercache/authentic-*.bin
sync
"""


def preset(screen):
    lines = [f"minarch_nrofshaders = {len(passes()[screen])}"]
    for i, (name, _, upscale) in enumerate(passes()[screen], 1):
        lines += [
            f"minarch_shader{i} = {name}",
            f"minarch_shader{i}_filter = LINEAR",
            f"minarch_shader{i}_srctype = source",
            f"minarch_shader{i}_scaletype = source",
            f"minarch_shader{i}_upscale = {upscale}",
        ]
    # No overlay here: each device keeps the one for its screen size.
    lines += [
        "minarch_scale_filter = NEAREST",
        "minarch_screen_scaling = Native",
        "minarch_screen_effect = None",
    ] + CORE[screen]
    return "\n".join(lines) + "\n"


def png(rgba):
    buf = io.BytesIO()
    Image.fromarray(rgba, "RGBA").save(buf, "PNG", optimize=True)
    return buf.getvalue()


def build():
    tree = f"{ROOT}/build/pak"
    shutil.rmtree(tree, ignore_errors=True)
    os.makedirs(f"{tree}/Shaders/glsl")
    for screen, ps in passes().items():
        for name, src, _ in ps:
            open(f"{tree}/Shaders/glsl/{name}", "w").write(src)
        open(f"{tree}/Shaders/authentic-{screen}.cfg", "w").write(preset(screen))
    open(f"{tree}/Shaders/authentic-README.txt", "w").write(README)
    for screen, tags in SCREENS.items():
        for w, h in SIZES:
            for sub, bezel in (("", True), (PANEL_DIR, False)):
                data = png(overlay(w, h, screen, panel_srgb(screen), bezel))
                for tag in tags:
                    d = os.path.join(tree, "Overlays", tag, sub)
                    os.makedirs(d, exist_ok=True)
                    open(f"{d}/authentic-{screen}-{w}x{h}.png", "wb").write(data)
    old = " ".join(f'"{p}"' for p in OLD)
    open(f"{tree}/post_install.sh", "w").write(POST_INSTALL.format(old=old))
    out = f"{ROOT}/build/dist/Authentic-GB-GBC-GBA.pakz"
    shutil.rmtree(f"{ROOT}/build/dist", ignore_errors=True)
    os.makedirs(f"{ROOT}/build/dist")
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for d, _, files in sorted(os.walk(tree)):
            for f in sorted(files):
                p = os.path.join(d, f)
                info = zipfile.ZipInfo.from_file(p, os.path.relpath(p, tree))
                info.external_attr = (0o755 if f.endswith(".sh") else 0o644) << 16
                info.compress_type = zipfile.ZIP_STORED if f.endswith(".png") else zipfile.ZIP_DEFLATED
                z.writestr(info, open(p, "rb").read())
    return out


if __name__ == "__main__":
    print(build())
