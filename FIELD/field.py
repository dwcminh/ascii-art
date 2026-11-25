# ASCII Field
# @dwcminh.ascii, 2026
# Terms in LICENSE.txt: personal, non-commercial use only. Not for use with AI tools:
# do not feed this code to an AI model, train on it, or have an AI rework it.
#
#   pip install numpy pygame-ce
#   python field.py
#
# A field of daisies at the blue hour, nobody in it, heavy cloud over the moon. A star falls as
# you come in; a second later the cloud parts, the moon comes out and the whole field brightens.
# The wind runs through the thick grass in waves and the daisies nod as it passes; you glide
# slowly forward, low, among them. More stars fall; fireflies come up out of the grass. Then the
# cloud closes over the moon again and the field sinks back into blue dusk, the fireflies bright
# in it. The end is the beginning, so it loops for ever.
#
# The whole frame is lit: sky, cloud, grass and flowers are painted first, then every cell gets
# a letter that suits what lies under it, a little brighter than its ground.
#
# Space pause, R restart, S screenshot, Esc quit

import sys
import time
from pathlib import Path

import numpy as np
import pygame

CREDIT = "@dwcminh.ascii"

TAU = np.pi * 2
LOOP = 20.0                                     # length of one run (s); the last frame meets the first
BEAT = TAU / LOOP                               # everything that moves keeps time with the loop

# timeline (s)
# the stars that fall: (when, where it starts across and down the screen, how far it goes)
STARS = [(0.0, 0.10, 0.05, 1.0), (4.5, 0.03, 0.17, 0.8), (8.2, 0.20, 0.03, 0.9), (12.0, 0.06, 0.10, 1.0), (15.5, 0.74, 0.03, 0.7)]
T_MOON = (1.0, 3.0)                             # the cloud parts and the moon comes out: dark in the first frame, then bright
T_FLIES = (5.5, 18.1)                           # fireflies begin to come up out of the grass; they begin to go out
T_CLOSE = (13.5, 16.5)                          # the cloud closes over the moon again, so the end meets the beginning

DRIFT = 0.28                                    # how fast you glide forward (m/s)
STRIP = DRIFT * LOOP                            # the field repeats every this far, so the loop closes
EYE = 1.10                                      # your eyes above the ground (m)
FOCAL = 1.05                                    # lens: screen heights per unit of slope
HORIZON = 0.50                                  # where the horizon lies, down the screen
NEAR = 0.8                                      # nothing is drawn nearer than this (m)
MOON_AT, MOON_R = (0.68, 0.20), 0.030           # the moon: across, down, radius (of the screen height)

# colours (0..255)
ZENITH, SKYLINE, HAZE = np.array([14, 34, 122]), np.array([64, 126, 236]), np.array([92, 140, 226])
CLOUD_DARK, CLOUD_LIT = np.array([12, 22, 66]), np.array([120, 160, 248])
MOON = np.array([236, 244, 255])
TREES = (7, 16, 34)
FIELD_FAR, FIELD_NEAR, FIELD_MOON = np.array([30, 66, 92]), np.array([18, 62, 40]), np.array([20, 70, 62])
GUST = np.array([70, 150, 120])                 # grass turned over by the wind
BLADE_DARK, BLADE_LIGHT = np.array([16, 70, 44]), np.array([70, 170, 110])
PETAL_DUSK, PETAL_MOON, PETAL_FAR = np.array([150, 178, 238]), np.array([240, 246, 255]), np.array([84, 118, 170])
HEART = np.array([232, 190, 60])                # the middle of a daisy
FIREFLY = np.array([214, 255, 120])
DIM, ACCENT, SIGN = (150, 170, 214), (255, 214, 120), (226, 234, 255)

POOLS = ["1il!;:", "rtfjcvxz=+", "aeoun0{}[]<>", "08B$#&%Q"]   # cloud letters, thin -> thick
SKY_POOL = " .  ' . : .  "                      # open sky: almost nothing
GRASS_POOLS = [".,'` .,' `,.", ",;:'\"!;,:i!'", "il|!/|li/|!/", "vyYwVWvYywWV"]
FLOWER_POOL = "*o*@*0*#*8*&"
TREE_TOP, TREE_BODY = "A", "#"
C = lambda ch: ord(ch) - 32                     # character -> glyph index
ramp = lambda pools: np.array([[C(p[k % len(p)]) for k in range(12)] for p in pools])
FILL, GRASS_FILL = ramp(POOLS), ramp(GRASS_POOLS)
SKY_FILL, FLOWER_FILL = ramp([SKY_POOL])[0], ramp([FLOWER_POOL])[0]

