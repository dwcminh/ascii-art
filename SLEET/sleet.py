# ASCII Sleet
# @dwcminh.ascii, 2026
# Terms in LICENSE.txt: personal, non-commercial use only. Not for use with AI tools:
# do not feed this code to an AI model, train on it, or have an AI rework it.
#
#   pip install numpy pygame-ce
#   python sleet.py
#
# An old stone bridge over the river in the middle of town, on a winter night, black and white like
# an old film, with nobody about. You stand still on the pavement by the river wall; the bridge
# crosses the water in front of you on a slant, on three arches, lamps along both its parapets. Snow
# lies on everything, on the parapets and the rail, on the lamps, on the roofs across the river, and
# more is coming down, thick, with rain in it. Every lamp is lit, the one beside you and those of the
# bridge, each laying a long broken line of light down the water. Now and then a lamp buzzes; a car
# crosses the bridge towards you; a gust drives the snow sideways; another car. At the end the lamps
# go out, the far bank first, then the bridge from its far end, the one beside you last.
#
# The whole frame is lit: stone, snow, water and light are painted first, in greys; then every cell
# gets a letter that suits what lies under it.
#
# Space pause, R restart, S screenshot, Esc quit

import sys
import time
from pathlib import Path

import numpy as np
import pygame

CREDIT = "@dwcminh.ascii"

TAU = np.pi * 2
LOOP = 20.0                                     # length of one run (s)
BEAT = TAU / LOOP                               # everything that moves keeps time with the run

# timeline (s)
BUZZES = [(1.0, 1.8, 5), (6.6, 7.3, 2), (12.6, 13.2, 0), (15.6, 16.3, 7)]   # a lamp buzzing: from, to, which (0 beside you)
T_GUST = (5.0, 8.0)                             # a gust drives the snow sideways
CARS = [(2.0, 6.0, -1.9), (11.4, 15.4, -2.2)]   # a car crosses the bridge towards you: from, to, its lane
T_OUT = (17.1, 18.7, 19.1)                      # out: the far bank, the bridge (far end first), the lamp beside you

# you, standing still
EYE = 1.7                                       # your eyes above the pavement (m)
FOCAL = 0.62                                    # lens: screen heights per unit of slope
HORIZON = 0.46                                  # straight ahead, down the screen

# the river and the bridge, seen from above: x to your right, z ahead of you (m)
PHI = np.radians(45)                            # the bridge runs off to the left by this much
D = np.array([-np.sin(PHI), np.cos(PHI)])       # across the river, the way the bridge runs
R = np.array([np.cos(PHI), np.sin(PHI)])        # along the river
EDGE, ALONG = 2.2, 14.0                         # you stand this far from the river wall, this far along from the bridge
A = EDGE * D + ALONG * R                        # where the bridge leaves your bank, on its middle line
RIVER_W = 40.0                                  # wall to wall
WATER_Y = -4.5                                  # the river, below the pavement
BW, PARAPET, PT = 9.0, 0.95, 0.45               # the bridge: how wide, how high its parapets, how thick
HUMP = 1.35                                     # how much its roadway rises over the middle
PIERS, PIER_W = (13.3, 26.7), 2.2               # the piers in the river, and how thick
SPRING = -3.4                                   # where the arches spring from the piers
SPANS = [(0.8, PIERS[0] - PIER_W / 2), (PIERS[0] + PIER_W / 2, PIERS[1] - PIER_W / 2), (PIERS[1] + PIER_W / 2, RIVER_W - 0.8)]
SETBACK = 9.0                                   # the houses across the river stand this far back from its wall
FAR = 400.0                                     # nothing is looked at further than this
FOG = 75.0                                      # far off, everything fades into the falling snow

# the lamps
LAMP_UP = 3.6                                   # a bridge lantern, above the parapet
BRIDGE_LAMPS = [(4.0, -1), (8.7, 1), (13.3, -1), (20.0, 1), (26.7, -1), (32.0, 1), (38.0, -1)]   # along, which parapet
BRACKET = 0.9                                   # the bridge lanterns hang this far out over the river
NEAR_LAMP = (-0.4, -7.5, 4.6)                   # the lamp beside you: across (from the wall), along, lantern height
RAIL_H = 0.85                                   # the iron rail along the river wall
FAR_LAMPS = list(range(-40, 140, 15))           # along the far bank
FAR_LAMP_Y = 4.0
LAMP_A = [2600.0] + [4200.0] * 7 + [900.0]      # how strong: beside you, the bridge, the far bank (all together)
REACH = 220.0                                   # a lamp's light hardly gets further than about this far (m, squared)
WRAP = 0.45                                     # light creeps a little round onto surfaces turned away
CONE_SLOPE = 0.55                               # how wide a lamp's light spreads as it falls

# the snow and the rain
N_SNOW, SNOW_V = 3400, 1.1                      # flakes, and how fast they fall (m/s)
N_RAIN, RAIN_V = 650, 7.5
SPREAD = 1.5                                    # how wide the falling weather is, per metre ahead
RAIN_SLANT = 0.22                               # sideways per metre fallen
RAIN_SHOW = 70.0                                # a streak this bright gets drawn
N_RINGS, RING_EVERY, RING_LIFE = 50, LOOP / 25, 0.7

# greys (0..255)
AMB = 46.0                                      # the town's glow on everything from the low cloud (and the snow)
SKY_TOP, SKY_LOW = 7.0, 30.0                    # the cloud overhead, and low over the roofs
HAZE0 = 16.0                                    # far off, things fade into this, plus the lamps' share
SNOW_A, STONE_A, GLASS_A = 0.86, 0.42, 0.06     # how much light each gives back
WINDOW_G, WATER_G = 120.0, 4.0                  # a lit window; the river's own dark
CAR_A = 5000.0
DIM, ACCENT, SIGN_RGB = (150, 150, 150), (240, 240, 240), (228, 228, 228)

# what each point is
K_SKY, K_HOUSE, K_STREET, K_WALL, K_WATER, K_GROUND, K_FACE, K_VAULT, K_COPING, K_DECK, K_INNER = range(11)
SNOWY = (K_GROUND, K_STREET, K_COPING, K_DECK)

# the letters
SNOW_POOLS = ["   .  ", "  . ' ", " .':. ", ".:'*:."]                # snow, dim to bright
STONE_POOLS = [" . ,.", ".:',;", ":;!il", "il!1|t"]
WATER_POOLS = ["     .", "  . - ", " .-~ .", ".~-~= "]
C = lambda ch: ord(ch) - 32                     # character -> glyph index
ramp = lambda p: np.array([[C(s[k % len(s)]) for k in range(12)] for s in p])
SNOW_FILL, STONE_FILL, WATER_FILL = ramp(SNOW_POOLS), ramp(STONE_POOLS), ramp(WATER_POOLS)
SLOPE_G = np.array([C(c) for c in "-/|\\"])
GROUND = 0.74                                   # how much of the painting shows under the letters


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
NOISE_A = make_noise(NT, 1.5, 4)


def tex(noise, u, v):
    return noise[np.asarray(v).astype(np.int32) & (NT - 1), np.asarray(u).astype(np.int32) & (NT - 1)]


def cell_hash(*keys):
    # a fixed 0..1 for every combination of whole numbers
    h = np.int64(2166136261)
    for k in keys:
        h = ((h ^ np.asarray(k).astype(np.int64)) * 16777619) % 4294967291
    return (h % 10007) / 10007.0


def world(s, u):
    # across the river (s, from your bank) and along it (u, from the bridge's middle line) -> x, z
    return A[0] + s * D[0] + u * R[0], A[1] + s * D[1] + u * R[1]


def frame(x, z):
    # and back
    return (x - A[0]) * D[0] + (z - A[1]) * D[1], (x - A[0]) * R[0] + (z - A[1]) * R[1]


def deck_y(s):
    return HUMP * np.sin(np.pi * np.clip(s / RIVER_W, 0, 1))


def coping(s):
    return deck_y(s) + PARAPET


def arch_y(s):
    # the underside of the bridge over each span (below it, open); nothing over the piers and the banks
    s = np.asarray(s, np.float32)
    out = np.full(s.shape, -1e9, np.float32)
    for a, b in SPANS:
        c, half = (a + b) / 2, (b - a) / 2
        q = (s - c) / half
        crown = deck_y(c) - 0.95
        out = np.where(np.abs(q) < 1, SPRING + (crown - SPRING) * np.sqrt(np.clip(1 - q * q, 0, 1)), out)
    return out


