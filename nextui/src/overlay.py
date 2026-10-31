"""Precomputes everything around and over the picture into one NextUI overlay per screen size.

NextUI draws the shader's picture at Native scale, then alpha-blends the overlay over the whole
screen. The overlay holds the lit panel around the picture, the bezel, and over the window the
glass of Harlequin's dmg-3x and gb-pocket-3x presets: their border art's screen layer (libretro
glsl-shaders, handheld/console-border/resources, GPL-3.0), with its shine at the top right, its
shade toward the bottom and the bezel's shadow along the window's edges. Blending it over the
picture reproduces dmg-3x's own blend, mix(lcd, layer, layer alpha), then the plastic over that.
"""
import os

import numpy as np
from PIL import Image

from authentic import picture_rect

RESOURCES = os.path.join(os.path.dirname(__file__), "resources")
# Each screen's glass: Harlequin drew one for the Game Boy and one for the Pocket.
GLASS = {"dmg": "dmg", "gbc": "pocket", "gba": "pocket", "pocket": "pocket", "light": "pocket"}
# How far in from the art's window its rim of shadow runs, in the art's pixels; the panel-only
# overlays stretch the glass inside it over the whole screen.
RIM = 14


def glass_layer(screen, w, h):
    """The glass inside the art's window, without its rim, resized to w x h:
    (straight colour (h, w, 3), alpha (h, w)), 0..1."""
    art = np.asarray(Image.open(os.path.join(RESOURCES, f"{GLASS[screen]}-border-square-4x.png")).convert("RGBA"))
    ys, xs = np.nonzero(art[..., 3] < 255)
    glass = art[ys.min() + RIM:ys.max() + 1 - RIM, xs.min() + RIM:xs.max() + 1 - RIM].astype(np.float64) / 255
    out = _resize(glass, w, h)
    return out[..., :3], out[..., 3]


# Harlequin's border art for each screen: the file, and its light with the light's label
# (art pixels: x0, y0, x1, y1).
ART = {
    "dmg": ("dmg", (1092, 670, 1232, 782)),
    "pocket": ("pocket", (1152, 586, 1254, 668)),
}
ART["light"] = ART["gbc"] = ART["gba"] = ART["pocket"]
# How much of the art around its window is kept: its lip. Beyond it the lens is plain.
LIP = 6
# The art's window, and the picture's centre in it: dmg-3x frames a 3x picture there, 4 art
# pixels to a game pixel.
WINDOW = (1266, 494, 1937, 1106)
CENTRE = (1601.5, 800.0)
ART_PER_GAME_PIXEL = 4.0


# The game's picture, in game pixels, for each screen.
SOURCE = {"gba": (240, 160)}
# The art's margin of glass around a picture, in art pixels: dmg-3x's, centred.
MARGIN = (15.5, 18.0)
# How much of the window's edge (its lip and rim of shadow) keeps its size when the window is
# stretched to another shape; only the glass inside it stretches.
BORDER = LIP + 26


def source(screen):
    return SOURCE.get(screen, (160, 144))


