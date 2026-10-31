"""Renders a game frame the way NextUI's GL pipeline does (generic_video.c, PLAT_GL_Swap):
the frame as a texture, one shader pass at the picture's size, placed on the screen, then
the overlay alpha-blended over the whole screen."""
import moderngl
import numpy as np
from PIL import Image

from authentic import picture_rect

_ctx = None


def ctx():
    global _ctx
    if _ctx is None:
        _ctx = moderngl.create_standalone_context()
    return _ctx


def program(source):
    # NextUI drops its #pragma parameter lines before compiling.
    source = "\n".join(l for l in source.split("\n")
                       if not l.startswith("#pragma parameter") and not l.startswith("#version"))
    # NextUI swaps any desktop #version for 300 es and puts its defines after it; here the
    # desktop equivalent, so the shader's own __VERSION__ >= 130 branches are the ones used.
    c = ctx()
    return c.program(
        vertex_shader="#version 330 core\n#define VERTEX\n" + source,
        fragment_shader="#version 330 core\n#define FRAGMENT\n#define PARAMETER_UNIFORM\n" + source,
    )


def shade(source, frame, out_w, out_h, filter_linear=True, params=None, components=3):
    """One pass: frame (h, w, 3 or 4 uint8) to out_w x out_h, top row first."""
    c = ctx()
    h, w = frame.shape[:2]
    rgba = frame if frame.shape[2] == 4 else np.dstack([frame, np.full((h, w), 255, np.uint8)])
    tex = c.texture((w, h), 4, np.ascontiguousarray(rgba).tobytes())
    f = moderngl.LINEAR if filter_linear else moderngl.NEAREST
    tex.filter = (f, f)
    tex.repeat_x = tex.repeat_y = False
    prog = program(source)
    # NextUI's quad: x, y, z, w, u, v, s, t, top-left first, with v = 1 at the top.
    verts = np.array([
        -1, 1, 0, 1, 0, 1, 0, 0,
        -1, -1, 0, 1, 0, 0, 0, 0,
        1, 1, 0, 1, 1, 1, 0, 0,
        1, -1, 0, 1, 1, 0, 0, 0,
    ], dtype="f4")
    vbo = c.buffer(verts.tobytes())
    vao = c.vertex_array(prog, [(vbo, "4f 4f", "VertexCoord", "TexCoord")])
    for name, val in (("TextureSize", (w, h)), ("InputSize", (w, h)), ("OutputSize", (out_w, out_h))):
        if name in prog:
            prog[name].value = val
    # NextUI starts each parameter at its #pragma default.
    defaults = {l.split()[2]: float(l.rsplit('"', 1)[1].split()[0])
                for l in source.split("\n") if l.startswith("#pragma parameter")}
    for name, val in {**defaults, **(params or {})}.items():
        if name in prog:
            prog[name].value = val
    if "Texture" in prog:
        prog["Texture"].value = 0
    fbo = c.framebuffer(color_attachments=[c.texture((out_w, out_h), 4)])
    fbo.use()
    c.viewport = (0, 0, out_w, out_h)
    tex.use(0)
    vao.render(moderngl.TRIANGLE_STRIP)
    # Row 0 of the framebuffer sampled the frame's top row (v = 0): it reads back top first,
    # as NextUI's final flip shows it.
    data = np.frombuffer(fbo.read(components=components), np.uint8).reshape(out_h, out_w, components)
    for o in (fbo, vao, vbo, tex, prog):
        o.release()
    return data


def chain(passes, frame, out_w, out_h, params=None):
    """NextUI's shader passes in order, each (source, upscale): upscale "1" renders at the
    game's size into an RGBA8 texture the next pass reads; "screen" at out_w x out_h."""
    img = frame
    for i, (source, upscale) in enumerate(passes):
        last = i == len(passes) - 1
        w, h = (out_w, out_h) if upscale == "screen" else (img.shape[1], img.shape[0])
        img = shade(source, img, w, h, params=params, components=3 if last else 4)
    return img


def screen(passes, frame, w, h, overlay=None, params=None):
    if isinstance(passes, str):
        passes = [(passes, "screen")]
    x, y, pw, ph = picture_rect(w, h, (frame.shape[1], frame.shape[0]))
    out = np.zeros((h, w, 3), np.float64)
    out[y:y + ph, x:x + pw] = chain(passes, frame, pw, ph, params=params)
    if overlay is not None:
        ov = np.asarray(overlay.convert("RGBA").resize((w, h), Image.NEAREST)).astype(np.float64)
        a = ov[..., 3:4] / 255.0
        out = ov[..., :3] * a + out * (1 - a)
    return Image.fromarray(np.clip(np.round(out), 0, 255).astype(np.uint8), "RGB")