GROUND = 0.74                                   # how much of the painting shows under the letters
INK, INK_CLOUD, INK_GRASS = 0.50, 0.30, 0.36    # how bright the letters are over it; over cloud and petals; over grass


def smooth(x):
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3 - 2 * x)


def wind(x, z, t):
    # gusts crossing the field, 0..1; in time with the loop
    return 0.5 + 0.5 * np.sin(0.55 * x + 0.35 * z - 8 * BEAT * t + 1.4 * np.sin(0.13 * z + 2 * BEAT * t) + 0.9 * np.sin(0.21 * x - BEAT * t))


def moonlight(t):
    # 0 the moon behind cloud, 1 out: covered at first, soon out, covered again at the end
    return float(smooth((t - T_MOON[0]) / (T_MOON[1] - T_MOON[0])) * (1 - smooth((t - T_CLOSE[0]) / (T_CLOSE[1] - T_CLOSE[0]))))


def make_noise(n, beta, seed):
    # soft noise that tiles, every value from 0 to 1 equally often
    rng = np.random.default_rng(seed)
    f = np.fft.fftfreq(n)
    k = np.hypot(*np.meshgrid(f, f))
    k[0, 0] = 1.0
    img = np.fft.ifft2((rng.normal(size=(n, n)) + 1j * rng.normal(size=(n, n))) / k ** beta).real
    rank = np.empty(n * n)
    rank[np.argsort(img.ravel())] = np.linspace(0, 1, n * n)
    return rank.reshape(n, n)


TILE = 512
NOISE_A, NOISE_B = make_noise(TILE, 1.75, 4), make_noise(TILE, 1.55, 9)


def tex(noise, u, v):
    return noise[v.astype(int) & (TILE - 1), u.astype(int) & (TILE - 1)]


# what grows in the field: one strip of it, STRIP long, laid end to end as far as you can see

N_DAISIES, DAISY_TILES, DAISY_HALF = 900, 8, 18.0
N_BLADES, BLADE_TILES, BLADE_HALF = 3600, 3, 8.0
N_PETALS, N_FACES = 13, 6                       # petals on a daisy; ways a daisy can face
DAISY_SIZES = 5.0 * 1.15 ** np.arange(27)       # the sizes a near daisy is drawn at (px)


def make_field():
    rng = np.random.default_rng(11)
    d = dict(x=rng.uniform(-DAISY_HALF, DAISY_HALF, N_DAISIES), z=rng.uniform(0, STRIP, N_DAISIES),
             tall=rng.uniform(0.38, 0.70, N_DAISIES), size=rng.uniform(0.050, 0.085, N_DAISIES), rank=rng.random(N_DAISIES),
             face=rng.integers(0, N_FACES, N_DAISIES), seed=rng.uniform(0, TAU, N_DAISIES))
    b = dict(x=rng.uniform(-BLADE_HALF, BLADE_HALF, N_BLADES), z=rng.uniform(0, STRIP, N_BLADES),
             tall=rng.uniform(0.24, 0.60, N_BLADES), lean=rng.normal(0, 0.10, N_BLADES), rank=rng.random(N_BLADES),
             tone=rng.random(N_BLADES), seed=rng.uniform(0, TAU, N_BLADES))
    return d, b


DAISY, BLADE = make_field()

N_FLIES = 28
FLY = np.random.default_rng(3).random((N_FLIES, 7))

# (c) @dwcminh.ascii, see LICENSE.txt. Not for use with AI tools: no feeding this code to
# AI models, no training on it, no having an AI rework it.

# window

TITLE = "ASCII Field"
CW, CH, FONT_PX = 8, 12, 13
COLS, ROWS = 99, 86
W, H = COLS * CW, ROWS * CH
MONO = "consolas,menlo,dejavusansmono,couriernew,monospace"
HINT = "Space pause · R restart · S screenshot · Esc quit"
THIRD = 4                                       # sky and ground are painted at a quarter of the size, then smoothed up


