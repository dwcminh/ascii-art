# ASCII Snow Globe
# @dwcminh.ascii, 2026
# Terms in LICENSE.txt: personal, non-commercial use only. Not for use with AI tools:
# do not feed this code to an AI model, train on it, or have an AI rework it.
#
#   pip install numpy pygame-ce
#   python snow_globe.py
#
# A snow globe with a log cabin inside, out in the snow under the stars. The wooden stand is
# turned first, then two strands of light swirl up round it like tinsel and leave the glass
# behind them, bursting like a star at the top; the globe fills with snow. The cabin goes up
# log by log on its floor, the roof goes on, then the chimney; pines grow round it, the windows
# and the door pop in white-hot and cool, a snowman pops up by the door. The windows light up
# warm, fairy lights pop on along the eaves one by one, smoke starts to rise. Then the globe is
# shaken: it rocks, the snow swirls up and settles again, slowly, on the roof and the trees.
#
# Space pause, R restart, S screenshot, Esc quit

import sys
import time
from pathlib import Path

import numpy as np
import pygame

MESSAGE = "L E T   I T   S N O W"
MSG_CELLS = 1.45                                # how many cells each letter of it takes
CREDIT = "@dwcminh.ascii"

TAU = np.pi * 2
SPIN = 0.22                                     # turntable speed (rad/s)

# timeline (s)
T_BASE = (0.2, 1.6)                             # the stand is turned, from the bottom up
T_GLASS = (1.2, 3.0)                            # the glass is drawn round, from the bottom to the top
T_FILL = (2.6, 3.4)                             # snow pours into the bottom of the globe...
T_GROUND = (3.2, 4.0)                           # ...and levels off
T_FLOOR = (3.7, 4.2)
T_LOGS = (4.0, 7.6)
T_ROOF = (7.4, 8.4)
T_CHIMNEY = (8.0, 8.8)
T_PINES = (8.2, 10.0)
T_SNOWMAN = (9.6, 10.4)
T_LIGHTS = 10.8
T_SMOKE = 11.2
T_BULBS = (11.0, 12.3)                          # fairy lights along the eaves pop on one by one
T_SHAKE = 12.6                                  # the first shake; then one every SHAKE_EVERY
ROOF_SNOW_EARLY = 2.0                           # the snow on the roof and chimney comes this much sooner (s)
SHAKE_EVERY = 16.0
T_UNTURN = (14.4, 18.0)                         # it turns round at 14.4 and is back square on at 18.0
TURN_ROUND = 0.6                                # how long the turn-round takes (s)
T_RESUME = 20.5                                 # then it turns on again
T_MSG = 14.6
FLASH = 0.6                                     # how long a new thing glows white (s)

C = lambda ch: ord(ch) - 32                     # character -> glyph index

SNOW, FLOOR, LOG, ROOF, FRAME, RSNOW, STONE, PINE, PSNOW, BASE, BRASS, MAN, CLOTH, MARK = range(14)
POOLS = [["1il!;:", "rtfjcvxz=+", "aeoun0{}[]<>", "08B$#&%Q"],     # letters, for the solid things
         [".", ".:", ":::.", "::*:"],                               # snow
         [":;^", "^v*x", "x%*&v", "%&#W"],                           # needles
         [":", "=+", "%&", "@#"],                                    # brass
         ["-", "-~", "~~=", "~=~"],                                  # snow lying soft on the roof
         [".o", "oc", "oO", "O@"]]                                   # the snowman: round letters for snowballs
FILL = np.array([[[C(p[lv][j % len(p[lv])]) for j in range(12)] for lv in range(4)] for p in POOLS])
POOL = np.array([1, 0, 0, 0, 0, 4, 0, 2, 1, 0, 3, 5, 0, 0])
OUTLINED = np.array([1, 1, 1, 1, 1, 1, 1, 0, 0, 1, 1, 1, 1, 0], bool)
HARD = np.isin(np.arange(14), (LOG, ROOF, FRAME, RSNOW, STONE, BASE, BRASS, MAN, CLOTH))
FLASHY = np.isin(np.arange(14), (FLOOR, LOG, ROOF, FRAME, STONE, BASE, BRASS, MAN, CLOTH, MARK))
# how each part takes the light: ambient, diffuse, shine, shine power, and window light
AMB = np.array([0.45, 0.35, 0.30, 0.30, 0.35, 0.65, 0.30, 0.40, 0.55, 0.22, 0.25, 0.55, 0.30, 1.00])
DIF = np.array([0.75, 0.70, 0.85, 0.85, 0.80, 0.55, 0.80, 0.80, 0.50, 0.70, 0.75, 0.75, 0.80, 0.00])
SPK = np.array([0.25, 0.00, 0.00, 0.00, 0.00, 0.25, 0.00, 0.00, 0.20, 0.90, 1.20, 0.20, 0.00, 0.00])
POW = np.array([8, 1, 8, 8, 1, 8, 1, 1, 8, 24, 16, 8, 8, 1])     # 8, 16 or 24 only
WARMS = np.array([1.0, 0.0, 0.45, 0.30, 0.60, 1.0, 0.40, 0.70, 1.0, 0.0, 0.0, 1.0, 0.60, 0.0])
SLOPE = np.array([C(c) for c in "-/|\\-"])

PANE, MUNTIN, LANTERN, CARROT, TWIG, GLINT, BULB, FOOT = range(1, 9)  # points that change on their own

WHITE = np.array([1.00, 0.98, 0.95])
SNOW_INK = np.array([0.80, 0.88, 1.00])
WARM = np.array([1.00, 0.68, 0.30])
GOLD = np.array([1.00, 0.78, 0.32])
GLASS = np.array([0.62, 0.84, 1.00])
NIGHT_PANE = np.array([0.22, 0.30, 0.52])
WOOD = np.array([0.60, 0.37, 0.19])
RED = np.array([0.95, 0.13, 0.13])
GREEN = np.array([0.20, 0.75, 0.35])
BULB_INK = np.array([[1.00, 0.84, 0.45], [0.95, 0.20, 0.18], [0.25, 0.85, 0.40], [0.30, 0.55, 1.00], [1.00, 0.64, 0.08]])


def smooth(x):
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3 - 2 * x)


def unit(v):
    v = np.asarray(v, float)
    return v / np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-12)


def fib_sphere(n):
    i = np.arange(n) + 0.5
    y = 1 - 2 * i / n
    r = np.sqrt(1 - y * y)
    th = np.pi * (3 - np.sqrt(5)) * i
    return np.stack([r * np.cos(th), y, r * np.sin(th)], 1)


def slope_char(dx, dy):
    # screen direction (y up) -> the ASCII stroke that looks most like it
    ang = np.degrees(np.arctan2(dy, dx)) % 180
    return SLOPE[np.digitize(ang, [25, 72, 108, 155])]


def outline_letter(gx, gy):
    ax, ay = np.abs(gx), np.abs(gy)
    c = np.where(ax > 2 * ay, C("|"), np.where(ay > 2 * ax, np.where(gy > 0, C("_"), C("-")),
                 np.where(gx * gy > 0, C("/"), C("\\"))))
    return np.where(ax + ay == 0, C("+"), c)


class Parts:
    def __init__(self):
        self.cols = []

    def add(self, p, n, rgb, part, appear, centre=None, base=1.0, glyph=-1, group=-1, tag=0, pop=False, spark=False):
        p = np.asarray(p, float).reshape(-1, 3)
        m = len(p)
        if m == 0:
            return
        f = lambda v, w=None: np.broadcast_to(np.asarray(v, float), (m, w) if w else (m,)).copy()
        i = lambda v: np.broadcast_to(np.asarray(v, int), (m,)).copy()
        cen = p if centre is None else np.broadcast_to(np.asarray(centre, float), (m, 3))
        self.cols.append((cen.copy(), p - cen, unit(f(n, 3)), f(rgb, 3), i(part), f(appear), f(base), i(glyph),
                          i(group), i(tag), np.broadcast_to(np.asarray(pop, bool), (m,)).copy(),
                          np.broadcast_to(np.asarray(spark, bool), (m,)).copy()))

    def build(self):
        return [np.concatenate(c) for c in zip(*self.cols)]


# the globe: glass of radius 1 round the origin, snow up to FLOOR_Y, sitting in a turned stand

R_GLASS, R_IN = 1.0, 0.985                      # the glass, and the snow packed against it inside
FLOOR_Y = -0.42
RHO = np.sqrt(R_IN ** 2 - FLOOR_Y ** 2)         # how far the snow reaches across
BASE_Y = -1.32                                  # the bottom of the stand
PIVOT = np.array([0.0, BASE_Y, 0.0])            # it rocks about here when shaken

# the cabin: walls of logs round a floor, half its length and depth measured to the log centres
HALF_W, HALF_D = 0.50, 0.34
LOG_R, STEP, LAYERS = 0.036, 0.066, 7
SIDE_FULL = 6                                   # side walls: full logs up to here, then the gables
CABIN_Z = -0.10                                 # the cabin stands back a little, leaving room in front
EXT = 0.075                                     # how far the log ends stick out past the corners
RIDGE_Y, EAVE_Y, EAVE_Z = 0.31, -0.01, HALF_D + 0.10
DROP = RIDGE_Y - EAVE_Y
ROOF_X, THICK = HALF_W + EXT + 0.04, 0.025
CHIM_X, CHIM_Z, CHIM_H = 0.25, -0.14, 0.058    # the chimney: where it is, half its width
CHIM_TOP = RIDGE_Y + 0.17

WIN_Y = (FLOOR_Y + 0.15, FLOOR_Y + 0.31)
OPENINGS = [("front", -0.09, 0.09, FLOOR_Y - 0.05, FLOOR_Y + 0.33, "door"),
            ("front", 0.22, 0.38, *WIN_Y, "window"), ("front", -0.38, -0.22, *WIN_Y, "window"),
            ("right", -0.08, 0.08, *WIN_Y, "window"), ("back", 0.18, 0.34, *WIN_Y, "window"),
            ("back", -0.34, -0.18, *WIN_Y, "window"), ("left", -0.08, 0.08, *WIN_Y, "window")]
