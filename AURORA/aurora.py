# ASCII Aurora
# @dwcminh.ascii, 2026
# Terms in LICENSE.txt: personal, non-commercial use only. Not for use with AI tools:
# do not feed this code to an AI model, train on it, or have an AI rework it.
#
#   pip install numpy pygame-ce
#   python aurora.py
#
# A frozen lake far in the north, at night, with nobody on it but you. A star falls as you come in
# and the arc over the far shore flares at once into curtains of green light, their rays shooting
# up the sky, the black ice giving them back upside down. You glide slowly out over the ice,
# looking straight ahead, over drifts of snow and white cracks. Every couple of seconds a surge
# runs along the curtains, each in its own colours (a white flash, a pink hem, a violet crown, a
# crimson crown, a blue hem, then pink and crimson together, violet and blue together) and the
# snow takes its colour; more stars fall. Then the storm quietens back into the arc. The end is
# the beginning, so it loops for ever.
#
# The whole frame is lit: sky, light, ice and snow are painted first, then every cell gets a
# letter that suits what lies under it.
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
# the stars that fall: (when, where it starts: round from straight ahead (rad) and down the screen, how far it goes, which way)
STARS = [(0.0, -0.32, 0.05, 1.0, 1), (6.7, 0.28, 0.04, 0.8, -1), (11.8, -0.22, 0.13, 0.9, 1), (17.2, 0.30, 0.08, 0.7, -1)]
T_RISE = (0.0, 0.5)                            # the arc flares up into curtains, at once
# the surges: (when, which way, kinds, how much of the whole curtain it lights)
# kinds: 0 a white flash, 1 a pink hem, 2 a violet crown, 3 a crimson crown, 4 a blue hem
SURGES = [(0.2, 1, (0,), 0.85), (3.2, -1, (1,), 0.32), (5.6, 1, (2,), 0.32), (8.0, -1, (3,), 0.25),
          (10.4, 1, (4,), 0.18), (12.8, -1, (1, 3), 0.25), (15.2, 1, (2, 4), 0.30)]
SURGE_RUN = 1.8                                 # how long a surge takes to run the length of a curtain
T_CALM = (17.0, 19.9)                           # the storm quietens back into the arc, so the end meets the beginning

# you, gliding forward
DRIFT = 0.60                                    # how fast you glide over the ice (m/s)
STRIP = DRIFT * LOOP                            # the ice repeats every this far, so the loop closes
EYE = 1.60                                      # your eyes above the ice (m)
FOCAL = 1.05                                    # lens: screen heights per unit of slope
HORIZON = 0.58                                  # where the far shore lies, down the screen
NEAR = 0.8                                      # nothing is drawn nearer than this (m)

# the curtains of light, a little wider than you can see: where they hang (rad round from straight ahead; screen
# heights above the shore), how they fold, how tall and bright they are, how close their rays
# stand, how violet and how crimson their tops are (the highest has crimson of its own: oxygen
# glows red only far up). Waves and rays are counted per radian along the curtain.
CURTAINS = [
    dict(a0=-0.55, span=1.10, fold=0.091, ff=1.56, fw=2, s0=0.150, sa=0.045, sf=0.86, sw=-3, tall=0.30, bright=1.00, rays=251, violet=0.30, red=0.00, n=760, seed=0.0),
    dict(a0=-0.55, span=1.10, fold=0.044, ff=2.62, fw=-3, s0=0.315, sa=0.035, sf=1.48, sw=2, tall=0.17, bright=0.55, rays=342, violet=0.40, red=0.30, n=550, seed=2.1),
    dict(a0=-0.55, span=1.10, fold=0.022, ff=1.34, fw=1, s0=0.050, sa=0.012, sf=0.86, sw=-1, tall=0.07, bright=0.45, rays=416, violet=0.10, red=0.00, n=360, seed=4.4),
]
GAIN = 0.95                                     # how quickly the light saturates

# colours (0..255; the light's own colours 0..1)
ZENITH, SKYLINE, HAZE = np.array([10, 26, 78]), np.array([34, 84, 140]), np.array([62, 118, 152])
GREEN, VIOLET, RED = np.array([0.16, 1.00, 0.40]), np.array([0.52, 0.22, 1.00]), np.array([1.00, 0.12, 0.22])
PINK, WHITE, BLUE = np.array([1.00, 0.28, 0.62]), np.array([0.85, 1.00, 0.90]), np.array([0.14, 0.32, 1.00])
HILL, FIRS = np.array([26, 40, 68]), np.array([5, 11, 24])
ICE, SNOW, CRACK = np.array([12, 30, 54]), np.array([80, 104, 146]), np.array([176, 218, 244])
STAR = np.array([232, 240, 255])
GLINT = np.array([226, 240, 255])
DIM, ACCENT, SIGN = (150, 196, 204), (150, 255, 190), (226, 242, 255)