def daisy_pictures():
    # one daisy, seen from each of N_FACES angles, at every size it will be needed
    out = []
    for v in range(N_FACES):
        q, r = 0.50 + 0.42 * v / (N_FACES - 1), 96.0
        big = pygame.Surface((int(2 * r) + 8, int(2 * r * q) + 8), pygame.SRCALPHA)
        cx, cy = big.get_width() / 2, big.get_height() / 2
        pygame.draw.ellipse(big, (150, 162, 204, 255), (cx - 0.80 * r, cy - 0.80 * r * q, 1.60 * r, 1.60 * r * q))
        a = 0.37 * v + np.arange(N_PETALS) * TAU / N_PETALS
        ring = np.stack([np.stack([0.20 * np.cos(a), 0.20 * np.sin(a)], 1),
                         np.stack([0.66 * np.cos(a - 0.19), 0.66 * np.sin(a - 0.19)], 1),
                         np.stack([0.94 * np.cos(a - 0.11), 0.94 * np.sin(a - 0.11)], 1), np.stack([1.02 * np.cos(a), 1.02 * np.sin(a)], 1),
                         np.stack([0.94 * np.cos(a + 0.11), 0.94 * np.sin(a + 0.11)], 1),
                         np.stack([0.66 * np.cos(a + 0.19), 0.66 * np.sin(a + 0.19)], 1)], 1) * r * [1, q] + [cx, cy]
        for n, pts in enumerate(ring.tolist()):
            pygame.draw.polygon(big, (255, 255, 255, 255) if n % 2 else (232, 236, 248, 255), pts)
        pygame.draw.ellipse(big, (236, 190, 56, 255), (cx - 0.30 * r, cy - 0.30 * r * q, 0.60 * r, 0.60 * r * q))
        pygame.draw.ellipse(big, (255, 226, 120, 255), (cx - 0.17 * r, cy - 0.24 * r * q, 0.26 * r, 0.24 * r * q))
        out.append([pygame.transform.smoothscale(big, (max(3, int(big.get_width() * k / r)), max(3, int(big.get_height() * k / r))))
                    for k in DAISY_SIZES])
    return out