# the houses across the river: blocks along the bank (from, to, roof); one with a spire
_rng = np.random.default_rng(21)
_edges = [-140.0]
while _edges[-1] < 220:
    _edges.append(_edges[-1] + float(_rng.uniform(8, 15)))
HOUSE_FROM = np.array(_edges[:-1], np.float32)
HOUSE_TO = np.array(_edges[1:], np.float32)
HOUSE_TOP = _rng.uniform(11, 22, len(HOUSE_FROM)).astype(np.float32)
SPIRE = (int(np.searchsorted(HOUSE_FROM, 58.0)) - 1, 36.0, 15.0)      # which block, how high, how high the point above it


def houses(u):
    # which block a point along the far bank is in, where it begins and ends, how high its roof is there
    b = np.clip(np.searchsorted(HOUSE_FROM, u, side="right") - 1, 0, len(HOUSE_FROM) - 1)
    u0, u1, top = HOUSE_FROM[b], HOUSE_TO[b], HOUSE_TOP[b]
    sb, high, point = SPIRE
    mid, half = (u0 + u1) / 2, (u1 - u0) / 2
    spire = (b == sb)
    top = np.where(spire, high + point * np.clip(1 - np.abs(u - mid) / (0.22 * half), 0, 1) - 4 * np.clip(np.abs(u - mid) / half - 0.35, 0, 1) * 10, top)
    return b, u0, u1, top


# following rays into the scene

def trace(o, v, tmin, bridge=True):
    # the nearest thing each ray meets beyond tmin, and, if it passes into an arch first, where
    ox, oy, oz = o
    vx, vy, vz = v
    s0, u0 = frame(ox, oz)
    vs, vu = vx * D[0] + vz * D[1], vx * R[0] + vz * R[1]
    n = vx.shape[0]
    best = np.full(n, FAR, np.float32)
    kind = np.full(n, K_SKY, np.int8)
    hole = np.full(n, np.inf, np.float32)

    def offer(t, ok, k):
        ok = ok & np.isfinite(t) & (t > tmin + 1e-4) & (t < best)
        best[ok] = t[ok]
        kind[ok] = k

    with np.errstate(divide="ignore", invalid="ignore"):
        t = (0 - oy) / vy                                       # the pavement on your bank; the street across
        s = s0 + t * vs
        offer(t, (vy < 0) & (s < 0), K_GROUND)
        offer(t, (vy < 0) & (s > RIVER_W) & (s < RIVER_W + SETBACK), K_STREET)
        t = (WATER_Y - oy) / vy                                 # the river
        s = s0 + t * vs
        offer(t, (vy < 0) & (s > 0) & (s < RIVER_W), K_WATER)
        for at, way in ((0.0, -1), (RIVER_W, 1)):               # the river walls
            t = (at - s0) / vs
            y = oy + t * vy
            offer(t, (vs * way > 0) & (y > WATER_Y) & (y < 0), K_WALL)
        t = (RIVER_W + SETBACK - s0) / vs                       # the houses
        y, u = oy + t * vy, u0 + t * vu
        offer(t, (vs > 0) & (y > 0) & (y < houses(u)[3]), K_HOUSE)
        if bridge:
            # its side facing you, from the water up to the coping, open under the arches
            t = (-BW / 2 - u0) / vu
            s, y = s0 + t * vs, oy + t * vy
            on = (vu > 0) & (s >= 0) & (s <= RIVER_W) & (y >= WATER_Y) & (y <= coping(s))
            gap = on & (y < arch_y(s))
            offer(t, on & ~gap, K_FACE)
            gap &= (t > tmin) & (t < best)
            hole[gap] = t[gap]
            # the snow on the copings, and on the roadway between them (worked out a few times over, as they curve)
            for k, lo, hi, height in ((K_COPING, -BW / 2, -BW / 2 + PT, coping), (K_COPING, BW / 2 - PT, BW / 2, coping),
                                      (K_DECK, -BW / 2 + PT, BW / 2 - PT, deck_y)):
                t = (height(np.clip(s0 + ((PARAPET - oy) / vy) * vs, 0, RIVER_W)) - oy) / vy
                for _ in range(3):
                    t = (height(s0 + t * vs) - oy) / vy
                s, u = s0 + t * vs, u0 + t * vu
                offer(t, (vy < 0) & (s >= 0) & (s <= RIVER_W) & (u >= lo) & (u <= hi), k)
            t = (BW / 2 - PT - u0) / vu                         # the far parapet's inner side
            s, y = s0 + t * vs, oy + t * vy
            offer(t, (vu > 0) & (s >= 0) & (s <= RIVER_W) & (y >= deck_y(s)) & (y <= coping(s)), K_INNER)
    hole[hole >= best] = np.inf
    return best, kind, hole


def march(o, v, t0):
    # a ray through an arch: the vault over it, the water under the bridge, or out the far side
    s0, u0 = frame(o[0], o[2])
    vs, vu = v[0] * D[0] + v[2] * D[1], v[0] * R[0] + v[2] * R[1]
    t1 = (BW / 2 - u0) / vu
    k = np.linspace(0, 1, 41)[1:]
    tt = t0[:, None] + (t1 - t0)[:, None] * k[None]
    s = s0[:, None] + tt * vs[:, None]
    y = o[1][:, None] + tt * v[1][:, None]
    wet = y < WATER_Y
    hit = wet | (y >= arch_y(s)) | (s < 0) | (s > RIVER_W)
    first = np.argmax(hit, 1)
    row = np.arange(len(t0))
    found = hit.any(1)
    t = np.where(found, tt[row, first], t1).astype(np.float32)
    kind = np.where(wet[row, first], K_WATER, K_VAULT).astype(np.int8)
    return t, kind, ~found


def cast(o, v):
    # follow rays into the scene, through the arches too
    n = v.shape[1]
    t, kind, hole = trace(o, v, np.zeros(n, np.float32))
    idx = np.nonzero(np.isfinite(hole))[0]
    if len(idx):
        tt, kk, out = march(o[:, idx], v[:, idx], hole[idx])
        t[idx], kind[idx] = tt, kk
        j = idx[out]
        if len(j):
            t2, k2, _ = trace(o[:, j], v[:, j], tt[out], bridge=False)
            t[j], kind[j] = t2, k2
    return t, kind