SKY_POOL = " .  ' . : .  "                      # open sky: almost nothing
AURORA_POOLS = ["'.:'`.", ":!i;:'", "!|il1|", "|I#H|I"]      # the light: rays stand upright, thin -> thick
REFLECT_POOLS = ["  .   ", " . ' .", ".:!:'|", "|!:|i!"]     # the light given back by the ice
SNOW_POOLS = ["  . , ", " .,-. ", ".-~,-.", "-~=~-~"]        # drifts lie across
C = lambda ch: ord(ch) - 32                     # character -> glyph index
ramp = lambda pools: np.array([[C(p[k % len(p)]) for k in range(12)] for p in pools])
AURORA_FILL, REFLECT_FILL, SNOW_FILL = ramp(AURORA_POOLS), ramp(REFLECT_POOLS), ramp(SNOW_POOLS)
SKY_FILL = ramp([SKY_POOL])[0]
SLOPE = np.array([C(c) for c in "-/|\\"])

GROUND = 0.74                                   # how much of the painting shows under the letters
INK, INK_AURORA, INK_ICE, INK_SNOW, INK_CRACK = 0.50, 0.42, 0.40, 0.30, 0.55


def smooth(x):
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3 - 2 * x)


def activity(t):
    # how strong the storm is: an arc at first, curtains a moment later, an arc again at the end
    return float(smooth((t - T_RISE[0]) / (T_RISE[1] - T_RISE[0])) * (1 - smooth((t - T_CALM[0]) / (T_CALM[1] - T_CALM[0]))))


def surges(a, t):
    # the bright waves running along a curtain, across the part of the sky you see:
    # how strong at each point of it (a, rad round from straight ahead), of each kind
    out = np.zeros((5, len(a)))
    for t0, way, kinds, broad in SURGES:
        p = (t - t0) / SURGE_RUN
        if -0.1 < p < 1.3:
            c = way * (-0.48 + 0.96 * p)
            env = smooth(p / 0.12) * (1 - smooth((p - 0.85) / 0.4))
            wave = env * (np.exp(-((a - c) / 0.12) ** 2) + broad)
            for kind in kinds:
                out[kind] += wave / len(kinds) ** 0.5
    return out


def surge_level(t):
    return sum(float(smooth((t - t0) / (0.12 * SURGE_RUN)) * (1 - smooth(((t - t0) / SURGE_RUN - 0.85) / 0.4)))
               for t0, *_ in SURGES if -0.1 < (t - t0) / SURGE_RUN < 1.3)


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
NOISE_A, NOISE_B, RAYS = make_noise(TILE, 1.75, 4), make_noise(TILE, 1.55, 9), make_noise(TILE, 1.15, 21)


def tex(noise, u, v):
    return noise[np.asarray(v).astype(int) & (TILE - 1), np.asarray(u).astype(int) & (TILE - 1)]


def soft_tex(noise, u, v):
    # the same, read between the texels, so edges near you stay smooth
    u, v = np.asarray(u, np.float32), np.asarray(v, np.float32)
    u0, v0 = np.floor(u), np.floor(v)
    fu, fv = u - u0, v - v0
    i0, j0 = u0.astype(int) & (TILE - 1), v0.astype(int) & (TILE - 1)
    i1, j1 = (i0 + 1) & (TILE - 1), (j0 + 1) & (TILE - 1)
    top = noise[j0, i0] * (1 - fu) + noise[j0, i1] * fu
    return top + (noise[j1, i0] * (1 - fu) + noise[j1, i1] * fu - top) * fv


def per_loop(per_metre):
    # texels per metre along the way you go, rounded so a whole number of tiles passes every loop
    return max(1, round(per_metre * STRIP / TILE)) * TILE / STRIP


def snow_on(x, zw):
    # how much snow lies at a point of the ice: drifts, longer across than along
    return smooth((soft_tex(NOISE_A, x * 110 + 300, zw * per_loop(170)) - 0.64) / 0.10)