UP = np.array([0.0, 1.0, 0.0])
WALLS = {  # centre, along the wall, out of it, half its length
    "front": (np.array([0, 0, HALF_D]), np.array([1.0, 0, 0]), np.array([0, 0, 1.0]), HALF_W),
    "right": (np.array([HALF_W, 0, 0]), np.array([0, 0, -1.0]), np.array([1.0, 0, 0]), HALF_D),
    "back": (np.array([0, 0, -HALF_D]), np.array([-1.0, 0, 0]), np.array([0, 0, -1.0]), HALF_W),
    "left": (np.array([-HALF_W, 0, 0]), np.array([0, 0, 1.0]), np.array([-1.0, 0, 0]), HALF_D),
}
SNOWMAN_AT = np.array([-0.42, FLOOR_Y, 0.64])          # out in front of the corner, clear of the wall
FOOT_WAY = np.array([(0.03, 0.33), (0.08, 0.66), (-0.16, 0.78), (-0.30, 0.67)])   # door to snowman (x, z)
FACE = unit([0.35, 0.0, 1.0])                   # which way the snowman looks
PINES = [(0.74, 0.04, 0.50), (-0.74, -0.10, 0.44)]


def on_wall(w, a, y, out):
    c, along, o, _ = WALLS[w]
    a, y, out = np.broadcast_arrays(np.asarray(a, float), np.asarray(y, float), np.asarray(out, float))
    return c + a[..., None] * along + y[..., None] * UP + out[..., None] * o


def layer_y(w, k):
    return FLOOR_Y + 0.6 * LOG_R + (k + 0.5 * (w in ("right", "left"))) * STEP


def roof_y(z):
    return RIDGE_Y - DROP * np.abs(z) / EAVE_Z


def grid(a0, a1, b0, b1, step_a, step_b, rng, jitter=0.5):
    a, b = np.meshgrid(np.arange(a0, a1, step_a), np.arange(b0, b1, step_b), indexing="ij")
    a = a.ravel() + (rng.random(a.size) - 0.5) * step_a * jitter
    b = b.ravel() + (rng.random(b.size) - 0.5) * step_b * jitter
    return a, b


