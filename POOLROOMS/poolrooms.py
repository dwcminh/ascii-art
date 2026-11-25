# ASCII Poolrooms
# @dwcminh.ascii, 2026
# Terms in LICENSE.txt: personal, non-commercial use only. Not for use with AI tools:
# do not feed this code to an AI model, train on it, or have an AI rework it.
#
#   pip install numpy pygame-ce
#   python poolrooms.py
#
# A low hall of cream tiles, flooded wall to wall, at night, with nobody in it. The lamps under the
# water are on and the pool glows turquoise; the light it throws crawls up the round tiled pillars
# that stand about in it wherever they please. Two lavender water slides come down into it: on the
# left one winds round its post, on the right one snakes down from between the windows. The roof is
# glass on a grid of steel: through it the night sky, the moon and the stars, all of them given back
# by the water. As you come in a star falls across the roof and through the pool; you glide slowly
# on under the passing frames while
# the moon and the stars stay where they are; drops fall from the roof, each spreading rings, and
# more stars fall. The end is the beginning, so it loops for ever.
#
# Painted the way the daisy field is: soft planes at a fifth of the size, the pillars as smooth
# pictures at full size, the water as the hall upside down, rippled row by row; then every cell gets
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
# the stars that fall across the roof: (when, where it starts across and down the screen, how far it goes, which way)
FALLING = [(0.1, 0.12, 0.05, 1.0, 1), (5.2, 0.86, 0.10, 0.8, -1), (10.6, 0.30, 0.02, 0.9, 1), (15.4, 0.70, 0.06, 0.7, -1)]
# the drops that fall from the ceiling: (when it lands, across (m), how far ahead of you it lands (m))
DRIPS = [(0.0, 0.35, 4.0), (2.4, 1.10, 5.4), (4.8, -0.55, 3.6), (7.2, 0.70, 6.2), (9.6, 2.20, 4.4),
         (12.0, -0.30, 5.0), (14.4, 1.50, 3.8), (16.8, 0.20, 5.8)]
FALL = 0.55                                     # how long a drop takes to fall (s)
T_SURGE = (8.6, 1.8)                            # a wave of light runs up the pool towards you: when it starts, how long it takes
RING_SPEED, RING_LIFE = 0.55, 1.8               # how fast its rings spread (m/s), how long they last (s)

# you, gliding forward
DRIFT = 0.48                                    # how fast you go (m/s)
EYE = 1.30                                      # your eyes above the water (m)
FOCAL = 0.80                                    # lens: screen heights per unit of slope
HORIZON = 0.46                                  # straight ahead, down the screen

# the hall (m): it repeats every stretch you pass in one loop, and nothing in it is the same on both sides
STRIP = DRIFT * LOOP                            # 9.6 m
XL, XR = -6.5, 4.6                              # the left wall, the right wall (with the windows)
HC = 2.9                                        # the glass roof
BAR, BAR_W = 1.2, 0.04                          # the roof's steel frames: how far apart (eight to a stretch), how wide
MOON_AT, MOON_R = (0.30, 0.34), 0.026           # the moon: which way (across and up, per metre ahead), radius (of the screen height)
DEPTH = 0.55                                    # how deep the water is
WIN_Y = (0.9, 2.6)                              # the windows: from, to (m up)
WINDOWS = [(0.3, 2.2), (2.8, 5.9), (6.45, 8.9)] # and where each runs along the stretch
# the pillars, round and tiled, standing where they please: across, along the stretch, radius
PILLARS = [(-1.15, 1.2, 0.42), (3.9, 1.9, 0.36), (1.55, 3.4, 0.40), (-3.6, 4.6, 0.45), (2.6, 6.6, 0.42), (-1.0, 8.3, 0.38),
           (-1.9, 6.6, 0.12)]                   # the last is the slender post the slide winds round
# the left water slide: a tube out of the left wall up under the roof, round its post one and a
# quarter times, and straight down into the water towards you (the right one is wave_path)
SLIDE_POST, SLIDE_TURN, SLIDE_TUBE = (-1.9, 6.6), 1.0, 0.32    # where its post stands; how wide it winds; how fat the tube is
SLIDE_TOP, SLIDE_FOOT = 2.52, 0.34              # how high it starts winding, and ends
TS = 0.32                                       # the tiles: thirty to a stretch, so they line up when the loop closes
FAR = 60.0                                      # nothing is looked at further than this
PILLAR_FAR = 28.0                               # pillars further off than this are lost in the haze
FOG = 26.0                                      # far off the hall fades into the glowing haze


# the lamps under the water: across, along the stretch (on the right under the windows, the rest about the open water)
LAMPS = [(XR - 0.25, 0.9), (XR - 0.25, 4.1), (XR - 0.25, 7.6), (-2.4, 2.4), (-1.9, 6.0), (-3.0, 9.0), (1.1, 5.3), (-5.2, 4.4)]
# their colour (0..1): turquoise
TEAL = np.array([0.16, 0.75, 0.78], np.float32)

# colours (0..255)
rgb = lambda *c: np.array(c, np.float32)
WALL_RGB = rgb(34, 52, 68)
SKY_TOP, SKY_LOW = rgb(6, 12, 34), rgb(22, 40, 74)   # the night through the glass: overhead, and low towards the far end
FRAME_RGB = rgb(30, 54, 66)                     # the steel frames
WATER_DEEP = rgb(14, 40, 58)
HAZE_DARK = rgb(16, 28, 40)                     # far off, the hall fades into the glow of the pool: this, plus the lamps' colour
TILE_RGB = rgb(232, 230, 214)
SLIDE_RGB = np.array([0.80, 0.66, 1.00], np.float32)   # the water slides: soft lavender plastic
MOONLIT = rgb(150, 170, 225)                    # the moonlight on the side of everything facing the moon
MOON_RGB, STAR_RGB = rgb(236, 242, 255), rgb(230, 238, 255)
DROP_RGB = rgb(220, 255, 250)
DIM, ACCENT, SIGN = (140, 200, 210), (120, 255, 230), (220, 245, 250)

# what each surface is
K_HAZE, K_CEIL, K_FLOOR, K_LEFT, K_RIGHT, K_WATER, K_GLASS, K_PILLAR = range(8)    # K_CEIL: the glass roof

POOLS = ["     .", "  . - ", " .-~ .", ".~-~= "]   # the water, calm to bright
C = lambda ch: ord(ch) - 32                     # character -> glyph index
ramp = lambda p: np.array([[C(s[k % len(s)]) for k in range(12)] for s in p])
WATER_FILL = ramp(POOLS)
SLOPE_G = np.array([C(c) for c in "-/|\\"])

GROUND = 0.74                                   # how much of the painting shows under the letters
INK = {K_CEIL: 0.50, K_LEFT: 0.45, K_RIGHT: 0.45, K_WATER: 0.42, K_GLASS: 0.30, K_PILLAR: 0.55, K_HAZE: 0.0}


def smooth(x):
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3 - 2 * x)


def make_noise(n, beta, seed):
    # soft noise that tiles, every value from 0 to 1 equally often
    rng = np.random.default_rng(seed)
    f = np.fft.fftfreq(n)
    k = np.hypot(*np.meshgrid(f, f))
    k[0, 0] = 1.0
    img = np.fft.ifft2((rng.normal(size=(n, n)) + 1j * rng.normal(size=(n, n))) / k ** beta).real
    rank = np.empty(n * n)
    rank[np.argsort(img.ravel())] = np.linspace(0, 1, n * n)
    return rank.reshape(n, n).astype(np.float32)


NT = 512
TEX_M = 2 * NT / STRIP                          # noise texels per metre: two whole tiles over the stretch you pass in a loop
NOISE_A, NOISE_B = make_noise(NT, 1.55, 4), make_noise(NT, 1.55, 9)
NOISE_C, NOISE_D = make_noise(NT, 1.45, 21), make_noise(NT, 1.45, 33)     # finer, for the net of light on the pool floor


