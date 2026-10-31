/* Times a NextUI single-pass GLSL shader on the device's GPU, offscreen.
 * bench <shader.glsl> <frame.rgb> <width> <height> [-src W H] [NAME=value ...]
 * Builds the shader as NextUI's generic_video.c does, draws it over a width x height
 * framebuffer with a fresh frame uploaded each time, and prints milliseconds per frame. */
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

typedef unsigned int GLenum, GLuint, GLbitfield;
typedef int GLint, GLsizei, EGLint;
typedef float GLfloat;
typedef unsigned char GLubyte, GLboolean;
typedef char GLchar;
typedef void *EGLDisplay, *EGLConfig, *EGLSurface, *EGLContext;
typedef unsigned int EGLBoolean;

#define EGL_NONE 0x3038
#define EGL_SURFACE_TYPE 0x3033
#define EGL_PBUFFER_BIT 0x0001
#define EGL_RENDERABLE_TYPE 0x3040
#define EGL_OPENGL_ES2_BIT 0x0004
#define EGL_RED_SIZE 0x3024
#define EGL_GREEN_SIZE 0x3023
#define EGL_BLUE_SIZE 0x3022
#define EGL_WIDTH 0x3057
#define EGL_HEIGHT 0x3056
#define EGL_CONTEXT_CLIENT_VERSION 0x3098
#define EGL_OPENGL_ES_API 0x30A0

#define GL_TEXTURE_2D 0x0DE1
#define GL_RGBA 0x1908
#define GL_UNSIGNED_BYTE 0x1401
#define GL_TEXTURE_MIN_FILTER 0x2801
#define GL_TEXTURE_MAG_FILTER 0x2800
#define GL_TEXTURE_WRAP_S 0x2802
#define GL_TEXTURE_WRAP_T 0x2803
#define GL_LINEAR 0x2601
#define GL_CLAMP_TO_EDGE 0x812F
#define GL_FRAMEBUFFER 0x8D40
#define GL_COLOR_ATTACHMENT0 0x8CE0
#define GL_FRAMEBUFFER_COMPLETE 0x8CD5
#define GL_VERTEX_SHADER 0x8B31
#define GL_FRAGMENT_SHADER 0x8B30
#define GL_COMPILE_STATUS 0x8B81
#define GL_LINK_STATUS 0x8B82
#define GL_FLOAT 0x1406
#define GL_TRIANGLE_STRIP 0x0005
#define GL_TEXTURE0 0x84C0
#define GL_RENDERER 0x1F01
#define GL_VERSION 0x1F02
#define GL_COLOR_BUFFER_BIT 0x4000
#define GL_BLEND 0x0BE2
#define GL_SRC_ALPHA 0x0302
#define GL_ONE_MINUS_SRC_ALPHA 0x0303
#define GL_NEAREST 0x2600