def build():
    rng = np.random.default_rng(7)
    q = Parts()

    # stand: a turned wooden base with a brass band, rising from the bottom up
    prof = np.array([(0.556, -0.828), (0.600, -0.842), (0.606, -0.900), (0.578, -0.935), (0.590, -0.958),
                     (0.628, -0.972), (0.632, -1.018), (0.664, -1.040), (0.735, -1.170), (0.768, -1.268),
                     (0.772, BASE_Y)])
    seg = np.hypot(*np.diff(prof, axis=0).T)
    s = np.linspace(0, seg.sum(), 900)
    at = np.concatenate([[0], np.cumsum(seg)])
    r, y = np.interp(s, at, prof[:, 0]), np.interp(s, at, prof[:, 1])
    dr, dy = np.gradient(r), np.gradient(y)
    w = r * np.hypot(dr, dy)
    pick = np.searchsorted(np.cumsum(w) / w.sum(), rng.random(10000))
    pick = np.clip(pick, 0, len(s) - 1)
    phi = rng.random(len(pick)) * TAU
    rr, yy = r[pick], y[pick]
    nr, ny = unit(np.stack([-dy[pick], dr[pick]], 1)).T
    p = np.stack([np.cos(phi) * rr, yy, np.sin(phi) * rr], 1)
    n = np.stack([np.cos(phi) * nr, ny, np.sin(phi) * nr], 1)
    band = (yy < -0.970) & (yy > -1.020)
    grain = 0.85 + 0.15 * np.sin(yy * 260 + 2 * np.sin(phi * 3))
    app = T_BASE[0] + (T_BASE[1] - T_BASE[0]) * (yy - BASE_Y) / (prof[0, 1] - BASE_Y)
    q.add(p[~band], n[~band], np.array([0.42, 0.22, 0.11]) * grain[~band, None], BASE, app[~band], spark=True)
    q.add(p[band], n[band], GOLD, BRASS, app[band], spark=True)

    # snow inside: it pours into the bottom of the globe, packed against the glass...
    sp = fib_sphere(36000) * R_IN
    sp = sp[(sp[:, 1] < FLOOR_Y + 0.004) & (sp[:, 1] > -0.95)]
    strata = 0.88 + 0.12 * np.sin(sp[:, 1] * 80)
    q.add(sp, sp, SNOW_INK * np.array([0.88, 0.92, 1.0]), SNOW,
          T_FILL[0] + (T_FILL[1] - T_FILL[0]) * (sp[:, 1] + 0.95) / (FLOOR_Y + 0.95), base=1.1 * strata)

    # ...and levels off, from the glass in towards the middle, in soft drifts
    x, z = grid(-RHO, RHO, -RHO, RHO, 0.012, 0.028, rng)
    rho = np.hypot(x, z)
    keep = (rho < RHO - 0.004) & ~((np.abs(x) < HALF_W) & (np.abs(z - CABIN_Z) < HALF_D))
    x, z, rho = x[keep], z[keep], rho[keep]
    hgt = lambda x, z: 0.010 * np.sin(5 * x + 1.3) * np.cos(4 * z - 0.5) + 0.006 * np.sin(11 * x + 7 * z) \
        + 0.02 * smooth((np.hypot(x, z) - 0.72) / 0.18)
    e = 1e-3
    n = unit(np.stack([-(hgt(x + e, z) - hgt(x - e, z)) / (2 * e), np.ones_like(x),
                       -(hgt(x, z + e) - hgt(x, z - e)) / (2 * e)], 1))
    p = np.stack([x, FLOOR_Y + hgt(x, z), z], 1)
    glint = np.where(rng.random(len(x)) < 0.025, GLINT, 0)
    q.add(p, n, SNOW_INK, SNOW, T_GROUND[0] + (T_GROUND[1] - T_GROUND[0]) * (1 - rho / RHO) + 0.08 * rng.random(len(x)),
          tag=glint)

    # footprints: someone walks out of the door to where the snowman will stand, one step at a
    # time, just before he pops up; the snow after the shake fills them in again
    s = np.linspace(0, 1, 400)[:, None]
    way = ((1 - s) ** 3 * FOOT_WAY[0] + 3 * (1 - s) ** 2 * s * FOOT_WAY[1] + 3 * (1 - s) * s ** 2 * FOOT_WAY[2]
           + s ** 3 * FOOT_WAY[3])
    run = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(way, axis=0), axis=1))])
    steps = np.arange(0.02, run[-1], 0.064)
    for i, d in enumerate(steps):
        at = np.array([np.interp(d, run, way[:, 0]), np.interp(d, run, way[:, 1])])
        ahead = unit(np.array([np.interp(d + 0.01, run, way[:, 0]), np.interp(d + 0.01, run, way[:, 1])]) - at)
        foot = at + (0.017 if i % 2 else -0.017) * np.array([-ahead[1], ahead[0]])
        th = rng.random(12) * TAU
        rr = np.sqrt(rng.random(12))
        px = foot[0] + ahead[0] * 0.010 * rr * np.cos(th) - ahead[1] * 0.005 * rr * np.sin(th)
        pz = foot[1] + ahead[1] * 0.010 * rr * np.cos(th) + ahead[0] * 0.005 * rr * np.sin(th)
        q.add(np.stack([px, FLOOR_Y + hgt(px, pz) + 0.004, pz], 1), UP, SNOW_INK, SNOW,
              T_SNOWMAN[0] - 1.1 + 1.0 * i / len(steps), glyph=C("o"), group=i, tag=FOOT)

    cabin = len(q.cols)                         # the cabin is built about its own middle, then moved back

    # floor: boards inside the cabin, laid from one end to the other
    x, z = grid(-HALF_W, HALF_W, -HALF_D, HALF_D, 0.012, 0.018, rng)
    boards = 0.78 + 0.22 * (((z + HALF_D) / 0.058) % 1 > 0.15)
    q.add(np.stack([x, np.full_like(x, FLOOR_Y + 0.008), z], 1), UP, np.array([0.70, 0.50, 0.32]) * boards[:, None],
          FLOOR, T_FLOOR[0] + (T_FLOOR[1] - T_FLOOR[0]) * (x + HALF_W) / (2 * HALF_W), spark=True)

    # logs: layer by layer, round the four walls, each growing from one end to the other;
    # front and back sit half a log lower than the sides, so they cross at the corners
    logs = []
    for k in range(LAYERS + 4):
        for w in ("front", "right", "back", "left"):
            side = w in ("right", "left")
            if not side and k < LAYERS:
                logs.append((w, k, False))
            elif side and k < SIDE_FULL:
                logs.append((w, k, False))
            elif side and (RIDGE_Y - layer_y(w, k) - LOG_R) / DROP * EAVE_Z > 0.07:
                logs.append((w, k, True))                       # the gables, shorter as they rise
    GROW = 0.42
    starts = T_LOGS[0] + np.arange(len(logs)) * (T_LOGS[1] - T_LOGS[0] - GROW) / (len(logs) - 1)
    layer_time = {}
    for i, ((w, k, gable), t0) in enumerate(zip(logs, starts)):
        c, along, out, half = WALLS[w]
        y0 = layer_y(w, k)
        hl = (RIDGE_Y - y0 - LOG_R) / DROP * EAVE_Z - 0.01 if gable else half + EXT
        layer_time.setdefault(k, t0)
        m = int(4000 * 2 * hl * TAU * LOG_R)
        a = (rng.random(m) * 2 - 1) * hl
        ph = rng.random(m) * TAU
        side = np.cos(ph)[:, None] * out + np.sin(ph)[:, None] * UP
        p = c + a[:, None] * along + y0 * UP + LOG_R * side
        cut = np.zeros(m, bool)
        for ow, a0, a1, b0, b1, _ in OPENINGS:
            if ow == w:
                cut |= (a > a0) & (a < a1) & (p[:, 1] > b0) & (p[:, 1] < b1)
        bark = 0.80 + 0.20 * np.sin(a * 70 + 3 * ph + i) ** 2
        ink = WOOD * (0.86 + 0.22 * rng.random())
        dirn = 1 if i % 2 == 0 else -1
        app = t0 + GROW * (dirn * a + hl) / (2 * hl)
        q.add(p[~cut], side[~cut], ink, LOG, app[~cut], base=bark[~cut], glyph=C("="), spark=True)
        if not gable:                           # the cut ends, with their rings
            for end in (-1, 1):
                rr, th = LOG_R * np.sqrt(rng.random(50)), rng.random(50) * TAU
                disc = c + end * hl * along + y0 * UP + rr[:, None] * (np.cos(th)[:, None] * out + np.sin(th)[:, None] * UP)
                q.add(disc, end * along, np.array([0.88, 0.70, 0.46]), MARK, t0 + GROW * (dirn * end + 1) / 2,
                      base=0.95, glyph=C("@"))

    # windows and the door: panes set into the logs, with a frame round each
    def wall_done(y):
        k = int(np.ceil((y - FLOOR_Y) / STEP))
        return layer_time.get(min(k, LAYERS - 1), T_LOGS[1]) + 0.3

    lights, bulbs = [], []
    for j, (w, a0, a1, b0, b1, kind) in enumerate(OPENINGS):
        b0c = max(b0, FLOOR_Y + 0.004)
        a, y = grid(a0, a1, b0c, b1, 0.007, 0.010, rng, 0.3)
        t0 = wall_done(b1)
        out = WALLS[w][2]
        mid = on_wall(w, (a0 + a1) / 2, (b0c + b1) / 2, 0.0)   # each thing pops out from its middle
        if kind == "window":
            ac, yc = (a0 + a1) / 2, (b0 + b1) / 2
            mu, mv = np.abs(a - ac) < 0.011, np.abs(y - yc) < 0.011
            glyph = np.where(mu & mv, C("+"), np.where(mu, C("|"), np.where(mv, C("-"), C("#"))))
            q.add(on_wall(w, a, y, -0.002), out, NIGHT_PANE, MARK, t0, centre=mid, glyph=glyph, group=j,
                  tag=np.where(glyph == C("#"), PANE, MUNTIN), pop=True)
            lights.append(on_wall(w, ac, yc - 0.06, 0.14))
        else:
            q.add(on_wall(w, a, y, -0.002), out, np.array([0.50, 0.30, 0.15]), MARK, t0, centre=mid, base=0.85,
                  glyph=C("|"), pop=True)
            q.add(on_wall(w, [0.046, 0.046], [FLOOR_Y + 0.13] * 2, [0.004, 0.006]), out, GOLD, MARK, t0 + 0.5,
                  centre=mid, glyph=C("o"), pop=True)
            th = rng.random(260) * TAU                          # a wreath on the door, with berries
            ring = 0.030 + 0.010 * (rng.random(260) - 0.5)
            wreath = on_wall(w, 0, FLOOR_Y + 0.205, 0.01)
            q.add(on_wall(w, np.cos(th) * ring, FLOOR_Y + 0.205 + np.sin(th) * ring * 0.9, 0.010), out,
                  np.array([0.16, 0.55, 0.22]), PINE, t0 + 0.6, pop=True, centre=wreath)
            q.add(on_wall(w, [-0.012, 0.0, 0.012], [FLOOR_Y + 0.178] * 3, [0.016] * 3), out,
                  np.array([1.0, 0.16, 0.14]), MARK, t0 + 0.8, centre=wreath, glyph=C("o"), pop=True)
            lantern = on_wall(w, 0.118, FLOOR_Y + 0.235, LOG_R + 0.028)
            q.add(lantern + fib_sphere(24) * 0.014, fib_sphere(24), np.array([0.35, 0.33, 0.30]), MARK, t0 + 0.7,
                  centre=lantern, glyph=C("@"), tag=LANTERN, pop=True)
            lights.append(lantern)
        fw = 0.016                                              # the frame
        a, y = grid(a0 - fw, a1 + fw, b0c, b1 + fw, 0.004, 0.006, rng, 0.3)
        ring = (a < a0) | (a > a1) | (y > b1) | ((y < b0) & (kind == "window"))
        a2, y2 = grid(a0 - fw, a1 + fw, b0 - fw, b0, 0.004, 0.006, rng, 0.3)
        if kind == "window":
            a, y, ring = np.concatenate([a, a2]), np.concatenate([y, y2]), np.concatenate([ring, np.ones(len(a2), bool)])
        a, y = a[ring], y[ring]
        glyph = np.where((a < a0) | (a > a1), C("|"), np.where(y > b1, C("-"), C("=")))
        q.add(on_wall(w, a, y, LOG_R + 0.004), out, np.array([0.80, 0.62, 0.40]), FRAME, t0 + 0.15, centre=mid,
              glyph=glyph, pop=True)

    # roof: two slopes of boards, laid from the eaves up to the ridge
    for side in (1, -1):
        nrm = unit([0, EAVE_Z, side * DROP])
        down = unit([0, -DROP, side * EAVE_Z])
        u, v = grid(-ROOF_X, ROOF_X, 0, 1, 0.012, 0.022, rng)
        p = np.stack([u, roof_y(v * EAVE_Z) + THICK, side * v * EAVE_Z], 1)
        board = 0.80 + 0.20 * (((u + ROOF_X) / 0.05) % 1 > 0.14)
        app = T_ROOF[0] + 0.85 * (T_ROOF[1] - T_ROOF[0]) * (1 - v)
        q.add(p, nrm, np.array([0.70, 0.26, 0.18]) * board[:, None], ROOF, app, glyph=C("^"), spark=True)
        u, d = grid(-ROOF_X, ROOF_X, 0, THICK, 0.005, 0.006, rng, 0.3)  # the board along the eaves
        q.add(np.stack([u, EAVE_Y + d, np.full_like(u, side * EAVE_Z)], 1), down, np.array([0.70, 0.50, 0.30]),
              ROOF, T_ROOF[1] - 0.1)
        for end in (-1, 1):                                     # and up the gable ends
            v, d = grid(0, 1, 0, THICK, 0.010, 0.006, rng, 0.3)
            q.add(np.stack([np.full_like(v, end * ROOF_X), roof_y(v * EAVE_Z) + d, side * v * EAVE_Z], 1),
                  [end, 0, 0], np.array([0.70, 0.50, 0.30]), ROOF, T_ROOF[0] + (T_ROOF[1] - T_ROOF[0]) * (1 - v))

        # snow on the roof: it lands just before the first shake, a patch at a time
        u, v = grid(-ROOF_X - 0.008, ROOF_X + 0.008, 0, 1.0, 0.012, 0.020, rng)
        clear = (np.abs(u - CHIM_X) < CHIM_H + 0.006) & (np.abs(side * v * EAVE_Z - CHIM_Z) < CHIM_H + 0.006)
        u, v = u[~clear], v[~clear]
        depth = (0.020 + 0.008 * np.sin(u * 31 + side) * np.sin(v * 9)) * smooth((ROOF_X + 0.01 - np.abs(u)) / 0.03)
        p = np.stack([u, roof_y(v * EAVE_Z) + THICK, side * v * EAVE_Z], 1) + nrm * depth[:, None]
        patch = 0.5 + 0.5 * np.sin(u * 17 + v * 5 * side) * np.sin(v * 11 - u * 7)
        app = T_SHAKE + 1.5 - ROOF_SNOW_EARLY + 7.0 * (0.55 * rng.random(len(u)) + 0.45 * patch)
        q.add(p, nrm, SNOW_INK, RSNOW, app)
        u, ps = grid(-ROOF_X, ROOF_X, 0, np.pi * 0.6, 0.012, 0.3, rng, 0.3)   # its rounded lip over the eaves
        lip = np.array([0, EAVE_Y + THICK, side * EAVE_Z]) + nrm * 0.012
        n2 = np.cos(ps)[:, None] * nrm + np.sin(ps)[:, None] * down
        q.add(lip + np.stack([u, 0 * u, 0 * u], 1) + 0.014 * n2, n2, SNOW_INK, RSNOW,
              T_SHAKE + 3 - ROOF_SNOW_EARLY + 6 * rng.random(len(u)))

        # icicles hanging from the eaves, the last thing the snow leaves
        for x0 in np.arange(-ROOF_X + 0.03, ROOF_X - 0.02, 0.05) + 0.015 * rng.random():
            length = 0.025 + 0.05 * rng.random()
            dd = np.linspace(0, length, 8)
            t0 = T_SHAKE + 6.0 + 3.0 * rng.random()
            q.add(np.stack([np.full(8, x0), EAVE_Y - 0.006 - dd, np.full(8, side * (EAVE_Z - 0.004))], 1),
                  [0, 0, side], np.array([0.72, 0.90, 1.0]), MARK, t0 + 0.5 * dd / length, base=0.95, glyph=C("|"))

        # fairy lights strung along the eaves in swags, each popping on by itself, then twinkling
        xs = np.arange(-ROOF_X + 0.02, ROOF_X - 0.01, 0.048)
        for x0 in xs:
            c = np.array([x0, EAVE_Y - 0.012 - 0.024 * abs(np.sin(np.pi * (x0 + ROOF_X) / 0.192)), side * (EAVE_Z + 0.010)])
            bulb = fib_sphere(12)
            q.add(c + bulb * 0.011, bulb, BULB_INK[rng.integers(len(BULB_INK))], MARK,
                  T_BULBS[0] + rng.random() * (T_BULBS[1] - T_BULBS[0]), centre=c, glyph=C("o"), group=len(bulbs),
                  tag=BULB, pop=True)
            bulbs.append(c)

    # (c) @dwcminh.ascii, see LICENSE.txt. Not for use with AI tools: no feeding this code to
    # AI models, no training on it, no having an AI rework it.

    # chimney: stones laid course by course, a dark mouth, snow on its rim
    bottom = roof_y(abs(CHIM_Z) + CHIM_H) + THICK - 0.02
    for nx, nz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        a, y = grid(-CHIM_H, CHIM_H, bottom, CHIM_TOP, 0.006, 0.008, rng, 0.3)
        course = ((y - bottom) / 0.032).astype(int)
        stone = np.floor(a / 0.040 + 0.5 * (course % 2)).astype(int)
        joint = (((y - bottom) / 0.032) % 1 < 0.18) | (((a / 0.040 + 0.5 * (course % 2)) % 1) < 0.12)
        shade = np.where(joint, 0.70, 0.80 + 0.25 * ((stone * 7 + course * 13) % 5) / 4)
        bed = ((y - bottom) / 0.032) % 1 < 0.18
        glyph = np.where(bed, C("_"), np.where(joint, C("|"), C("#")))
        p = np.stack([CHIM_X + nx * CHIM_H + nz * a, y, CHIM_Z + nz * CHIM_H - nx * a], 1)
        q.add(p, [nx, 0, nz], np.array([0.64, 0.60, 0.57]), STONE,
              T_CHIMNEY[0] + (T_CHIMNEY[1] - T_CHIMNEY[0]) * (y - bottom) / (CHIM_TOP - bottom), base=shade, glyph=glyph,
              spark=True)
    x, z = grid(-CHIM_H, CHIM_H, -CHIM_H, CHIM_H, 0.004, 0.004, rng, 0.3)
    hole = (np.abs(x) < CHIM_H - 0.014) & (np.abs(z) < CHIM_H - 0.014)
    top = np.stack([CHIM_X + x, np.full_like(x, CHIM_TOP), CHIM_Z + z], 1)
    q.add(top[hole] - [0, 0.01, 0], UP, np.array([0.12, 0.10, 0.10]), STONE, T_CHIMNEY[1], base=0.4)
    q.add(top[~hole] + [0, 0.006, 0], UP, SNOW_INK, RSNOW, T_SHAKE + 2 - ROOF_SNOW_EARLY + 5 * rng.random((~hole).sum()))

    for c in q.cols[cabin:]:
        c[0][:, 2] += CABIN_Z
    lights = [p + [0, 0, CABIN_Z] for p in lights]

    # pines: whorls of drooping branches, as on the Christmas tree, only small
    for k, (cx, cz, h) in enumerate(PINES):
        t0 = T_PINES[0] + k * 0.25
        pine(q, rng, cx, cz, h, t0, t0 + 0.8)

    # snowman: three balls that pop up one on another, then his face, scarf, hat and arms
    r0, r1, r2 = 0.100, 0.074, 0.054
    c0 = SNOWMAN_AT + [0, 0.090, 0]
    c1 = c0 + [0, r0 * 0.75 + r1 * 0.85, 0]
    c2 = c1 + [0, r1 * 0.80 + r2 * 0.85, 0]
    for j, (c, r) in enumerate(((c0, r0), (c1, r1), (c2, r2))):
        sph = fib_sphere(int(12000 * r * r * 4 * np.pi))
        q.add(c + sph * r, sph, np.array([0.92, 0.95, 1.0]), MAN, T_SNOWMAN[0] + 0.2 * j, centre=c, pop=True)
    t1 = T_SNOWMAN[0] + 0.6
    side = unit(np.cross(UP, FACE))
    for sgn in (-1, 1):
        q.add(c2 + r2 * unit(FACE + 0.38 * sgn * side + 0.30 * UP), FACE, np.array([0.22, 0.22, 0.26]), MARK, t1,
              centre=c2, glyph=C("o"), pop=True)
    nose = c2 + FACE * r2 * np.linspace(0.95, 1.9, 6)[:, None]
    q.add(nose, FACE, np.array([1.0, 0.50, 0.12]), MARK, t1 + 0.15, centre=c2, glyph=C(">"), tag=CARROT, pop=True)
    for hgt_ in (0.25, -0.15):
        q.add(c1 + r1 * unit(FACE + hgt_ * UP), FACE, np.array([0.22, 0.22, 0.26]), MARK, t1, centre=c1, glyph=C("o"),
              pop=True)
    th = rng.random(500) * TAU
    tube = rng.random(500) * TAU
    neck = c1 + [0, r1 * 0.78, 0]
    rad = np.stack([np.cos(th), 0 * th, np.sin(th)], 1)
    nrm = np.cos(tube)[:, None] * rad + np.sin(tube)[:, None] * UP
    q.add(neck + rad * 0.052 + nrm * 0.013, nrm, np.array([0.90, 0.14, 0.14]), CLOTH, t1, centre=neck, pop=True)
    crown = c2 + [0, r2 * 0.80, 0]
    th, hh = rng.random(700) * TAU, rng.random(700) * 0.062
    rad = np.stack([np.cos(th), 0 * th, np.sin(th)], 1)
    band = (hh > 0.010) & (hh < 0.020)
    q.add(crown + rad * 0.038 + hh[:, None] * UP, rad, np.where(band[:, None], [0.9, 0.14, 0.14], [0.13, 0.13, 0.16]),
          CLOTH, t1 + 0.1, centre=crown, pop=True)
    rr = np.sqrt(rng.random(500))
    th = rng.random(500) * TAU
    lid = np.stack([np.cos(th) * rr, 0 * th, np.sin(th) * rr], 1)
    q.add(crown + lid * 0.064, UP, [0.13, 0.13, 0.16], CLOTH, t1 + 0.1, centre=crown, pop=True)
    q.add(crown + lid * 0.038 + [0, 0.062, 0], UP, [0.13, 0.13, 0.16], CLOTH, t1 + 0.1, centre=crown, pop=True)
    twigs = []
    for g, sgn in enumerate((-1, 1)):
        a = c1 + sgn * side * r1 * 0.95
        b = a + unit(sgn * side + 0.55 * UP) * 0.12
        twigs.append((a, b))
        q.add(a + (b - a) * np.linspace(0, 1, 14)[:, None], UP, np.array([0.55, 0.34, 0.18]), MARK, t1 + 0.2,
              centre=a, glyph=C("-"), group=g, tag=TWIG, pop=True)

    return q.build(), np.array(lights), np.array(twigs)


