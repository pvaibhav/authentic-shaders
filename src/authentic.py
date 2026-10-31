"""slot's Authentic screens (crates/slot-gfx/src/authentic.rs), ported to NextUI.

One source of truth for the constants the shaders and overlays share.
"""

GAP = 0.38      # share of each neighbour's ink a gap between dots takes
SHADOW = 0.45   # share of a dot's ink its shadow carries, per unit of shadow strength

# Each 5-bit code's light on the GBA and the GBC, in gamma 2.2: Pokefan531's measured ramps.
RAMP_GBA = [0, 3, 6, 10, 15, 25, 36, 50, 62, 71, 82, 92, 102, 109, 116, 124, 131, 138, 145, 152,
            160, 168, 176, 184, 193, 202, 211, 218, 229, 240, 249, 255]
RAMP_GBC = [0, 8, 15, 26, 37, 49, 67, 85, 97, 110, 121, 134, 140, 148, 154, 160,
            170, 180, 188, 196, 202, 207, 212, 217, 222, 228, 232, 237, 246, 252, 254, 255]


def rgb(hex_):
    return [((hex_ >> s) & 0xff) / 255.0 for s in (16, 8, 0)]


def linear(c):
    return [v ** 2.2 for v in c]


DOTS = {
    # Harlequin's dmg-3x.
    "dmg": dict(panel=0xa1a100, ink=0x005aaa, baseline_alpha=0.05, grey_balance=2.6,
                contrast=0.7, screen_light=0.85, pixel_opacity=0.9, shadow_opacity=0.9),
    # gb-pocket-3x.
    "pocket": dict(panel=0xa6ac84, ink=0x121922, baseline_alpha=0.03, grey_balance=3.5,
                   contrast=0.8, screen_light=0.9, pixel_opacity=0.95, shadow_opacity=0.9),
}
# The Pocket's settings, with the panel and ink that put its white and black on TWB64's Light shades.
DOTS["light"] = dict(DOTS["pocket"], panel=0x00cb90, ink=0x006550)


def gb_look(model):
    d = DOTS[model]
    return dict(
        light=rgb(d["panel"]),
        dark=rgb(d["ink"]),
        ink=[3.0 / d["grey_balance"], d["baseline_alpha"], GAP,
             d["contrast"] * d["shadow_opacity"] * SHADOW],
        glass=[d["contrast"], d["screen_light"], d["contrast"] * d["pixel_opacity"]],
    )


def gbc_look():
    white, dark = linear(rgb(0x868c7a)), linear(rgb(0x0e191c))
    return dict(
        ramp=RAMP_GBC,
        light=white,
        dark=dark,
        # Column-major, as slot hands it to glUniformMatrix3fv and as GLSL's mat3() reads it.
        response=[0.9173, 0.0822, 0.1309, 0.1560, 0.6685, 0.1116, -0.0732, 0.2493, 0.7574],
        gamma=[2.2, 2.2 * 0.775, 2.2 * 0.725],
        # How far below black, as a share of the way to white, a colour may fall: BGB draws the
        # GBC's red darker than its black, as the screen's own red is.
        least=[-dark[i] / (white[i] - dark[i]) for i in range(3)],
        grain=0.03,
        lcd=[0.6, 0.85],   # how much the gaps between columns and rows darken
    )


def gba_look():
    """The GBA's measured colours at the GBC look's brightness. Pokefan531's 2026 ramp and
    matrix and the panel's cool tint (#def6ff, from the Handheld Color Space Project's
    reflectance readings) as slot has them; but slot's white, 82% of the tint, with black a
    fourteenth of it, reads as fog on a lit screen, so here white is as bright as the GBC
    look's and black a 35th of it, tinted as the panel's black measured."""
    gbc_white = gbc_look()["light"]
    tint_white = linear(rgb(0xdef6ff))
    luminance = lambda c: 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
    white = [c * luminance(gbc_white) / luminance(tint_white) for c in tint_white]
    tint = [1.02, 0.97, 1.06]
    return dict(
        ramp=RAMP_GBA,
        light=white,
        dark=[white[i] / 35 * tint[i] for i in range(3)],
        response=[v * 0.8915 for v in [0.8988, 0.1163, 0.1831, 0.2229, 0.6217, 0.2438, -0.1217, 0.2620, 0.5731]],
        gamma=[2.2] * 3,
        least=[0.0] * 3,
        # The GBA's reflector glints under a lamp rather than showing grain.
        grain=0.0,
        lcd=[0.45, 0.20],
    )


COLOUR_LOOKS = {"gbc": gbc_look, "gba": gba_look}


def panel_srgb(screen):
    """The lit panel around the picture, in sRGB 0..1, as slot's shader paints it."""
    if screen in COLOUR_LOOKS:
        return [v ** (1 / 2.2) for v in COLOUR_LOOKS[screen]()["light"]]
    look = gb_look(screen)
    return [v * look["glass"][1] for v in look["light"]]



def picture_rect(w, h, src=(160, 144)):
    """Where NextUI's Native scaling puts the picture: the largest whole scale, centred."""
    sw, sh = src
    s = min(w // sw, h // sh)
    pw, ph = sw * s, sh * s
    return ((w - pw) // 2, (h - ph) // 2, pw, ph)


def fmt(v):
    s = f"{v:.6f}".rstrip("0")
    return s + "0" if s.endswith(".") else s


def vec(vs):
    return f"vec{len(vs)}({', '.join(fmt(v) for v in vs)})"