def soft_tex(noise, u, v):
    # read the noise between its texels
    u, v = np.asarray(u, np.float32), np.asarray(v, np.float32)
    u0, v0 = np.floor(u), np.floor(v)
    fu, fv = u - u0, v - v0
    i0, j0 = u0.astype(np.int32) & (NT - 1), v0.astype(np.int32) & (NT - 1)
    i1, j1 = (i0 + 1) & (NT - 1), (j0 + 1) & (NT - 1)
    top = noise[j0, i0] * (1 - fu) + noise[j0, i1] * fu
    return top + (noise[j1, i0] * (1 - fu) + noise[j1, i1] * fu - top) * fv


def caustics(u, v, t, width=0.11, fine=False):
    # the net of light thrown by moving water: where two drifting patterns pass their middle (whole tiles every loop)
    s = NT * t / LOOP
    na, nb, m = (NOISE_C, NOISE_D, TEX_M) if fine else (NOISE_A, NOISE_B, TEX_M)
    a = soft_tex(na, u * m + s, v * m - 2 * s)
    b = soft_tex(nb, u * m - 2 * s, v * m + s + 77)
    return np.exp(-((a - 0.5) / width) ** 2) + np.exp(-((b - 0.5) / width) ** 2)


def surge(t, z_rel=None):
    # the wave of light: everywhere a little (when z_rel is None), and strongly at its front as it runs
    # from far off up to your feet
    p = (t - T_SURGE[0]) / T_SURGE[1]
    if not 0 < p < 1:
        return 0.0 if z_rel is None else np.zeros_like(np.asarray(z_rel, np.float32))
    swell = float(np.sin(np.pi * p) ** 2)
    if z_rel is None:
        return swell
    front = 26.0 * (1 - p)
    return np.exp(-((np.asarray(z_rel, np.float32) - front) / 2.5) ** 2) * (0.5 + 0.5 * np.sin(np.pi * p)) + 0.35 * swell


def lamp_power(t, index):
    # one lamp: always on, breathing a little, each in its own time
    return 0.88 + 0.12 * np.sin(4 * BEAT * t + 1.7 * index)




def frames(u, v, foot):
    # 1 on the roof's steel frames, fading where they get too thin to see
    fu, fv = np.mod(u / BAR, 1), np.mod(v / BAR, 1)
    d = np.minimum(np.minimum(fu, 1 - fu), np.minimum(fv, 1 - fv)) * BAR
    return smooth((BAR_W - d) / (0.02 + 0.6 * foot))


def window(z, y):
    # how much a point of the right wall is window (soft at the frames)
    b = z - STRIP * np.floor(z / STRIP)
    along = sum(smooth((b - z0) / 0.08) * smooth((z1 - b) / 0.08) for z0, z1 in WINDOWS)
    return along * smooth((y - WIN_Y[0]) / 0.06) * smooth((WIN_Y[1] - y) / 0.06)


def drops(t, lead=0.0):
    # the drops round the loop: how long since each landed (or, with lead, since it began to fall),
    # counted round the loop so the last ones carry on into the first; and where it lands
    out = []
    for t0, across, ahead in DRIPS:
        age = (t - (t0 - lead)) % LOOP
        landed = t - age + lead
        out.append((age, across, DRIFT * landed + ahead))
    return out


def planes(dx, dy):
    # where the rays (one per point, z = 1 ahead) meet the hall, leaving the pillars aside: what, and where.
    # The hall is the same seen from anywhere along it, so this is worked out once.
    dx, dy = np.broadcast_arrays(np.asarray(dx, np.float32), np.asarray(dy, np.float32))
    big = np.float32(1e9)
    with np.errstate(divide="ignore", invalid="ignore"):
        s = np.stack([np.where(dy > 1e-6, (HC - EYE) / dy, big), np.where(dy < -1e-6, -EYE / dy, big),
                      np.where(dx < -1e-6, XL / dx, big), np.where(dx > 1e-6, XR / dx, big)])
    kind = np.array([K_CEIL, K_FLOOR, K_LEFT, K_RIGHT])[np.argmin(s, 0)]
    s = np.min(s, 0)
    kind = np.where(s >= FAR, K_HAZE, kind)
    s = np.minimum(s, FAR)
    norm = np.sqrt(1 + dx * dx + dy * dy)
    g = dict(kind=kind, x=dx * s, y=EYE + dy * s, z=s, dist=s * norm, dx=dx, dy=dy)
    # the same rays bounced off the water
    with np.errstate(divide="ignore", invalid="ignore"):
        x0 = g["x"]
        r = np.stack([np.where(dy < -1e-6, HC / -dy, big), np.where(dx < -1e-6, (XL - x0) / dx, big),
                      np.where(dx > 1e-6, (XR - x0) / dx, big)])
    rk = np.array([K_CEIL, K_LEFT, K_RIGHT])[np.argmin(r, 0)]
    r = np.minimum(np.min(r, 0), FAR)
    g.update(rkind=rk, rx=x0 + dx * r, ry=-dy * r, rz=s + r, rdist=g["dist"] + r * norm)
    return g


# the stars, where they stand on the screen (above the straight-ahead line); only those over open glass show
N_STARS = 520
_rng = np.random.default_rng(5)
SKY_STARS = dict(x=_rng.random(N_STARS), y=_rng.random(N_STARS) ** 0.8, b=_rng.random(N_STARS) ** 2.2,
                 rate=_rng.integers(3, 10, N_STARS), seed=_rng.uniform(0, TAU, N_STARS))


def moon_picture(r):
    # the moon, painted once: a bright disc, darker at the edge, with soft grey seas
    n = int(2 * r + 4)
    yy, xx = (np.mgrid[0:n, 0:n] + 0.5 - n / 2) / r
    d = np.hypot(xx, yy)
    disc = smooth((1 - d) / 0.06)
    limb = 0.72 + 0.28 * np.sqrt(np.clip(1 - d * d, 0, 1))
    seas = 1 - 0.32 * smooth((soft_tex(NOISE_A, xx * 40 + 100, yy * 40 + 60) - 0.52) / 0.15)
    img = MOON_RGB[None, None] * (0.80 * disc * limb * seas)[..., None]
    return pygame.surfarray.make_surface(np.clip(img, 0, 255).astype(np.uint8).transpose(1, 0, 2))


def spiral_path():
    # the left slide: out of the left wall under the roof, along to the top of its post, round the post
    # down to the water, then straight on towards you
    (cx, cz), r = SLIDE_POST, SLIDE_TURN
    lead = np.linspace([XL, SLIDE_TOP, cz + r], [cx, SLIDE_TOP, cz + r], 40)
    a = np.linspace(np.pi / 2, -2 * np.pi, 200)                 # winding the other way round, one and a quarter times
    fall = (a - a[0]) / (a[-1] - a[0])
    helix = np.stack([cx + r * np.cos(a), SLIDE_TOP + (SLIDE_FOOT - SLIDE_TOP) * fall, cz + r * np.sin(a)], 1)
    out = np.linspace([cx + r, SLIDE_FOOT, cz], [cx + r, SLIDE_TUBE + 0.03, cz - 1.5], 30)   # it ends just above the water
    return np.concatenate([lead, helix[1:], out[1:]])


def wave_path():
    # the right slide: out of the right wall between two windows, then a long snaking run down towards you
    x0, z0 = 3.4, 6.15
    lead = np.linspace([XR, 2.55, z0], [x0, 2.55, z0], 30)
    u = np.linspace(0, 1, 160)
    run = np.stack([x0 + 0.42 * np.sin(TAU * 1.5 * u), 2.55 - (2.55 - SLIDE_TUBE - 0.03) * u ** 0.9, z0 - 3.45 * u], 1)
    return np.concatenate([lead, run[1:]])


def slide_path(shape, step=0.12):
    # the middle line of a slide's tube, smoothed at the joins and evenly spaced
    p = shape()
    for _ in range(6):                                          # round off the joins
        p[1:-1] = 0.25 * p[:-2] + 0.5 * p[1:-1] + 0.25 * p[2:]
    seg = np.r_[0, np.cumsum(np.linalg.norm(np.diff(p, axis=0), axis=1))]
    s = np.arange(0, seg[-1], step)
    return np.stack([np.interp(s, seg, p[:, k]) for k in range(3)], 1).astype(np.float32)