def pine(q, rng, cx, cz, h, t0, t1):
    # built like the Christmas tree (tip at 1.22, ground at -1.12) and scaled down into place
    k = h / 2.34
    to = lambda p: np.stack([cx + 0.72 * k * p[:, 0], FLOOR_Y + k * (p[:, 1] + 1.12), cz + 0.72 * k * p[:, 2]], 1)
    grow = lambda y: t0 + (t1 - t0) * np.clip((y + 1.12) / 2.34, 0, 1)
    env = lambda y: 0.93 * np.clip((1.22 - np.asarray(y, float)) / 2.14, 0, 1) ** 0.92 + 0.02
    for i, y in enumerate(np.linspace(-0.90, 1.16, 13)):
        u = (y + 0.92) / 2.14
        R = env(y) + 0.05
        nb = int(5 + 8 * (1 - u))
        for b in range(nb):
            a = TAU * (b + 0.5 * rng.random()) / nb + i * 0.77
            L = R * rng.uniform(0.85, 1.08)
            n = int(6 + 55 * L)
            s = rng.random(n) ** 0.65
            d = np.array([np.cos(a), 0, np.sin(a)])
            sd = np.array([-np.sin(a), 0, np.cos(a)])
            sl = s * L
            p = d * sl[:, None] + sd * ((0.03 + 0.10 * s) * rng.normal(0, 1, n))[:, None]
            p[:, 1] = y + 0.06 * sl - 0.20 * sl ** 2 + 0.015 * rng.normal(0, 1, n)
            nrm = unit(d * 0.75 + np.array([0, 0.55, 0]) + 0.3 * rng.normal(0, 1, (n, 3)))
            ao = (0.30 + 0.70 * s ** 1.3) * rng.uniform(0.75, 1.1, n)
            snow = (s > 0.5) & (rng.random(n) < 0.07 * s) & (nrm[:, 1] > 0.5)
            green = np.array([0.10, 0.46, 0.20]) + np.array([0.10, 0.34, 0.14]) * rng.random((n, 1))
            app = grow(y) + 0.3 * s
            q.add(to(p[~snow]), nrm[~snow], green[~snow], PINE, app[~snow], base=ao[~snow], spark=True)
            q.add(to(p[snow]), nrm[snow], SNOW_INK, PSNOW, app[snow])
            late = (s > 0.35) & (rng.random(n) < 0.14) & (nrm[:, 1] > 0.3) & ~snow     # more snow after the shake
            q.add(to(p[late] + [0, 0.04, 0]), nrm[late], SNOW_INK, PSNOW, T_SHAKE + 1.5 + 7 * rng.random(late.sum()))
    m = 600                                     # a dark core, so nothing shows through
    y = -0.92 + 2.0 * rng.random(m)
    phi = rng.random(m) * TAU
    r = 0.6 * env(y)
    q.add(to(np.stack([np.cos(phi) * r, y, np.sin(phi) * r], 1)), np.stack([np.cos(phi), 0.3 + 0 * y, np.sin(phi)], 1),
          np.array([0.08, 0.36, 0.16]), PINE, grow(y), base=0.7)
    m = 160
    y, phi = -1.12 + rng.random(m) * 0.3, rng.random(m) * TAU
    n = np.stack([np.cos(phi), 0 * y, np.sin(phi)], 1)
    q.add(to(n * 0.09 + np.stack([0 * y, y, 0 * y], 1)), n, np.array([0.42, 0.26, 0.14]), PINE, grow(y))


_cols, LIGHTS, TWIGS = build()
_order = np.argsort(_cols[5], kind="stable")    # in the order they appear: what is shown is always a prefix
CEN, OFF, N0, RGB, PART, APPEAR, BASE_LUM, GLYPH, GROUP, TAG, POP, SPARK = (c[_order] for c in _cols)
POS = CEN + OFF
AMB_P, DIF_P, SPK_P, FLASHY_P = AMB[PART], DIF[PART], SPK[PART], FLASHY[PART]
SHINY = {p: np.flatnonzero((SPK_P > 0) & (POW[PART] == p)) for p in (8, 16, 24)}
TAGGED = {k: np.flatnonzero(TAG == k) for k in (PANE, MUNTIN, LANTERN, CARROT, TWIG, GLINT, BULB, FOOT)}
GLINT_SPEED = 2 + 3 * ((np.arange(len(POS)) * 0.618) % 1)
GLINT_PHASE = (np.arange(len(POS)) * 2.39996) % TAU