def material(kind, x, y, z):
    # what each point is made of: how much light it gives back, light of its own, which way it faces,
    # and which part of the scene it is (for the outlines between parts)
    s, u = frame(x, z)
    alb = np.zeros(kind.shape, np.float32)
    emit = np.zeros(kind.shape, np.float32)
    nx, ny, nz = np.zeros(kind.shape, np.float32), np.ones(kind.shape, np.float32), np.zeros(kind.shape, np.float32)
    part = kind.astype(np.int64) * 100000
    grain = tex(NOISE_A, u * 10 + 300, s * 10 + 300)
    snowy = np.isin(kind, SNOWY)
    alb = np.where(snowy, SNOW_A * (0.84 + 0.30 * grain), alb)
    # the river walls: stone in courses, snow along the top
    m = kind == K_WALL
    alb = np.where(m, np.where(y > -0.22, SNOW_A * 0.9, STONE_A * (0.7 + 0.5 * grain) * np.where(np.mod(y, 0.6) < 0.07, 0.6, 1)), alb)
    way = np.where(s < 1, 1.0, -1.0)
    nx, ny, nz = np.where(m, way * D[0], nx), np.where(m, 0, ny), np.where(m, way * D[1], nz)
    # the houses: stone, windows (some lit), snow on the sills and along the roofs
    m = kind == K_HOUSE
    if m.any():
        b, h0, h1, top = houses(u)
        col = np.round((u - h0 - 1.3) / 2.6)
        uc = h0 + 1.3 + col * 2.6
        fl = np.floor((y - 3.2) / 3.1)
        yl = y - 3.2 - fl * 3.1
        okc = (col >= 0) & (uc + 0.6 < h1 - 0.5) & (fl >= 0) & (3.2 + fl * 3.1 + 2.5 < top - 0.8)
        win = okc & (np.abs(u - uc) < 0.6) & (yl > 0.9) & (yl < 2.5)
        sill = okc & (np.abs(u - uc) < 0.72) & (yl > 0.74) & (yl <= 0.9)
        lit = win & (cell_hash(b, fl, col) < 0.2)
        roof = y > top - 0.4
        wall = STONE_A * 0.8 * (0.75 + 0.5 * grain)
        house = np.where(roof | sill, SNOW_A * 0.85, np.where(win, GLASS_A, wall))
        alb = np.where(m, house, alb)
        emit = np.where(m & lit, WINDOW_G * (0.55 + 0.45 * cell_hash(b, fl, col, 3)), emit)
        nx, ny, nz = np.where(m, -D[0], nx), np.where(m, 0, ny), np.where(m, -D[1], nz)
        part = np.where(m & win, part + 1 + b * 1000 + fl * 40 + col, part)
        part = np.where(m & lit, part + 50000, part)
        part = np.where(m & (roof | sill), part + 90000, part)
    # the bridge's side: stone in courses, the arch rings paler, snow on the ledge along the roadway and on the coping
    m = kind == K_FACE
    if m.any():
        dk = deck_y(s)
        ay = arch_y(s)
        cope = y > dk + PARAPET - 0.12
        ledge = (y > dk - 0.26) & (y < dk - 0.10)
        ring = (y - ay > 0) & (y - ay < 0.6)
        course = np.mod(y - WATER_Y, 0.5) < 0.05
        stone = STONE_A * (0.72 + 0.56 * grain) * np.where(course, 0.62, 1.0)
        face = np.where(cope | ledge, SNOW_A * 0.9, np.where(ring, STONE_A * 1.9 * (0.8 + 0.3 * grain), stone))
        alb = np.where(m, face, alb)
        nx, ny, nz = np.where(m, -R[0], nx), np.where(m, 0, ny), np.where(m, -R[1], nz)
        zone = np.where(cope, 3, np.where(ledge, 2, np.where(ring, 1, 0)))
        part = np.where(m, part + zone, part)
    m = kind == K_INNER
    alb = np.where(m, np.where(y > coping(s) - 0.12, SNOW_A * 0.9, STONE_A * (0.7 + 0.5 * grain)), alb)
    nx, ny, nz = np.where(m, -R[0], nx), np.where(m, 0, ny), np.where(m, -R[1], nz)
    m = kind == K_VAULT
    alb = np.where(m, STONE_A * 0.6, alb)
    ny = np.where(m, -1, ny)
    return alb, emit, (nx, ny, nz), part


def lamp_light(px, py, pz, n, lx, ly, lz):
    # how much of a lamp's light falls on points facing n: mostly downwards, a little round the edges
    vx, vy, vz = lx - px, ly - py, lz - pz
    d2 = vx * vx + vy * vy + vz * vz
    inv = 1.0 / np.sqrt(d2 + 1e-6)
    lam = np.clip((n[0] * vx + n[1] * vy + n[2] * vz) * inv + WRAP, 0, None) / (1 + WRAP)
    down = np.clip(vy * inv, 0, 1)
    return (0.25 + 0.75 * down) * lam * np.exp(-d2 / REACH) / (d2 + 1.0)


def lamps():
    # every lamp: where its lantern hangs (x, y, z), where its post stands (x, y, z); which light it belongs to
    out = []
    s, u, hy = NEAR_LAMP
    x, z = world(s, u)
    out.append(((x, hy, z), (x, 0.0, z), 0))
    for i, (s, side) in enumerate(BRIDGE_LAMPS):
        x, z = world(s, side * (BW / 2 + BRACKET))              # on brackets out over the river
        bx, bz = world(s, side * (BW / 2 - PT / 2))
        out.append(((x, float(coping(s)) + LAMP_UP, z), (bx, float(coping(s)), bz), 1 + i))
    for u in FAR_LAMPS:
        x, z = world(RIVER_W + 1.3, u)
        out.append(((x, FAR_LAMP_Y, z), (x, 0.0, z), 8))
    return out


LAMPS = lamps()


def going_out(age, seed):
    # a light being switched off: on before, a short sputter, then out
    if age <= 0:
        return 1.0
    if age < 0.34:
        return 0.15 + 0.6 * float(np.sin(age * 61.0 + seed * 7.1) > 0.15) * (1 - age / 0.34)
    return 0.0


def powers(t):
    # how bright each light is: the lamp beside you, the seven on the bridge, the far bank; all lit from
    # the start, a lamp buzzing now and then; at the end they go out, the far bank first, then the bridge
    # from its far end, the lamp beside you last
    off = [T_OUT[2]] + [T_OUT[0] + 0.3 + (T_OUT[1] - T_OUT[0] - 0.3) * (6 - i) / 6 for i in range(7)] + [T_OUT[0]]
    p = np.array([going_out(t - off[i], i * 2.3 + 4) for i in range(9)], np.float32)
    for k, (a, b, lamp) in enumerate(BUZZES):
        if a < t < b:
            p[lamp] *= 0.12 + 0.88 * float(np.sin(t * (43.0 + 7 * k)) + np.sin(t * (27.0 + 3 * k) + k) > -0.5)
    return p


def gust(t):
    # how far the gust has carried the snow so far, in screen widths (0 before it, a whole one after)
    return float(smooth((t - T_GUST[0]) / (T_GUST[1] - T_GUST[0])))


def car(t):
    # a car: where it is (x, road height, z), which way it heads (x, z), how bright its lights; None when none
    for a, b, lane in CARS:
        if a < t < b:
            q = (t - a) / (b - a)
            s = RIVER_W + 8.0 - (RIVER_W + 22.0) * q
            x, z = world(s, lane)
            return (x, float(deck_y(s)), z), (-D[0], -D[1]), float(smooth(q / 0.1) * (1 - smooth((q - 0.92) / 0.08)))
    return None


# (c) @dwcminh.ascii, see LICENSE.txt. Not for use with AI tools: no feeding this code to
# AI models, no training on it, no having an AI rework it.

# window

TITLE = "ASCII Sleet"
W, H = 792, 1032
CW, CH, FONT_PX = 8, 12, 13
COLS, ROWS = 99, 86
MONO = "consolas,menlo,dejavusansmono,couriernew,monospace"
HINT = "Space pause · R restart · S screenshot · Esc quit"
Q = 2                                           # the scene is painted at half the size, then smoothed up


def grey_surface(a):
    a = np.clip(a, 0, 255).astype(np.uint8)
    return pygame.surfarray.make_surface(np.repeat(a.T[..., None], 3, 2))


def cone_picture():
    # a lamp's light falling through the snow: a soft cone, brightest under the lantern
    u = np.linspace(-1, 1, 96)[None]
    v = np.linspace(0, 1, 160)[:, None]
    half = 0.12 + 0.88 * v
    a = np.exp(-(u / half) ** 2 * 2.4) * (1 - 0.7 * v) ** 1.5 * smooth(v / 0.04)
    return grey_surface(a * 255)