def slide_mesh(shape, ring):
    # the tube round that line: for every point along it, `ring` points round it, and which way each faces
    p = slide_path(shape)
    t = np.gradient(p, axis=0)
    t /= np.linalg.norm(t, axis=1, keepdims=True)
    side = np.cross(t, [0.0, 1.0, 0.0])
    side /= np.linalg.norm(side, axis=1, keepdims=True)
    up = np.cross(side, t)
    a = np.linspace(0, TAU, ring, endpoint=False)
    normal = np.cos(a)[None, :, None] * side[:, None] + np.sin(a)[None, :, None] * up[:, None]
    return (p[:, None] + SLIDE_TUBE * normal).astype(np.float32), normal.astype(np.float32)


def grout(u, v, foot):
    # 1 on the lines between the tiles, fading out where the tiles get too small to see
    fu, fv = np.mod(u / TS, 1), np.mod(v / TS, 1)
    d = np.minimum(np.minimum(fu, 1 - fu), np.minimum(fv, 1 - fv))
    return smooth((0.05 - d) / 0.03) * np.clip(1.3 - 2.5 * foot, 0, 1)


# (c) @dwcminh.ascii, see LICENSE.txt. Not for use with AI tools: no feeding this code to
# AI models, no training on it, no having an AI rework it.

# window

TITLE = "ASCII Poolrooms"
CW, CH, FONT_PX = 8, 12, 13
COLS, ROWS = 99, 86
W, H = COLS * CW, ROWS * CH
MONO = "consolas,menlo,dejavusansmono,couriernew,monospace"
HINT = "Space pause · R restart · S screenshot · Esc quit"
Q = 5                                           # the soft planes are painted at a fifth of the size, then smoothed up
SPRITE_W, SPRITE_H = 128, 640                   # a pillar picture, water line to ceiling