def upto(idx, n):
    return idx[:np.searchsorted(idx, n)]


def light_warmth():
    # how much of the warm window light falls on each point (it moves with the cabin, so once)
    w = np.zeros(len(POS))
    for L in LIGHTS:
        d = L - POS
        d2 = (d * d).sum(1)
        w += np.exp(-d2 / 0.05) * np.clip((N0 * unit(d)).sum(1) + 0.25, 0, 1.25)
    # each window also lays a pool of light on the snow in front of it, widening as it goes out
    on = np.flatnonzero((PART == SNOW) & (POS[:, 1] > FLOOR_Y - 0.03))
    for wall, a0, a1, b0, b1, kind in OPENINGS:
        if kind != "window":
            continue
        c, along, out, _ = WALLS[wall]
        rel = POS[on] - c - [0, 0, CABIN_Z]
        d = rel @ out - LOG_R                                   # how far out from the wall
        side = np.abs(rel @ along - (a0 + a1) / 2)              # how far to the side of the window's middle
        half = (a1 - a0) / 2 * (1 + 1.6 * np.clip(d, 0, None) / 0.3) + 0.01
        w[on] += 1.0 * smooth(d / 0.03) * (1 - smooth((d - 0.10) / 0.24)) * (1 - smooth((side - half) / 0.03))
    return np.clip(w, 0, 1.4) * WARMS[PART]


WARMTH = light_warmth()
WARM_AT = np.flatnonzero(WARMTH > 0.01)

# camera: a little above the globe, looking down into it
EYE, TARGET = np.array([0.0, 0.65, 5.0]), np.array([0.0, -0.30, 0.0])
FWD = unit(TARGET - EYE)
RIGHT = unit(np.cross(FWD, [0, 1.0, 0]))
UPC = np.cross(RIGHT, FWD)
BASIS = np.stack([RIGHT, UPC, FWD])             # world -> camera axes
EYE_CAM = BASIS @ EYE
ZOOM = 3.5
VIEW = unit(EYE - TARGET)
KEY = unit([-0.50, 0.70, 0.45])                 # the moon
HALF = unit(KEY + VIEW)


def to_cam(p):
    return p @ BASIS.T - EYE_CAM


def project_cam(cam, cols, rows, aspect):
    z = cam[..., 2]
    zz = np.maximum(z, 0.2)
    return (0.5 + cam[..., 0] / zz * ZOOM * 0.5) * cols, (0.5 - cam[..., 1] / zz * ZOOM * 0.5 * aspect) * rows, z


# the turntable, and the shake

def shake_age(t):
    return None if t < T_SHAKE else (t - T_SHAKE) % SHAKE_EVERY


def yaw_at(t):
    # the turntable: the door faces us as the lights come on and it keeps turning; at T_UNTURN[0]
    # it reverses (over a short, smooth turn-round) and winds back at the very same speed, so the
    # cabin is square on to us again exactly at T_UNTURN[1]; it holds there, then turns on again.
    # (back at the same speed: T_UNTURN[1] = 2 * T_UNTURN[0] - T_LIGHTS)
    t = np.asarray(t, float)
    w = TURN_ROUND
    start = SPIN * (T_UNTURN[0] - w / 2 - T_LIGHTS)             # where it is when the turn-round begins
    u = np.clip((t - (T_UNTURN[0] - w / 2)) / w, 0, 1)
    turning = start + SPIN * w * (u - 2 * (u ** 3 - u ** 4 / 2))   # speed goes smoothly from +SPIN to -SPIN
    back = np.where(t < T_UNTURN[0] + w / 2, turning, start - SPIN * (t - T_UNTURN[0] - w / 2))
    tau = np.clip((t - T_RESUME) / 2.0, 0, 1)
    onward = SPIN * (2.0 * (tau ** 3 - tau ** 4 / 2) + np.maximum(t - T_RESUME - 2.0, 0))
    yaw = np.where(t < T_UNTURN[0] - w / 2, SPIN * (t - T_LIGHTS), np.where(t < T_UNTURN[1], back, 0.0))
    return np.where(t < T_RESUME, yaw, onward)


def transform(t):
    # model -> world: turned on the turntable, then rocked about the bottom of the stand
    yaw = float(yaw_at(t))
    c, s = np.cos(yaw), np.sin(yaw)
    R = np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
    a = shake_age(t)
    tilt = 0.0 if a is None else float(0.11 * np.sin(TAU * 1.6 * a) * np.exp(-1.9 * a) * smooth(a / 0.06))
    ct, st = np.cos(tilt), np.sin(tilt)
    T = np.array([[ct, -st, 0], [st, ct, 0], [0, 0, 1]])
    return T @ R, PIVOT - T @ PIVOT, T, yaw