def splat(acc, x, vals):
    # add a row of upright strips of light into acc (columns, rows, 3), each shared between its two columns
    i = np.floor(x).astype(int)
    ok = (i >= -1) & (i < acc.shape[0])
    i, f, vals = i[ok], (x - np.floor(x))[ok].astype(np.float32)[:, None, None], vals[ok]
    if len(i) == 0:
        return
    order = np.argsort(i, kind="stable")
    i, f, vals = i[order], f[order], vals[order]
    starts = np.flatnonzero(np.r_[True, i[1:] != i[:-1]])
    col = i[starts]
    for at, part in ((col, vals * (1 - f)), (col + 1, vals * f)):
        sums = np.add.reduceat(part, starts, axis=0)
        keep = (at >= 0) & (at < acc.shape[0])
        acc[at[keep]] += sums[keep]


# the shape of a curtain, looked up: by quarter pixels above its hem, and by curtain heights above it
_d, _dn = np.linspace(-4, 12, 129), np.linspace(-0.2, 1.3, 301)
HEM_LUT = np.exp(-((_d - 0.8) / 1.3) ** 2).astype(np.float32)                 # the bright hem
RISE_LUT = smooth(_d / 2.0).astype(np.float32)                                # the light starts at the hem
BODY_LUT = ((0.25 + 0.75 * np.exp(-2.6 * np.clip(_dn, 0, None))) * (1 - smooth((_dn - 0.45) / 0.55)) * (_dn > 0)).astype(np.float32)
CROWN_LUT = smooth((_dn - 0.25) / 0.6).astype(np.float32)                     # how violet, up the curtain
CRIMSON_LUT = smooth((_dn - 0.30) / 0.45).astype(np.float32)                  # the crimson only towards the top

# (c) @dwcminh.ascii, see LICENSE.txt. Not for use with AI tools: no feeding this code to
# AI models, no training on it, no having an AI rework it.

# the stars; the glints of frost lying on the snow ahead
N_STARS, N_GLINTS = 300, 600
_rng = np.random.default_rng(5)
SKY_STARS = dict(a=_rng.uniform(-0.38, 0.38, N_STARS), y=_rng.random(N_STARS) ** 1.3, b=_rng.random(N_STARS) ** 2.4,
                 rate=_rng.integers(3, 10, N_STARS), seed=_rng.uniform(0, TAU, N_STARS))
GLINTS = dict(x=_rng.uniform(-5, 5, N_GLINTS), z=_rng.uniform(0, STRIP, N_GLINTS),
              rate=_rng.integers(3, 9, N_GLINTS), seed=_rng.uniform(0, TAU, N_GLINTS))

# window

