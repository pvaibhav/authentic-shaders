"""Writes the Authentic GLSL shaders in NextUI's single-file libretro format.

Each shader draws only the picture, at Native scale. The overlay (overlay.py) holds the panel,
the bezel and the glass, precomputed, so the GPU spends nothing on them but one blend.
"""
from authentic import gb_look, COLOUR_LOOKS, vec, fmt

HEADER = """#version 300 es
// Authentic {title}: slot's reflective LCD, ported to NextUI.
// From slot's Authentic shader (crates/slot-gfx/src/authentic.rs, shaders.rs) by Prashant Vaibhav.
//
// {usage}
// Screen Scaling is Native, and the matching authentic overlay holds the panel, bezel and glass.
// The LCD's ghosting comes from the core's interframe blending.
{sources}
{pragmas}
#if defined(VERTEX)

#if __VERSION__ >= 130
#define COMPAT_VARYING out
#define COMPAT_ATTRIBUTE in
#else
#define COMPAT_VARYING varying
#define COMPAT_ATTRIBUTE attribute
#endif

COMPAT_ATTRIBUTE vec4 VertexCoord;
COMPAT_ATTRIBUTE vec4 TexCoord;
COMPAT_VARYING vec2 vTexCoord;

void main() {{
    gl_Position = VertexCoord;
    vTexCoord = TexCoord.xy;
}}

#elif defined(FRAGMENT)

#if __VERSION__ >= 130
#define COMPAT_VARYING in
#define COMPAT_TEXTURE texture
out vec4 FragColor;
#else
#define COMPAT_VARYING varying
#define FragColor gl_FragColor
#define COMPAT_TEXTURE texture2D
#endif

#ifdef GL_ES
#ifdef GL_FRAGMENT_PRECISION_HIGH
precision highp float;
#else
precision mediump float;
#endif
// Integers default to 16 bits in fragment shaders, too few for a hash.
precision highp int;
#endif

uniform sampler2D Texture;
uniform vec2 TextureSize;
uniform vec2 InputSize;
uniform vec2 OutputSize;
COMPAT_VARYING vec2 vTexCoord;

{uniforms}
"""

# The menu shows each setting's name, so the names say what their values do.
DOT_PARAMS = [
    ("DOT_SHADOW", "Dot shadow", 1.0, 0.0, 3.0, 0.25),
    ("DOT_SHADOW_OFFSET", "Dot shadow offset, in game pixels", 1.0, 0.0, 2.0, 0.25),
]
DOT_PRAGMAS = "\n".join(f'#pragma parameter {n} "{label}" {d} {lo} {hi} {step}' for n, label, d, lo, hi, step in DOT_PARAMS)


def uniforms(names_defaults):
    on = "\n".join(f"uniform float {n};" for n, _ in names_defaults)
    off = "\n".join(f"#define {n} {fmt(d)}" for n, d in names_defaults)
    return f"#ifdef PARAMETER_UNIFORM\n{on}\n#else\n{off}\n#endif"


GB_SOURCES = """//
// Harlequin's gameboy shader in its dmg-3x and gb-pocket-3x presets (libretro glsl-shaders,
// handheld/console-border): each dot is a share of ink over the lit panel, the gaps between
// dots take some of their neighbours' ink, and the dots cast a soft shadow on the reflector.
// The core draws grey (GBC - Grayscale); this shader lays the model's panel and ink over it."""

COLOUR_SOURCES = {
    "gbc": """//
// BGB's "GBC reality" colours at their true, dark reflective brightness, fitted to
// Pokefan531's measured ramp, raised to a power for each channel, and a matrix.
// The core's own colour correction must be off.""",
    "gba": """//
// The GBA's colour response from Pokefan531's 2026 spectrophotometer measurements
// (github.com/Pokefan531/Handheld-Colorspace-Shaders): a ramp for each 5-bit code and a
// matrix; its white the panel's cool tint from the Handheld Color Space Project's
// reflectance readings, as bright as the GBC's, its black a 35th of white. The core's own
// colour correction must be off.""",
}
COLOUR_TITLES = {"gbc": "Game Boy Color", "gba": "Game Boy Advance"}

GB_COMMON = """
const vec3 PANEL = {panel};
const vec3 INK = {ink};
const vec4 DOTS = {dots};   // ink gain, ink a white dot still holds, share a gap takes, shadow strength
const vec3 GLASS = {glass};  // ink contrast, panel light, how much light a dot takes away

// A dot's ink, from its grey.
float ink(float grey) {{
    return min(DOTS.x * (1.0 - grey) + DOTS.y, 1.0);
}}
"""