def pillar_pictures():
    # one pillar, painted once at a good size: round, tiled, lit turquoise from the water below and
    # silver on the side that faces the moon; and the moving light the water throws on it, as two
    # layers that drift past each other
    u = (np.arange(SPRITE_W) + 0.5) / SPRITE_W * 2 - 1
    a = np.arcsin(np.clip(u, -1, 1))[None]                     # round from the side facing you
    up = ((1 - (np.arange(SPRITE_H) + 0.5) / SPRITE_H) * HC)[:, None]   # how high above the water
    face = 0.18 + 0.82 * np.cos(a) ** 0.9                       # round: bright where it faces you, dark at the sides
    rounds = 10
    around = (a + np.pi / 2) / TAU * rounds
    du = np.abs(around - np.round(around))
    dv = np.abs(up / TS - np.round(up / TS))
    line = np.maximum(smooth((0.05 - du / np.maximum(np.cos(a), 0.15)) / 0.03), smooth((0.035 - dv) / 0.02))
    below = 0.10 + 1.10 * np.exp(-up / 0.85)                  # the glow of the pool, from below
    rim = np.clip(np.sin(a) * 0.8 + 0.2, 0, 1) ** 1.5 * (0.35 + 0.65 * smooth(up / 1.2))   # the moonlight, from up on the right
    tile = TILE_RGB / 255.0 * (1 - 0.30 * line)[..., None]
    night = np.array([0.22, 0.27, 0.40])                      # the cool light of the night, everywhere
    sheen = np.exp(-((u + 0.30) / 0.22) ** 2)[None] * 0.35    # glazed tiles: a soft gleam down one side
    # what the night and the moon give it, and what the pool gives it for each unit of the pool's colour
    base = tile * (night * 0.8 + MOONLIT / 255.0 * rim[..., None] * 0.45) * face[..., None] + 0.25 * (sheen * (0.4 + below))[..., None]
    glow = tile * (below * face * 1.6)[..., None] + 0.6 * (sheen * (0.4 + below))[..., None]
    # the light off the water, tiling every NT rows so it can drift up and down and still loop
    rows = np.arange(NT)[:, None].astype(np.float32)
    cu = (around * 46).astype(np.float32) + 0 * rows
    web = lambda noise: np.exp(-((soft_tex(noise, cu, rows * 0.6) - 0.5) / 0.045) ** 2)     # thin wavy threads
    fall = np.exp(-up / 1.25) * face
    return (base * 255).astype(np.float32), (glow * 255).astype(np.float32), web(NOISE_A), web(NOISE_B), fall


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
        self.mirror = pygame.Surface((w, h))
        self.glow = pygame.Surface((w, h))
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

        # the lens, and the hall worked out once for the small grid, and for every cell
        self.f, self.yh = FOCAL * h, HORIZON * h
        self.tw, self.th = w // Q, h // Q
        px, py = (np.arange(self.tw) + 0.5) * Q, (np.arange(self.th) + 0.5) * Q
        self.geo = planes(((px - w / 2) / self.f)[None], ((self.yh - py) / self.f)[:, None])
        cx, cy = np.arange(cols + 1) * cw, np.arange(rows + 1) * ch
        self.corner = planes(((cx - w / 2) / self.f)[None], ((self.yh - cy) / self.f)[:, None])
        self.pix = Q / self.f                                   # how wide one point of the small grid is, per metre away
        # how much the water mirrors, row by row: little at your feet, nearly all towards the far end
        self.fres = np.clip(0.10 + 0.88 * (1 - np.clip(-self.geo["dy"] * 2.4, 0, 1)) ** 2, 0, 0.95).astype(np.float32)
        self.first_wet = int(self.yh) + 1                       # the first screen row that can be water
        self.base, self.glow_pic, self.web_a, self.web_b, self.fall = pillar_pictures()
        self.moon = moon_picture(MOON_R * h)
        # the slides, finer when near, coarser further off (and in the water); and where along the stretch each stands
        self.slides = []
        for shape in (spiral_path, wave_path):
            near, far = slide_mesh(shape, 18), slide_mesh(shape, 10)
            self.slides.append((near, (far[0][::2], far[1][::2]), float(near[0][..., 2].mean())))
        self.mask = pygame.Surface((w // 2, h // 2))            # which slice of the slide is where, for the letters


    # the soft planes: glass roof, walls, windows and the glowing water, painted small with numpy

    def lamp_light(self, x, z, cz, t):
        # the light of the lamps under the water on each point of the pool, in their colour (0..1 a channel)
        out = np.zeros(x.shape, np.float32)
        for i, (lx, lz) in enumerate(LAMPS):
            dz = np.mod(z - lz + STRIP / 2, STRIP) - STRIP / 2
            out += lamp_power(t, i) * np.exp(-((x - lx) ** 2 + dz * dz) / 2.6)
        out *= 1 + 2.6 * surge(t, z - cz)                       # the wave of light, passing
        return out[..., None] * self.hue

    def colours(self, t):
        # the lamps' colour, and what it makes of the pool's light, its moving net and the haze
        self.hue = TEAL
        self.pool_light = self.hue * 250.0              # what the glowing pool throws on everything round it
        self.caustic = 110.0 + self.hue * 145.0
        self.haze = HAZE_DARK + self.hue * 115.0

    def shade(self, kind, x, y, z, dist, cz, t, light, only=None, lamps=None):
        # the colour of the hall's planes, each worked out only where it shows (and only within `only`);
        # and, for the roof, where its frames are
        far = self.haze
        POOL_LIGHT, CAUSTIC_RGB = self.pool_light, self.caustic
        img = np.empty(kind.shape + (3,), np.float32)
        img[:] = far
        steel = np.zeros(kind.shape, np.float32)
        pick = lambda m: m if only is None else (m & only)
        # the glass roof: the night sky through it (darkest overhead), a faint teal sheen of the pool on
        # the glass, and the steel frames (drawn sharp later; here soft, for the water to mirror)
        m = pick(kind == K_CEIL)
        if m.any():
            xs, zs, ds = x[m], z[m], dist[m]
            low = 1 - np.exp(-ds / 10.0)
            sky = SKY_TOP + (SKY_LOW - SKY_TOP) * low[:, None] + POOL_LIGHT * (0.06 * np.exp(-ds / 6.0))[:, None]
            bar = frames(xs, zs, ds * self.pix) * (1 - smooth((ds - 4.0) / 14.0))
            steel[m] = bar
            img[m] = sky + (FRAME_RGB - sky) * bar[:, None]
        # walls: dark tiles, lit from the water below; on the right the windows, looking out on the night
        m = pick(np.isin(kind, (K_LEFT, K_RIGHT)))
        if m.any():
            ys, zs, ds = y[m], z[m], dist[m]
            line = grout(zs, ys, ds * self.pix)
            low, near = np.exp(-np.clip(ys, 0, None) / 0.9), np.exp(-ds / 9.0)
            wall = WALL_RGB * (1 - 0.35 * line)[:, None] + POOL_LIGHT * (light * low * 0.45)[:, None]
            wall = wall + CAUSTIC_RGB * (caustics(zs, ys, t) * light * low * 0.25 * near)[:, None]
            right = kind[m] == K_RIGHT
            glass = window(zs, ys) * right
            up = np.clip((ys - WIN_Y[0]) / (WIN_Y[1] - WIN_Y[0]), 0, 1)[:, None]
            sky = SKY_LOW * 1.25 + (SKY_TOP - SKY_LOW * 1.25) * up ** 0.8     # the night outside, a little lighter low down
            mull = grout(zs * 2, ys * 2, ds * self.pix * 2)
            wall = wall + (sky * (1 - 0.5 * mull)[:, None] - wall) * glass[:, None]
            img[m] = wall
        # the floor: the glowing pool, wall to wall, brightest over the lamps, with the net of light moving on it
        m = pick(kind == K_FLOOR)
        if m.any():
            xs, zs, ds = x[m], z[m], dist[m]
            lamp = lamps[m]
            water = WATER_DEEP + self.hue * (40.0 * light) + lamp * 230.0
            sharp = np.clip(1.5 - ds / 4.0, 0, 1)               # far off the net is finer than a point: only its glow
            net = caustics(xs, zs, t, 0.035, fine=True) * sharp + 0.12 * (1 - sharp)
            water = water + (CAUSTIC_RGB * 0.6 + lamp * 120.0) * (net * light * 0.30)[:, None]
            img[m] = water
        m = kind != K_HAZE if only is None else only & (kind != K_HAZE)
        haze = (1 - np.exp(-dist[m] / FOG)) * np.where(kind[m] == K_CEIL, 0.35, 1.0)    # the sky through the roof stays dark
        img[m] = img[m] + (far - img[m]) * haze[:, None]
        return img, steel

    def coarse_lamps(self, x, z, cz, t):
        # the lamps' glow is soft, so it is worked out on every other point each way and spread
        th, tw = x.shape
        glow = self.lamp_light(x[::2, ::2], z[::2, ::2], cz, t)     # rows, columns, 3
        return np.repeat(np.repeat(glow, 2, 0), 2, 1)[:th, :tw]

    def backdrop(self, t, light, view, pic, fog):
        g, cz = self.geo, DRIFT * t
        lamps = self.coarse_lamps(g["x"], g["z"] + cz, cz, t)
        img, _ = self.shade(g["kind"], g["x"], g["y"], g["z"] + cz, g["dist"], cz, t, light, lamps=lamps)
        wet = g["kind"] == K_FLOOR
        mirror, steel = self.shade(g["rkind"], g["rx"], g["ry"], g["rz"] + cz, g["rdist"], cz, t, light, only=wet)   # the roof and walls, mirrored
        # where the water shows the open sky through the roof (for the mirrored moon and stars)
        self.sky_in_water = np.where(wet & (g["rkind"] == K_CEIL), (1 - steel) * self.fres, 0).astype(np.float32)
        # the pillars mirrored in the water, small: the ripples blur them anyway
        flat = mirror.transpose(1, 0, 2)
        for z, px, pzw, r, sx, half, ytop, ybot, i in view:
            self.draw_pillar(flat, pic, sx, half, z, r, fog, float(1 - np.exp(-z / FOG)), mirrored=True, scale=Q)
        mix = np.where(wet, self.fres, 0)[..., None]
        img = img * (1 - mix)
        to_surface = lambda a: pygame.surfarray.make_surface(np.clip(a, 0, 255).astype(np.uint8).transpose(1, 0, 2))
        pygame.transform.smoothscale(to_surface(img), (self.w, self.h), self.scene)
        pygame.transform.smoothscale(to_surface(mirror * mix), (self.w, self.h), self.mirror)    # only as much as the water mirrors

    def place(self, x, y, z):
        # a point in the hall (z measured from you) -> where it is on screen
        return self.w / 2 + self.f * x / z, self.yh + self.f * (EYE - y) / z

    def pillars(self, cz):
        # the pillars in view, furthest first: where, how far, how big on screen
        out = []
        for i, (px, pz, r) in enumerate(PILLARS):
            for k in range(0, 4):
                z = pz + STRIP * k - cz
                if z < 0.6 or z > PILLAR_FAR:
                    continue
                sx, ytop = self.place(px, HC, z)
                _, ybot = self.place(px, 0.0, z)
                half = self.f * r / z
                if sx + half < 0 or sx - half > self.w:
                    continue
                out.append((z, px, pz + STRIP * k, r, sx, half, ytop, ybot, i))
        return sorted(out, reverse=True)

    @staticmethod
    def blit_part(target, picture, left, top, width, height, flags=0):
        # put a picture on a surface at any size, scaling only the part that shows
        tw_, th_ = target.get_size()
        x0, y0 = max(0, left), max(0, top)
        x1, y1 = min(tw_, left + width), min(th_, top + height)
        if x1 - x0 < 1 or y1 - y0 < 1:
            return
        pw, ph = picture.get_size()
        sx0, sy0 = (x0 - left) / width * pw, (y0 - top) / height * ph
        sx1, sy1 = (x1 - left) / width * pw, (y1 - top) / height * ph
        part = picture.subsurface((int(sx0), int(sy0), max(1, min(pw - int(sx0), int(np.ceil(sx1 - sx0)))),
                                   max(1, min(ph - int(sy0), int(np.ceil(sy1 - sy0))))))
        target.blit(pygame.transform.smoothscale(part, (int(x1 - x0), int(y1 - y0))), (int(x0), int(y0)), special_flags=flags)

    def pillar_picture(self, t, light):
        # this frame's pillar: what the night gives it (with a white edge to the moving light off the
        # water), and what the pool gives it per unit of its colour (two nets drifting past each other,
        # whole tiles every loop)
        a = np.roll(self.web_a, int(NT * t / LOOP), 0)
        b = np.roll(self.web_b, -int(2 * NT * t / LOOP), 0)
        net = (np.clip((a + b)[np.arange(SPRITE_H) % NT] * self.fall, 0, 1.5) / 1.5)[..., None] * 255.0
        return self.base + net * 0.25 + (self.glow_pic + net * 0.75) * (self.hue * 0.82 * light)

    def draw_pillar(self, arr, pic, sx, half, z, r, fog, haze, mirrored=False, scale=1):
        # one round pillar into a pixel array (x, y, 3), column by column: every column of the pillar is at
        # its own distance, so the foot and the top curve round and so do the rings of tiles; in the water
        # upside down. With scale the array is that many times smaller than the screen.
        aw, ah = arr.shape[0], arr.shape[1]
        c0, c1 = int(max(0, np.ceil((sx - half) / scale))), int(min(aw, np.floor((sx + half) / scale) + 1))
        if c1 <= c0:
            return
        u = np.clip(((np.arange(c0, c1) + 0.5) * scale - sx) / half, -1, 1)
        zc = z - r * np.sqrt(1 - u * u)                         # the front of the pillar is nearer than its sides
        if mirrored:
            top, bot = self.yh + self.f * EYE / zc, self.yh + self.f * (EYE + HC) / zc
        else:
            top, bot = self.yh + self.f * (EYE - HC) / zc, self.yh + self.f * EYE / zc
        y0, y1 = int(max(0, np.floor(top.min() / scale))), int(min(ah, np.ceil(bot.max() / scale)))
        if y1 <= y0:
            return
        y = (np.arange(y0, y1)[None] + 0.5) * scale
        height = (y - self.yh) * zc[:, None] / self.f            # how far below your eyes, at each pixel
        up = (height - EYE) if mirrored else (EYE - height)      # how far above the water the pillar is there
        inside = (up >= 0) & (up <= HC)
        row = np.clip(((1 - up / HC) * SPRITE_H).astype(np.int32), 0, SPRITE_H - 1)
        col = np.clip(((u + 1) / 2 * SPRITE_W).astype(np.int32), 0, SPRITE_W - 1)[:, None]
        block = arr[c0:c1, y0:y1]
        colour = pic[row[inside], np.broadcast_to(col, row.shape)[inside]]
        block[inside] = np.clip(colour * (1 - haze) + fog * haze, 0, 255).astype(block.dtype)

    def water_rows(self, t):
        # ripple the mirrored hall: every row of water slides a little sideways, more near you
        rows = np.arange(self.first_wet, self.h)
        z = self.f * EYE / np.maximum(rows - self.yh, 1.0)
        zw = z + DRIFT * t
        shift = (0.020 * self.f / z) * (np.sin(TAU * zw / (STRIP / 24) - 7 * BEAT * t) + 0.6 * np.sin(TAU * zw / (STRIP / 37) + 11 * BEAT * t + 1.3))
        shift = np.clip(np.round(shift), -9, 9).astype(np.int32)
        src = self.mirror.copy()
        for y, s in zip(rows.tolist(), shift.tolist()):
            if s:
                self.mirror.blit(src, (0, y), area=(-s if s < 0 else 0, y, self.w, 1)) if s < 0 else \
                    self.mirror.blit(src, (s, y), area=(0, y, self.w - s, 1))

    def pool_floor(self, t, light):
        # the tiles of the pool floor near you, seen through the water: thin lines that wobble with the ripples
        cz = DRIFT * t
        shallow = DEPTH * 0.75                                  # the water makes the floor look shallower
        colour = tuple(int(c) for c in np.clip(WATER_DEEP * 0.6 + self.hue * 40.0 * light, 0, 255))
        wob = lambda z: 0.012 * np.sin(TAU * z / (STRIP / 12) - 9 * BEAT * t)
        z0 = np.ceil((cz + 1.6) / TS) * TS
        for zl in np.arange(z0, cz + 9.0, TS):                  # lines across
            zr = zl - cz
            xs = np.linspace(XL, XR, 64)
            sx = self.w / 2 + self.f * (xs + wob(zl + xs)) / zr
            sy = self.yh + self.f * (EYE + shallow) / zr + 0 * xs
            self.line(np.stack([sx, sy], 1), colour, zr)
        zs = np.linspace(cz + 1.6, cz + 9.0, 40)
        zr = zs - cz
        for xl in np.arange(np.ceil(XL / TS) * TS, XR, TS):     # lines along
            sx = self.w / 2 + self.f * (xl + wob(zs + xl)) / zr
            sy = self.yh + self.f * (EYE + shallow) / zr
            self.line(np.stack([sx, sy], 1), colour, 4.0)

    def line(self, pts, colour, z):
        fade = float(np.clip(1.4 - z / 7.0, 0, 1))
        if fade > 0.05:
            c = tuple(int(v * fade + 40 * (1 - fade)) for v in colour)
            pygame.draw.aalines(self.scene, c, False, pts.tolist())

    def spark(self, surf, x, y, size, colour):
        # a soft point of light
        key = (int(size / 4), tuple((np.asarray(colour) // 16).astype(int).tolist()))
        if key not in self.tinted:
            pic = pygame.transform.smoothscale(self.halo, (key[0] * 4 + 4,) * 2)
            pic.fill(tuple(min(255, c * 16 + 8) for c in key[1]), special_flags=pygame.BLEND_MULT)
            self.tinted[key] = pic
        pic = self.tinted[key]
        surf.blit(pic, (x - pic.get_width() / 2, y - pic.get_height() / 2), special_flags=pygame.BLEND_ADD)

    # (c) @dwcminh.ascii, see LICENSE.txt. Not for use with AI tools: no feeding this code to
    # AI models, no training on it, no having an AI rework it.

    def lamps(self, t, cz):
        # the lamps themselves, glowing under the water, white at the heart
        self.lamp_cells = []
        for i, (lx, lz) in enumerate(LAMPS):
            hue = self.hue
            for k in range(-1, 4):
                z = lz + STRIP * k - cz
                if z < 1.0 or z > 40:
                    continue
                wave = float(surge(t, z))                       # as the wave of light passes, it flares white
                on = float(lamp_power(t, i)) * (1 + 0.8 * wave)
                sx, sy = self.place(lx, -0.32, z)
                size = float(np.clip(self.f * 0.9 / z * (1 + 1.2 * wave), 10, 260))
                colour = np.clip(hue * 255 * on * 1.05 + 220 * wave, 0, 255)
                self.spark(self.scene, sx, sy, size, colour)
                self.spark(self.scene, sx, sy, size * 0.35, np.clip(colour * 0.7 + 90, 0, 255))
                self.lamp_cells.append((sx, sy, on, hue))

    # the night through the roof: so far off that it stays put on the screen while the frames pass

    def open_sky(self, sx, sy, mirrored=False):
        # how clearly a point of the screen shows the open sky (through the glass, between the frames);
        # mirrored: how clearly the water there gives it back
        r = np.clip((np.asarray(sy) / Q).astype(int), 0, self.th - 1)
        c = np.clip((np.asarray(sx) / Q).astype(int), 0, self.tw - 1)
        if mirrored:
            return self.sky_in_water[r, c]
        return (self.geo["kind"][r, c] == K_CEIL).astype(np.float32)

    def night(self, t):
        # the stars and the moon on the roof, and the same given back by the water (before it ripples)
        s = SKY_STARS
        x, y = s["x"] * self.w, s["y"] * self.yh
        b = s["b"] * (0.60 + 0.40 * np.sin(s["rate"] * BEAT * t + s["seed"]))
        self.stars = []
        for surf, ys, bs in ((self.scene, y, b * self.open_sky(x, y)),
                             (self.mirror, 2 * self.yh - y, b * 0.7 * self.open_sky(x, 2 * self.yh - y, mirrored=True))):
            ok = (bs > 0.08) & (ys >= 1) & (ys < self.h - 2) & (x >= 1) & (x < self.w - 2)
            ix, iy, bv = x[ok].astype(int), ys[ok].astype(int), bs[ok]
            px = pygame.surfarray.pixels3d(surf)
            rgb_ = STAR_RGB[None] * np.clip(bv, 0, 1)[:, None]
            px[ix, iy] = np.maximum(px[ix, iy], rgb_.astype(np.uint8))
            big = bv > 0.5
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                px[ix[big] + dx, iy[big] + dy] = np.maximum(px[ix[big] + dx, iy[big] + dy], (rgb_[big] * 0.45).astype(np.uint8))
            del px
            self.stars.append((ix, iy, bv))
        # the moon: its glow in the sky, its disc, and its broken path on the water
        mx, my = self.w / 2 + self.f * MOON_AT[0], self.yh - self.f * MOON_AT[1]
        self.spark(self.scene, mx, my, self.h * 0.30, MOON_RGB * 0.22)
        self.spark(self.scene, mx, my, self.h * 0.11, MOON_RGB * 0.30)
        self.scene.blit(self.moon, (mx - self.moon.get_width() / 2, my - self.moon.get_height() / 2), special_flags=pygame.BLEND_ADD)
        ry = 2 * self.yh - my
        k = float(self.open_sky(mx, ry, mirrored=True))
        if k > 0.02:
            pic = self.moon.copy()
            pic.fill((int(255 * k),) * 3, special_flags=pygame.BLEND_MULT)
            self.mirror.blit(pic, (mx - pic.get_width() / 2, ry - pic.get_height() / 2), special_flags=pygame.BLEND_ADD)
            self.spark(self.mirror, mx, ry, self.h * 0.10, MOON_RGB * 0.30 * k)
        self.moon_at = (mx, my, ry)

    def falling(self, t):
        # stars falling across the roof, and through the water upside down
        h = self.h
        for t0, across, down, far, way in FALLING:
            age = (t - t0) / 0.8
            if 0 <= age < 1:
                step = np.array([0.34 * way, 0.15]) * h * 0.024    # which way, and one piece of its tail
                a = np.array([across * self.w, down * h]) + step / 0.024 * far * age
                tail = pygame.Surface(self.scene.get_size())
                for k in range(14):                             # head first, the tail fading behind it
                    for mirror, gain in ((False, 1.0), (True, 0.45)):
                        p, q = a - step * k, a - step * (k + 1)
                        if mirror:
                            p, q = (p[0], 2 * self.yh - p[1]), (q[0], 2 * self.yh - q[1])
                        pygame.draw.line(tail, tuple(int(c * gain * (1 - age) ** 0.5 * (1 - k / 14) ** 1.5) for c in (235, 240, 255)),
                                         p, q, 3 if k < 5 else 2)
                self.scene.blit(tail, (0, 0), special_flags=pygame.BLEND_ADD)
                self.spark(self.scene, float(a[0]), float(a[1]), 34.0, rgb(235, 240, 255) * (1 - age) ** 0.5)
                self.spark(self.scene, float(a[0]), float(2 * self.yh - a[1]), 30.0, rgb(235, 240, 255) * 0.45 * (1 - age) ** 0.5)

    def roof(self, cz):
        # the steel frames of the glass roof, drawn sharp: along the hall and across it, fading into the haze
        hw = BAR_W / 2
        def colour(z):
            k = float(smooth((z - 4.0) / 14.0))                 # far off they melt into the night beyond
            c = FRAME_RGB * (1 - k) + (SKY_TOP + SKY_LOW) / 2 * k
            return tuple(int(v) for v in c)
        for xb in np.arange(np.ceil(XL / BAR) * BAR, XR, BAR):        # along
            for z0, z1 in ((0.35, 1.5), (1.5, 3.5), (3.5, 6.0), (6.0, 9.0), (9.0, 13.0), (13.0, 18.0)):
                pts = [self.place(xb - hw, HC, z0), self.place(xb + hw, HC, z0), self.place(xb + hw, HC, z1), self.place(xb - hw, HC, z1)]
                pygame.draw.polygon(self.scene, colour((z0 + z1) / 2), pts)
        for zb in np.arange(np.ceil((cz + 0.5) / BAR) * BAR, cz + 18.0, BAR):  # across
            z = zb - cz
            (x0, y0), (x1, _) = self.place(XL, HC, z), self.place(XR, HC, z)
            thick = self.f * (HC - EYE) * (1 / max(z - hw, 0.1) - 1 / (z + hw))
            if thick >= 1.5:
                pygame.draw.rect(self.scene, colour(z), (x0, y0 - thick / 2, x1 - x0, thick))
            else:
                pygame.draw.line(self.scene, colour(z), (x0, y0), (x1, y0), 1)

    def ripples_and_drops(self, t):
        # the rings round where the drops have fallen, and the drops falling: light, added to the picture
        self.glow.fill((0, 0, 0))
        cz = DRIFT * t
        for age, across, at in drops(t):
            z = at - cz
            if age < RING_LIFE and z > 0.8:
                cx, cy = self.place(across, 0.0, z)
                for k in range(3):
                    r = RING_SPEED * age - 0.10 * k
                    if r <= 0.02:
                        continue
                    fade = (1 - age / RING_LIFE) ** 1.5 * (1 - 0.3 * k)
                    rx, ry = self.f * r / z, self.f * r * EYE / (z * z)
                    c = tuple(int(v * fade) for v in DROP_RGB)
                    pygame.draw.ellipse(self.glow, c, (cx - rx, cy - ry, 2 * rx, 2 * ry), 2 if k == 0 else 1)
        for since, across, at in drops(t, FALL):
            age = since / FALL
            if age < 1:
                z = at - cz
                y0, y1 = HC * (1 - age * age), HC * (1 - max(age - 0.15, 0) ** 2)
                (ax, ay), (bx, by) = self.place(across, y0, z), self.place(across, y1, z)
                pygame.draw.aaline(self.glow, tuple(int(c * 0.7) for c in DROP_RGB), (bx, by), (ax, ay))
                self.spark(self.glow, ax, ay, 14.0, DROP_RGB * 0.9)
        self.scene.blit(self.glow, (0, 0), special_flags=pygame.BLEND_ADD)

    # the water slide: a tube of flat facets, each lit for the way it faces, drawn furthest first

    def slide_pieces(self, cz, mirrored=False):
        # the facets of the slide that face you, in every copy of it in view, furthest first: how far each
        # is, its corners on screen, its colour and which slice of the tube it belongs to; and the tube's mouth
        dists, quads, colours, slices, mouths = [], [], [], [], []
        f, eye = self.f, np.array([0.0, EYE, 0.0], np.float32)
        hue = self.hue
        moon = np.array([MOON_AT[0], MOON_AT[1], 1.0], np.float32)
        moon /= np.linalg.norm(moon)
        for (slide_near, slide_far, at), k in [(s, k) for s in self.slides for k in range(0, 4)]:
            ahead = at + STRIP * k - cz
            if ahead < -3.0 or ahead > PILLAR_FAR:
                continue
            for verts, normals in ((slide_near if ahead < 11.0 and not mirrored else slide_far),):
                v = verts + np.array([0, 0, STRIP * k - cz], np.float32)
                if v[..., 2].max() < 0.4:
                    continue
                n = normals
                if mirrored:
                    v, n = v * np.array([1, -1, 1], np.float32), n * np.array([1, -1, 1], np.float32)
                # each facet: the four corners between two slices and two points round
                a, b = v[:-1], v[1:]
                quad = np.stack([a, b, np.roll(b, -1, 1), np.roll(a, -1, 1)], 2)          # slices, round, 4, xyz
                fn = n[:-1] + n[1:] + np.roll(n[:-1], -1, 1) + np.roll(n[1:], -1, 1)
                fn /= np.linalg.norm(fn, axis=-1, keepdims=True)
                centre = quad.mean(2)
                look = centre - eye
                dist = np.linalg.norm(look, axis=-1)
                facing = (fn * look).sum(-1) < 0
                ahead = quad[..., 2].min(-1) > 0.3
                dry = centre[..., 1] * (-1 if mirrored else 1) > 0.0    # what is under the water does not show
                keep = facing & ahead & dry
                if not keep.any():
                    continue
                # light: the pool from below in the lamps' colour, the moon from above, a glossy gleam, the night
                ny = fn[..., 1] * (-1 if mirrored else 1)
                pool = np.clip(-ny, 0, 1) * 0.85 + 0.25
                height = centre[..., 1] * (-1 if mirrored else 1)
                pool = pool * (0.45 + 0.9 * np.exp(-np.clip(height, 0, None) / 1.1))
                moonlit = np.clip((fn * moon * np.array([1, -1 if mirrored else 1, 1])).sum(-1), 0, 1)
                view = -look / dist[..., None]
                gleam = np.clip((fn * view).sum(-1), 0, 1) ** 6 * 0.45 * np.clip(ny + 0.6, 0, 1)
                # its own lavender first (it is pale plastic, it keeps its colour, lit softly by the glowing hall),
                # the pool's colour glowing on its underside, the moon catching its top; round: darker where
                # the tube turns away from you
                turn = np.clip((fn * view).sum(-1), 0, 1)
                colour = SLIDE_RGB * (0.60 * 255 + MOONLIT * moonlit[..., None] * 0.40)
                colour = colour + hue * 255 * (pool * 0.22)[..., None]
                colour = colour * (0.50 + 0.50 * turn ** 0.6)[..., None] + 255 * gleam[..., None]
                haze = (1 - np.exp(-dist / FOG))[..., None] * 0.7
                colour = colour + (self.haze - colour) * haze
                if mirrored:
                    colour = colour * 0.85
                sx = self.w / 2 + f * quad[..., 0] / np.maximum(quad[..., 2], 0.05)
                sy = self.yh + f * (EYE - quad[..., 1]) / np.maximum(quad[..., 2], 0.05)
                i, j = np.nonzero(keep)
                dists.append(dist[i, j])
                quads.append(np.stack([sx, sy], -1)[i, j])
                colours.append(np.clip(colour[i, j], 0, 255))
                slices.append(i)
                # the open mouth at its foot, dark inside, glowing a little with the pool
                mouth = v[-1]
                if mouth[:, 2].min() > 0.3:
                    mx = self.w / 2 + f * mouth[:, 0] / mouth[:, 2]
                    my = self.yh + f * (EYE - mouth[:, 1]) / mouth[:, 2]
                    # a pale lip, then the inside of the tube getting darker the deeper you look
                    d0 = float(np.linalg.norm(mouth.mean(0) - eye))
                    ring = np.stack([mx, my], 1)
                    middle = ring.mean(0)
                    dim = 0.85 if mirrored else 1.0
                    for depth, (scale, shade) in enumerate(((1.0, 150), (0.86, 95), (0.62, 55), (0.36, 30))):
                        inside = np.clip(SLIDE_RGB * shade + hue * shade * 0.35, 0, 255) * dim
                        mouths.append((d0 - 0.01 * (depth + 1), (middle + (ring - middle) * scale).tolist(), [int(c) for c in inside]))
        if not dists:
            return np.zeros(0), np.zeros((0, 4, 2)), np.zeros((0, 3)), np.zeros(0, int), mouths
        dists, quads, colours, slices = (np.concatenate(a) for a in (dists, quads, colours, slices))
        order = np.argsort(-dists)
        return dists[order], quads[order], colours[order], slices[order], mouths

    def draw_slices(self, surf, part, mask=None, fres=None):
        # put facets of the slide on a surface (and, for the letters, which slice and how far, on a small mask)
        dists, quads, colours, slices = part
        if fres is not None:                                    # in the water: only as much as it mirrors
            colours = colours * fres[np.clip((quads[:, :, 1].mean(1) / Q).astype(int), 0, self.th - 1)][:, None]
        draw = pygame.draw.polygon
        for p, c in zip(quads.tolist(), colours.astype(int).tolist()):
            draw(surf, c, p)
        if mask is not None:
            tags = np.stack([np.full(len(dists), 255), (slices % 32) * 8, np.minimum(dists * 8, 255)], 1).astype(int).tolist()
            for p, c in zip((quads * 0.5).tolist(), tags):
                draw(mask, c, p)

    def draw_mouths(self, surf, mouths, upto=-1.0, mask=None):
        # the tube's open mouth(s) further than `upto`; returns those still to draw
        rest = []
        for d, pts, c in mouths:
            if d > upto:
                pygame.draw.polygon(surf, c, pts)
                if mask is not None:
                    pygame.draw.polygon(mask, (255, 0, int(min(d * 8, 255))), [(x * 0.5, y * 0.5) for x, y in pts])
            else:
                rest.append((d, pts, c))
        return rest

    def draw_scene(self, t):
        cz = DRIFT * t
        light = 1.0 + 1.0 * surge(t)                            # the pool is lit all night; brighter as the wave of light runs
        self.colours(t)
        view = self.pillars(cz)
        pic = self.pillar_picture(t, light)
        fog = self.haze
        self.backdrop(t, light, view, pic, fog)
        self.night(t)
        self.falling(t)
        self.roof(cz)
        # the mirrored hall rippled, then laid on the water; the slide mirrored too
        *mirrored, mouths = self.slide_pieces(cz, mirrored=True)
        fres = self.fres[:, self.tw // 2]
        self.draw_slices(self.mirror, mirrored, fres=fres)
        self.draw_mouths(self.mirror, [(d, p, [int(v * fres[int(np.clip(np.mean([q[1] for q in p]) / Q, 0, self.th - 1))]) for v in c])
                                       for d, p, c in mouths])
        self.water_rows(t)
        self.pool_floor(t, light)
        self.scene.blit(self.mirror, (0, 0), special_flags=pygame.BLEND_ADD)
        self.lamps(t, cz)
        # the pillars and the slide, furthest first: before each pillar, the facets further off than it
        # (a pillar wipes the slide off the mask where it stands in front)
        self.mask.fill((0, 0, 0))
        dists, quads, colours, slices, mouths = self.slide_pieces(cz)
        start = 0

        def slide_upto(d):
            # the facets (and mouth) of the slide further off than d
            nonlocal start, mouths
            stop = int(np.searchsorted(-dists, -d))
            self.draw_slices(self.scene, (dists[start:stop], quads[start:stop], colours[start:stop], slices[start:stop]), mask=self.mask)
            mouths = self.draw_mouths(self.scene, mouths, d, mask=self.mask)
            start = stop

        for z, px, pzw, r, sx, half, ytop, ybot, i in sorted(view, key=lambda p: -np.hypot(p[0], p[1])):
            slide_upto(np.hypot(z, px))
            arr = pygame.surfarray.pixels3d(self.scene)
            self.draw_pillar(arr, pic, sx, half, z, r, fog, float(1 - np.exp(-z / FOG)))
            del arr
            pygame.draw.rect(self.mask, (0, 0, 0), ((sx - half) / 2, ytop / 2, half, (ybot - ytop) / 2))
        slide_upto(-1.0)
        self.view = view
        self.ripples_and_drops(t)
        return light

    # the letters: one for every cell, chosen by what the painting shows there

    # (c) @dwcminh.ascii, see LICENSE.txt. Not for use with AI tools: no feeding this code to
    # AI models, no training on it, no having an AI rework it.

    def letters(self, t, cell):
        rows, cols, cz = self.rows, self.cols, DRIFT * t
        g = self.corner
        kind = g["kind"].copy()
        x, y, z = g["x"], g["y"], g["z"] + cz
        floor = kind == K_FLOOR
        kind = np.where(floor, K_WATER, kind)
        kind = np.where((kind == K_RIGHT) & (window(z, y) > 0.5), K_GLASS, kind)
        # what each corner's tiles are: the pool floor lies flat, walls stand, glass has panes
        shallow = (EYE + DEPTH * 0.75) / np.maximum(-g["dy"], 1e-3)
        fx, fz = g["dx"] * shallow, shallow + cz
        fx = fx + 0.012 * np.sin(TAU * fz / (STRIP / 12) - 9 * BEAT * t)
        roof = kind == K_CEIL                                   # the roof's frames, one "tile" between each two
        u = np.select([kind == K_WATER, kind == K_GLASS, roof], [fx, z * 0.5, x * TS / BAR], z) / TS
        v = np.select([kind == K_WATER, kind == K_GLASS, roof], [fz, y * 0.5, z * TS / BAR], y) / TS
        near = np.where(kind == K_WATER, shallow, g["dist"])
        corners = lambda a: np.stack([a[:-1, :-1], a[:-1, 1:], a[1:, :-1], a[1:, 1:]])
        K, U, V, N = corners(kind), corners(u), corners(v), corners(near)
        same = (K.min(0) == K.max(0))
        k = K[0]
        span_u = np.floor(U).max(0) - np.floor(U).min(0)
        span_v = np.floor(V).max(0) - np.floor(V).min(0)

        def slope(a):
            # the way a tile line runs on screen: across the way its value changes
            gx = ((a[1] - a[0]) + (a[3] - a[2])) / 2 / self.cw
            gy = ((a[2] - a[0]) + (a[3] - a[1])) / 2 / self.ch
            return SLOPE_G[np.round((np.arctan2(-gx, -gy) % np.pi) / (np.pi / 4)).astype(int) % 4]

        tiled = same & np.isin(k, (K_LEFT, K_RIGHT, K_GLASS, K_CEIL))       # the pool floor is drawn as fine lines instead
        char = np.zeros((rows, cols), int)
        char = np.where(tiled & (span_u == 1) & (span_v == 0), slope(U), char)
        char = np.where(tiled & (span_v == 1) & (span_u == 0), slope(V), char)
        char = np.where(tiled & (span_u == 1) & (span_v == 1), C("+"), char)
        char = np.where(tiled & (np.maximum(span_u, span_v) >= 2) & (self.hash % 3 == 0) & (k != K_CEIL), C("."), char)
        # where one plane meets another: an outline
        across = (K[0] != K[1]) | (K[2] != K[3])
        down = (K[0] != K[2]) | (K[1] != K[3])
        char = np.where(~same, np.where(across & down, C("+"), np.where(across, C("|"), C("-"))), char)
        # open water further off, and the ceiling: by how bright the painting is there
        lum = cell @ np.array([0.30, 0.55, 0.15])
        level = np.clip(((lum - 0.12) / 0.12 + (self.hash % 100) / 100.0 - 0.5).astype(int), 0, 3)
        quick = (self.hash + int(t * 4.2)) % 12                # 84 steps a loop, so it comes round with it
        water = (k == K_WATER) & (char == 0) & (self.hash % 2 == 0)        # every other cell: the painting shows between
        char = np.where(water, WATER_FILL[level, quick], char)
        walls = same & np.isin(k, (K_LEFT, K_RIGHT)) & (N.min(0) > 12.0)     # far walls: no tile lines, only haze
        char = np.where(walls, 0, char)
        roof_far = same & (k == K_CEIL) & (N.min(0) > 9.0)      # frames too far off to draw: only the night
        char = np.where(roof_far, 0, char)
        ink = np.select([k == K_CEIL, k == K_WATER, k == K_GLASS], [INK[K_CEIL], INK[K_WATER], INK[K_GLASS]], INK[K_LEFT])
        ink = np.where(k == K_HAZE, 0.0, ink)
        # the pillars, furthest first: their tiles round the curve, an edge at each side
        rows_y = (np.arange(rows + 1) * self.ch).astype(np.float32)
        cols_x = (np.arange(cols + 1) * self.cw).astype(np.float32)
        # the slide, read off its mask: which slice of the tube is in each cell, and how far off
        m = pygame.surfarray.pixels3d(self.mask)
        my_, mx_ = ((np.arange(rows) + 0.5) * self.ch / 2).astype(int), ((np.arange(cols) + 0.5) * self.cw / 2).astype(int)
        cellmask = m[mx_][:, my_].transpose(1, 0, 2).astype(np.int32)    # rows, cols, 3
        del m
        tube = cellmask[..., 0] > 128
        slice_ = cellmask[..., 1]
        tube_far = np.where(tube, cellmask[..., 2] / 8.0, 1e9)
        front = np.zeros((rows, cols), bool)                    # where a pillar or the slide stands in front of everything
        for zp, px, pzw, r, sx, half, ytop, ybot, i in self.view:
            c0, c1 = int(max(0, np.floor((sx - half) / self.cw))), int(min(cols, np.ceil((sx + half) / self.cw)))
            if c1 <= c0:
                continue
            mid = np.clip(((np.arange(c0, c1) + 0.5) * self.cw - sx) / half, -1, 1)
            zc = zp - r * np.sqrt(1 - mid * mid)               # each column of the pillar at its own distance
            up = (EYE - (rows_y[:, None] - self.yh) * zc[None] / self.f) / TS     # tiles above the water, at every cell corner
            inside = (up[:-1] <= HC / TS) & (up[1:] >= 0)
            inside &= ~(tube[:, c0:c1] & (tube_far[:, c0:c1] < np.hypot(zp, px) - r))   # unless the slide is in front
            horiz = np.floor(up[1:]) != np.floor(up[:-1])
            uu = np.clip((cols_x[c0:c1 + 1] - sx) / half, -1, 1)
            sides = (np.abs(uu[:-1]) >= 0.999) | (np.abs(uu[1:]) >= 0.999)
            # the rings of grout round the pillar (curving with it), an outline at each side; between, the tiles' faint dots
            dots = np.where((self.hash[:, c0:c1] % 4) == 0, C("."), 0)
            pc = np.where(horiz, C("-"), dots)
            pc = np.where(sides[None], C("|"), pc)
            if half < self.cw * 0.8:                            # far pillars: just a stroke
                pc = np.full_like(pc, C("|"))
            char[:, c0:c1] = np.where(inside, pc, char[:, c0:c1])
            ink[:, c0:c1] = np.where(inside, INK[K_PILLAR], ink[:, c0:c1])
            front[:, c0:c1] |= inside
        # the slide's own letters: an outline where the tube ends against what is behind it, rings across
        # it every few slices, and its glossy face otherwise left to the painting
        visible = tube & ~(front & (tube_far > 0))              # pillars already cleared it from the mask where they are in front
        edge_ = visible & ~(np.roll(visible, 1, 0) & np.roll(visible, -1, 0) & np.roll(visible, 1, 1) & np.roll(visible, -1, 1))
        p = visible.astype(np.float32)
        gx, gy = (np.roll(p, -1, 1) - np.roll(p, 1, 1)) / self.cw, (np.roll(p, -1, 0) - np.roll(p, 1, 0)) / self.ch
        outline = SLOPE_G[np.round((np.arctan2(gx, -gy) % np.pi) / (np.pi / 4)).astype(int) % 4]
        band = (slice_ // 64) != (np.roll(slice_, -1, 0) // 64)          # a ring every eight slices
        ring = visible & ~edge_ & band
        char = np.where(visible, np.where(edge_, outline, np.where(ring, C("="), np.where(self.hash % 5 == 0, C("."), 0))), char)
        ink = np.where(visible, 0.55, ink)
        front |= visible
        tint = np.clip(cell * 1.55 + 0.05, 0, 1) * ink[..., None]
        # the stars, on the roof and in the water, where nothing stands in front of them
        for (ix, iy, bv), dim in zip(self.stars, (1.0, 0.75)):
            rr, cc = np.clip(iy // self.ch, 0, rows - 1), np.clip(ix // self.cw, 0, cols - 1)
            free = ((char[rr, cc] == 0) | (dim < 1.0)) & ~front[rr, cc]
            for lo, glyph in ((0.28, "."), (0.55, "+"), (0.80, "*")):
                sel = free & (bv >= lo)
                char[rr[sel], cc[sel]] = C(glyph)
                tint[rr[sel], cc[sel]] = np.clip(STAR_RGB[None] / 255.0 * (0.45 + 0.6 * bv[sel])[:, None] * dim, 0, 1)
        # the moon keeps its own face: no letters over its disc, so its seas show
        mx, my, ry = self.moon_at
        rad = MOON_R * self.h
        cy_, cx_ = (np.arange(rows)[:, None] + 0.5) * self.ch, (np.arange(cols)[None] + 0.5) * self.cw
        disc = (np.hypot(cx_ - mx, cy_ - my) < rad * 1.1) & ~front
        char = np.where(disc, 0, char)
        for sx, sy, p, hue in self.lamp_cells:
            if 0 <= sx < self.w and 0 <= sy < self.h:
                rr, cc = int(sy / self.ch), int(sx / self.cw)
                char[rr, cc] = C("o")
                tint[rr, cc] = np.clip(hue * 0.6 + 0.35, 0, 1)
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
        light = self.draw_scene(t)
        cell = pygame.surfarray.array3d(pygame.transform.smoothscale(self.scene, (self.cols, self.rows))).transpose(1, 0, 2) / 255.0
        char, tint = self.letters(t, cell)
        pygame.surfarray.blit_array(self.art, self.atlas[char].transpose(1, 3, 0, 2, 4).reshape(w, h, 3))
        ink = pygame.surfarray.make_surface((tint * 255).astype(np.uint8).transpose(1, 0, 2))
        self.art.blit(pygame.transform.scale(ink, (w, h)), (0, 0), special_flags=pygame.BLEND_MULT)
        self.out.blit(self.scene, (0, 0))
        self.out.fill((int(255 * GROUND),) * 3, special_flags=pygame.BLEND_MULT)
        self.out.blit(self.art, (0, 0), special_flags=pygame.BLEND_ADD)
        self.bloom(self.out)
        lamps = len(self.lamp_cells)
        stars = len(self.stars[0][0])
        rings = sum(1 for age, _, _ in drops(t) if age < RING_LIFE)
        lines = [f"lamps {lamps:>2}      stars {stars:>3}      rings {rings}",
                 f"letters {int((char > 0).sum()):,}      waded {DRIFT * t:4.1f} m"]
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
        self.out.blit(self.small.render(text, True, (4, 14, 22)), (at[0] + 1, at[1] + 1))
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
    screen_ = pygame.display.set_mode(size)
    pygame.display.set_caption(TITLE)
    renderer, clock = Renderer(), pygame.time.Clock()
    t, paused = 0.0, False
    frame = renderer.draw(t)
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
                pygame.image.save(frame, str(Path(__file__).with_name(f"poolrooms_{int(time.time())}.png")))
        dt = clock.tick(30) / 1000
        if not paused:
            t += min(dt, 1 / 15)
            if t >= LOOP:
                t -= LOOP
            frame = renderer.draw(t)
        screen_.blit(frame if size == (W, H) else pygame.transform.smoothscale(frame, size), (0, 0))
        pygame.display.flip()


if __name__ == "__main__":
    sys.exit(main())