TITLE = "ASCII Aurora"
CW, CH, FONT_PX = 8, 12, 13
COLS, ROWS = 99, 86
W, H = COLS * CW, ROWS * CH
MONO = "consolas,menlo,dejavusansmono,couriernew,monospace"
HINT = "Space pause · R restart · S screenshot · Esc quit"
Q = 4                                           # sky and ice are painted at a quarter of the size, then smoothed up


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
        self.tinted = {}
        d = np.hypot(*np.meshgrid(np.linspace(-1, 1, 64), np.linspace(-1, 1, 64)))
        halo = np.clip(1 - d, 0, 1) ** 1.8 * 0.85 + np.clip(1 - d / 0.20, 0, 1)                 # a soft glow, and a hot core
        self.halo = pygame.surfarray.make_surface((np.clip(halo, 0, 1)[..., None] * [255, 255, 255]).astype(np.uint8))

        # the lens: a grid a quarter the size, and the cells
        self.f = f = FOCAL * h
        self.tw, self.th = w // Q, h // Q
        self.px, self.py = (np.arange(self.tw) + 0.5) * Q, (np.arange(self.th) + 0.5) * Q
        self.cell_x = np.clip(((np.arange(cols) + 0.5) * cw / Q).astype(int), 0, self.tw - 1)
        self.cell_y = np.clip(((np.arange(rows) + 0.5) * ch / Q).astype(int), 0, self.th - 1)
        self.cell_cx = (np.arange(cols) + 0.5) * cw
        self.cell_cy = (np.arange(rows)[:, None] + 0.5) * ch

        # the far shore: low snowy hills with stands of firs along the water
        rng = np.random.default_rng(6)
        a = np.arange(-0.45, 0.45, 4.0 / f)                   # round from straight ahead (rad)
        x, k = a * f, 792 / w
        hill = h * (0.012 + 0.052 * tex(NOISE_A, x * 0.30 * k + 300, x * 0 + 140) ** 1.4)
        wood = lambda at: tex(NOISE_B, np.asarray(at) * 0.8 * k + 400, np.asarray(at) * 0 + 33) > 0.45      # firs grow in stands, not everywhere
        firs = 0.003 * h * wood(x)
        for at, tall, wide in zip(rng.uniform(-0.45 * f, 0.45 * f, 320), rng.uniform(0.005, 0.017, 320) * h, rng.uniform(3, 8, 320) / k):
            if wood(at):
                firs = np.maximum(firs, tall * 1.6 * np.clip(1 - np.abs(x - at) / wide, 0, 1) + 0.003 * h * (np.abs(x - at) < wide))
        self.ridge = (a, hill, firs)

        # where every point of the quarter grid looks
        px, py = self.px, self.py
        self.yh = yh = HORIZON * h
        self.n_sky = n = int((py < yh).sum())
        self.sky_up = ((yh - py[:n]) / yh)[:, None]             # 0 at the shore, 1 at the top
        depth = np.minimum(f * EYE / np.maximum(py[n:] - yh, 0.5), 200.0)    # the ice: how far ahead each row is
        self.ice_x = ((px - w / 2) / f)[None] * depth[:, None]
        self.ice_z = np.broadcast_to(depth[:, None], self.ice_x.shape)
        # the mirror: for every row of ice, the rows of sky it gives back (smeared a little upward)
        mirror = (2 * yh - py[n:]) / Q - 0.5
        self.mirror = [np.clip(np.round(mirror - k).astype(int), 0, n - 1) for k in (0, 1, 3)]
        self.sky_cells = int(np.ceil(yh / ch - 0.5))
        self.shore, self.shore_ink = self.shore_cells()

    def round_to_screen(self, a):
        # something far off, so far round from straight ahead -> across the screen
        return self.w / 2 + self.f * np.tan(np.clip(a, -1.3, 1.3))

    # the light: every curtain is a row of upright strips hung from a wandering hem

    def aurora(self, t, act):
        n, tw = self.n_sky, self.tw
        acc = np.zeros((tw, n, 3), np.float32)
        rows = (np.arange(n) + 0.5).astype(np.float32)
        strength = 0.42 + 0.58 * act
        for k, c in enumerate(CURTAINS):
            u = np.linspace(0, 1, c["n"])
            v = u * c["span"]                                   # along the curtain (rad)
            surge = surges(c["a0"] + v, t)
            s_all = surge.sum(0)
            ph = c["seed"]
            a = c["a0"] + v + c["fold"] * (1 + 0.6 * s_all) * np.sin(TAU * c["ff"] * v + c["fw"] * BEAT * t + ph)
            xq = self.round_to_screen(a) / Q
            seen = (xq > -3) & (xq < tw + 3)
            if not seen.any():
                continue
            # each strip lights the width of sky it covers; seen edge on, where the curtain folds, a little more
            cover = np.abs(np.gradient(xq))
            per = self.f / Q * c["span"] / c["n"]
            u, v, xq, cover, surge, s_all = u[seen], v[seen], xq[seen], cover[seen], surge[:, seen], s_all[seen]
            s = c["s0"] + c["sa"] * (np.sin(TAU * c["sf"] * v + c["sw"] * BEAT * t + 1.7 * ph) + 0.35 * np.sin(TAU * 2.6 * v - 2 * BEAT * t + ph))
            way = 1 if k % 2 == 0 else -1
            lane = np.full(len(u), 64 * k + 17)
            fine = 0.65 * tex(RAYS, v * c["rays"] + way * TILE * t / LOOP, lane) + 0.35 * tex(RAYS, v * c["rays"] * 1.7 - way * 2 * TILE * t / LOOP, lane + 200)
            coarse = tex(NOISE_A, v * 140 + way * TILE * t / LOOP, lane + 90)
            ends = smooth(u / 0.08) * smooth((1 - u) / 0.08)
            edge_on = 1 + 1.3 * np.exp(-cover / (0.30 * per))
            tall = c["tall"] * self.h / Q * (0.40 + 0.75 * coarse) * (0.62 + 0.70 * fine) * (0.40 + 0.60 * act) * (1 + 0.3 * s_all)
            bright = c["bright"] * strength * (0.5 + 0.5 * coarse) * (1 + 1.4 * s_all) * ends * cover * edge_on
            hem = (self.yh - s * self.h) / Q
            r0, r1 = int(max(0, np.floor((hem - tall).min()) - 1)), int(min(n, np.ceil(hem.max()) + 4))
            if r1 <= r0:
                continue
            d = hem.astype(np.float32)[:, None] - rows[None, r0:r1]                 # how far above the hem (quarter pixels)
            jd = np.clip(((d + 4) * 8).astype(np.int32), 0, len(_d) - 1)
            jn = np.clip(((d * (1 / tall).astype(np.float32)[:, None] + 0.2) * 200).astype(np.int32), 0, len(_dn) - 1)
            ray = (0.10 + 1.5 * fine ** 3).astype(np.float32)
            body = RISE_LUT[jd] * BODY_LUT[jn] * ray[:, None]
            # the top of the curtain: violet, and crimson above it; they glow brighter than the green they take over from
            red = np.clip(c["red"] + 1.2 * surge[3], 0, 1).astype(np.float32)[:, None]
            fc = CRIMSON_LUT[jn] * red
            fv = (1 - fc) * CROWN_LUT[jn] * np.clip(c["violet"] + surge[2], 0, 1).astype(np.float32)[:, None]
            green = body * (1 - fc - fv)
            crimson, violet = body * fc * 2.2, body * fv * 1.4
            edge = HEM_LUT[jd]
            # the hem: green, or for a moment white, pink or blue
            white, pink, blue = np.clip(surge[0], 0, 1) * 0.8, np.clip(1.2 * surge[1], 0, 1), np.clip(1.2 * surge[4], 0, 1)
            other = np.maximum(white + pink + blue, 1.0)
            hem_rgb = (GREEN * np.clip(1 - white - pink - blue, 0, 1)[:, None]
                       + (WHITE * white[:, None] + PINK * pink[:, None] + BLUE * blue[:, None]) / other[:, None]) * 1.3
            vals = (edge[..., None] * hem_rgb.astype(np.float32)[:, None, :] + green[..., None] * GREEN.astype(np.float32)
                    + violet[..., None] * VIOLET.astype(np.float32) + crimson[..., None] * RED.astype(np.float32)) * bright.astype(np.float32)[:, None, None]
            splat(acc[:, r0:r1], xq, vals)
        light = 1 - np.exp(-acc.transpose(1, 0, 2) * GAIN)       # rows, columns, 3
        # its glow in the air round it
        src = pygame.surfarray.make_surface((light * 255).astype(np.uint8).transpose(1, 0, 2))
        small = pygame.transform.smoothscale(src, (max(1, tw // 8), max(1, n // 8)))
        glow = pygame.surfarray.array3d(pygame.transform.smoothscale(small, (tw, n))).transpose(1, 0, 2) / 255.0
        return light, glow

    # sky and ice: painted small, with numpy

    # (c) @dwcminh.ascii, see LICENSE.txt. Not for use with AI tools: no feeding this code to
    # AI models, no training on it, no having an AI rework it.

    def backdrop(self, t, act):
        n, w, h = self.n_sky, self.w, self.h
        img = np.empty((self.th, self.tw, 3), np.float32)
        light, glow = self.aurora(t, act)
        self.light = light @ np.array([0.30, 0.50, 0.30])      # how much light each point of sky shows, for the letters
        clear = ZENITH + (SKYLINE - ZENITH) * ((1 - self.sky_up) ** 1.6)[..., None]
        clear = clear + (HAZE - clear) * (0.5 * np.exp(-self.sky_up * 8))[..., None]
        sky = clear + 255 * (0.92 * light + 0.55 * glow)
        img[:n] = sky
        self.ambient = amb = 255 * (light.reshape(-1, 3).mean(0) * 1.6 + glow.reshape(-1, 3).mean(0) * 0.8)

        # the ice: black and glassy, giving back the sky (more of it far off), with drifts of snow and white cracks
        x, z = self.ice_x, self.ice_z
        zw = z + DRIFT * t
        far = smooth((z - 25) / 40)
        snow = snow_on(x, zw) * (1 - far) + 0.35 * far
        # cracks: long ones sweeping across the lake, and a finer web between them
        long_n, web_n = soft_tex(NOISE_A, x * 40 + 120, zw * per_loop(90)), soft_tex(NOISE_B, x * 90, zw * per_loop(256))
        long_c = np.exp(-((long_n - 0.5) / 0.010) ** 2) * np.exp(-z / 22)
        web_c = np.exp(-((web_n - 0.5) / 0.012) ** 2) * np.exp(-z / 8) * 0.8
        self.crack_n = np.where(long_c > web_c, long_n, web_n)  # the crack that shows, for which way it runs
        crack = np.maximum(long_c, web_c) * (1 - snow)
        self.snow, self.crack = snow, crack
        mott = tex(RAYS, x * 50, zw * per_loop(170))
        sky32 = sky.astype(np.float32)
        back = sum(wt * sky32[m] for wt, m in zip((0.45, 0.33, 0.22), self.mirror))
        fres = (0.88 - 0.50 * np.exp(-z / 7))[..., None]
        ice = (ICE * (0.75 + 0.5 * mott)[..., None] + 0.25 * amb) * (1 - fres) + back * fres * 0.85
        drift = SNOW * (0.80 + 0.35 * mott)[..., None] + 0.7 * amb
        ice = ice + (drift - ice) * snow[..., None]
        img[n:] = ice + (CRACK - ice) * (0.75 * crack)[..., None]
        small = pygame.surfarray.make_surface(np.clip(img, 0, 255).astype(np.uint8).transpose(1, 0, 2))
        pygame.transform.smoothscale(small, (w, h), self.scene)

    def place(self, x, y, z):
        # a point in front of you -> where it is on screen
        return self.w / 2 + self.f * x / z, self.yh + self.f * (EYE - y) / z

    def shore_and_stars(self, t):
        # the far shore and its likeness in the ice; the stars and theirs
        scene, w, h, yh, amb = self.scene, self.w, self.h, self.yh, self.ambient
        a, hill_h, fir_h = self.ridge
        sx = self.round_to_screen(a)
        seen = np.flatnonzero((sx > -40) & (sx < w + 40))
        sx = sx[seen]
        shape = lambda top, base: [(sx[0], base)] + np.stack([sx, top], 1).tolist() + [(sx[-1], base)]
        hill_top, fir_top = yh - hill_h[seen], yh - fir_h[seen]
        hill = tuple(int(c) for c in np.clip(HILL + 0.30 * amb, 0, 255))
        firs = tuple(int(c) for c in np.clip(FIRS + 0.10 * amb, 0, 255))
        pygame.draw.polygon(scene, tuple(int(c * 0.80) for c in hill), shape(2 * yh - hill_top, yh))
        pygame.draw.polygon(scene, tuple(int(c * 1.3 + 6) for c in firs), shape(2 * yh - fir_top, yh))
        pygame.draw.polygon(scene, hill, shape(hill_top, yh + 1))
        pygame.draw.polygon(scene, firs, shape(fir_top, yh))
        s = SKY_STARS
        x, y = self.round_to_screen(s["a"]), (yh - HORIZON * h) + s["y"] * (HORIZON - 0.07) * h
        b = s["b"] * (0.62 + 0.38 * np.sin(s["rate"] * BEAT * t + s["seed"])) * ((x >= 1) & (x < w - 2) & (y >= 1))
        # given back by the ice, only where it is clear of snow
        yb = 2 * yh - y
        row = np.clip((yb / Q).astype(int) - self.n_sky, 0, self.snow.shape[0] - 1)
        col = np.clip((x / Q).astype(int), 0, self.tw - 1)
        bb = b * 0.40 * (1 - self.snow[row, col]) * (yb < h - 2)
        px = pygame.surfarray.pixels3d(scene)
        for xs, ys, bs in ((x, y, b), (x, yb, bb)):
            ok = (bs > 0.10) & (ys < h - 2)
            ix, iy, bv = xs[ok].astype(int), ys[ok].astype(int), bs[ok]
            rgb = (STAR[None] * np.clip(bv, 0, 1)[:, None])
            px[ix, iy] = np.maximum(px[ix, iy], rgb.astype(np.uint8))
            big = bv > 0.55
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                px[ix[big] + dx, iy[big] + dy] = np.maximum(px[ix[big] + dx, iy[big] + dy], (rgb[big] * 0.5).astype(np.uint8))
        del px
        self.stars = [(x, y, b), (x, yb, bb)]
        return int((b > 0.10).sum())

    def shore_cells(self):
        # the letter of every cell of the far shore and of its likeness (-1 elsewhere), and their ink
        a, hill_h, fir_h = self.ridge
        cols, rows, cw, ch, yh, cy = self.cols, self.rows, self.cw, self.ch, self.yh, self.cell_cy
        at = np.arctan((self.cell_cx - self.w / 2) / self.f)
        ht, ft = (yh - np.interp(at, a, hill_h))[None], (yh - np.interp(at, a, fir_h))[None]
        stand = (yh - ft) > 0.3 * ch                            # only where the firs are tall enough to fill a cell
        fir = (cy > ft - ch * 0.2) & (cy < yh) & stand
        hill_c = (cy > ht - ch * 0.2) & (cy < yh) & ~fir
        fir_b = (cy > yh) & (cy < 2 * yh - ft + ch * 0.2) & stand
        hill_b = (cy > yh) & (cy < 2 * yh - ht + ch * 0.2) & ~fir_b
        rise = -np.gradient(ht[0]) / cw                         # how the skyline of the hills climbs, left to right
        crest = np.where(rise > 0.30, C("/"), np.where(rise < -0.30, C("\\"), C("-")))[None]
        crest_b = np.where(rise > 0.30, C("\\"), np.where(rise < -0.30, C("/"), C("-")))[None]
        shore = np.full((rows, cols), -1)
        shore[hill_c] = C(":")
        shore[hill_b] = C(".")
        top = hill_c & ~np.roll(hill_c | fir, 1, 0)
        shore[top] = np.broadcast_to(crest, top.shape)[top]
        top_b = hill_b & ~np.roll(hill_b | fir_b, -1, 0)
        shore[top_b] = np.broadcast_to(crest_b, top_b.shape)[top_b]
        shore[fir | fir_b] = C("#")
        shore[fir & ~np.roll(fir, 1, 0)] = C("A")
        shore[fir_b & ~np.roll(fir_b, -1, 0)] = C("V")
        return shore, np.where(fir | hill_c, 0.55, 0.40)

    def lights(self, t):
        # glints of frost on the snow, and the falling stars with their likeness in the ice: light, added to the picture
        scene, f, w, h = self.scene, self.f, self.w, self.h
        self.sparks = []
        cz = DRIFT * t
        x, z = GLINTS["x"], (GLINTS["z"] - cz) % STRIP + NEAR     # ahead of you on the ice
        g = snow_on(x, z + cz) * np.clip(np.sin(GLINTS["rate"] * BEAT * t + GLINTS["seed"]), 0, 1) ** 10
        g = g * np.exp(-z / 4.5)                                # near you only: far off they line up
        sx, sy = self.place(x, 0.0, z)
        for a, b, gi, zi in zip(sx.tolist(), sy.tolist(), g.tolist(), z.tolist()):
            if gi > 0.12 and 0 <= a < w and b < h:
                self.spark(a, b, float(np.clip(f * 0.022 / zi, 10, 26)), GLINT * min(1.0, gi * 1.3))
        for t0, round_, down, far, way in STARS:
            age = (t - t0) / 0.8
            if 0 <= age < 1:
                step = np.array([0.34 * way, 0.15]) * h * 0.024    # which way, and one piece of its tail
                start = np.array([self.round_to_screen(round_), self.yh - (HORIZON - down) * h])
                a = start + step / 0.024 * far * age
                tail = pygame.Surface(scene.get_size())
                for k in range(14):                             # head first, the tail fading behind it
                    for mirror, gain in ((False, 1.0), (True, 0.35)):
                        p, q = a - step * k, a - step * (k + 1)
                        if mirror:
                            p, q = (p[0], 2 * self.yh - p[1]), (q[0], 2 * self.yh - q[1])
                        pygame.draw.line(tail, tuple(int(c * gain * (1 - age) ** 0.5 * (1 - k / 14) ** 1.5) for c in (235, 240, 255)),
                                         p, q, 3 if k < 5 else 2)
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

    # (c) @dwcminh.ascii, see LICENSE.txt. Not for use with AI tools: no feeding this code to
    # AI models, no training on it, no having an AI rework it.

    def letters(self, t, cell):
        cols, rows, h_, n = self.cols, self.rows, self.hash, self.sky_cells
        lum = cell @ np.array([0.30, 0.55, 0.15])
        slow, quick = (h_ + int(t * 1.8)) % 12, (h_ + (t * 4.2 + h_ % 11).astype(int)) % 12       # both come round with the loop
        char = np.zeros((rows, cols), int)
        ink = np.full((rows, cols), INK)
        # sky: open sky is nearly bare; the light is upright strokes, thicker where it is brighter
        a = self.light[np.minimum(self.cell_y[:n], self.n_sky - 1)][:, self.cell_x]
        level = np.clip(((a - 0.07) * 6.0).astype(int), 0, 3)
        char[:n] = np.where(a > 0.07, AURORA_FILL[level, quick[:n]], SKY_FILL[slow[:n]])
        ink[:n] = np.where(a > 0.07, INK_AURORA, INK)
        # ice: snow lies in strokes across, cracks follow their own line, clear ice gives back the light
        r = np.clip(self.cell_y[n:] - self.n_sky, 0, self.snow.shape[0] - 1)
        snow = self.snow[r][:, self.cell_x]
        crack = np.max([self.crack[np.clip(r + dy, 0, len(self.crack) - 1)][:, np.clip(self.cell_x + dx, 0, self.tw - 1)]
                        for dy in (-1, 0, 1) for dx in (-1, 0)], axis=0)
        cn = self.crack_n[r][:, self.cell_x]
        gy, gx = np.gradient(cn)
        angle = np.arctan2(gx / self.cw, -gy / self.ch) % np.pi    # the crack runs across its gradient
        slope = SLOPE[(np.round(angle / (np.pi / 4)).astype(int)) % 4]
        g = lum[n:]
        jitter = (h_[n:] % 100) / 100.0 - 0.5
        lr = np.clip(((g - 0.06) / 0.075 + jitter).astype(int), 0, 3)
        ls = np.clip(((g - 0.30) / 0.10 + jitter).astype(int), 0, 3)
        char[n:] = np.where(crack > 0.35, slope, np.where(snow > 0.5, SNOW_FILL[ls, slow[n:]], REFLECT_FILL[lr, quick[n:]]))
        ink[n:] = np.where(crack > 0.35, INK_CRACK, np.where(snow > 0.5, INK_SNOW, INK_ICE))
        shore = self.shore >= 0
        char = np.where(shore, self.shore, char)
        ink = np.where(shore, self.shore_ink, ink)
        tint = np.clip(cell * 1.55 + 0.05, 0, 1) * ink[..., None]
        # the stars, where the light does not drown them, and the glints and falling stars
        for (x, y, b), dim in zip(self.stars, (1.0, 0.7)):
            ix, iy = np.clip(x / self.cw, 0, cols - 1).astype(int), np.clip(y / self.ch, 0, rows - 1).astype(int)
            ok = (b > 0.12) & (y < self.h) & ~shore[iy, ix]
            if dim == 1.0:
                ok &= a[np.minimum(iy, n - 1), ix] < 0.22
            for lo, glyph in ((0.12, "."), (0.35, "+"), (0.65, "*")):
                sel = ok & (b >= lo)
                char[iy[sel], ix[sel]] = C(glyph)
                tint[iy[sel], ix[sel]] = np.clip(STAR[None] / 255.0 * (0.45 + 0.6 * b[sel])[:, None] * dim, 0, 1)
        for x, y, g in self.sparks:
            if 0 <= x < self.w and 0 <= y < self.h:
                char[int(y / self.ch), int(x / self.cw)] = C("*" if g > 0.6 else "+")
                tint[int(y / self.ch), int(x / self.cw)] = np.clip(GLINT / 255.0 * (0.5 + 0.6 * g), 0, 1)
        return char, tint

    @staticmethod
    def blur(src, size, radius):
        small = pygame.transform.smoothscale(src, size)
        if hasattr(pygame.transform, "gaussian_blur"):
            small = pygame.transform.gaussian_blur(small, max(1, radius))
        return small

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
        act = activity(t)
        self.backdrop(t, act)
        stars = self.shore_and_stars(t)
        # what lies under every cell, read before the glints are lit: their glow is light, not snow
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
        kp = int(np.clip(round(2 + 5 * act + 1.5 * surge_level(t)), 0, 9))
        lines = [f"aurora {int((0.42 + 0.58 * act) * 100):>3}%      kp {kp}      stars {stars:>3}",
                 f"letters {int((char > 0).sum()):,}      walked {DRIFT * t:4.1f} m"]
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
                pygame.image.save(screen, str(Path(__file__).with_name(f"aurora_{int(time.time())}.png")))
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