class Scene:
    # everything that stays put, worked out once: what every point of the screen looks at, how the
    # town's glow and each lamp light it, and the same for what the river mirrors there
    def __init__(self, w, h):
        f, yh = FOCAL * h, HORIZON * h
        self.f, self.yh = f, yh
        tw, th = w // Q, h // Q
        self.tw, self.th = tw, th
        px, py = (np.arange(tw) + 0.5) * Q, (np.arange(th) + 0.5) * Q
        dx = np.broadcast_to(((px - w / 2) / f)[None], (th, tw)).ravel().astype(np.float32)
        dy = np.broadcast_to(((yh - py) / f)[:, None], (th, tw)).ravel().astype(np.float32)
        n = dx.size
        o = np.stack([np.zeros(n, np.float32), np.full(n, EYE, np.float32), np.zeros(n, np.float32)])
        v = np.stack([dx, dy, np.ones(n, np.float32)])
        t, kind = cast(o, v)
        p = o + t * v
        norm = np.sqrt(dx * dx + dy * dy + 1)
        dist = t * norm
        s, u = frame(p[0], p[2])
        under = (kind == K_WATER) & (np.abs(u) < BW / 2)        # the river in the shadow of the bridge
        self.kind = kind.reshape(th, tw)
        self.depth = np.where(kind == K_SKY, 1e9, dist).reshape(th, tw).astype(np.float32)
        alb, emit, nrm, part = material(kind, p[0], p[1], p[2])
        up = np.clip(nrm[1], 0, 1)
        self.base = alb * AMB * (0.65 + 0.35 * up) + emit
        sky = SKY_TOP + (SKY_LOW - SKY_TOP) * (1 - np.clip(dy / 0.9, 0, 1)) ** 2.2
        self.base = np.where(kind == K_SKY, sky, self.base)
        self.fog = np.where(kind == K_SKY, 0, 1 - np.exp(-dist / FOG)).astype(np.float32)
        self.maps = self.light_maps(p, nrm, alb, kind != K_SKY)
        # the river: what it mirrors (the same, for rays bounced off the water), and how much
        wet = np.nonzero((kind == K_WATER) & ~under)[0]
        ro = p[:, wet]
        rv = np.stack([dx[wet], -dy[wet], np.ones(len(wet), np.float32)])
        rt, rk = cast(ro, rv)
        rp = ro + rt * rv
        ralb, remit, rnrm, _ = material(rk, rp[0], rp[1], rp[2])
        rdist = dist[wet] + rt * norm[wet]
        rbase = ralb * AMB * (0.65 + 0.35 * np.clip(rnrm[1], 0, 1)) + remit
        rsky = SKY_TOP + (SKY_LOW - SKY_TOP) * (1 - np.clip(dy[wet] / 0.9, 0, 1)) ** 2.2
        rbase = np.where(rk == K_SKY, rsky, rbase)
        self.wet = wet
        self.rbase = rbase
        self.rfog = np.where(rk == K_SKY, 0, 1 - np.exp(-rdist / FOG)).astype(np.float32)
        self.rmaps = self.light_maps(rp, rnrm, ralb, rk != K_SKY)
        self.fres = np.clip(0.50 + 0.45 * (1 - np.clip(-dy[wet] * 3.0, 0, 1)) ** 2, 0, 0.95).astype(np.float32)
        self.under = under.reshape(th, tw)
        # the tops of the bridge, which the car's lights reach
        top = np.isin(kind, (K_DECK, K_COPING, K_INNER))
        self.top_idx = np.nonzero(top)[0]
        self.top_p = p[:, self.top_idx]
        self.top_alb = alb[self.top_idx]
        self.parts = part.reshape(th, tw)

    @staticmethod
    def light_maps(p, nrm, alb, ok):
        maps = np.zeros((9, p.shape[1]), np.float32)
        for (lx, ly, lz), _, i in LAMPS:
            maps[i][ok] += (alb * LAMP_A[i] * lamp_light(p[0], p[1], p[2], nrm, lx, ly, lz))[ok]
        return maps


_SCENES = {}


def scene(w, h):
    # worked out once for each size of picture
    if (w, h) not in _SCENES:
        _SCENES[(w, h)] = Scene(w, h)
    return _SCENES[(w, h)]


def corner_rays(cols, rows, cw, ch):
    # what each cell corner of the letters' grid looks at: for the outlines between parts
    w, h = cols * cw, rows * ch
    f, yh = FOCAL * h, HORIZON * h
    cx, cy = np.arange(cols + 1) * cw, np.arange(rows + 1) * ch
    dx = np.broadcast_to(((cx - w / 2) / f)[None], (rows + 1, cols + 1)).ravel().astype(np.float32)
    dy = np.broadcast_to(((yh - cy) / f)[:, None], (rows + 1, cols + 1)).ravel().astype(np.float32)
    n = dx.size
    o = np.stack([np.zeros(n, np.float32), np.full(n, EYE, np.float32), np.zeros(n, np.float32)])
    v = np.stack([dx, dy, np.ones(n, np.float32)])
    t, kind = cast(o, v)
    p = o + t * v
    _, emit, _, part = material(kind, p[0], p[1], p[2])
    dist = t * np.sqrt(dx * dx + dy * dy + 1)
    shape = (rows + 1, cols + 1)
    return kind.reshape(shape), part.reshape(shape), dist.reshape(shape), (emit > 0).reshape(shape)