#define FN(ret, name, args) static ret (*name) args;
FN(EGLDisplay, eglGetDisplay, (void *))
FN(EGLBoolean, eglInitialize, (EGLDisplay, EGLint *, EGLint *))
FN(EGLBoolean, eglBindAPI, (GLenum))
FN(EGLBoolean, eglChooseConfig, (EGLDisplay, const EGLint *, EGLConfig *, EGLint, EGLint *))
FN(EGLSurface, eglCreatePbufferSurface, (EGLDisplay, EGLConfig, const EGLint *))
FN(EGLContext, eglCreateContext, (EGLDisplay, EGLConfig, EGLContext, const EGLint *))
FN(EGLBoolean, eglMakeCurrent, (EGLDisplay, EGLSurface, EGLSurface, EGLContext))
FN(EGLint, eglGetError, (void))
FN(void, glGenTextures, (GLsizei, GLuint *))
FN(void, glBindTexture, (GLenum, GLuint))
FN(void, glTexImage2D, (GLenum, GLint, GLint, GLsizei, GLsizei, GLint, GLenum, GLenum, const void *))
FN(void, glTexSubImage2D, (GLenum, GLint, GLint, GLint, GLsizei, GLsizei, GLenum, GLenum, const void *))
FN(void, glTexParameteri, (GLenum, GLenum, GLint))
FN(void, glGenFramebuffers, (GLsizei, GLuint *))
FN(void, glBindFramebuffer, (GLenum, GLuint))
FN(void, glFramebufferTexture2D, (GLenum, GLenum, GLenum, GLuint, GLint))
FN(GLenum, glCheckFramebufferStatus, (GLenum))
FN(GLuint, glCreateShader, (GLenum))
FN(void, glShaderSource, (GLuint, GLsizei, const GLchar **, const GLint *))
FN(void, glCompileShader, (GLuint))
FN(void, glGetShaderiv, (GLuint, GLenum, GLint *))
FN(void, glGetShaderInfoLog, (GLuint, GLsizei, GLsizei *, GLchar *))
FN(GLuint, glCreateProgram, (void))
FN(void, glAttachShader, (GLuint, GLuint))
FN(void, glBindAttribLocation, (GLuint, GLuint, const GLchar *))
FN(void, glLinkProgram, (GLuint))
FN(void, glGetProgramiv, (GLuint, GLenum, GLint *))
FN(void, glGetProgramInfoLog, (GLuint, GLsizei, GLsizei *, GLchar *))
FN(void, glUseProgram, (GLuint))
FN(GLint, glGetUniformLocation, (GLuint, const GLchar *))
FN(void, glUniform1f, (GLint, GLfloat))
FN(void, glUniform2f, (GLint, GLfloat, GLfloat))
FN(void, glUniform1i, (GLint, GLint))
FN(void, glUniformMatrix4fv, (GLint, GLsizei, GLboolean, const GLfloat *))
FN(void, glVertexAttribPointer, (GLuint, GLint, GLenum, GLboolean, GLsizei, const void *))
FN(void, glEnableVertexAttribArray, (GLuint))
FN(void, glViewport, (GLint, GLint, GLsizei, GLsizei))
FN(void, glDrawArrays, (GLenum, GLint, GLsizei))
FN(void, glFinish, (void))
FN(void, glFlush, (void))
FN(void, glActiveTexture, (GLenum))
FN(void, glClear, (GLbitfield))
FN(void, glReadPixels, (GLint, GLint, GLsizei, GLsizei, GLenum, GLenum, void *))
FN(const GLubyte *, glGetString, (GLenum))
FN(void, glEnable, (GLenum))
FN(void, glDisable, (GLenum))
FN(void, glBlendFunc, (GLenum, GLenum))

static void *lib(const char **names) {
    for (; *names; names++) {
        void *h = dlopen(*names, RTLD_NOW | RTLD_GLOBAL);
        if (h) return h;
    }
    return NULL;
}

#define LOAD(h, name) do { *(void **)&name = dlsym(h, #name); if (!name) { fprintf(stderr, "no %s\n", #name); exit(1); } } while (0)

static double now(void) {
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    return t.tv_sec * 1e3 + t.tv_nsec / 1e6;
}

static char *slurp(const char *path) {
    FILE *f = fopen(path, "rb");
    if (!f) { perror(path); exit(1); }
    fseek(f, 0, SEEK_END);
    long n = ftell(f);
    rewind(f);
    char *s = malloc(n + 1);
    fread(s, 1, n, f);
    s[n] = 0;
    fclose(f);
    return s;
}

#define MAXP 16
static int SRCW = 160, SRCH = 144;
static char pname[MAXP][64];
static float pval[MAXP];
static int np;

/* NextUI drops the #pragma parameter lines; their defaults become the uniforms' values. */
static char *clean(char *src) {
    char *out = calloc(strlen(src) + 1, 1);
    for (char *line = strtok(src, "\n"); line; line = strtok(NULL, "\n")) {
        if (strncmp(line, "#pragma parameter", 17) == 0) {
            char name[64];
            const char *q = strrchr(line, '"');
            if (np < MAXP && sscanf(line + 17, "%63s", name) == 1 && q) {
                strcpy(pname[np], name);
                pval[np++] = strtof(q + 1, NULL);
            }
            continue;
        }
        strcat(out, line);
        strcat(out, "\n");
    }
    return out;
}