# First pass, once per game pixel: its ink, its share of each gap, and its grey.
GB_DOTS = """
float grey(vec2 at) {{
    return dot(COMPAT_TEXTURE(Texture, at).rgb, vec3(1.0 / 3.0));
}}

void main() {{
    vec2 texel = 1.0 / TextureSize;
    vec2 q = vTexCoord * TextureSize;
    float g = grey(vTexCoord);
    float a = ink(g);
    // A gap takes a share of the ink on either side of it: the dot left of a column gap,
    // the dot above a row gap, and none from past the picture.
    float left = q.x > 1.0 ? ink(grey(vTexCoord - vec2(texel.x, 0.0))) : 0.0;
    float up = q.y > 1.0 ? ink(grey(vTexCoord - vec2(0.0, texel.y))) : 0.0;
    FragColor = vec4(a, DOTS.z * (a + left), DOTS.z * (a + up), g);
}}

#endif
"""

# Second pass, per screen pixel: the dot or gap, the dots' shadow, and the panel's light.
GB_SCREEN = """
void main() {{
    vec2 q = vTexCoord * TextureSize;
    vec2 texel = 1.0 / TextureSize;
    // The screen pixel along each game pixel's top and left edge is the gap between dots,
    // and where gaps cross there is no ink.
    vec2 gap = step(fract(q), vec2(InputSize.y / OutputSize.y));
    vec4 dot_ = COMPAT_TEXTURE(Texture, (floor(q) + 0.5) * texel);
    float a = gap.x > 0.5 ? (gap.y > 0.5 ? 0.0 : dot_.g) : (gap.y > 0.5 ? dot_.b : dot_.r);
    // The dots' shadow on the reflector, down and to the left, blurred over about a pixel by
    // the texture's filtering, and none from past the picture: the texture clamps to its
    // edge, so cover fades it out over the half game pixel beyond. Ink in front of it hides it.
    float d = DOT_SHADOW_OFFSET;
    vec2 at = q * texel + vec2(d, -d) * texel;
    vec2 cover = clamp(min(vec2(q.x + d, q.y - d), vec2(InputSize.x - d - q.x, InputSize.y + d - q.y)) + 0.5, 0.0, 1.0);
    float shadow = ink(COMPAT_TEXTURE(Texture, at).a) * cover.x * cover.y;
    shadow = min(shadow * DOT_SHADOW * DOTS.w * (1.0 - 0.75 * a), 1.0);
    vec3 c = INK * a * (1.0 - GLASS.x * a * a) + PANEL * (1.0 - shadow) * (GLASS.y - GLASS.z * a);
    FragColor = vec4(c, 1.0);
}}

#endif
"""

COLOUR_COMMON = """
const vec3 BLACK = {dark};
"""

# First pass, once per game pixel: its colour on the panel, in linear light, stored as its
# square root so that 8 bits keep the dark colours' detail.
COLOUR_PASS1 = """
// The panel's response to each channel, scaled from black to the reflector's white.
const mat3 RESPONSE = mat3({response});
const vec3 WHITE = {light};
// The darkest a colour is drawn.
const vec3 LEAST = {least};

// Each 5-bit code's light (Pokefan531's measured ramp, in gamma 2.2), raised to each
// channel's power.
const float RAMP_R[32] = float[32]({ramp_r});
const float RAMP_G[32] = float[32]({ramp_g});
const float RAMP_B[32] = float[32]({ramp_b});

void main() {{
    // The 5-bit code is a channel's top 5 bits, however the frame widened it to 8 (NextUI
    // repeats the top bits; some sources leave zeros), read exactly rather than filtered.
    ivec3 code = ivec3(texelFetch(Texture, ivec2(vTexCoord * TextureSize), 0).rgb * 255.0 + 0.5) >> 3;
    vec3 lin = clamp(RESPONSE * vec3(RAMP_R[code.r], RAMP_G[code.g], RAMP_B[code.b]) + BLACK, LEAST, WHITE);
    FragColor = vec4(sqrt(lin), 1.0);
}}

#endif
"""

# Second pass, per screen pixel: the cell or the grid, and the reflector's sparkle.
SPARKLE = """
// One screen pixel in ten, at random: a multiply-xorshift integer hash, compared as an
// integer. A few integer operations, where a float hash costs several fract()s.
bool sparkles(uvec2 p) {{
    uint h = p.x * 0x8da6b343u ^ p.y * 0xd8163841u;
    return (h ^ (h >> 15)) * 0x2c1b3c6du >= 0xe6666666u;
}}
"""