class Renderer:
    def __init__(self, cols=COLS, rows=ROWS, cw=CW, ch=CH, font_px=FONT_PX, hud_px=15, hint=True):
        self.cols, self.rows, self.cw, self.ch = cols, rows, cw, ch
        self.w, self.h = w, h = cols * cw, rows * ch
        font = pygame.font.SysFont(MONO, font_px)
        atlas = []
        for code in range(32, 127):
            s = pygame.Surface((cw, ch))
            g = font.render(chr(code), True, (255, 255, 255))
            s.blit(g, ((cw - g.get_width()) // 2, (ch - g.get_height()) // 2))
            atlas.append(pygame.surfarray.array3d(s).transpose(1, 0, 2))
        self.atlas = np.stack(atlas)                            # glyph, CH, CW, 3
        self.scene = pygame.Surface((w, h))
        self.art = pygame.Surface((w, h))
        self.out = pygame.Surface((w, h))
        self.small = pygame.font.SysFont(MONO, hud_px)
        self.hud_gap = int(hud_px * 1.45)
        self.hint = hint
        self.hash = np.random.default_rng(1).integers(0, 9973, (rows, cols))
        self.daisies, self.tinted = daisy_pictures(), {}
        d = np.hypot(*np.meshgrid(np.linspace(-1, 1, 64), np.linspace(-1, 1, 64)))
        halo = np.clip(1 - d, 0, 1) ** 1.8 * 0.85 + np.clip(1 - d / 0.20, 0, 1)                 # a soft glow, and a hot core
        self.halo = pygame.surfarray.make_surface((np.clip(halo, 0, 1)[..., None] * [255, 255, 255]).astype(np.uint8))

        # the lens
        self.f, self.yh = FOCAL * h, HORIZON * h
        self.moon = np.array([MOON_AT[0] * w, MOON_AT[1] * h])
        # a grid a third the size: for every point of it, where it looks
        self.tw, self.th = w // THIRD, h // THIRD
        px, py = (np.arange(self.tw) + 0.5) * THIRD, (np.arange(self.th) + 0.5) * THIRD
        self.n_sky = n = int((py < self.yh).sum())
        far = 1.0 / ((self.yh - py[:n]) / self.f + 0.035)       # the cloud is a ceiling: how far off each row meets it
        self.cloud_u = ((px - w / 2) / self.f)[None] * far[:, None] * 210.0
        self.cloud_v = np.broadcast_to(far[:, None] * 210.0, self.cloud_u.shape)
        self.sky_up = ((self.yh - py[:n]) / self.yh)[:, None]   # 0 at the horizon, 1 at the top
        self.moon_far = np.hypot(px[None] - self.moon[0], py[:n, None] - self.moon[1]) / h
        zg = np.minimum(self.f * EYE / np.maximum(py[n:] - self.yh, 0.5), 120.0)    # the ground: how far off each row is
        self.ground_x = ((px - w / 2) / self.f)[None] * zg[:, None]
        self.ground_z = np.broadcast_to(zg[:, None], self.ground_x.shape)
        # the same, for every cell
        self.cell_x = np.clip(((np.arange(cols) + 0.5) * cw / THIRD).astype(int), 0, self.tw - 1)
        self.cell_y = np.clip(((np.arange(rows) + 0.5) * ch / THIRD).astype(int), 0, self.th - 1)
        self.sky_cells = int(np.ceil(self.yh / ch - 0.5))

        # trees along the horizon: a dark line of firs
        rng = np.random.default_rng(6)
        x = np.arange(0, w + 4, 4)
        top = 0.012 * h + 0.016 * h * tex(NOISE_A, x * 0.9, x * 0 + 77)
        for at, tall, wide in zip(rng.uniform(0, w, 150), rng.uniform(0.006, 0.030, 150) * h, rng.uniform(5, 12, 150) * w / 792):
            top = np.maximum(top, tall * 1.6 * np.clip(1 - np.abs(x - at) / wide, 0, 1) + 0.010 * h * (np.abs(x - at) < wide))
        self.tree_top = self.yh - top
        self.tree_shape = [(0, self.yh + 3)] + list(zip(x.tolist(), self.tree_top.tolist())) + [(w, self.yh + 3)]
        cell_top = np.interp((np.arange(cols) + 0.5) * cw, x, self.tree_top)
        cy = (np.arange(rows)[:, None] + 0.5) * ch
        self.tree_cells = (cy > cell_top[None] - ch * 0.2) & (cy < self.yh + 3)
        self.tree_crown = self.tree_cells & ~np.roll(self.tree_cells, 1, 0)

    # sky and ground: painted small, with numpy

    def backdrop(self, t, light):
        n, w, h = self.n_sky, self.w, self.h
        img = np.empty((self.th, self.tw, 3), np.float32)
        # cloud: two layers of noise sliding at their own speed over a ceiling seen in perspective
        slide = TILE * t / LOOP
        u, v = self.cloud_u, self.cloud_v
        dense = 0.68 * tex(NOISE_A, u + slide, v + 2 * slide) + 0.32 * tex(NOISE_B, 2.1 * u + 3 * slide + 37, 2.1 * v + 5 * slide + 91)
        toward = 0.68 * tex(NOISE_A, u + slide + 16, v + 2 * slide - 16) + 0.32 * tex(NOISE_B, 2.1 * (u + 16) + 3 * slide + 37, 2.1 * (v - 16) + 5 * slide + 91)
        gap = np.exp(-(self.moon_far / 0.13) ** 2)              # round the moon it is thick at first, then it parts
        cover = smooth((dense - 0.40 - gap * (0.62 * light - 0.30 * (1 - light))) / 0.20)
        lit = np.clip(0.42 + 4.5 * (dense - toward), 0, 1) * (0.55 + 0.45 * light) + 0.45 * (1 - smooth((dense - 0.40) / 0.45))
        lit = np.clip(lit + 0.9 * light * np.exp(-(self.moon_far / 0.20) ** 2), 0, 1)
        self.cover, self.lit = cover, lit
        clear = ZENITH + (SKYLINE - ZENITH) * ((1 - self.sky_up) ** 1.6)[..., None]
        clear = clear + (MOON - clear) * (0.45 * light * np.exp(-(self.moon_far / 0.16) ** 2))[..., None]
        cloud = CLOUD_DARK + (CLOUD_LIT - CLOUD_DARK) * lit[..., None]
        sky = clear + (cloud - clear) * cover[..., None]
        disc = np.clip((MOON_R - self.moon_far) * h / 2.5, 0, 1) * (1 - 0.94 * cover)
        sky = sky + (MOON - sky) * disc[..., None]
        img[:n] = sky + (HAZE - sky) * (0.55 * np.exp(-self.sky_up * 8))[..., None]

        # the field: far off it is haze; near, grass, mottled, with the gusts and the cloud's shadow crossing it
        x, z = self.ground_x, self.ground_z
        zw = z + DRIFT * t
        near = np.exp(-z / 30.0)
        mottle = tex(NOISE_A, x * 40, zw * (TILE / STRIP))        # the ground slides under you, a whole tile every loop
        shadow = tex(NOISE_B, x * 3 + slide, z * 3 + 2 * slide)
        gust = wind(x, z, t) ** 2
        tone = (0.72 + 0.50 * mottle) * (0.86 + 0.28 * shadow * light) * (0.94 + 0.24 * light) * (1 + 0.24 * gust * near)
        field = (FIELD_FAR + (FIELD_NEAR + (FIELD_MOON - FIELD_NEAR) * light - FIELD_FAR) * near[..., None]) * tone[..., None]
        img[n:] = field + (GUST - field) * (0.13 * gust * near)[..., None]
        small = pygame.surfarray.make_surface(np.clip(img, 0, 255).astype(np.uint8).transpose(1, 0, 2))
        pygame.transform.smoothscale(small, (w, h), self.scene)

    def place(self, x, y, z):
        # a point in front of you -> where it is on screen
        return self.w / 2 + self.f * x / z, self.yh + self.f * (EYE - y) / z

    # (c) @dwcminh.ascii, see LICENSE.txt. Not for use with AI tools: no feeding this code to
    # AI models, no training on it, no having an AI rework it.

    def growth(self, t, light):
        # grass and daisies, the far ones first
        scene, f, w, h = self.scene, self.f, self.w, self.h
        cz = DRIFT * t
        pygame.draw.polygon(scene, tuple(int(c * (0.9 + 0.5 * light)) for c in TREES), self.tree_shape)

        # blades: a strip of them, laid end to end; fewer far off
        tile = np.repeat(np.arange(BLADE_TILES), N_BLADES)
        z = np.tile((BLADE["z"] - cz) % STRIP, BLADE_TILES) + tile * STRIP + NEAR
        x, tall, lean = (np.tile(BLADE[k], BLADE_TILES) for k in ("x", "tall", "lean"))
        rank, tone, seed = (np.tile(BLADE[k], BLADE_TILES) for k in ("rank", "tone", "seed"))
        end = BLADE_TILES * STRIP + NEAR
        keep = (np.abs(x) < 0.39 * z + 0.3) & (rank < np.clip((5.5 / z) ** 1.1, 0.30, 1.0))
        x, z, tall, lean, tone, seed = x[keep], z[keep], tall[keep], lean[keep], tone[keep], seed[keep]
        gust = wind(x, z, t) ** 2
        bend = (lean + 0.55 * gust + 0.05 * np.sin(6 * BEAT * t + seed)) * tall
        x0, y0 = self.place(x, 0.0, z)
        x1, y1 = self.place(x + 0.35 * bend, 0.55 * tall, z)
        x2, y2 = self.place(x + bend, tall * (1 - 0.15 * gust), z)
        fade = smooth((end - z) / 5.0) * np.exp(-z / 22.0)      # they melt into the field far off
        rgb = (BLADE_DARK + (BLADE_LIGHT - BLADE_DARK) * (tone * (0.35 + 0.65 * gust))[:, None]) * (0.80 + 0.32 * light)
        base = FIELD_FAR + (FIELD_NEAR - FIELD_FAR) * np.exp(-z / 30.0)[:, None]
        rgb = np.clip(base + (rgb - base) * fade[:, None], 0, 255).astype(int)
        wide = np.clip(f * 0.010 / z, 1, 6).astype(int)
        order = np.argsort(-z)
        blades = [(z_, c, [a, b, d], w_) for z_, c, a, b, d, w_ in zip(
            z[order].tolist(), rgb[order].tolist(), zip(x0[order].tolist(), y0[order].tolist()),
            zip(x1[order].tolist(), y1[order].tolist()), zip(x2[order].tolist(), y2[order].tolist()), wide[order].tolist())]

        # daisies: each on its stalk, nodding in the gust that is passing; more of them near you
        tile = np.repeat(np.arange(DAISY_TILES), N_DAISIES)
        z = np.tile((DAISY["z"] - cz) % STRIP, DAISY_TILES) + tile * STRIP + NEAR
        x, tall, size, face, rank, seed = (np.tile(DAISY[k], DAISY_TILES) for k in ("x", "tall", "size", "face", "rank", "seed"))
        keep = (np.abs(x) < 0.39 * z + 0.25) & (rank < np.clip(7.0 / z, 0.30, 1.0))
        x, z, tall, size, face, seed = x[keep], z[keep], tall[keep], size[keep], face[keep], seed[keep]
        gust = wind(x, z, t) ** 2
        nod = 0.03 * np.sin(4 * BEAT * t + seed) + 0.13 * gust
        hx, hy = self.place(x + nod, tall - 0.04 * gust, z)
        fx, fy = self.place(x, 0.0, z)
        r = f * size / z
        near = np.round(np.exp(-z / 16.0) * 6)[:, None] / 6     # in a few steps, so the pictures can be kept
        petal = PETAL_FAR + ((PETAL_DUSK + (PETAL_MOON - PETAL_DUSK) * round(light * 10) / 10) - PETAL_FAR) * near
        self.heads = (hx, hy, r, petal)                         # the letters want to know where they are
        # the far ones are a point each, or four
        px = pygame.surfarray.pixels3d(scene)
        for lo, hi, spots in ((0.0, 1.1, ((0, 0),)), (1.1, 2.2, ((0, 0), (1, 0), (0, 1), (1, 1)))):
            far = (r >= lo) & (r < hi) & (hx >= 0) & (hx < w - 1) & (hy >= 0) & (hy < h - 1)
            ix, iy = hx[far].astype(int), hy[far].astype(int)
            dot = np.clip(petal[far] * np.clip(r[far] / 1.1, 0.45, 1)[:, None], 0, 255).astype(np.uint8)
            for dx, dy in spots:
                px[ix + dx, iy + dy] = dot
        del px
        big = np.flatnonzero((r >= 2.2) & (hx > -150) & (hx < w + 150) & (hy < h + 150))
        big = big[np.argsort(-z[big])]
        level = np.clip(np.round(np.log(np.maximum(r[big], 1) / DAISY_SIZES[0]) / np.log(1.15)), 0, len(DAISY_SIZES) - 1).astype(int)
        n_blade = 0
        for zi, ri, cx, cy, gx, gy, col, v, l in zip(z[big].tolist(), r[big].tolist(), hx[big].tolist(), hy[big].tolist(), fx[big].tolist(),
                                                     fy[big].tolist(), petal[big].astype(int).tolist(), face[big].tolist(), level.tolist()):
            while n_blade < len(blades) and blades[n_blade][0] > zi:        # the grass behind it first
                _, c, pts, w_ = blades[n_blade]
                pygame.draw.lines(scene, c, False, pts, w_)
                n_blade += 1
            if ri < 5.0:                                        # a small one: a white dot, a gold one in it
                pygame.draw.circle(scene, col, (cx, cy), int(ri + 0.5))
                if ri > 3.2:
                    pygame.draw.circle(scene, (200, 164, 52), (cx, cy), int(ri * 0.36))
                continue
            pygame.draw.line(scene, (24, 92, 56), (cx, cy), (gx, gy), max(2, int(ri / 6)))       # a near one: its stalk, and its picture
            key = (v, l, col[0], col[1], col[2])
            if key not in self.tinted:
                if len(self.tinted) > 9000:
                    self.tinted.clear()
                pic = self.daisies[v][l].copy()
                pic.fill((col[0], col[1], col[2], 255), special_flags=pygame.BLEND_RGBA_MULT)
                self.tinted[key] = pic
            pic = self.tinted[key]
            scene.blit(pic, (cx - pic.get_width() / 2, cy - pic.get_height() / 2))
        for _, c, pts, w_ in blades[n_blade:]:                  # and the grass nearer than any daisy
            pygame.draw.lines(scene, c, False, pts, w_)
        return int((r >= 1.1).sum())

    def lights(self, t):
        # fireflies coming up out of the grass, and the falling stars: light, added to the picture
        scene, f, h = self.scene, self.f, self.h
        here = smooth((t - T_FLIES[0] - 2.5 * FLY[:, 6]) / 1.5) * (1 - smooth((t - T_FLIES[1] - 0.8 * FLY[:, 6]) / 1.0))
        x = (FLY[:, 0] - 0.5) * 9 + 0.6 * np.sin(2 * BEAT * t + FLY[:, 1] * TAU)
        z = 1.8 + 14 * FLY[:, 2] ** 1.6 + 0.5 * np.cos(BEAT * t + FLY[:, 3] * TAU)
        y = (0.20 + 0.75 * FLY[:, 4]) * here + 0.14 * np.sin(3 * BEAT * t + FLY[:, 5] * TAU)
        glow = here * np.clip(0.55 + 0.6 * np.sin(7 * BEAT * t + FLY[:, 5] * 40), 0, 1)
        sx, sy = self.place(x, y, z)
        self.sparks = []
        for a, b, g, zi in zip(sx.tolist(), sy.tolist(), glow.tolist(), z.tolist()):
            if g > 0.08:
                self.spark(a, b, float(np.clip(f * 0.20 / zi, 20, 84)), FIREFLY * g)
        step = np.array([0.34, 0.15]) * h * 0.024             # a falling star: which way, and one piece of its tail
        for t0, across, down, far in STARS:
            age = (t - t0) / 0.8
            if 0 <= age < 1:
                a = np.array([across * self.w, down * h]) + step / 0.024 * far * age
                tail = pygame.Surface(scene.get_size())
                for k in range(14):                             # head first, the tail fading behind it
                    pygame.draw.line(tail, tuple(int(c * (1 - age) ** 0.5 * (1 - k / 14) ** 1.5) for c in (235, 240, 255)),
                                     a - step * k, a - step * (k + 1), 3 if k < 5 else 2)
                scene.blit(tail, (0, 0), special_flags=pygame.BLEND_ADD)
                self.spark(float(a[0]), float(a[1]), 34.0, np.array([235, 240, 255]) * (1 - age) ** 0.5)

    def spark(self, x, y, size, rgb):
        # a soft point of light
        key = (int(size / 4), tuple((np.asarray(rgb) // 16).astype(int).tolist()))
        if key not in self.tinted:
            pic = pygame.transform.smoothscale(self.halo, (key[0] * 4 + 4,) * 2)
            pic.fill(tuple(min(255, c * 16 + 8) for c in key[1]), special_flags=pygame.BLEND_MULT)
            self.tinted[key] = pic
        pic = self.tinted[key]
        self.scene.blit(pic, (x - pic.get_width() / 2, y - pic.get_height() / 2), special_flags=pygame.BLEND_ADD)
        self.sparks.append((x, y, float(np.max(rgb)) / 255.0))

    # the letters: one for every cell, chosen by what the painting shows there

    def letters(self, t, cell):
        cols, rows, h_ = self.cols, self.rows, self.hash
        lum = cell @ np.array([0.30, 0.55, 0.15])
        slow, quick = (h_ + int(t * 1.8)) % 12, (h_ + (t * 4.2 + h_ % 11).astype(int)) % 12       # both come round with the loop
        char = np.zeros((rows, cols), int)
        # sky: open sky is nearly bare, cloud is letters, thicker where it is lit
        n = self.sky_cells
        cover = self.cover[np.minimum(self.cell_y[:n], self.n_sky - 1)][:, self.cell_x]
        lit = self.lit[np.minimum(self.cell_y[:n], self.n_sky - 1)][:, self.cell_x]
        level = np.clip(((lit - 0.18) * 4.4).astype(int), 0, 3)
        char[:n] = np.where(cover > 0.45, FILL[level, slow[:n]], SKY_FILL[slow[:n]])
        ink = np.full((rows, cols), INK)
        ink[:n] = np.where(cover > 0.45, INK_CLOUD, INK)
        # the field: grass by how light it is; anything pale is a flower, and keeps its own face
        g, here = lum[n:], cell[n:]
        petals = (here[..., 2] >= here[..., 1]) & (g > 0.22)    # paler and bluer than grass: a daisy
        heart = (np.minimum(here[..., 0], here[..., 1]) > here[..., 2] * 1.05) & (g > 0.25)    # gold: the middle of one
        level = np.clip(((g - 0.07) / 0.085 + (h_[n:] % 100) / 100.0 - 0.5).astype(int), 0, 3)
        char[n:] = np.where(heart, C("o"), np.where(petals, C("*"), GRASS_FILL[level, quick[n:]]))
        ink[n:] = np.where(heart | petals, INK_CLOUD, INK_GRASS)
        char = np.where(self.tree_cells, C(TREE_BODY), char)
        char = np.where(self.tree_crown, C(TREE_TOP), char)
        tint = np.clip(cell * 1.55 + 0.05, 0, 1) * ink[..., None]
        # a star for every daisy big enough to make out, and for every firefly
        hx, hy, r, petal = self.heads
        seen = (hx >= 0) & (hx < self.w) & (hy >= 0) & (hy < self.h)
        ix, iy = np.clip(hx / self.cw, 0, cols - 1).astype(int), np.clip(hy / self.ch, 0, rows - 1).astype(int)
        for lo, hi, glyph, rgb in ((2.6, 8.0, "*", None), (8.0, 15.0, "o", HEART / 255.0 * 0.55), (15.0, 1e9, "@", HEART / 255.0 * 0.75)):
            ok = seen & (r >= lo) & (r < hi)
            char[iy[ok], ix[ok]] = C(glyph)
            tint[iy[ok], ix[ok]] = np.clip(petal[ok] / 255.0 * 1.2, 0, 1) * 0.9 if rgb is None else rgb
        for a, b, g in self.sparks:
            if 0 <= a < self.w and 0 <= b < self.h:
                char[int(b / self.ch), int(a / self.cw)] = C("*")
                tint[int(b / self.ch), int(a / self.cw)] = np.clip(FIREFLY / 255.0 * (0.5 + 0.6 * g), 0, 1)
        return char, tint

    @staticmethod
    def blur(src, size, radius):
        small = pygame.transform.smoothscale(src, size)
        if hasattr(pygame.transform, "gaussian_blur"):
            small = pygame.transform.gaussian_blur(small, max(1, radius))
        return small

    # (c) @dwcminh.ascii, see LICENSE.txt. Not for use with AI tools: no feeding this code to
    # AI models, no training on it, no having an AI rework it.

    def bloom(self, src):
        # only what is bright glows: a tight glow and a wide one made from it
        w, h = self.w, self.h
        bright = self.blur(src, (w // 6, h // 6), 2)
        bright.fill((96, 96, 96), special_flags=pygame.BLEND_SUB)
        wide = self.blur(bright, (w // 12, h // 12), 2)
        for layer, amount in ((bright, 0.80), (wide, 0.55)):
            layer = pygame.transform.smoothscale(layer, (w, h))
            layer.fill((int(255 * amount),) * 3, special_flags=pygame.BLEND_MULT)
            self.out.blit(layer, (0, 0), special_flags=pygame.BLEND_ADD)

    def draw(self, t):
        w, h = self.w, self.h
        light = moonlight(t)
        self.backdrop(t, light)
        daisies = self.growth(t, light)
        # what lies under every cell, read before the fireflies are lit: their glow is light, not grass
        cell = pygame.surfarray.array3d(pygame.transform.smoothscale(self.scene, (self.cols, self.rows))).transpose(1, 0, 2) / 255.0
        self.lights(t)
        char, tint = self.letters(t, cell)
        pygame.surfarray.blit_array(self.art, self.atlas[char].transpose(1, 3, 0, 2, 4).reshape(w, h, 3))
        ink = pygame.surfarray.make_surface((tint * 255).astype(np.uint8).transpose(1, 0, 2))
        self.art.blit(pygame.transform.scale(ink, (w, h)), (0, 0), special_flags=pygame.BLEND_MULT)
        self.out.blit(self.scene, (0, 0))
        self.out.fill((int(255 * GROUND),) * 3, special_flags=pygame.BLEND_MULT)
        self.out.blit(self.art, (0, 0), special_flags=pygame.BLEND_ADD)
        self.bloom(self.out)
        lines = [f"daisies {daisies:>4}      moon {int(light * 100):>3}%      fireflies {len(self.sparks):>2}",
                 f"letters {int((char > 0).sum()):,}"]
        if self.hint:
            lines.append(HINT)
        g = self.hud_gap
        for i, text in enumerate(lines):
            self.label(text, DIM, (24, h - 18 - g * (len(lines) - i)))
        self.label(CREDIT, SIGN, (24, h - 18 - g * (len(lines) + 1) - g // 3))
        tt = f"{'●' if int(t * 2) % 2 == 0 else ' '} t {t:05.2f}s"
        self.label(tt, ACCENT, (w - 24 - self.small.size(tt)[0], 20))
        return self.out

    def label(self, text, colour, at):
        self.out.blit(self.small.render(text, True, (4, 10, 30)), (at[0] + 1, at[1] + 1))
        self.out.blit(self.small.render(text, True, colour), at)


def window_size():
    info = pygame.display.Info()
    k = 1.0
    if info.current_w > 0 and info.current_h > 0:
        k = min(1.0, 0.88 * info.current_h / H, 0.95 * info.current_w / W)
    return int(W * k), int(H * k)


def main():
    pygame.init()
    size = window_size()
    window = pygame.display.set_mode(size)
    pygame.display.set_caption(TITLE)
    renderer, clock = Renderer(), pygame.time.Clock()
    t, paused = 0.0, False
    screen = renderer.draw(t)
    while True:
        for e in pygame.event.get():
            if e.type == pygame.QUIT or (e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE):
                pygame.quit()
                return 0
            if e.type == pygame.KEYDOWN and e.key == pygame.K_SPACE:
                paused = not paused
            if e.type == pygame.KEYDOWN and e.key == pygame.K_r:
                t = 0.0
            if e.type == pygame.KEYDOWN and e.key == pygame.K_s:
                pygame.image.save(screen, str(Path(__file__).with_name(f"field_{int(time.time())}.png")))
        dt = clock.tick(30) / 1000
        if not paused:
            t += min(dt, 1 / 15)
            if t >= LOOP:
                t -= LOOP
            screen = renderer.draw(t)
        window.blit(screen if size == (W, H) else pygame.transform.smoothscale(screen, size), (0, 0))
        pygame.display.flip()


if __name__ == "__main__":
    sys.exit(main())