def scene(t, cols, rows, aspect):
    # everything that has appeared by now: the points are stored in the order they appear, so
    # it is the first nv of them, and the ones that have only just appeared are at the end
    M, shift, T, yaw = transform(t)
    nv = int(np.searchsorted(APPEAR, t, side="right"))
    new = np.arange(int(np.searchsorted(APPEAR, t - FLASH - 0.25)), nv)
    age = t - APPEAR[new]
    key_m, half_m = M.T @ KEY, M.T @ HALF
    A, b = BASIS @ M, BASIS @ shift - EYE_CAM
    cam = POS[:nv] @ A.T + b
    pop = POP[new]
    if pop.any():                                               # new things pop out from their middle, a little big at first
        g = smooth(age[pop] / 0.2) * (1 + 0.35 * np.clip(1 - age[pop] / FLASH, 0, 1) ** 2)
        k = new[pop]
        cam[k] = (CEN[k] + OFF[k] * g[:, None]) @ A.T + b
    n = N0[:nv]
    diff = np.clip(n @ key_m, 0, 1)
    shine = np.clip(n @ half_m, 0, 1)
    lum = BASE_LUM[:nv] * (AMB_P[:nv] + DIF_P[:nv] * diff)
    s2 = shine * shine
    s8 = s2 * s2
    s8 *= s8
    s16 = s8 * s8
    for p, pw in ((8, s8), (16, s16), (24, s16 * s8)):
        s = upto(SHINY[p], nv)
        lum[s] += SPK_P[s] * pw[s]
    rgb = RGB[:nv].copy()
    glyph = GLYPH[:nv].copy()

    # the windows: dark glass under the moon, until the lights come on warm, with the fire flickering
    lit = float(smooth((t - T_LIGHTS) / 0.4))
    hot = float(np.clip(1 - (t - T_LIGHTS) / FLASH, 0, 1) ** 2) if t >= T_LIGHTS else 0.0
    m = upto(TAGGED[PANE], nv)
    if len(m):
        win = GROUP[m]
        fire = 0.85 + 0.10 * np.sin(t * 7.1 + win * 1.7) + 0.06 * np.sin(t * 17.3 + win * 4.1)
        ink = NIGHT_PANE + (WARM - NIGHT_PANE) * lit
        rgb[m] = ink + (WHITE - ink) * hot
        lum[m] = (0.55 + 0.5 * shine[m] ** 20) * (1 - lit) + (1.05 + 0.25 * fire) * lit + 0.5 * hot
    m = upto(TAGGED[MUNTIN], nv)
    rgb[m], lum[m] = [0.50, 0.30, 0.16], 0.75 + 0.25 * hot
    m = upto(TAGGED[LANTERN], nv)
    rgb[m] = rgb[m] + (WARM - rgb[m]) * lit
    lum[m] = 0.55 + 0.8 * lit

    # the warm light from the windows falls on the snow and the trees round the cabin
    if lit > 0:
        m = upto(WARM_AT, nv)
        w = WARMTH[m] * lit * (0.92 + 0.05 * np.sin(t * 7.1) + 0.03 * np.sin(t * 17.3))
        lum[m] += 0.65 * w
        rgb[m] += (WARM - rgb[m]) * np.clip(1.1 * w, 0, 0.8)[:, None]

    # the snowman's nose points the way he faces, his arms the way they reach
    m = upto(TAGGED[CARROT], nv)
    glyph[m] = C(">") if (M @ FACE) @ RIGHT > 0 else C("<")
    m = upto(TAGGED[TWIG], nv)
    if len(m):
        ends = to_cam(TWIGS @ M.T + shift)
        dx = ends[:, 1, 0] / ends[:, 1, 2] - ends[:, 0, 0] / ends[:, 0, 2]
        dy = ends[:, 1, 1] / ends[:, 1, 2] - ends[:, 0, 1] / ends[:, 0, 2]
        glyph[m] = slope_char(dx, dy / aspect)[GROUP[m]]

    # (c) @dwcminh.ascii, see LICENSE.txt. Not for use with AI tools: no feeding this code to
    # AI models, no training on it, no having an AI rework it.

    # fairy lights: each pops on, then twinkles at its own pace
    m = upto(TAGGED[BULB], nv)
    if len(m):
        ph = GROUP[m] * 2.39996
        k = (0.6 + 0.6 * np.clip(np.sin(t * (1.5 + ph % 2) + ph * 7), 0, 1) ** 2) * smooth((t - APPEAR[m]) / 0.3)
        lum[m] = k
        glyph[m] = np.where(k > 1.0, C("@"), np.where(k > 0.8, C("O"), C("o")))

    # footprints: little hollows in shadow, until the snow from the shake fills them in, one by one
    m = upto(TAGGED[FOOT], nv)
    if len(m):
        filled = t > T_SHAKE + 3.0 + 5.0 * ((GROUP[m] * 0.618) % 1)
        glyph[m[filled]] = -1
        k = m[~filled]
        lum[k] *= 0.6
        rgb[k] = rgb[k] * [0.55, 0.62, 0.85]

    # glints in the snow
    m = upto(TAGGED[GLINT], nv)
    on = m[np.sin(t * GLINT_SPEED[m] + GLINT_PHASE[m]) > 0.95]
    glyph[on], lum[on], rgb[on] = C("*"), 1.2, WHITE

    # the growing edge throws white sparks, and everything new flashes white and cools
    m = new[SPARK[new] & (age < 0.12)]
    glyph[m], lum[m], rgb[m] = C("*"), 1.25, WHITE
    # each thing that pops in comes as a white-hot blob and cools to its own colour; the things
    # that grow only warm up a little
    f = np.clip(1 - age / FLASH, 0, 1) ** 2 * np.where(pop, 1.0, 0.6 * FLASHY_P[new])
    m = new[f > 0]
    f = f[f > 0]
    hot_pop = POP[m]
    rgb[m] += (WHITE - rgb[m]) * f[:, None]
    lum[m] += np.where(hot_pop, 1.3, 0.5) * f

    flares = []
    if hot > 0.05:
        for p in LIGHTS:
            flares.append((p @ M.T + shift, int(3 + 6 * hot), 1.3 * hot, WHITE, "force"))
    if lit > 0:                                                 # the lantern by the door
        flares.append((LIGHTS[0] @ M.T + shift, 2, 0.5 * lit, WARM, False))

    sx, sy, z = project_cam(cam, cols, rows, aspect)
    info = {"deg": float(np.degrees(yaw) % 360), "lights": int((APPEAR[TAGGED[BULB]] <= t).sum() // 12)}
    return (sx, sy, z, lum, rgb, PART[:nv], glyph), flares, M, shift, T, info


_HASH = {}


def HASH(rows, cols):
    if (rows, cols) not in _HASH:
        r, c = np.mgrid[0:rows, 0:cols]
        _HASH[rows, cols] = (r * 7919 + c * 104729) % 9973
    return _HASH[rows, cols]


def bodies(sx, sy, z, lum, rgb, part, glyph, cols, rows, t):
    # nearest point per cell; outlines where a part meets empty space or another part further
    # back; points with their own glyph (logs, tiles, panes, stones) keep it; the rest is
    # filled with letters chosen by brightness
    ok = np.flatnonzero((sx >= 0) & (sx < cols) & (sy >= 0) & (sy < rows) & (z > 0.3))
    if len(ok) == 0:
        return np.zeros((rows, cols), int), np.zeros((rows, cols, 3)), np.full((rows, cols), np.inf)
    cell = sy[ok].astype(int) * cols + sx[ok].astype(int)
    order = np.argsort(-z[ok])
    gi = np.full(rows * cols, -1)
    gi[cell[order]] = ok[order]
    gi = gi.reshape(rows, cols)
    body = gi >= 0
    g = np.maximum(gi, 0)
    prt = np.where(body, part[g], -1)
    dep = np.where(body, z[g], np.inf)
    own = np.where(body, glyph[g], -1)
    solid = body & (own < 0) & OUTLINED[np.maximum(prt, 0)]
    pp, pd = np.pad(prt, 1, constant_values=-1), np.pad(dep, 1, constant_values=np.inf)
    edge = np.zeros_like(body)
    gx, gy = np.zeros((rows, cols)), np.zeros((rows, cols))
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dx == dy == 0:
                continue
            nb, nz = pp[1 + dy:rows + 1 + dy, 1 + dx:cols + 1 + dx], pd[1 + dy:rows + 1 + dy, 1 + dx:cols + 1 + dx]
            other = (nb >= 0) & (nb != prt)
            seam = HARD[np.maximum(prt, 0)] & other & HARD[np.maximum(nb, 0)] & (prt < nb)
            out = solid & ((nb < 0) | (other & (nz > dep + 0.035)) | seam)
            gx += dx * out
            gy += dy * out
            if dx == 0 or dy == 0:
                edge |= out
    h = HASH(rows, cols)
    L = np.where(body, lum[g], 0.0)
    level = np.clip((L * 3.0).astype(int), 0, 3)
    inside = FILL[POOL[np.maximum(prt, 0)], level, (h + (t * 1.5 + h % 11).astype(int)) % 12]
    char = np.where(body, np.where(own >= 0, own, np.where(edge, outline_letter(gx, gy), inside)), 0)
    bright = np.where(own >= 0, L, np.where(edge, np.maximum(0.85, L), np.clip(0.45 + 0.55 * L / 0.9, 0.45, 1.0)))
    col = np.where(body[..., None], rgb[g] * np.minimum(bright, 1.4)[..., None], 0.0)
    return char, col, dep


def put(char, col, y, x, ch, rgb, k):
    if 0 <= y < char.shape[0] and 0 <= x < char.shape[1]:
        char[y, x], col[y, x] = C(ch), np.asarray(rgb) * k


def rays(char, col, cy, cx, reach, rgb, strength=1.0, force=False):
    # a four-pointed flare: long arms sideways and up/down, short diagonals (force: over anything)
    rows, cols = char.shape
    for dist in range(1, reach + 1):
        fade = (1 - dist / (reach + 1)) * strength
        arms = [(0, 1, "-"), (0, -1, "-"), (1, 0, "|"), (-1, 0, "|")]
        if dist <= reach // 2:
            arms += [(1, 1, "\\"), (-1, -1, "\\"), (1, -1, "/"), (-1, 1, "/")]
        for dy, dx, ch in arms:
            yy, xx = cy + dy * dist, cx + dx * dist * (2 if dy == 0 else 1)
            k = fade * (0.7 if dx and dy else 1.0)
            if 0 <= yy < rows and 0 <= xx < cols and (force or col[yy, xx].max() < k):
                char[yy, xx], col[yy, xx] = C(ch), np.asarray(rgb) * k
    put(char, col, cy, cx, "*", rgb, 1.3 * strength)


def dots(char, col, dep, p, glyph, rgb, k, cols, rows, aspect):
    # loose points of light, hidden where something solid is in front of them
    sx, sy, z = project_cam(to_cam(p), cols, rows, aspect)
    ix, iy = np.floor(sx).astype(int), np.floor(sy).astype(int)
    ok = np.flatnonzero((ix >= 0) & (ix < cols) & (iy >= 0) & (iy < rows) & (k > 0.05))
    ok = ok[z[ok] < dep[iy[ok], ix[ok]]]
    ok = ok[np.argsort(k[ok])]                                  # the brightest drawn last
    char[iy[ok], ix[ok]] = glyph[ok]
    col[iy[ok], ix[ok]] = rgb[ok] * k[ok, None]
    return len(ok)


# snowflakes: a few always drifting down; on every shake hundreds are thrown up off the
# ground, swirl round the globe and settle again, slowly

N_CALM, N_SHAKEN = 150, 700
CALM = np.random.default_rng(3).random((N_CALM, 5))
SHAKEN = np.random.default_rng(4).random((N_SHAKEN, 6))
FLAKE_GLYPH = np.array([C("."), C("+"), C("*")])
FLAKE_INK = np.array([0.86, 0.93, 1.00])


def in_globe(ang, rf, y):
    rad = rf * np.sqrt(np.clip(0.94 ** 2 - y * y, 0, None))
    return np.stack([np.cos(ang) * rad, y, np.sin(ang) * rad], 1)


def flakes(t):
    out = []
    if t > T_GROUND[1]:
        c = CALM
        top = 0.88
        span = top - FLOOR_Y
        fall = (t * (0.045 + 0.06 * c[:, 2]) + c[:, 3] * span) % span
        y = top - fall
        p = in_globe(c[:, 0] * TAU + 0.3 * np.sin(0.4 * t + c[:, 4] * TAU), 0.95 * np.sqrt(c[:, 1]), y)
        k = (0.30 + 0.60 * c[:, 2] ** 2) * smooth(fall / 0.12) * smooth((span - fall) / 0.04) \
            * smooth((t - T_GROUND[1]) / 1.0)
        out.append((p, c[:, 2], k))
    a = shake_age(t)
    if a is not None:
        s = SHAKEN
        lift = 0.35 + 0.45 * s[:, 5]
        peak = FLOOR_Y + 0.08 + (0.84 - FLOOR_Y - 0.08) * s[:, 1] ** 0.8
        v = 0.045 + 0.085 * s[:, 2]
        rise = 1 - (1 - np.clip(a / lift, 0, 1)) ** 3
        y = np.where(a < lift, FLOOR_Y + (peak - FLOOR_Y) * rise, peak - v * (a - lift))
        swirl = 5.5 * (1 - np.exp(-a / 1.2)) * (0.6 + 0.6 * s[:, 4])
        ang = s[:, 0] * TAU + swirl + 0.25 * np.sin(0.7 * a + s[:, 3] * TAU)
        rf = np.clip(0.22 + 0.74 * s[:, 3] + 0.08 * np.sin(1.3 * a + s[:, 4] * 9), 0, 0.98)
        p = in_globe(ang, rf, np.maximum(y, FLOOR_Y))
        k = (0.30 + 0.65 * s[:, 2] ** 2) * smooth((y - FLOOR_Y) / 0.05) * smooth(a / 0.15 + 0.3)
        out.append((p, s[:, 2], k))
    return out


# smoke: puffs from the chimney that rise, spread, drift and thin out before the glass

PUFF_EVERY, PUFF_LIFE = 0.10, 4.0               # a puff every 0.1 s, each living 4 s
SMOKE_INK = np.array([0.84, 0.88, 0.96])        # brighter than the snow, so it reads against the stars
SMOKE_DENSITY = 0.90                            # how solid each puff is (max brightness)
SMOKE_GLYPH = np.array([C("."), C("o"), C("O"), C("o"), C(".")])


def smoke(t):
    if t < T_SMOKE:
        return []
    k = np.arange(max(0, int((t - T_SMOKE - PUFF_LIFE) / PUFF_EVERY)), int((t - T_SMOKE) / PUFF_EVERY) + 1)
    born = T_SMOKE + k * PUFF_EVERY
    age = t - born
    k, born, age = k[(age >= 0) & (age < PUFF_LIFE)], born[(age >= 0) & (age < PUFF_LIFE)], age[(age >= 0) & (age < PUFF_LIFE)]
    if len(k) == 0:
        return []
    yaw = yaw_at(born)                                          # where the chimney was when it left
    cz = CHIM_Z + CABIN_Z
    ox, oz = CHIM_X * np.cos(yaw) + cz * np.sin(yaw), -CHIM_X * np.sin(yaw) + cz * np.cos(yaw)
    rnd = (np.stack([k * 0.618, k * 0.414, k * 0.732], 1) % 1.0)
    spread = 0.03 + 0.08 * age                                  # the column opens out as it rises
    pts, glyph, fade = [], [], []
    for off in (-1, 0, 1):                                      # three strands, so it reads as a cloud, not a thread
        x = ox + 0.07 * age + 0.04 * np.sin(1.3 * age + rnd[:, 0] * TAU) + off * spread * (0.5 + rnd[:, 1])
        y = CHIM_TOP + 0.03 + 0.17 * age - 0.009 * age * age
        z = oz + 0.04 * np.cos(1.1 * age + rnd[:, 2] * TAU) + 0.03 * off * np.sin(0.7 * age + rnd[:, 1] * TAU)
        p = np.stack([x, y, z], 1)
        f = smooth(age / 0.3) * (1 - age / PUFF_LIFE) * smooth((0.90 - np.linalg.norm(p, axis=1)) / 0.12)
        pts.append(p), fade.append(SMOKE_DENSITY * f * (1 if off == 0 else 0.8))
        glyph.append(SMOKE_GLYPH[np.clip((age / PUFF_LIFE * 5).astype(int), 0, 4)])
    return [(np.concatenate(pts), np.concatenate(glyph), np.tile(SMOKE_INK, (3 * len(k), 1)),
             np.concatenate(fade))]


# the glass is drawn by two strands of light that swirl up round it from the stand to the top,
# like the garland going up the Christmas tree; each point of the strand glitters as it passes

GLASS_FOOT, TURNS = -0.83, 2.0                  # where the glass comes out of the stand; how many times round


def make_swirl():
    g = fib_sphere(16000) * R_GLASS
    g = g[g[:, 1] > GLASS_FOOT]
    u = (g[:, 1] - GLASS_FOOT) / (R_GLASS - GLASS_FOOT)
    phi = (np.arctan2(g[:, 2], g[:, 0]) / TAU) % 1
    pts, when = [], []
    for strand in (0.0, 0.5):
        w = u * TURNS - ((phi + strand) % 1)                    # how many times round the strand is at this height
        near = np.abs(w - np.round(w)) < 0.035
        pts.append(g[near])
        when.append(np.clip((np.round(w[near]) + (phi[near] + strand) % 1) / TURNS, 0, 1))
    when = np.concatenate(when)
    return np.concatenate(pts), T_GLASS[0] + (T_GLASS[1] - T_GLASS[0]) * when


SWIRL, SWIRL_T = make_swirl()
SWIRL_LIFE = 0.6                                # how long the strands take to fade once the glass is whole


def swirl(t, M, shift):
    # the strands stay wound round the glass like tinsel, glittering, until the glass is whole
    out = 1 - smooth((t - T_GLASS[1]) / SWIRL_LIFE)
    age = t - SWIRL_T
    live = np.flatnonzero(age >= 0)
    if len(live) == 0 or out <= 0:
        return []
    a = age[live]
    p = SWIRL[live] @ M.T
    facing = 0.35 + 0.65 * np.clip(0.5 + 0.5 * (p @ VIEW), 0, 1)     # the far side of the glass is dimmer
    sparkle = np.clip(np.sin(t * 5 + live * 2.39996), 0, 1) ** 12
    head = a < 0.12
    glyph = np.where(head | (sparkle > 0.5), C("*"), C("+"))
    rgb = WHITE + (GOLD - WHITE) * smooth(a / 0.3)[:, None]
    k = np.where(head, 1.4, 0.55 + 0.6 * sparkle) * facing * out
    return [(p + shift, glyph, rgb, k)]


# the glass: one ray per cell against the sphere. Its rim is an outline, there is a little
# light in its edge, and a crescent of light inside the rim, upper left

_RAYS = {}


def cell_rays(cols, rows, aspect):
    if (cols, rows) not in _RAYS:
        x = ((np.arange(cols) + 0.5) / cols - 0.5) * 2 / ZOOM
        y = (0.5 - (np.arange(rows) + 0.5) / rows) * 2 / (ZOOM * aspect)
        X, Y = np.meshgrid(x, y)
        _RAYS[cols, rows] = unit(np.stack([X, Y, np.ones_like(X)], -1))
    return _RAYS[cols, rows]


def globe_cells(centre, cols, rows, aspect):
    D = cell_rays(cols, rows, aspect)
    b = D @ centre
    disc = b * b - (centre @ centre - R_GLASS ** 2)
    hit = disc > 0
    P = D * (b - np.sqrt(np.clip(disc, 0, None)))[..., None]
    return D, hit, P, (P - centre) / R_GLASS


def glass(char, col, dep, t, centre, cols, rows, aspect, flares):
    if t < T_GLASS[0]:
        return
    D, hit, P, N = globe_cells(centre, cols, rows, aspect)
    front = hit & (P[..., 2] < dep + 0.02)                      # not where the stand is in front of it
    cosv = np.clip(-(D * N).sum(-1), 0, 1)

    # the rim, drawn round from the bottom on both sides at once
    ph = np.pad(hit, 1, constant_values=False)
    rim = np.zeros_like(hit)
    gx, gy = np.zeros((rows, cols)), np.zeros((rows, cols))
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dx == dy == 0:
                continue
            out = hit & ~ph[1 + dy:rows + 1 + dy, 1 + dx:cols + 1 + dx]
            gx += dx * out
            gy += dy * out
            if dx == 0 or dy == 0:
                rim |= out
    # the rim comes up behind the swirl of light, as high as it has climbed
    height = ((P + EYE_CAM) @ BASIS - (centre + EYE_CAM) @ BASIS)[..., 1]
    up = (height - GLASS_FOOT) / (1 - GLASS_FOOT)               # 0 where the glass meets the stand, 1 at the top
    prog = float(np.clip((t - T_GLASS[0]) / (T_GLASS[1] - T_GLASS[0]), 0, 1))
    done = float(np.clip(1 - (t - T_GLASS[1]) / FLASH, 0, 1) ** 2) if t >= T_GLASS[1] else 0.0
    head = np.exp(-((up - prog) / 0.06) ** 2) * (prog < 1)
    drawn = rim & front & (up <= prog + 0.01)
    k = 0.80 + 0.6 * head + 0.5 * done
    ink = GLASS + (WHITE - GLASS) * np.clip(head + done, 0, 1)[..., None]
    char[drawn] = outline_letter(gx, gy)[drawn]
    col[drawn] = (ink * k[..., None])[drawn]

    # (c) @dwcminh.ascii, see LICENSE.txt. Not for use with AI tools: no feeding this code to
    # AI models, no training on it, no having an AI rework it.

    # when the swirl reaches the top it bursts like the star on the tree
    burst = float(np.clip(1 - (t - T_GLASS[1]) / 1.0, 0, 1) ** 2) if t >= T_GLASS[1] else 0.0
    if burst > 0.02:
        top = centre + BASIS @ UP * R_GLASS                     # the top of the glass, in camera space
        sx, sy, _ = project_cam(top[None], cols, rows, aspect)
        flares.append(((int(sy[0]), int(sx[0])), int(3 + 12 * burst), 1.5 * burst, GOLD + (WHITE - GOLD) * burst, True))
    shown = float(smooth((t - T_GLASS[1] + 0.2) / 0.8))
    if shown <= 0:
        return

    # light in the edge of the glass, thickest near the rim
    edge = front & ~rim & (cosv < 0.34)
    fres = np.clip((0.34 - cosv) / 0.34, 0, 1) * shown
    empty = char == 0
    m = edge & empty & (fres > 0.55)
    char[m] = C(".")
    col[m] = GLASS * (0.22 * fres[m])[:, None]
    m = edge & ~empty
    col[m] += GLASS * (0.10 * fres[m])[:, None]

    # a crescent of light along the upper left inside the rim
    ang = np.degrees(np.arctan2(N[..., 1], N[..., 0]))
    arc = front & ~rim & (cosv > 0.13) & (cosv < 0.24) & (ang > 105) & (ang < 200)
    arc_k = np.sin(np.clip((ang - 105) / 95, 0, 1) * np.pi) * shown
    m = arc & (arc_k > 0.25)
    char[m] = slope_char(-N[..., 1], N[..., 0])[m]
    col[m] = np.maximum(col[m], (WHITE * 0.85) * arc_k[m, None])


# around the globe, as round the Christmas tree: snowy ground, stars, and snow falling

def make_ground():
    # snowy ground, sampled evenly in screen rows (uniform in 1 / distance)
    rng = np.random.default_rng(11)
    m = 14000
    dist = 1 / rng.uniform(1 / 16, 1 / 1.4, m)
    x = (rng.random(m) - 0.5) * dist * 0.62
    p = np.stack([x, BASE_Y + 0.01 * rng.normal(0, 1, m), EYE[2] - dist], 1)
    near = np.exp(-(p[:, 0] ** 2 + p[:, 2] ** 2) / 2.0)
    lum = (0.16 + 0.28 * rng.random(m)) * (0.55 + 0.45 * np.exp(-dist / 9)) + 0.35 * near
    return p, lum


GROUND_P, GROUND_L = make_ground()
GROUND_GLYPH = np.array([[C(p[j % len(p)]) for j in range(12)] for p in (".", "-.", "--=", "=-")])
SKY = np.random.default_rng(5).random((320, 3))
SNOWFALL = 1000                                 # flakes falling outside the globe
OUTSIDE = np.random.default_rng(13).random((SNOWFALL, 5))
_GROUND = {}


def ground_layer(cols, rows, aspect):
    # the ground never moves, so it is drawn once and kept
    if (cols, rows) not in _GROUND:
        sx, sy, z = project_cam(to_cam(GROUND_P), cols, rows, aspect)
        ok = np.flatnonzero((sx >= 0) & (sx < cols) & (sy >= 0) & (sy < rows) & (z > 0.3))
        order = ok[np.argsort(-z[ok])]
        iy, ix = sy[order].astype(int), sx[order].astype(int)
        lum = np.zeros((rows, cols))
        lum[iy, ix] = GROUND_L[order]
        h = HASH(rows, cols)
        char = np.where(lum > 0, GROUND_GLYPH[np.clip((lum * 3.3).astype(int), 0, 3), h % 12], 0)
        col = np.array([0.66, 0.74, 0.88]) * np.clip(0.25 + 0.75 * lum, 0, 1)[..., None] * (lum > 0)[..., None]
        horizon = int(project_cam(to_cam(np.array([[0, BASE_Y, EYE[2] - 60]])), cols, rows, aspect)[1][0])
        _GROUND[cols, rows] = char, col, horizon
    return _GROUND[cols, rows]


def snowfall(t, centre):
    # falling snow outside the globe; none of it inside the glass
    f = OUTSIDE
    fy = 1.9 - (t * (0.14 + 0.20 * f[:, 2]) + f[:, 3] * 3.3) % 3.3
    p = np.stack([-3.2 + 6.4 * f[:, 0] + 0.10 * np.sin(t * 0.9 + f[:, 4] * TAU), fy, -2.5 + 5.5 * f[:, 1]], 1)
    k = (0.25 + 0.75 * f[:, 2] ** 2) * (np.linalg.norm(p - centre, axis=1) > R_GLASS + 0.04) * (fy > BASE_Y)
    glyph = np.where(k < 0.45, C("."), np.where(k < 0.75, C("+"), C("*")))
    return p, glyph, k

def frame(t, cols, rows, aspect):
    pts, flares, M, shift, T, info = scene(t, cols, rows, aspect)
    char, col, dep = bodies(*pts, cols, rows, t)
    centre = BASIS @ shift - EYE_CAM                            # the middle of the globe, in camera space
    _, hit, P, _ = globe_cells(centre, cols, rows, aspect)

    # the snowy ground and the stars, only where nothing else is
    gch, gcol, horizon = ground_layer(cols, rows, aspect)
    free = (char == 0) & ~hit & (gch > 0)
    char[free], col[free] = gch[free], gcol[free] * smooth(t / 0.8)
    sk_x, sk_y = (SKY[:, 0] * cols).astype(int), (SKY[:, 1] * max(horizon - 1, 1)).astype(int)
    tw = 0.12 + 0.6 * np.clip(np.sin(t * (1 + 2 * SKY[:, 2]) + SKY[:, 2] * 50), 0, 1) ** 4
    ok = (char[sk_y, sk_x] == 0) & ~hit[sk_y, sk_x]
    sk_x, sk_y, tw = sk_x[ok], sk_y[ok], tw[ok]
    char[sk_y, sk_x] = np.where(tw < 0.35, C("."), np.where(tw < 0.6, C("+"), C("*")))
    col[sk_y, sk_x] = WHITE * tw[:, None]

    # the snow in the water, the smoke, and the swirl of light that draws the glass
    n_flakes = 0
    to_world = lambda p: p @ T.T + (PIVOT - T @ PIVOT)
    for p, size, k in flakes(t):
        glyph = FLAKE_GLYPH[np.clip((size * 3).astype(int) - (size < 0.6), 0, 2)]
        n_flakes += dots(char, col, dep, to_world(p), glyph, np.tile(FLAKE_INK, (len(p), 1)), k, cols, rows, aspect)
    for p, glyph, rgb, k in smoke(t) + swirl(t, M, shift):
        dots(char, col, dep, p, glyph, rgb, k, cols, rows, aspect)

    glass(char, col, dep, t, centre, cols, rows, aspect, flares)

    # snow falling outside, in front of the glass or round it
    outside = np.where(hit & (P[..., 2] < dep), P[..., 2], dep) if t >= T_GLASS[0] else dep
    p, glyph, k = snowfall(t, shift)
    n_flakes += dots(char, col, outside, p, glyph, np.tile(WHITE, (len(p), 1)), k, cols, rows, aspect)

    # flares: the top of the glass, the windows lighting up, the lantern
    for p, reach, strength, rgb, always in flares:
        if isinstance(p, tuple):
            y, x = p
            rays(char, col, y, x, reach, rgb, strength, force=True)
            continue
        sx, sy, z = project_cam(to_cam(np.asarray(p, float)[None]), cols, rows, aspect)
        y, x = int(sy[0]), int(sx[0])
        if 0 <= y < rows and 0 <= x < cols and (always is True or z[0] <= dep[y, x] + 0.08):
            rays(char, col, y, x, reach, rgb, strength, force=always == "force")

    # the greeting is lettered on top by the renderer, in big letters: clear a band for it
    if t > T_MSG:
        row, span = rows - (16 if rows > 90 else 7), int(len(MESSAGE) * MSG_CELLS) + 6     # below the stand
        char[row - 1:row + 2, max((cols - span) // 2, 0):(cols + span) // 2] = 0
        info["msg"] = (row, min(len(MESSAGE), int((t - T_MSG) * 10)))
    info["flakes"] = n_flakes
    info["letters"] = int((char > 0).sum())
    return char, col, info

# window

TITLE = "ASCII Snow Globe"
CW, CH, FONT_PX = 7, 10, 11
COLS, ROWS = 112, 104
W, H = COLS * CW, ROWS * CH
MONO = "consolas,menlo,dejavusansmono,couriernew,monospace"
HINT = "Space pause · R restart · S screenshot · Esc quit"
DIM, ACCENT, SIGN = (100, 110, 132), (150, 210, 255), (176, 184, 210)


class Renderer:
    def __init__(self, cols=COLS, rows=ROWS, cw=CW, ch=CH, font_px=FONT_PX, hud_px=15, hint=True):
        self.cols, self.rows, self.cw, self.ch = cols, rows, cw, ch
        self.w, self.h = cols * cw, rows * ch
        font = pygame.font.SysFont(MONO, font_px)
        atlas = []
        for code in range(32, 127):
            s = pygame.Surface((cw, ch))
            g = font.render(chr(code), True, (255, 255, 255))
            s.blit(g, ((cw - g.get_width()) // 2, (ch - g.get_height()) // 2))
            atlas.append(pygame.surfarray.array3d(s).transpose(1, 0, 2))
        self.atlas = np.stack(atlas)                            # glyph, CH, CW, 3
        self.art = pygame.Surface((self.w, self.h))
        self.out = pygame.Surface((self.w, self.h))
        self.small = pygame.font.SysFont(MONO, hud_px)
        self.big = pygame.font.SysFont(MONO, int(font_px * 1.4))
        self.hud_gap = int(hud_px * 1.45)
        self.hint = hint

    @staticmethod
    def blur(src, size, radius):
        small = pygame.transform.smoothscale(src, size)
        if hasattr(pygame.transform, "gaussian_blur"):
            small = pygame.transform.gaussian_blur(small, max(1, radius))
        return small

    def glow(self):
        # a tight glow and a wide one; the wide one is made from the tight one
        w, h = self.w, self.h
        tight = self.blur(self.art, (w // 5, h // 5), 1)
        wide = self.blur(tight, (w // 10, h // 10), 2)
        for layer, amount in ((tight, 0.65), (wide, 0.42)):
            layer = pygame.transform.smoothscale(layer, (w, h))
            layer.fill((int(255 * amount),) * 3, special_flags=pygame.BLEND_MULT)
            self.out.blit(layer, (0, 0), special_flags=pygame.BLEND_ADD)

    def draw(self, t):
        w, h = self.w, self.h
        char, col, info = frame(t, self.cols, self.rows, w / h)
        pygame.surfarray.blit_array(self.art, self.atlas[char].transpose(1, 3, 0, 2, 4).reshape(w, h, 3))
        tint = pygame.surfarray.make_surface((np.clip(col, 0, 1) * 255).astype(np.uint8).transpose(1, 0, 2))
        self.art.blit(pygame.transform.scale(tint, (w, h)), (0, 0), special_flags=pygame.BLEND_MULT)
        if "msg" in info:                                       # typed out, the letters taking turns red, gold, green
            row, shown = info["msg"]
            adv = self.cw * MSG_CELLS
            x0, y0 = (w - len(MESSAGE) * adv) / 2, row * self.ch + self.ch / 2
            for i, ch in enumerate(MESSAGE[:shown]):
                if ch != " ":
                    tint = (RED, GOLD, GREEN)[(i // 2 + int(t * 1.5)) % 3] * (0.85 + 0.25 * np.sin(t * 5 + i))
                    g = self.big.render(ch, True, tuple(int(c) for c in np.clip(tint, 0, 1) * 255))
                    self.art.blit(g, (int(x0 + i * adv + (adv - g.get_width()) / 2), int(y0 - g.get_height() / 2)))
        self.out.fill((4, 6, 12))
        self.out.blit(self.art, (0, 0), special_flags=pygame.BLEND_ADD)
        self.glow()
        lines = [f"rotation {info['deg']:06.2f}°      lights {info['lights']:>3}      snowflakes {info['flakes']:>4}",
                 f"letters {info['letters']:,}"]
        if self.hint:
            lines.append(HINT)
        g = self.hud_gap
        for i, text in enumerate(lines):
            self.out.blit(self.small.render(text, True, DIM), (24, h - 18 - g * (len(lines) - i)))
        self.out.blit(self.small.render(CREDIT, True, SIGN), (24, h - 18 - g * (len(lines) + 1) - g // 3))
        tt = self.small.render(f"{'●' if int(t * 2) % 2 == 0 else ' '} t {t:05.2f}s", True, ACCENT)
        self.out.blit(tt, (w - 24 - tt.get_width(), 20))
        return self.out


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
                pygame.image.save(screen, str(Path(__file__).with_name(f"snow_globe_{int(time.time())}.png")))
        dt = clock.tick(30) / 1000
        if not paused:
            t += min(dt, 1 / 15)
            screen = renderer.draw(t)
        window.blit(screen if size == (W, H) else pygame.transform.smoothscale(screen, size), (0, 0))
        pygame.display.flip()


if __name__ == "__main__":
    sys.exit(main())