def _lens(screen):
    """The art's parts: an endless plain lens of its own texture, the window with its lip,
    and the light. Returns (lens RGBA, window-and-lip RGBA, light RGBA), floats."""
    name, (x0, y0, x1, y1) = ART[screen]
    art = np.asarray(Image.open(os.path.join(RESOURCES, f"{name}-border-square-4x.png")).convert("RGBA")).astype(np.float64) / 255
    # Lens texture: a plain patch of it from the right of the window, mirrored as it repeats
    # so it has no seams.
    patch = art[560:700, 1950:2040]
    patch = np.concatenate([patch, patch[:, ::-1]], 1)
    patch = np.concatenate([patch, patch[::-1]], 0)
    reps = (art.shape[0] // patch.shape[0] + 1, art.shape[1] // patch.shape[1] + 1, 1)
    lens = np.tile(patch, reps)[:art.shape[0], :art.shape[1]]
    window = art[WINDOW[1] - LIP:WINDOW[3] + LIP, WINDOW[0] - LIP:WINDOW[2] + LIP].copy()
    return lens, window, art[y0:y1, x0:x1].copy()


def _nine_slice(rgba, w, h, b):
    """rgba stretched to w x h with its border b pixels wide kept as it is: corners as they
    are, edges stretched along themselves, the middle both ways."""
    if (w, h) == rgba.shape[1::-1]:
        return rgba
    H, W = rgba.shape[:2]
    xs, ys = [(0, b, 0, b), (b, W - b, b, w - b), (W - b, W, w - b, w)], [(0, b, 0, b), (b, H - b, b, h - b), (H - b, H, h - b, h)]
    out = np.zeros((h, w, 4))
    for sy0, sy1, dy0, dy1 in ys:
        for sx0, sx1, dx0, dx1 in xs:
            out[dy0:dy1, dx0:dx1] = _resize(rgba[sy0:sy1, sx0:sx1], dx1 - dx0, dy1 - dy0)
    return out


def _resize(rgba, w, h):
    """Premultiplied resize, so colours don't bleed from clear pixels."""
    a = rgba[..., 3]
    planes = [rgba[..., i] * a for i in range(3)] + [a]
    filt = Image.BOX if w <= rgba.shape[1] else Image.BICUBIC
    out = np.dstack([np.asarray(Image.fromarray(p.astype(np.float32), "F").resize((w, h), filt)) for p in planes])
    alpha = np.clip(out[..., 3], 0, 1)
    colour = np.where(alpha[..., None] > 1e-6, out[..., :3] / np.maximum(alpha, 1e-6)[..., None], 0.0)
    return np.dstack([np.clip(colour, 0, 1), alpha])


def bezel(w, h, screen):
    """Harlequin's lens at this screen's size, its window around NextUI's centred Native
    picture with dmg-3x's margin, the light in the margin left of it. RGBA float (h, w, 4)."""
    sw_, sh_ = source(screen)
    x, y, pw, ph = picture_rect(w, h, (sw_, sh_))
    k = (pw / sw_) / ART_PER_GAME_PIXEL             # screen pixels to an art pixel
    lens, window, sprite = _lens(screen)
    art = lens.copy()
    # The window around the picture, in the art: as the art has it for a Game Boy's, its
    # glass stretched for another shape, centred where the art centres its picture.
    win_w = round(sw_ * ART_PER_GAME_PIXEL + 2 * MARGIN[0])
    win_h = round(sh_ * ART_PER_GAME_PIXEL + 2 * MARGIN[1])
    wx0 = round(CENTRE[0] - win_w / 2)
    wy0 = round(CENTRE[1] - win_h / 2)
    block = _nine_slice(window, win_w + 2 * LIP, win_h + 2 * LIP, BORDER)
    art[wy0 - LIP:wy0 + win_h + LIP, wx0 - LIP:wx0 + win_w + LIP] = block
    # Where the screen's edges fall in the art, the picture's centre on the art's.
    left = CENTRE[0] - (x + pw / 2) / k
    top = CENTRE[1] - (y + ph / 2) / k
    # The light, centred in the lens left of the window, as large as the art has it or as
    # fits there.
    margin = wx0 - left
    fit = min(1.0, 0.8 * margin / sprite.shape[1])
    if fit > 0.2:
        sw, sh = max(1, round(sprite.shape[1] * fit)), max(1, round(sprite.shape[0] * fit))
        small = _resize(sprite, sw, sh) if fit < 1 else sprite
        cx = round(left + margin / 2 - sw / 2)
        light = ART[screen][1]
        # As high on the window as the art has it on a Game Boy's.
        cy = round(wy0 + ((light[1] + light[3]) / 2 - WINDOW[1]) * win_h / (WINDOW[3] - WINDOW[1]) - sh / 2)
        art[cy:cy + sh, cx:cx + sw] = small
    # Scale the art so the view is w x h, offset by the fraction of an art pixel.
    big_w, big_h = round(art.shape[1] * k), round(art.shape[0] * k)
    scaled = _resize(art, big_w, big_h)
    ox, oy = round(left * k), round(top * k)
    return scaled[oy:oy + h, ox:ox + w]


def overlay(w, h, screen, panel, bezel_on):
    """RGBA uint8 (h, w, 4), top row first. panel: sRGB of the lit panel around the picture;
    bezel_on: False for the lit panel and the glass to the screen's edges."""
    x, y, pw, ph = picture_rect(w, h, source(screen))
    if bezel_on:
        art = bezel(w, h, screen)
        c, a = art[..., :3], art[..., 3]
    else:
        c, a = glass_layer(screen, w, h)
    py, px = np.mgrid[0:h, 0:w] + 0.5
    inside = (px >= x) & (px < x + pw) & (py >= y) & (py < y + ph)
    # Around the picture the shader draws nothing, so the lit panel under the glass is the
    # overlay's own; over the picture the glass blends as it is.
    under = np.where(inside[..., None], 0.0, np.array(panel))
    c = np.where(inside[..., None], c, c * a[..., None] + under * (1 - a[..., None]))
    a = np.where(inside, a, 1.0)
    return np.round(np.dstack([np.clip(c, 0, 1), a]) * 255).astype(np.uint8)