COLOUR_SCREEN = """
const float GRAIN = {grain};
const float GAP_X = {lcd0};
const float GAP_Y = {lcd1};
{sparkle_fn}
void main() {{
    // The measured colour is a whole pixel's: its cell and the dark grid around it. Light
    // the cell so that the two together still average to it.
    float thin = min(InputSize.y / OutputSize.y, 1.0);
    float grid = thin * (1.0 - thin) * (GAP_X + GAP_Y) + thin * thin * max(GAP_X, GAP_Y);
    vec2 lit = vec2(1.0 - GRAIN, 1.0 + 9.0 * GRAIN) / (1.0 - grid);
    vec2 q = vTexCoord * TextureSize;
    // The screen pixel along each game pixel's top and left edge is the gap between cells.
    vec2 gap = step(fract(q), vec2(InputSize.y / OutputSize.y));
    vec3 lin = COMPAT_TEXTURE(Texture, (floor(q) + 0.5) / TextureSize).rgb;
    lin *= lin;
{light}
    lin = min(BLACK + (lin - BLACK) * light, vec3(1.0));
    lin = mix(lin, BLACK, max(gap.x * GAP_X, gap.y * GAP_Y));
    FragColor = vec4(pow(lin, vec3(1.0 / 2.2)), 1.0);
}}

#endif
"""

SPARKLE_LIGHT = """    // The reflector shows through the colour filter as a fine sparkle.
    float light = sparkles(uvec2(gl_FragCoord.xy)) ? lit.y : lit.x;"""
PLAIN_LIGHT = """    float light = lit.x;"""

GB_MODELS = {"dmg": "Game Boy", "pocket": "Game Boy Pocket", "light": "Game Boy Light"}


def gb_passes(model):
    look = gb_look(model)
    common = GB_COMMON.format(panel=vec(look["light"]), ink=vec(look["dark"]),
                              dots=vec(look["ink"]), glass=vec(look["glass"]))
    first = HEADER.format(
        title=GB_MODELS[model] + ", dots", sources=GB_SOURCES, pragmas="", uniforms="",
        usage=f"First of two passes, upscale = 1, before authentic-{model}-2.glsl.",
    ) + common + GB_DOTS.format()
    second = HEADER.format(
        title=GB_MODELS[model], sources=GB_SOURCES, pragmas=DOT_PRAGMAS,
        uniforms=uniforms([(n, d) for n, _, d, *_ in DOT_PARAMS]),
        usage=f"Second of two passes, after authentic-{model}-1.glsl, upscale = screen, filter = LINEAR.",
    ) + common + GB_SCREEN.format()
    return [(f"authentic-{model}-1.glsl", first, "1"), (f"authentic-{model}-2.glsl", second, "screen")]


def colour_passes(screen):
    look = COLOUR_LOOKS[screen]()
    ramps = [", ".join(fmt((v / 255) ** g) for v in look["ramp"]) for g in look["gamma"]]
    white, black = look["light"], look["dark"]
    # Column-major; column j scales row i by the white-to-black span of channel i.
    response = [look["response"][j * 3 + i] * (white[i] - black[i]) for j in range(3) for i in range(3)]
    least = [black[i] + (white[i] - black[i]) * look["least"][i] for i in range(3)]
    common = COLOUR_COMMON.format(dark=vec(black))
    title, sources = COLOUR_TITLES[screen], COLOUR_SOURCES[screen]
    first = HEADER.format(
        title=title + ", colours", sources=sources, pragmas="", uniforms="",
        usage=f"First of two passes, upscale = 1, before authentic-{screen}-2.glsl.",
    ) + common + COLOUR_PASS1.format(
        response=", ".join(fmt(v) for v in response), light=vec(white), least=vec([max(v, 0.0) for v in least]),
        ramp_r=ramps[0], ramp_g=ramps[1], ramp_b=ramps[2])
    sparkle = look["grain"] > 0
    second = HEADER.format(
        title=title, sources=sources, pragmas="", uniforms="",
        usage=f"Second of two passes, after authentic-{screen}-1.glsl, upscale = screen, filter = LINEAR.",
    ) + common + COLOUR_SCREEN.format(
        grain=fmt(look["grain"]), lcd0=fmt(look["lcd"][0]), lcd1=fmt(look["lcd"][1]),
        sparkle_fn=SPARKLE.format() if sparkle else "", light=SPARKLE_LIGHT if sparkle else PLAIN_LIGHT)
    return [(f"authentic-{screen}-1.glsl", first, "1"), (f"authentic-{screen}-2.glsl", second, "screen")]


def passes():
    """Each screen's shader passes, in order: (file, source, upscale)."""
    out = {m: gb_passes(m) for m in GB_MODELS}
    for screen in COLOUR_LOOKS:
        out[screen] = colour_passes(screen)
    return out