static GLuint compile(GLenum type, const char *head, const char *body) {
    const char *parts[2] = {head, body};
    GLuint s = glCreateShader(type);
    glShaderSource(s, 2, parts, NULL);
    glCompileShader(s);
    GLint ok;
    glGetShaderiv(s, GL_COMPILE_STATUS, &ok);
    if (!ok) {
        char log[4096];
        glGetShaderInfoLog(s, sizeof log, NULL, log);
        fprintf(stderr, "compile failed:\n%s\n", log);
        exit(1);
    }
    return s;
}

int main(int argc, char **argv) {
    if (argc < 5) {
        fprintf(stderr, "bench shader.glsl frame.rgb width height [NAME=value ...] [-n frames]\n");
        return 2;
    }
    int W = atoi(argv[3]), H = atoi(argv[4]), frames = 240, SW = 0, SH = 0, overlay = 0;
    const char *dump = NULL, *pre = NULL;
    const char *egln[] = {"libEGL.so", "libEGL.so.1", "libmali.so", NULL};
    const char *glesn[] = {"libGLESv2.so", "libGLESv2.so.2", "libmali.so", NULL};
    void *egl = lib(egln), *gles = lib(glesn);
    if (!egl || !gles) { fprintf(stderr, "no EGL/GLES: %s\n", dlerror()); return 1; }
    LOAD(egl, eglGetDisplay); LOAD(egl, eglInitialize); LOAD(egl, eglBindAPI); LOAD(egl, eglChooseConfig);
    LOAD(egl, eglCreatePbufferSurface); LOAD(egl, eglCreateContext); LOAD(egl, eglMakeCurrent); LOAD(egl, eglGetError);
    LOAD(gles, glGenTextures); LOAD(gles, glBindTexture); LOAD(gles, glTexImage2D); LOAD(gles, glTexSubImage2D);
    LOAD(gles, glTexParameteri); LOAD(gles, glGenFramebuffers); LOAD(gles, glBindFramebuffer);
    LOAD(gles, glFramebufferTexture2D); LOAD(gles, glCheckFramebufferStatus); LOAD(gles, glCreateShader);
    LOAD(gles, glShaderSource); LOAD(gles, glCompileShader); LOAD(gles, glGetShaderiv); LOAD(gles, glGetShaderInfoLog);
    LOAD(gles, glCreateProgram); LOAD(gles, glAttachShader); LOAD(gles, glBindAttribLocation); LOAD(gles, glLinkProgram);
    LOAD(gles, glGetProgramiv); LOAD(gles, glGetProgramInfoLog); LOAD(gles, glUseProgram); LOAD(gles, glGetUniformLocation);
    LOAD(gles, glUniform1f); LOAD(gles, glUniform2f); LOAD(gles, glUniform1i); LOAD(gles, glUniformMatrix4fv); LOAD(gles, glVertexAttribPointer);
    LOAD(gles, glEnableVertexAttribArray); LOAD(gles, glViewport); LOAD(gles, glDrawArrays); LOAD(gles, glFinish); LOAD(gles, glFlush);
    LOAD(gles, glActiveTexture); LOAD(gles, glClear); LOAD(gles, glReadPixels); LOAD(gles, glGetString);
    LOAD(gles, glEnable); LOAD(gles, glDisable); LOAD(gles, glBlendFunc);

    EGLDisplay d = eglGetDisplay(NULL);
    EGLint major, minor;
    if (!d || !eglInitialize(d, &major, &minor)) { fprintf(stderr, "eglInitialize: 0x%x\n", eglGetError()); return 1; }
    eglBindAPI(EGL_OPENGL_ES_API);
    EGLint cattr[] = {EGL_SURFACE_TYPE, EGL_PBUFFER_BIT, EGL_RENDERABLE_TYPE, EGL_OPENGL_ES2_BIT,
                      EGL_RED_SIZE, 8, EGL_GREEN_SIZE, 8, EGL_BLUE_SIZE, 8, EGL_NONE};
    EGLConfig cfg;
    EGLint n;
    if (!eglChooseConfig(d, cattr, &cfg, 1, &n) || n < 1) { fprintf(stderr, "no pbuffer config: 0x%x\n", eglGetError()); return 1; }
    EGLint sattr[] = {EGL_WIDTH, 16, EGL_HEIGHT, 16, EGL_NONE};
    EGLSurface surf = eglCreatePbufferSurface(d, cfg, sattr);
    EGLint xattr[] = {EGL_CONTEXT_CLIENT_VERSION, 2, EGL_NONE};
    EGLContext ctx = eglCreateContext(d, cfg, NULL, xattr);
    if (!surf || !ctx || !eglMakeCurrent(d, surf, surf, ctx)) { fprintf(stderr, "context: 0x%x\n", eglGetError()); return 1; }

    char *body = clean(slurp(argv[1]));
    for (int i = 5; i < argc; i++) {
        if (!strcmp(argv[i], "-n") && i + 1 < argc) { frames = atoi(argv[++i]); continue; }
        if (!strcmp(argv[i], "-screen") && i + 2 < argc) { SW = atoi(argv[++i]); SH = atoi(argv[++i]); continue; }
        if (!strcmp(argv[i], "-overlay")) { overlay = 1; continue; }
        if (!strcmp(argv[i], "-src") && i + 2 < argc) { SRCW = atoi(argv[++i]); SRCH = atoi(argv[++i]); continue; }
        if (!strcmp(argv[i], "-pre") && i + 1 < argc) { pre = argv[++i]; continue; }
        if (!strcmp(argv[i], "-dump") && i + 1 < argc) { dump = argv[++i]; continue; }
        char *eq = strchr(argv[i], '=');
        if (!eq) continue;
        *eq = 0;
        int k;
        for (k = 0; k < np && strcmp(pname[k], argv[i]); k++) {}
        if (k == np && np < MAXP) strcpy(pname[np++], argv[i]);
        pval[k] = strtof(eq + 1, NULL);
    }
    /* As NextUI: a desktop #version or 300 es becomes #version 300 es; none means 100. */
    const char *ver = "#version 100\n";
    char *vl = strstr(body, "#version");
    if (vl) {
        ver = "#version 300 es\n";
        while (*vl && *vl != '\n') *vl++ = ' ';
    }
    char vhead[128], fhead[512];
    snprintf(vhead, sizeof vhead, "%s#define VERTEX\n", ver);
    snprintf(fhead, sizeof fhead, "%s#define FRAGMENT\n#ifdef GL_ES\n#ifdef GL_FRAGMENT_PRECISION_HIGH\n"
                        "precision highp float;\n#else\nprecision mediump float;\n#endif\n#endif\n#define PARAMETER_UNIFORM\n", ver);
    GLuint prog = glCreateProgram();
    glAttachShader(prog, compile(GL_VERTEX_SHADER, vhead, body));
    glAttachShader(prog, compile(GL_FRAGMENT_SHADER, fhead, body));
    glBindAttribLocation(prog, 0, "VertexCoord");
    glBindAttribLocation(prog, 1, "TexCoord");
    glLinkProgram(prog);
    GLint ok;
    glGetProgramiv(prog, GL_LINK_STATUS, &ok);
    if (!ok) { char log[4096]; glGetProgramInfoLog(prog, sizeof log, NULL, log); fprintf(stderr, "link: %s\n", log); return 1; }
    glUseProgram(prog);

    /* The game frame: SRCW x SRCH RGB, uploaded as RGBA every frame as the core hands it over. */
    unsigned char *rgb;
    if (!strcmp(argv[2], "-")) {
        /* Game Boy greys in 8x8 blocks, when no frame is given. */
        rgb = malloc(SRCW * SRCH * 3);
        static const unsigned char grey[4] = {255, 165, 82, 0};
        for (int i = 0; i < SRCW * SRCH; i++) {
            int x = i % SRCW, y = i / SRCW;
            rgb[i * 3] = rgb[i * 3 + 1] = rgb[i * 3 + 2] = grey[((x / 8) + (y / 8) * 3 + (x * y / 97)) & 3];
        }
    } else rgb = (unsigned char *)slurp(argv[2]);
    unsigned char *frame = malloc(SRCW * SRCH * 4);
    for (int i = 0; i < SRCW * SRCH; i++) {
        frame[i * 4] = rgb[i * 3]; frame[i * 4 + 1] = rgb[i * 3 + 1]; frame[i * 4 + 2] = rgb[i * 3 + 2]; frame[i * 4 + 3] = 255;
    }
    GLuint tex, outs[2], fbos[2];
    glGenTextures(1, &tex);
    glActiveTexture(GL_TEXTURE0);
    glBindTexture(GL_TEXTURE_2D, tex);
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, SRCW, SRCH, 0, GL_RGBA, GL_UNSIGNED_BYTE, frame);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE);
    glGenTextures(2, outs);
    glGenFramebuffers(2, fbos);
    for (int k = 0; k < 2; k++) {
        glBindTexture(GL_TEXTURE_2D, outs[k]);
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, W, H, 0, GL_RGBA, GL_UNSIGNED_BYTE, NULL);
        glBindFramebuffer(GL_FRAMEBUFFER, fbos[k]);
        glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, outs[k], 0);
        if (glCheckFramebufferStatus(GL_FRAMEBUFFER) != GL_FRAMEBUFFER_COMPLETE) { fprintf(stderr, "fbo incomplete\n"); return 1; }
    }
    glBindTexture(GL_TEXTURE_2D, tex);
    glViewport(0, 0, W, H);

    static const GLfloat quad[] = {-1, 1, 0, 1, 0, 1, 0, 0, -1, -1, 0, 1, 0, 0, 0, 0,
                                   1, 1, 0, 1, 1, 1, 0, 0, 1, -1, 0, 1, 1, 0, 0, 0};
    glVertexAttribPointer(0, 4, GL_FLOAT, 0, 32, quad);
    glVertexAttribPointer(1, 4, GL_FLOAT, 0, 32, quad + 4);
    glEnableVertexAttribArray(0);
    glEnableVertexAttribArray(1);
    GLint u;
    if ((u = glGetUniformLocation(prog, "Texture")) >= 0) glUniform1i(u, 0);
    if ((u = glGetUniformLocation(prog, "TextureSize")) >= 0) glUniform2f(u, SRCW, SRCH);
    if ((u = glGetUniformLocation(prog, "InputSize")) >= 0) glUniform2f(u, SRCW, SRCH);
    if ((u = glGetUniformLocation(prog, "OutputSize")) >= 0) glUniform2f(u, W, H);
    for (int k = 0; k < np; k++)
        if ((u = glGetUniformLocation(prog, pname[k])) >= 0) glUniform1f(u, pval[k]);
    /* What NextUI also hands every pass (generic_video.c). */
    static const GLfloat identity[16] = {1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1};
    if ((u = glGetUniformLocation(prog, "MVPMatrix")) >= 0) glUniformMatrix4fv(u, 1, 0, identity);
    if ((u = glGetUniformLocation(prog, "FrameDirection")) >= 0) glUniform1i(u, 1);
    if ((u = glGetUniformLocation(prog, "OrigTexture")) >= 0) glUniform1i(u, 0);
    if ((u = glGetUniformLocation(prog, "OrigTextureSize")) >= 0) glUniform2f(u, SRCW, SRCH);
    if ((u = glGetUniformLocation(prog, "OrigInputSize")) >= 0) glUniform2f(u, SRCW, SRCH);
    GLint frame_count = glGetUniformLocation(prog, "FrameCount");

    #define draw(i) do { \
        glBindTexture(GL_TEXTURE_2D, tex); \
        glTexSubImage2D(GL_TEXTURE_2D, 0, 0, 0, SRCW, SRCH, GL_RGBA, GL_UNSIGNED_BYTE, frame); \
        if (pre) { \
            glUseProgram(pprog); glViewport(0, 0, SRCW, SRCH); \
            glBindFramebuffer(GL_FRAMEBUFFER, pre_fbo); glClear(GL_COLOR_BUFFER_BIT); \
            glDrawArrays(GL_TRIANGLE_STRIP, 0, 4); glFlush(); \
            glBindTexture(GL_TEXTURE_2D, pre_tex); \
        } \
        glUseProgram(prog); glViewport(0, 0, W, H); \
        glBindFramebuffer(GL_FRAMEBUFFER, fbos[(i) & 1]); \
        glClear(GL_COLOR_BUFFER_BIT); \
        glDrawArrays(GL_TRIANGLE_STRIP, 0, 4); \
        if (SW) { \
            glFlush(); \
            glBindFramebuffer(GL_FRAMEBUFFER, screen_fbo); glClear(GL_COLOR_BUFFER_BIT); \
            glUseProgram(cprog); glBindTexture(GL_TEXTURE_2D, outs[(i) & 1]); \
            glViewport((SW - W) / 2, (SH - H) / 2, W, H); glDrawArrays(GL_TRIANGLE_STRIP, 0, 4); \
            if (overlay) { \
                glEnable(GL_BLEND); glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA); \
                glBindTexture(GL_TEXTURE_2D, ov_tex); glViewport(0, 0, SW, SH); \
                glDrawArrays(GL_TRIANGLE_STRIP, 0, 4); glDisable(GL_BLEND); \
            } \
        } \
        glFlush(); \
    } while (0)

    /* NextUI's last steps: the pass's output copied to the screen at its place, then the
     * overlay alpha-blended over the whole screen (generic_video.c, overlay.glsl). */
    static const char *copysrc =
        "#ifdef VERTEX\nattribute vec2 VertexCoord; attribute vec2 TexCoord; varying vec2 vTexCoord;\n"
        "void main() { vTexCoord = TexCoord; gl_Position = vec4(VertexCoord, 0.0, 1.0); }\n#endif\n"
        "#ifdef FRAGMENT\nprecision mediump float; uniform sampler2D Texture; varying vec2 vTexCoord;\n"
        "void main() { gl_FragColor = texture2D(Texture, vec2(vTexCoord.x, 1.0 - vTexCoord.y)); }\n#endif\n";
    GLuint cprog = 0, screen_tex = 0, screen_fbo = 0, ov_tex = 0, pprog = 0, pre_tex = 0, pre_fbo = 0;
    if (pre) {
        /* A first pass at the game's size, as NextUI runs a pass at upscale 1; the main pass
         * then reads its output, filtered LINEAR. */
        int keep_np = np;
        char *pbody = clean(slurp(pre));
        np = keep_np;
        for (char *pv = strstr(pbody, "#version"); pv && *pv && *pv != '\n'; ) *pv++ = ' ';
        pprog = glCreateProgram();
        glAttachShader(pprog, compile(GL_VERTEX_SHADER, vhead, pbody));
        glAttachShader(pprog, compile(GL_FRAGMENT_SHADER, fhead, pbody));
        glBindAttribLocation(pprog, 0, "VertexCoord");
        glBindAttribLocation(pprog, 1, "TexCoord");
        glLinkProgram(pprog);
        glGetProgramiv(pprog, GL_LINK_STATUS, &ok);
        if (!ok) { fprintf(stderr, "pre link failed\n"); return 1; }
        glUseProgram(pprog);
        if ((u = glGetUniformLocation(pprog, "Texture")) >= 0) glUniform1i(u, 0);
        if ((u = glGetUniformLocation(pprog, "TextureSize")) >= 0) glUniform2f(u, SRCW, SRCH);
        if ((u = glGetUniformLocation(pprog, "InputSize")) >= 0) glUniform2f(u, SRCW, SRCH);
        if ((u = glGetUniformLocation(pprog, "OutputSize")) >= 0) glUniform2f(u, SRCW, SRCH);
        for (int k = 0; k < np; k++)
            if ((u = glGetUniformLocation(pprog, pname[k])) >= 0) glUniform1f(u, pval[k]);
        glGenTextures(1, &pre_tex);
        glBindTexture(GL_TEXTURE_2D, pre_tex);
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, SRCW, SRCH, 0, GL_RGBA, GL_UNSIGNED_BYTE, NULL);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE);
        glGenFramebuffers(1, &pre_fbo);
        glBindFramebuffer(GL_FRAMEBUFFER, pre_fbo);
        glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, pre_tex, 0);
        if (glCheckFramebufferStatus(GL_FRAMEBUFFER) != GL_FRAMEBUFFER_COMPLETE) { fprintf(stderr, "pre fbo incomplete\n"); return 1; }
        glUseProgram(prog);
    }
    if (SW) {
        cprog = glCreateProgram();
        glAttachShader(cprog, compile(GL_VERTEX_SHADER, "#version 100\n#define VERTEX\n", copysrc));
        glAttachShader(cprog, compile(GL_FRAGMENT_SHADER, "#version 100\n#define FRAGMENT\n", copysrc));
        glBindAttribLocation(cprog, 0, "VertexCoord");
        glBindAttribLocation(cprog, 1, "TexCoord");
        glLinkProgram(cprog);
        glGenTextures(1, &screen_tex);
        glBindTexture(GL_TEXTURE_2D, screen_tex);
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, SW, SH, 0, GL_RGBA, GL_UNSIGNED_BYTE, NULL);
        glGenFramebuffers(1, &screen_fbo);
        glBindFramebuffer(GL_FRAMEBUFFER, screen_fbo);
        glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, screen_tex, 0);
        for (int k = 0; k < 2; k++) {
            glBindTexture(GL_TEXTURE_2D, outs[k]);
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);
        }
        if (overlay) {
            /* Opaque border, clear middle: the shape of a bezel overlay. */
            unsigned char *ov = calloc(SW * SH, 4);
            for (int y = 0; y < SH; y++) for (int x = 0; x < SW; x++) {
                unsigned char *p = ov + (y * SW + x) * 4;
                int border = x < (SW - W) / 2 || x >= (SW + W) / 2 || y < (SH - H) / 2 || y >= (SH + H) / 2;
                p[0] = p[1] = p[2] = 60; p[3] = border ? 255 : (x + y) & 15;
            }
            glGenTextures(1, &ov_tex);
            glBindTexture(GL_TEXTURE_2D, ov_tex);
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, SW, SH, 0, GL_RGBA, GL_UNSIGNED_BYTE, ov);
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);
        }
    }

    for (int i = 0; i < 30; i++) {
        draw(i);
    }
    glFinish();
    double best = 1e9;
    for (int rep = 0; rep < 3; rep++) {
        double t0 = now();
        for (int i = 0; i < frames; i++) {
            if (frame_count >= 0) glUniform1i(frame_count, i);
            draw(i);
        }
        unsigned char px[4];
        glReadPixels(W / 2, H / 2, 1, 1, GL_RGBA, GL_UNSIGNED_BYTE, px);
        glFinish();
        double ms = (now() - t0) / frames;
        if (rep == 2) fprintf(stderr, "centre pixel %d,%d,%d\n", px[0], px[1], px[2]);
        if (ms < best) best = ms;
    }
    if (dump) {
        int dw = SW ? SW : W, dh = SW ? SH : H;
        unsigned char *buf = malloc(dw * dh * 4);
        glBindFramebuffer(GL_FRAMEBUFFER, SW ? screen_fbo : fbos[(frames - 1) & 1]);
        glReadPixels(0, 0, dw, dh, GL_RGBA, GL_UNSIGNED_BYTE, buf);
        FILE *f = fopen(dump, "wb"); fwrite(buf, 4, dw * dh, f); fclose(f);
    }
    printf("%-28s %4dx%-4d %8.3f ms/frame  %6.1f%% of a 60 Hz frame   [%s]\n", strrchr(argv[1], '/') ? strrchr(argv[1], '/') + 1 : argv[1],
           W, H, best, best / (1000.0 / 60.0) * 100.0, (const char *)glGetString(GL_RENDERER));
    for (int k = 0; k < np; k++) fprintf(stderr, "  %s=%g", pname[k], pval[k]);
    fprintf(stderr, "\n");
    return 0;
}