class Renderer:
    def __init__(self, cols=COLS, rows=ROWS, cw=CW, ch=CH, font_px=FONT_PX, hud_px=15, hint=True):
        self.cols, self.rows, self.cw, self.ch = cols, rows, cw, ch
        self.w, self.h = w, h = cols * cw, rows * ch
        self.sc = sc = scene(w, h)
        self.f, self.yh = sc.f, sc.yh
        font = pygame.font.SysFont(MONO, font_px)
        cw, ch = self.cw, self.ch
        atlas = []
        for code in range(32, 127):
            s = pygame.Surface((cw, ch))
            g = font.render(chr(code), True, (255, 255, 255))
            s.blit(g, ((cw - g.get_width()) // 2, (ch - g.get_height()) // 2))
            atlas.append(pygame.surfarray.array3d(s).transpose(1, 0, 2))
        self.atlas = np.stack(atlas)
        self.scene, self.mirror, self.layer, self.fx, self.art, self.out = (pygame.Surface((w, h)) for _ in range(6))
        self.small = pygame.font.SysFont(MONO, hud_px)
        self.hud_gap = int(hud_px * 1.45)
        self.hint = hint
        self.hash = np.random.default_rng(1).integers(0, 9973, (self.rows, self.cols))
        self.tinted = {}
        d = np.hypot(*np.meshgrid(np.linspace(-1, 1, 64), np.linspace(-1, 1, 64)))
        halo = np.clip(1 - d, 0, 1) ** 1.8 * 0.85 + np.clip(1 - d / 0.20, 0, 1)
        self.halo = grey_surface(np.clip(halo, 0, 1) * 255)
        self.cone = cone_picture()
        self.water_mask = pygame.transform.scale(grey_surface((sc.kind == K_WATER) * 255.0), (w, h))
        self.first_wet = int(np.argmax((sc.kind == K_WATER).any(1))) * Q
        rng = np.random.default_rng(31)
        z = 0.9 + 44 * rng.random(N_SNOW) ** 1.7
        self.snow = dict(z=z, q=rng.random(N_SNOW), phase=rng.random(N_SNOW), sway=rng.uniform(0, TAU, N_SNOW),
                         size=rng.uniform(0.7, 1.4, N_SNOW), wraps=np.where(z < 6, 2, 1))
        z = 0.9 + 30 * rng.random(N_RAIN) ** 1.4
        self.rain = dict(z=z, q=rng.random(N_RAIN), phase=rng.random(N_RAIN), wraps=np.where(z < 6, 2, 1))
        self.ring_phase = rng.random(N_RINGS)
        self.prepare_letters()

    # the light this frame

    def state(self, t):
        self.p = powers(t)
        self.car_now = car(t)
        self.haze = HAZE0 + 14.0 * float(self.p.mean())
        self.lights = [((lx, ly, lz), self.p[i] * LAMP_A[i]) for (lx, ly, lz), _, i in LAMPS if self.p[i] > 0.01]

    def light_at(self, x, y, z):
        # the light at a few points in the air or on thin things (lamp posts, the rail, the car)
        out = np.full(np.shape(x), AMB * 0.6, np.float32)
        for (lx, ly, lz), a in self.lights:
            d2 = (x - lx) ** 2 + (y - ly) ** 2 + (z - lz) ** 2
            out += a * np.exp(-d2 / REACH) / (d2 + 1.0) * 0.8
        return out

    def paint(self, t):
        sc = self.sc
        img = sc.base + self.p @ sc.maps
        if self.car_now is not None:
            (cx, cy, cz), (hx, hz), pw = self.car_now
            if pw > 0.01:
                q = sc.top_p
                for side in (-0.7, 0.7):
                    lx, lz = cx + hx * 2.0 - hz * side, cz + hz * 2.0 + hx * side
                    vx, vy, vz = q[0] - lx, q[1] - (cy + 0.7), q[2] - lz
                    d2 = vx * vx + vy * vy + vz * vz
                    ahead = (vx * hx + vz * hz) / np.sqrt(d2 + 1e-6)
                    img[sc.top_idx] += pw * CAR_A * sc.top_alb * np.clip(ahead, 0, 1) ** 6 / (d2 + 2.0)
        img = img + (self.haze - img) * sc.fog
        refl = sc.rbase + self.p @ sc.rmaps
        refl = refl + (self.haze - refl) * sc.rfog
        img[sc.wet] = WATER_G
        img = img.reshape(sc.th, sc.tw)
        img[sc.under] = WATER_G * 0.5
        mirror = np.zeros(sc.tw * sc.th, np.float32)
        mirror[sc.wet] = refl * sc.fres
        mirror = mirror.reshape(sc.th, sc.tw)
        mirror = (mirror + 0.6 * (np.roll(mirror, 1, 0) + np.roll(mirror, -1, 0))) / 2.2
        pygame.transform.smoothscale(grey_surface(img), (self.w, self.h), self.scene)
        pygame.transform.smoothscale(grey_surface(mirror), (self.w, self.h), self.mirror)
        self.mirror_small = mirror

    def place(self, x, y, z):
        # a point (x right, y up, z ahead of you) -> where it is on screen
        return self.w / 2 + self.f * x / z, self.yh + self.f * (EYE - y) / z

    def spark(self, surf, x, y, size, grey, tall=1.0):
        # a soft point of light
        key = (int(size / 4), int(grey / 8), round(tall, 1))
        if key not in self.tinted:
            if len(self.tinted) > 4000:
                self.tinted.clear()
            pic = pygame.transform.smoothscale(self.halo, (key[0] * 4 + 4, int((key[0] * 4 + 4) * key[2])))
            pic.fill((min(255, key[1] * 8 + 4),) * 3, special_flags=pygame.BLEND_MULT)
            self.tinted[key] = pic
        pic = self.tinted[key]
        surf.blit(pic, (x - pic.get_width() / 2, y - pic.get_height() / 2), special_flags=pygame.BLEND_ADD)

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

    def seen_down_to(self, sx, top, far):
        # how far down the screen a thin upright thing at sx, this far off, shows before something nearer hides it
        sc = self.sc
        c = int(np.clip(sx / Q, 0, sc.tw - 1))
        r0 = int(np.clip(top / Q, 0, sc.th - 1))
        col = sc.depth[r0:, c]
        hid = np.nonzero(col < far - 0.6)[0]
        return (r0 + hid[0]) * Q if len(hid) else self.h

    # the water: ripples, the lamps' long broken lines on it, rings where the rain hits

    def water(self, t):
        rows = np.arange(self.first_wet, self.h)
        zr = self.f * (EYE - WATER_Y) / np.maximum(rows - self.yh, 1.0)
        shift = (0.03 * self.f / zr) * (np.sin(TAU * rows / 23.0 - 11 * BEAT * t) + 0.7 * np.sin(TAU * rows / 9.0 + 17 * BEAT * t + 1.3))
        shift = np.clip(np.round(shift), -10, 10).astype(np.int32)
        src = self.mirror.copy()
        for y, s in zip(rows.tolist(), shift.tolist()):
            if s < 0:
                self.mirror.blit(src, (0, y), area=(-s, y, self.w + s, 1))
            elif s > 0:
                self.mirror.blit(src, (s, y), area=(0, y, self.w - s, 1))
        # the lamps' reflections: a column of short dashes under each, swaying and breaking up
        self.layer.fill((0, 0, 0))
        draw = pygame.draw.line
        self.streaks = 0
        for (lx, ly, lz), _, i in LAMPS:
            p = self.p[i]
            if p < 0.02:
                continue
            x0, top = self.place(lx, WATER_Y, lz)
            _, bot = self.place(lx, 2 * WATER_Y - ly, lz)
            bot = top + (bot - top) * 1.35
            if x0 < -40 or x0 > self.w + 40 or top > self.h:
                continue
            width = self.f * 0.35 / lz
            ys = np.arange(top, min(bot, self.h), 3.0)
            if not len(ys):
                continue
            k = (ys - top) / max(bot - top, 1)
            wob = np.sin(ys * 0.71 + 13 * BEAT * t + i * 1.9) + np.sin(ys * 0.23 - 7 * BEAT * t + lx)
            half = width * (0.35 + 0.65 * np.clip(0.5 + 0.4 * wob, 0, 1)) * (1 + 1.5 * k)
            grey = np.clip(p * (230 - 150 * k) * np.clip(0.35 + 0.5 * (wob + 1), 0, 1), 0, 255).astype(int)
            mid = x0 + width * 0.6 * np.sin(ys * 0.13 + 5 * BEAT * t + i)
            for y, a, b, g in zip(ys.tolist(), (mid - half).tolist(), (mid + half).tolist(), grey.tolist()):
                if g > 6:
                    draw(self.layer, (g, g, g), (a, y), (b, y), 2)
                    self.streaks += 1
        self.layer.blit(self.water_mask, (0, 0), special_flags=pygame.BLEND_MULT)
        self.mirror.blit(self.layer, (0, 0), special_flags=pygame.BLEND_ADD)
        self.scene.blit(self.mirror, (0, 0), special_flags=pygame.BLEND_ADD)
        self.streak_layer = self.layer.copy()

    def rings(self, t):
        n = np.floor(t / RING_EVERY + self.ring_phase)
        age = (t / RING_EVERY + self.ring_phase - n) * RING_EVERY
        rep = np.mod(n, LOOP / RING_EVERY).astype(np.int64)
        slot = np.arange(N_RINGS)
        s = 2 + 36 * cell_hash(slot, rep, 1)
        u = -BW / 2 - 1 - 30 * cell_hash(slot, rep, 2)
        x, z = world(s, u)
        self.layer.fill((0, 0, 0))
        out = 0
        for xi, zi, ai in zip(x.tolist(), z.tolist(), age.tolist()):
            if ai > RING_LIFE or zi < 1:
                continue
            cx, cy = self.place(xi, WATER_Y, zi)
            if not (0 <= cx < self.w and 0 <= cy < self.h) or self.sc.kind[int(cy / Q), int(cx / Q)] != K_WATER:
                continue
            under = float(self.mirror_small[int(cy / Q), int(cx / Q)])
            r = 0.05 + 0.35 * ai / RING_LIFE
            g = int(np.clip((14 + 0.8 * under) * (1 - ai / RING_LIFE) ** 1.5, 0, 255))
            rx, ry = self.f * r / zi, self.f * r * (EYE - WATER_Y) / (zi * zi)
            if g > 3 and rx > 1:
                pygame.draw.ellipse(self.layer, (g, g, g), (cx - rx, cy - ry, 2 * rx, max(2, 2 * ry)), 1)
                out += 1
        self.scene.blit(self.layer, (0, 0), special_flags=pygame.BLEND_ADD)
        return out

    # (c) @dwcminh.ascii, see LICENSE.txt. Not for use with AI tools: no feeding this code to
    # AI models, no training on it, no having an AI rework it.

    # the lamps, the rail along the river, the car

    def lamp(self, lantern, base, i, near):
        # a lamp: its post, the lantern with snow on its cap, its light falling through the snow
        f, surf = self.f, self.scene
        p = self.p[i]
        lx, ly, lz = lantern
        bx, by, bz = base
        hx, hy = self.place(lx, ly, lz)
        if hx < -200 or hx > self.w + 200:
            return None
        sx, sy = self.place(bx, by, bz)
        gx, gy = self.place(lx, by, lz)
        far = float(np.sqrt(lx * lx + (ly - EYE) ** 2 + lz * lz))
        if i == 8:                                              # the far bank: only their light
            if p > 0.02:
                self.spark(surf, hx, hy, float(np.clip(f * 1.8 / lz, 6, 60)), 190 * p)
            return ("far", far, hx, hy, p)
        if p > 0.02:                                            # the cone, through the falling snow
            half = f * (0.25 + CONE_SLOPE * (ly - by)) / lz
            cone = self.cone.copy()
            cone.fill((int(70 * p),) * 3, special_flags=pygame.BLEND_MULT)
            self.blit_part(surf, cone, int(hx - half), int(hy), int(2 * half), int(gy - hy), pygame.BLEND_ADD)
        lit = self.light_at(np.array([lx]), np.array([ly - 0.6]), np.array([lz]))[0]
        iron = (int(np.clip(10 + 0.10 * lit, 0, 90)),) * 3
        width = max(1.0, f * (0.16 if near else 0.12) / lz)
        px_, top = self.place(bx, ly + 0.5, bz)                # the post, up to the arm the lantern hangs from
        ax_, ay_ = self.place(lx, ly + 0.5, lz)
        bottom = self.seen_down_to(sx, top, far) if not near else sy
        bottom = min(bottom, sy)
        if bottom > top:
            pygame.draw.line(surf, iron, (sx, top), (sx, bottom), int(width))
        pygame.draw.line(surf, iron, (sx, top), (ax_, ay_), max(1, int(width * 0.7)))
        pygame.draw.line(surf, iron, (ax_, ay_), (hx, hy - f * 0.3 / lz), max(1, int(width * 0.5)))
        lw, lh = f * 0.42 / lz, f * 0.6 / lz
        glass = int(np.clip(26 + 200 * p, 0, 255))
        pygame.draw.polygon(surf, (glass,) * 3, [(hx - lw * 0.42, hy - lh * 0.4), (hx + lw * 0.42, hy - lh * 0.4),
                                                 (hx + lw * 0.3, hy + lh * 0.45), (hx - lw * 0.3, hy + lh * 0.45)])
        cap = [(hx - lw * 0.62, hy - lh * 0.4), (hx + lw * 0.62, hy - lh * 0.4), (hx, hy - lh * 0.85)]
        pygame.draw.polygon(surf, iron, cap)
        snow = int(np.clip(SNOW_A * (AMB + 0.25 * lit + 120 * p), 0, 255))
        pygame.draw.polygon(surf, (snow,) * 3, [(hx - lw * 0.66, hy - lh * 0.43), (hx + lw * 0.66, hy - lh * 0.43),
                                                (hx + lw * 0.3, hy - lh * 0.62), (hx, hy - lh * 0.92), (hx - lw * 0.3, hy - lh * 0.62)])
        if p > 0.02:
            self.spark(surf, hx, hy, float(np.clip(f * 2.6 / lz, 10, 520)), 175 * p)
        return ("lamp", far, (sx, top, bottom, width), (hx, hy, lw, lh), p, (sx, top, ax_, ay_))

    def railing(self):
        # the iron rail along the river wall, snow lying along its top
        f = self.f
        us = np.arange(-21.0, -BW / 2 - 0.3, 1.6)
        x, z = world(-0.18, us)
        ok = z > 0.5
        x, z = x[ok], z[ok]
        lit = self.light_at(x, np.full_like(x, 0.9), z)
        marks = []
        tops = []
        for xi, zi, li in zip(x.tolist(), z.tolist(), lit.tolist()):
            (bx, by), (tx, ty) = self.place(xi, 0.0, zi), self.place(xi, RAIL_H, zi)
            g = int(np.clip(8 + 0.12 * li, 0, 80))
            pygame.draw.line(self.scene, (g, g, g), (bx, by), (tx, ty), max(1, int(f * 0.035 / zi)))
            tops.append((tx, ty, zi, li))
            marks.append((bx, ty, by))
        # each rail between two posts as a band of its real thickness, so it narrows smoothly with distance
        xs, zs, ls = x.tolist(), z.tolist(), lit.tolist()
        for height, snow in ((RAIL_H, True), (RAIL_H * 0.5, False)):
            for k in range(len(xs) - 1):
                x0, z0, x1, z1 = xs[k], zs[k], xs[k + 1], zs[k + 1]
                li = 0.5 * (ls[k] + ls[k + 1])
                band = lambda lo, hi: [self.place(x0, lo, z0), self.place(x1, lo, z1), self.place(x1, hi, z1), self.place(x0, hi, z0)]
                g = int(np.clip(8 + 0.12 * li, 0, 80))
                pygame.draw.polygon(self.scene, (g, g, g), band(height - 0.02, height + 0.02))
                if snow:
                    sg = int(np.clip(SNOW_A * (AMB + li * 0.6), 0, 255))
                    pygame.draw.polygon(self.scene, (sg, sg, sg), band(height + 0.015, height + 0.05))
        self.rail = (marks, [self.place(xi, RAIL_H, zi) for xi, zi in zip(x.tolist(), z.tolist())])

    def vehicle(self):
        # the car crossing the bridge: a dark body, snow on its roof, its lights; hidden where the parapet is nearer
        if self.car_now is None:
            return None
        (cx, cy, cz), (hx, hz), pw = self.car_now
        if cz < 2:
            return None
        sx_, sz_ = -hz, hx                                      # its side
        def box(l0, l1, w_, y0, y1):
            pts = []
            for a in (l0, l1):
                for b in (-w_, w_):
                    for y in (y0, y1):
                        pts.append(self.place(cx + hx * a + sx_ * b, cy + y, cz + hz * a + sz_ * b))
            return pts
        body, cabin = box(-2.1, 2.1, 0.9, 0.25, 0.8), box(-1.2, 0.9, 0.8, 0.8, 1.4)
        hull = lambda pts: [pts[k] for k in (0, 1, 3, 7, 6, 4)]
        g = int(np.clip(14 + 0.1 * float(self.light_at(np.array([cx]), np.array([1.0]), np.array([cz]))[0]), 0, 60))
        roof = [cabin[k] for k in (1, 3, 7, 5)]
        far = float(np.hypot(cx, cz))
        seen = pygame.transform.scale(grey_surface((self.sc.depth > far - 1.5) * 255.0), (self.w, self.h))
        # where it shows: cut its outline out of the picture, then lay it in
        cover = pygame.Surface((self.w, self.h))
        cover.fill((0, 0, 0))
        pygame.draw.polygon(cover, (255, 255, 255), hull(body))
        pygame.draw.polygon(cover, (255, 255, 255), hull(cabin))
        cover.blit(seen, (0, 0), special_flags=pygame.BLEND_MULT)
        hole = pygame.Surface((self.w, self.h))
        hole.fill((255, 255, 255))
        hole.blit(cover, (0, 0), special_flags=pygame.BLEND_SUB)
        self.scene.blit(hole, (0, 0), special_flags=pygame.BLEND_MULT)
        lay = self.layer
        lay.fill((0, 0, 0))
        pygame.draw.polygon(lay, (g, g, g), hull(body))
        pygame.draw.polygon(lay, (g, g, g), hull(cabin))
        pygame.draw.polygon(lay, (int(SNOW_A * (AMB + 60)),) * 3, roof)
        lay.blit(seen, (0, 0), special_flags=pygame.BLEND_MULT)
        self.scene.blit(lay, (0, 0), special_flags=pygame.BLEND_ADD)
        lights = []
        for side in (-0.7, 0.7):
            lx, lz = cx + hx * 2.1 + sx_ * side, cz + hz * 2.1 + sz_ * side
            px_, py_ = self.place(lx, cy + 0.65, lz)
            r, c = int(np.clip(py_ / Q, 0, self.sc.th - 1)), int(np.clip(px_ / Q, 0, self.sc.tw - 1))
            if self.sc.depth[r, c] > float(np.hypot(lx, lz)) - 1.5 and pw > 0.02:
                self.spark(self.scene, px_, py_, float(np.clip(self.f * 2.4 / lz, 10, 300)), 230 * pw)
                lights.append((px_, py_))
            else:
                self.spark(self.scene, px_, py_ - self.f * 0.6 / lz, float(np.clip(self.f * 3.0 / lz, 10, 300)), 60 * pw)
        return ("car", far, hull(body), hull(cabin), roof, lights)

    # the weather: flakes and drops, each in its own layer of depth; they wrap round sideways, so the gust
    # carries them a whole screen width (two, near you) and leaves them where they began

    def weather(self, t):
        f, sc = self.f, self.sc
        self.fx.fill((0, 0, 0))
        g = gust(t)
        g0 = gust(t - 0.05)
        S = self.snow
        z = S["z"]
        top = EYE + z * (self.yh / f) + 1.0
        span = top - WATER_Y
        k = np.maximum(1, np.round(SNOW_V * LOOP / span))
        y = top - np.mod(k * t / LOOP + S["phase"], 1) * span
        sway = 0.025 * np.sin(3 * BEAT * t + S["sway"])
        q = np.mod(S["q"] - S["wraps"] * g + sway, 1)
        q0 = np.mod(S["q"] - S["wraps"] * g0 + sway, 1)
        x = (q - 0.5) * z * SPREAD
        x0 = (q0 - 0.5) * z * SPREAD
        b = self.air_light(x, y, z) * S["size"]
        sx, sy = self.place(x, y, z)
        px0, _ = self.place(x0, y, z)
        r = np.clip(f * 0.006 * S["size"] / z, 0.6, 2.6)
        dist = np.sqrt(x * x + (y - EYE) ** 2 + z * z)
        ok = (sx >= 0) & (sx < self.w) & (sy >= 0) & (sy < self.h)
        ok &= sc.depth[np.clip((sy / Q).astype(int), 0, sc.th - 1), np.clip((sx / Q).astype(int), 0, sc.tw - 1)] > dist
        ok &= ~((y < 0) & (frame(x, z)[0] < 0))                # not under the pavement
        idx = np.nonzero(ok & (b > 4))[0]
        streak = np.abs(sx - px0) > 3
        circle = pygame.draw.circle
        line = pygame.draw.line
        fx = self.fx
        for j, a, c, rr, bb, s0 in zip(idx.tolist(), sx[idx].tolist(), sy[idx].tolist(), r[idx].tolist(), b[idx].tolist(), streak[idx].tolist()):
            gv = int(min(bb, 255))
            col = (gv, gv, gv)
            if s0:
                line(fx, col, (px0[j], c), (a, c), max(1, int(rr)))
            elif rr < 1.2:
                fx.set_at((int(a), int(c)), col)
            else:
                circle(fx, col, (a, c), rr)
        self.flakes = (sx[idx], sy[idx], r[idx], b[idx], streak[idx], px0[idx])
        # the rain: thin streaks, seen only where they fall through the light
        Rn = self.rain
        z = Rn["z"]
        top = EYE + z * (self.yh / f) + 1.0
        span = top - WATER_Y
        k = np.maximum(1, np.round(RAIN_V * LOOP / span))
        fallen = np.mod(k * t / LOOP + Rn["phase"], 1) * span
        y = top - fallen
        q = np.mod(Rn["q"] - Rn["wraps"] * g, 1)
        x = (q - 0.5) * z * SPREAD - RAIN_SLANT * fallen
        b = self.air_light(x, y, z, rain=True)
        hx, hy = self.place(x, y, z)
        lean = RAIN_SLANT + 1.2 * (g - g0) / 0.05 * 0.02
        tx, ty = self.place(x + lean * 0.45, y + 0.45, z)
        dist = np.sqrt(x * x + (y - EYE) ** 2 + z * z)
        ok = (hx >= 0) & (hx < self.w) & (hy >= 0) & (hy < self.h) & (b > RAIN_SHOW * 0.4)
        ok &= sc.depth[np.clip((hy / Q).astype(int), 0, sc.th - 1), np.clip((hx / Q).astype(int), 0, sc.tw - 1)] > dist
        idx = np.nonzero(ok)[0]
        for a0, a1, c0, c1, bb in zip(hx[idx].tolist(), hy[idx].tolist(), tx[idx].tolist(), ty[idx].tolist(), b[idx].tolist()):
            gv = int(min(bb * 0.6, 255))
            line(fx, (gv, gv, gv), (c0, c1), (a0, a1), 1)
        self.drops = (hx[idx], hy[idx], tx[idx], ty[idx], b[idx])
        return len(self.flakes[0]), len(idx)

    def air_light(self, x, y, z, rain=False):
        # how bright a flake or a drop is: the town's glow (snow shows even in the dark), more in a lamp's cone
        b = np.full(x.shape, 9.0 if rain else 38.0, np.float32)
        for (lx, ly, lz), a in self.lights:
            below = np.clip(ly - y, 0, None)
            rc = 0.3 + below * CONE_SLOPE
            h2 = (x - lx) ** 2 + (z - lz) ** 2
            share = a / 1700.0
            b += share * 210 * np.exp(-h2 / (rc * rc)) * (y < ly) * np.exp(-below / 7.0)
            b += share * 140 / (1 + (h2 + (y - ly) ** 2) / 1.5)
        if self.car_now is not None:
            (cx, cy, cz), (hx, hz), pw = self.car_now
            vx, vz = x - cx, z - cz
            d = np.sqrt(vx * vx + vz * vz) + 1e-3
            ahead = np.clip((vx * hx + vz * hz) / d, 0, 1) ** 8
            b += pw * 520 * ahead / (1 + d * d / 80) * np.exp(-np.abs(y - cy - 0.7) / 1.2)
        return b * (0.4 + 0.6 * np.exp(-z / 40.0))

    def draw_scene(self, t):
        self.state(t)
        self.paint(t)
        self.water(t)
        rings = self.rings(t)
        marks = []
        for lantern, base, i in sorted(LAMPS, key=lambda L: -L[0][2]):
            if i == 0:
                continue
            m = self.lamp(lantern, base, i, near=False)
            if m:
                marks.append(m)
        car_mark = self.vehicle()
        if car_mark:
            marks.append(car_mark)
        self.railing()
        lantern, base, i = LAMPS[0]
        m = self.lamp(lantern, base, 0, near=True)
        if m:
            marks.append(m)
        self.marks = marks
        return rings

    # the letters: one for every cell, chosen by what the painting shows there

    def prepare_letters(self):
        # the outlines that never move: between parts of the scene, round the arches, along the ledges and roofs
        cols, rows = self.cols, self.rows
        kind, part, dist, lit = corner_rays(cols, rows, self.cw, self.ch)
        corners = lambda a: np.stack([a[:-1, :-1], a[:-1, 1:], a[1:, :-1], a[1:, 1:]])
        K, P, N, L = corners(kind), corners(part), corners(dist), corners(lit)
        same = (P.min(0) == P.max(0))
        char = np.zeros((rows, cols), int)
        ink = np.zeros((rows, cols), np.float32)
        ind = (P == P[0][None]).astype(np.float32)
        quiet = ((K == K_SKY) | (K == K_WATER) | (K == K_VAULT)).all(0)
        far_house = (K == K_HOUSE).all(0) & (N.min(0) > 90)
        edge = ~same & ~quiet & ~far_house
        char = np.where(edge, self.slope(ind), char)
        ink = np.where(edge, 0.55, ink)
        window = (K == K_HOUSE).all(0) & L.any(0)
        char = np.where(window, C("#"), char)
        ink = np.where(window, 0.75, ink)
        self.static_char, self.static_ink = char, ink
        self.cell_kind = kind[:-1, :-1]
        centre = np.stack([K[k] for k in range(4)])
        self.cell_kind = np.array([[np.bincount(centre[:, r, c], minlength=11).argmax() for c in range(cols)] for r in range(rows)])
        self.cell_edge = edge | window

    # (c) @dwcminh.ascii, see LICENSE.txt. Not for use with AI tools: no feeding this code to
    # AI models, no training on it, no having an AI rework it.

    def slope(self, a):
        gx = ((a[1] - a[0]) + (a[3] - a[2])) / 2 / self.cw
        gy = ((a[2] - a[0]) + (a[3] - a[1])) / 2 / self.ch
        return SLOPE_G[np.round((np.arctan2(-gx, -gy) % np.pi) / (np.pi / 4)).astype(int) % 4]

    def cells(self, surf):
        # how bright each cell is on average
        return pygame.surfarray.array3d(pygame.transform.smoothscale(surf, (self.cols, self.rows)))[..., 0].T / 255.0

    def letters(self, t, lum):
        rows, cols, cw, ch = self.rows, self.cols, self.cw, self.ch
        k = self.cell_kind
        h_ = self.hash
        slow = (h_ + int(t * 1.8)) % 12
        quick = (h_ + int(t * 4.2)) % 12
        level = np.clip(((lum - 0.06) / 0.10 + (h_ % 100) / 100.0 - 0.5).astype(int), 0, 3)
        char = self.static_char.copy()
        ink = self.static_ink.copy()
        free = ~self.cell_edge
        snow = free & np.isin(k, SNOWY) & (lum > 0.10) & (h_ % 3 == 0)
        char = np.where(snow, SNOW_FILL[level, slow], char)
        ink = np.where(snow, 0.55, ink)
        stone = free & np.isin(k, (K_FACE, K_INNER, K_WALL)) & (lum > 0.12) & (h_ % 2 == 0)
        char = np.where(stone, STONE_FILL[level, slow], char)
        ink = np.where(stone, 0.5, ink)
        water = free & (k == K_WATER) & (h_ % 2 == 0)
        char = np.where(water, WATER_FILL[level, quick], char)
        ink = np.where(water, 0.45, ink)
        tint = np.clip(lum * 1.55 + 0.05, 0, 1) * ink
        # the lamps' lines on the water
        streak = self.cells(self.streak_layer)
        bright = streak > 0.10
        char = np.where(bright, np.where(streak > 0.3, C("="), C("-")), char)
        tint = np.where(bright, np.clip(streak * 2.2, 0, 1), tint)
        put = self.put
        # the railing, the car, the lamps, furthest first
        marks, rail = self.rail
        for bx, ty, by in marks:
            put(char, tint, bx, ty, by, "|", 0.35)
        for (ax, ay), (bx, by) in zip(rail[:-1], rail[1:]):
            n_ = max(2, int(abs(bx - ax) / cw) + 2)
            glyph = "-" if abs(by - ay) / ch < 0.45 * abs(bx - ax) / cw else ("/" if (bx - ax) * (by - ay) < 0 else "\\")
            for s_ in np.linspace(0, 1, n_):
                r_, c_ = int((ay + (by - ay) * s_) / ch), int((ax + (bx - ax) * s_) / cw)
                if 0 <= r_ < rows and 0 <= c_ < cols:
                    char[r_, c_], tint[r_, c_] = C(glyph), 0.8
        for m in sorted(self.marks, key=lambda m_: -m_[1]):
            if m[0] == "far":
                _, _, hx, hy, p = m
                r_, c_ = int(hy / ch), int(hx / cw)
                if 0 <= r_ < rows and 0 <= c_ < cols and p > 0.1:
                    char[r_, c_], tint[r_, c_] = C("*"), min(1.0, 0.3 + p)
            elif m[0] == "lamp":
                _, _, (sx, top, bottom, width), (hx, hy, lw, lh), p, (ax0, ay0, ax1, ay1) = m
                put(char, tint, sx, top, bottom, "|", 0.32)
                r_ = int(ay0 / ch)
                c0, c1 = sorted((int(ax0 / cw), int(ax1 / cw)))
                if 0 <= r_ < rows and c1 > c0:
                    char[r_, max(0, c0):min(cols, c1 + 1)], tint[r_, max(0, c0):min(cols, c1 + 1)] = C("-"), 0.32
                glow = min(1.0, 0.14 + 0.9 * p)
                if lh < ch * 1.6:
                    r_, c_ = int(hy / ch), int(hx / cw)
                    if 0 <= r_ < rows and 0 <= c_ < cols:
                        char[r_, c_], tint[r_, c_] = C("*" if p > 0.3 else "o"), glow
                else:
                    r0, r1 = int((hy - lh * 0.4) / ch), int((hy + lh * 0.45) / ch) + 1
                    c0, c1 = int((hx - lw * 0.42) / cw), int((hx + lw * 0.42) / cw) + 1
                    r0, r1, c0, c1 = max(0, r0), min(rows, r1), max(0, c0), min(cols, c1)
                    if r1 > r0 and c1 > c0:
                        char[r0:r1, c0:c1], tint[r0:r1, c0:c1] = C("#"), glow
                    rc = int((hy - lh * 0.6) / ch)
                    if 0 <= rc < rows and c1 > c0:
                        char[rc, c0:c1], tint[rc, c0:c1] = C("^"), 0.8
            elif m[0] == "car":
                _, _, body, cabin, roof, lights = m
                for x_, y_ in lights:
                    r_, c_ = int(y_ / ch), int(x_ / cw)
                    if 0 <= r_ < rows and 0 <= c_ < cols:
                        char[r_, c_], tint[r_, c_] = C("@"), 1.0
        # the snow and the rain
        sx, sy, r, b, streak_, px0 = self.flakes
        rr, cc = (sy / ch).astype(int), (sx / cw).astype(int)
        ok = (rr >= 0) & (rr < rows) & (cc >= 0) & (cc < cols) & (b > 30)
        glyph = np.where(streak_, C("-"), np.where(r > 1.6, C("*"), np.where(r > 1.0, C("+"), C("."))))
        char[rr[ok], cc[ok]] = glyph[ok]
        tint[rr[ok], cc[ok]] = np.clip(b[ok] / 160.0, 0.3, 1)
        hx, hy, tx, ty, b = self.drops
        for s_ in (0.2, 0.6, 1.0):
            px_, py_ = tx + (hx - tx) * s_, ty + (hy - ty) * s_
            rr, cc = (py_ / ch).astype(int), (px_ / cw).astype(int)
            ok = (rr >= 0) & (rr < rows) & (cc >= 0) & (cc < cols) & (b > RAIN_SHOW)
            char[rr[ok], cc[ok]] = C("/")
            tint[rr[ok], cc[ok]] = np.clip(b[ok] / 230.0, 0, 1)
        return char, tint

    def put(self, char, tint, x, top, bottom, glyph, grey):
        c = int(x / self.cw)
        if 0 <= c < self.cols:
            r0, r1 = max(0, int(top / self.ch)), min(self.rows, int(bottom / self.ch) + 1)
            if r1 > r0:
                char[r0:r1, c] = C(glyph)
                tint[r0:r1, c] = grey

    @staticmethod
    def blur(src, size, radius):
        small = pygame.transform.smoothscale(src, size)
        if hasattr(pygame.transform, "gaussian_blur"):
            small = pygame.transform.gaussian_blur(small, max(1, radius))
        return small

    def bloom(self, surf, amounts=(0.8, 0.6)):
        # only what is bright glows: a tight glow and a wide one made from it
        w, h = self.w, self.h
        bright = self.blur(surf, (w // 6, h // 6), 2)
        bright.fill((80, 80, 80), special_flags=pygame.BLEND_SUB)
        wide = self.blur(bright, (w // 12, h // 12), 2)
        for layer, amount in zip((bright, wide), amounts):
            layer = pygame.transform.smoothscale(layer, (w, h))
            layer.fill((int(255 * amount),) * 3, special_flags=pygame.BLEND_MULT)
            surf.blit(layer, (0, 0), special_flags=pygame.BLEND_ADD)

    def glyphs_out(self, char, tint, under):
        w, h = self.w, self.h
        pygame.surfarray.blit_array(self.art, self.atlas[char].transpose(1, 3, 0, 2, 4).reshape(w, h, 3))
        self.art.blit(pygame.transform.scale(grey_surface(tint * 255), (w, h)), (0, 0), special_flags=pygame.BLEND_MULT)
        self.out.blit(self.scene, (0, 0))
        self.out.fill((int(255 * under),) * 3, special_flags=pygame.BLEND_MULT)
        self.out.blit(self.art, (0, 0), special_flags=pygame.BLEND_ADD)

    def draw(self, t):
        w, h = self.w, self.h
        rings = self.draw_scene(t)
        # what lies under every cell, read before the weather: the flakes and drops get their own letters
        lum = self.cells(self.scene)
        flakes, drops = self.weather(t)
        char, tint = self.letters(t, lum)
        self.scene.blit(self.fx, (0, 0), special_flags=pygame.BLEND_ADD)
        self.glyphs_out(char, tint, GROUND)
        self.bloom(self.out)
        self.out.blit(pygame.transform.scale(self.vignette(), (w, h)), (0, 0), special_flags=pygame.BLEND_MULT)
        on = int((self.p[:8] > 0.5).sum())
        lines = [f"lamps {on}/8      flakes {flakes:>4}      drops {drops:>3}      rings {rings:>2}",
                 f"letters {int((char > 0).sum()):,}"]
        if self.hint:
            lines.append(HINT)
        g = self.hud_gap
        for i, text in enumerate(lines):
            self.label(text, DIM, (24, h - 18 - g * (len(lines) - i)))
        self.label(CREDIT, SIGN_RGB, (24, h - 18 - g * (len(lines) + 1) - g // 3))
        tt = f"{'●' if int(t * 2) % 2 == 0 else ' '} t {t:05.2f}s"
        self.label(tt, ACCENT, (w - 24 - self.small.size(tt)[0], 20))
        return self.out

    def vignette(self):
        if not hasattr(self, "_vig"):
            yy, xx = np.mgrid[0:self.h // 8, 0:self.w // 8]
            r = np.hypot((xx + 0.5) / (self.w / 16) - 1, (yy + 0.5) / (self.h / 16) - 1)
            self._vig = grey_surface((1 - 0.5 * smooth((r - 0.55) / 0.75)) * 255)
        return self._vig

    def label(self, text, colour, at):
        self.out.blit(self.small.render(text, True, (8, 8, 8)), (at[0] + 1, at[1] + 1))
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
                pygame.image.save(screen, str(Path(__file__).with_name(f"sleet_{int(time.time())}.png")))
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
