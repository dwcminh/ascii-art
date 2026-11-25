# ASCII Eiffel Tower
# @dwcminh.ascii, 2026
# Terms in LICENSE.txt: personal, non-commercial use only. Not for use with AI tools:
# do not feed this code to an AI model, train on it, or have an AI rework it.
#
#   pip install numpy pygame-ce
#   python eiffel_tower.py
#
# Night on a Paris street, looking up at the tower: it rises from the ground, lights up gold,
# sparkles, the beacon sweeps the sky and fireworks go up while people stroll past.
#
# Space pause, R restart, S screenshot, Esc quit

import sys
import time
from pathlib import Path

import numpy as np
import pygame

CREDIT = "@dwcminh.ascii"

TAU = np.pi * 2
TOWER_M = 330.0                                 # real height, metres
GROUND, HEIGHT = -1.15, 2.6                     # floor and tower height in world units
S = HEIGHT / TOWER_M                            # metres -> world units

# the street, in metres
CAM_DIST = 444.0                                # camera to the foot of the tower
EYE_H = 1.6                                     # eye level of someone standing in the street
STREET = 22.0                                   # centre line to the house fronts
ROW_END = 170.0                                 # the houses stop here, then the park opens up
ROOF = 3.5                                      # mansard roofs on top of the fronts
LAMP_X, LAMP_D = 19.0, np.arange(28.0, ROW_END, 24.0)

# timeline (s)
T_BUILD = (0.8, 7.2)
T_GLOW = (7.8, 9.8)
T_BEACON = 10.2
T_SPARKLE = 11.0
T_FIREWORKS = 12.0
FLASH = 0.6                                     # how long a new platform or arch glows white (s)

GIRDER, BRACE, ARCH, DECK, MESH = range(5)
LINES = (GIRDER, BRACE, ARCH)                   # drawn with - / | \ along their direction
POOLS = ["1il!;:", "rtfjcvxz=+", "aeoun0{}[]<>", "08B$#&%Q"]   # fill letters, dark -> bright
C = lambda ch: ord(ch) - 32                     # character -> glyph index
FILL = np.array([[C(p[k % len(p)]) for k in range(12)] for p in POOLS])
SLOPE = np.array([C(c) for c in "-/|\\-"])

WHITE = np.array([0.92, 0.95, 1.00])
STEEL = np.array([0.45, 0.62, 1.00])
GOLD = np.array([1.00, 0.62, 0.16])
GOLD_HI = np.array([1.00, 0.80, 0.36])
RED = np.array([1.00, 0.16, 0.20])
BEAM = np.array([1.00, 0.92, 0.72])
STONE = np.array([0.85, 0.76, 0.60])
ZINC = np.array([0.55, 0.64, 0.85])
IRON = np.array([0.62, 0.66, 0.80])
WARM = np.array([1.00, 0.74, 0.36])
COOL = np.array([0.70, 0.84, 1.00])
LAMP = np.array([1.00, 0.82, 0.50])
FIREWORK = np.array([(1.00, 0.25, 0.30), (1.00, 0.78, 0.30), (0.35, 0.85, 1.00), (1.00, 0.45, 0.85),
                     (0.50, 1.00, 0.55), (0.95, 0.95, 1.00), (0.60, 0.50, 1.00)])


def smooth(x):
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3 - 2 * x)


def unit(v):
    v = np.asarray(v, float)
    return v / np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-9)


def fib_sphere(n):
    i = np.arange(n) + 0.5
    y = 1 - 2 * i / n
    r = np.sqrt(1 - y * y)
    th = np.pi * (3 - np.sqrt(5)) * i
    return np.stack([r * np.cos(th), y, r * np.sin(th)], 1)


def slope_char(dx, dy):
    # screen direction -> the ASCII stroke that looks most like it
    ang = np.degrees(np.arctan2(dy, dx)) % 180
    return SLOPE[np.digitize(ang, [25, 72, 108, 155])]


# the tower's shape, in metres

def half_width(h):
    # the outer corners curve in roughly exponentially, 125 m square at the base
    return 62.5 * np.exp(-np.asarray(h, float) / 98)


def leg_size(h):
    return 0.12 * half_width(h) + 5


H_MERGE = 98 * np.log(62.5 * 0.76 / 10)        # where the four legs meet (~153 m)


def build_time(h):
    # the tower rises from the ground; the heavy bottom takes longer
    u = np.clip(np.asarray(h, float) / TOWER_M, 0, 1)
    return T_BUILD[0] + (T_BUILD[1] - T_BUILD[0]) * u ** 0.7


class Parts:
    def __init__(self):
        self.cols = []

    def add(self, p, kind, part, tan=(0, 0, 0), n=None, appear=None, centre=None, base=1.0, pop=False):
        p = np.asarray(p, float)
        m = len(p)
        if n is None:                                           # facing out from the axis, a bit up
            r = np.hypot(p[:, 0], p[:, 2])
            n = unit(np.stack([p[:, 0], 0.3 * r + 1e-3, p[:, 2]], 1))
        if appear is None:
            appear = build_time
        if callable(appear):
            appear = appear(p[:, 1])
        cen = p if centre is None else np.broadcast_to(np.asarray(centre, float), (m, 3))
        b = lambda v, w=None: np.broadcast_to(np.asarray(v, float), (m, w) if w else (m,)).copy()
        self.cols.append((cen.copy(), p - cen, b(n, 3), b(tan, 3), np.full(m, kind), b(appear), b(base),
                          np.full(m, pop), np.full(m, part)))

    def line(self, pts, kind, part, step=2.0, **kw):
        # resample a polyline evenly and remember which way it runs
        pts = np.asarray(pts, float)
        d = np.diff(pts, axis=0)
        s = np.concatenate([[0], np.cumsum(np.linalg.norm(d, axis=1))])
        u = np.append(np.arange(0, s[-1], step), s[-1])
        p = np.stack([np.interp(u, s, pts[:, i]) for i in range(3)], 1)
        seg = np.clip(np.searchsorted(s, u, side="right") - 1, 0, len(d) - 1)
        self.add(p, kind, part, tan=unit(d[seg]), **kw)

    def face(self, corner_a, corner_b, centre, h0, h1, part):
        # the skin between two corner girders, set back a little so the iron in front wins
        h = np.arange(h0, h1, 1.5)
        a, b, c = corner_a(h), corner_b(h), centre(h)
        s = np.linspace(0.04, 0.96, 12)[None, :, None]
        p = a[:, None] * (1 - s) + b[:, None] * s
        inward = unit((c[:, None] - p) * [1, 0, 1])
        self.add((p + 0.8 * inward).reshape(-1, 3), MESH, part, n=(-inward).reshape(-1, 3), base=0.62)

    def build(self):
        cen, off, n, tan, kind, appear, base, pop, part = [np.concatenate(c) for c in zip(*self.cols)]
        hgt = cen[:, 1] + off[:, 1]
        to_world = lambda p: np.stack([p[:, 0] * S, p[:, 1] * S, p[:, 2] * S], 1)
        cen = to_world(cen) + [0, GROUND, 0]
        return cen, to_world(off), n, tan, kind, appear, base, pop, hgt, part


def leg_corner(qx, qz, i, h):
    # corner i (0..3, going round) of the leg in quadrant (qx, qz) at height h
    w, s = half_width(h), leg_size(h)
    lo, hi = w - 2 * s, w
    ax, az = [(lo, lo), (hi, lo), (hi, hi), (lo, hi)][i]
    return np.stack([qx * ax, np.asarray(h, float), qz * az], -1)


def col_corner(i, h):
    w = half_width(h)
    ax, az = [(-1, -1), (1, -1), (1, 1), (-1, 1)][i]
    return np.stack([ax * w, np.asarray(h, float), az * w], -1)


def levels(h0, h1, step):
    out = [h0]
    while out[-1] + step(out[-1]) < h1 - 3:
        out.append(out[-1] + step(out[-1]))
    return out + [h1]


def lattice(q, corner, hs, part):
    # each face: a horizontal strut and an X between every pair of levels
    for i in range(4):
        j = (i + 1) % 4
        for h0, h1 in zip(hs[:-1], hs[1:]):
            q.line([corner(i, h0), corner(j, h1)], BRACE, part, base=0.85)
            q.line([corner(j, h0), corner(i, h1)], BRACE, part, base=0.85)
            q.line([corner(i, h1), corner(j, h1)], BRACE, part, base=0.95)


def platform(q, h0, h1, hw, hole, part):
    # a box-like band round the tower with a deck on top (open in the middle)
    appear = build_time(h1) + 0.15
    centre = (0, h0, 0)
    u = np.arange(-hw, hw, 1.0)
    for y in np.arange(h0, h1 + 0.1, 1.2):
        for sx, sz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            p = np.stack([sx * hw + sz * u, np.full_like(u, y), sz * hw - sx * u], 1)
            q.add(p, DECK, part, n=(sx, 0.2, sz), appear=appear, centre=centre, pop=True)
    g = np.arange(-hw, hw + 0.1, 2.0)
    x, z = [a.ravel() for a in np.meshgrid(g, g)]
    keep = np.maximum(np.abs(x), np.abs(z)) > hole
    p = np.stack([x[keep], np.full(keep.sum(), h1), z[keep]], 1)
    q.add(p, DECK, part, n=(0, 1, 0), appear=appear, centre=centre, base=0.7, pop=True)


def build():
    q = Parts()

    # legs: four curved square columns of iron lattice
    for leg, (qx, qz) in enumerate(((-1, -1), (1, -1), (1, 1), (-1, 1))):
        c = lambda i, h, qx=qx, qz=qz: leg_corner(qx, qz, i, h)
        mid = lambda h, qx=qx, qz=qz: np.stack([qx * (half_width(h) - leg_size(h)), h,
                                               qz * (half_width(h) - leg_size(h))], -1)
        h = np.arange(0, H_MERGE + 0.5, 1.0)
        for i in range(4):
            q.line(c(i, h), GIRDER, leg)
            q.face(lambda y, i=i: c(i, y), lambda y, i=i: c((i + 1) % 4, y), mid, 0, H_MERGE, leg)
        lattice(q, c, levels(0, H_MERGE, lambda y: 1.4 * leg_size(y)), leg)

    # arches: the decorative arcs between the legs, under the first floor
    th = np.linspace(0, np.pi, 90)
    span = half_width(18) - 2 * leg_size(18)
    for a, b in ((span, 34.0), (span - 3, 31.0)):
        arc = np.stack([a * np.cos(th), 18 + b * np.sin(th)], 1)
        for k in range(4):
            x, z = arc[:, 0], half_width(arc[:, 1]) - 1.5
            ca, sa = np.cos(k * TAU / 4), np.sin(k * TAU / 4)
            pts = np.stack([ca * x + sa * z, arc[:, 1], -sa * x + ca * z], 1)
            # each arch draws itself from both feet up to the crown once the legs are past it
            q.line(pts, ARCH, 9, step=1.5, base=1.1,
                   appear=lambda y: build_time(52) + 0.6 * np.clip((y - 18) / 34, 0, 1))

    # platforms: the first and second floor
    platform(q, 57, 64, half_width(57) + 3, 24, 5)
    platform(q, 115, 121, half_width(115) + 2, 12, 6)

    # upper column: the legs merged into one tapering lattice shaft
    h = np.arange(H_MERGE, 276.5, 1.0)
    axis = lambda y: np.stack([0 * y, y, 0 * y], -1)
    for i in range(4):
        q.line(col_corner(i, h), GIRDER, 4)
        q.face(lambda y, i=i: col_corner(i, y), lambda y, i=i: col_corner((i + 1) % 4, y), axis, H_MERGE, 276, 4)
    lattice(q, col_corner, levels(H_MERGE, 276, lambda y: 1.3 * half_width(y)), 4)

    # summit: the top floor, the lantern and the antenna
    platform(q, 274, 288, 7, 0, 7)
    platform(q, 288, 293, 4, 0, 8)
    q.line([(0, 293, 0), (0, TOWER_M, 0)], GIRDER, 8, step=0.8)
    for y, r in ((300, 2.5), (310, 1.5)):
        q.line([(-r, y, 0), (r, y, 0)], GIRDER, 8, step=0.8)

    return q.build()


CEN, OFF, N0, TAN, KIND, APPEAR, BASE, POP, HGT, PART = build()
POS, APPEAR_MAX = CEN + OFF, float(APPEAR.max())
IS_LINE = np.isin(KIND, LINES)
GLINT = np.random.default_rng(1).random(len(POS))                 # per point gold variation

# the sparkle: a thousand bulbs flashing at random over the iron
_rng = np.random.default_rng(9)
TW = _rng.choice(np.flatnonzero(IS_LINE), 1100, replace=False)
TW_PHASE, TW_RATE = _rng.random(len(TW)), 0.6 + 0.9 * _rng.random(len(TW))

# camera: standing in the street, level, the horizon low in the picture
EYE = np.array([0.0, GROUND + EYE_H * S, CAM_DIST * S])
BASIS = np.array([[1.0, 0, 0], [0, 1.0, 0], [0, 0, -1.0]])       # world -> camera axes
EYE_CAM = BASIS @ EYE
ZOOM = 2.45
HORIZON = 0.83                                                  # horizon height on screen (0 top, 1 bottom)
KEY = unit([-0.5, 0.55, 0.65])

# (c) @dwcminh.ascii, see LICENSE.txt. Not for use with AI tools: no feeding this code to
# AI models, no training on it, no having an AI rework it.

# the tower does not move, so its camera-space points, shading and strokes are worked out once
CAM_T = POS @ BASIS.T - EYE_CAM
DIFF = np.clip(N0 @ KEY, 0, 1)
_tc = TAN @ BASIS.T
STROKE = np.where(IS_LINE, np.where(np.hypot(_tc[:, 0], _tc[:, 1]) < 0.35, C("+"),
                                    slope_char(_tc[:, 0], _tc[:, 1])), -1)


def street_cam(x, y, d):
    # street coordinates (metres: across, up, ahead of the camera) -> camera space
    return np.stack([np.asarray(x, float) * S, (np.asarray(y, float) - EYE_H) * S, np.asarray(d, float) * S], -1)


def project_cam(cam, cols, rows, aspect):
    z = cam[..., 2]
    zz = np.maximum(z, 1e-3)
    return (0.5 + cam[..., 0] / zz * ZOOM * 0.5) * cols, (HORIZON - cam[..., 1] / zz * ZOOM * 0.5 * aspect) * rows, z


def project(p, cols, rows, aspect):
    return project_cam(p @ BASIS.T - EYE_CAM, cols, rows, aspect)


def lit_level(h, t):
    # the golden lights come on from the ground up
    on = T_GLOW[0] + (T_GLOW[1] - T_GLOW[0]) * np.asarray(h) / TOWER_M
    return smooth((t - on) / 0.5), np.exp(-((t - on - 0.15) / 0.2) ** 2)


T_STILL = max(APPEAR_MAX + FLASH, T_GLOW[1] + 1.0)              # after this the tower no longer changes
_STILL = []


def tower(t):
    # the tower as it stands at time t, in camera space
    if t > T_STILL:
        if not _STILL:
            _STILL.append(tower_at(T_STILL))
        return _STILL[0]
    return tower_at(t)


def tower_at(t):
    vis =np.flatnonzero(t >= APPEAR) if t < APPEAR_MAX else np.arange(len(POS))
    age = t - APPEAR[vis]
    if t < APPEAR_MAX + FLASH:
        swell = 1 + 0.25 * np.clip(1 - age / FLASH, 0, 1) ** 2
        grow = np.where(POP[vis], smooth(age / 0.25) * swell, 1.0)
        cam = (CEN[vis] + OFF[vis] * grow[:, None]) @ BASIS.T - EYE_CAM
    else:
        cam = CAM_T[vis]
    diff, kind, glyph = DIFF[vis], KIND[vis], STROKE[vis].copy()

    # golden lights: blue steel while it is built, then gold sweeping up with a white edge
    lit, front = lit_level(HGT[vis], t)
    lum = BASE[vis] * (0.55 + 0.55 * diff) + 0.9 * front
    gold = np.where((kind == MESH)[:, None], GOLD, GOLD_HI) * (0.88 + 0.2 * GLINT[vis, None])
    rgb = STEEL + (gold - STEEL) * lit[:, None]
    rgb += (1 - rgb) * np.clip(front, 0, 1)[:, None] * 0.7

    if t < T_BUILD[1] + 1.0:
        fresh = (age < 0.12) & (kind != MESH)                   # welding sparks on the rising edge
        glyph[fresh], lum[fresh], rgb[fresh] = C("*"), 1.3, WHITE

    if t < APPEAR_MAX + FLASH:
        # platforms and arches pop in white-hot and cool down
        f = np.where((kind == DECK) | (kind == ARCH), np.clip(1 - age / FLASH, 0, 1) ** 2, 0.0)
        on = f > 0
        if on.any():
            rgb[on] += (1 - rgb[on]) * f[on, None]
            lum[on] += 1.3 * f[on]
    return cam, lum, rgb, PART[vis], glyph


# people

COATS = np.array([(1.00, 0.30, 0.32), (0.38, 0.55, 1.00), (0.95, 0.80, 0.55), (0.75, 0.78, 0.86),
                  (0.30, 0.85, 0.75), (1.00, 0.68, 0.30), (0.85, 0.50, 0.95)])
SKIN, LEGS, PHONE = np.array([1.00, 0.82, 0.70]), np.array([0.45, 0.50, 0.66]), np.array([0.85, 0.95, 1.00])
HEAD_T = fib_sphere(40) * 0.11 + [0, 1.63, 0]
_a, _h = np.meshgrid(np.linspace(0, TAU, 20, endpoint=False), np.linspace(0.86, 1.48, 16))
_r = 0.22 - 0.05 * (_h - 0.86) / 0.62                                   # coat flares out a little
TORSO_T = np.stack([np.cos(_a) * _r, _h, 0.6 * np.sin(_a) * _r], -1).reshape(-1, 3)
TORSO_N = np.stack([np.cos(_a), np.zeros_like(_a), np.sin(_a)], -1).reshape(-1, 3)
LIMB_S = np.linspace(0, 1, 12)[:, None]
STREETLIGHT = unit([-0.3, 0.8, -0.5])
_g = np.stack(np.meshgrid(np.linspace(-0.035, 0.035, 3), np.linspace(1.47, 1.59, 4)), -1).reshape(-1, 2)
PHONE_T = np.stack([_g[:, 0], _g[:, 1], np.full(len(_g), 0.44)], 1)
BODY_N = np.concatenate([unit(HEAD_T - [0, 1.63, 0]), TORSO_N])
NH, NT, NL = len(HEAD_T), len(TORSO_T), len(LIMB_S)
SIDES = np.array([-1.0, 1.0])
HIP = np.stack([SIDES * 0.09, [0.9, 0.9], [0, 0]], 1)
SHOULDER = np.stack([SIDES * 0.22, [1.44, 1.44], [0, 0]], 1)
REACH = np.stack([SIDES * 0.04, [1.52, 1.52], [0.42, 0.42]], 1) - SHOULDER     # arms up, holding a phone
WALK, CROSS, PHOTO = range(3)


def make_crowd():
    rng = np.random.default_rng(21)
    n = 30
    mode = np.array([WALK] * 20 + [CROSS] * 5 + [PHOTO] * 5)
    near = rng.random(n) ** 1.5                                 # more people close to the camera
    return {
        "mode": mode,
        "x": np.where(mode == PHOTO, rng.uniform(-10, 10, n), rng.choice([-1, 1], n) * 17 * rng.random(n) ** 1.4),
        "d": np.select([mode == WALK, mode == CROSS], [12 + (ROW_END - 12) * near, 14 + 50 * near],
                       rng.uniform(14, 40, n)),
        "dir": rng.choice([-1.0, 1.0], n),
        "speed": rng.uniform(1.1, 1.6, n),
        "scale": rng.uniform(0.9, 1.08, n),
        "phase": rng.random(n) * TAU,
        "coat": COATS[rng.integers(0, len(COATS), n)],
    }


CROWD = make_crowd()


def crowd(t):
    # everyone at once: little figures of points with a head, a coat, and swinging legs and arms
    m = CROWD
    walk, cross, photo = m["mode"] == WALK, m["mode"] == CROSS, m["mode"] == PHOTO
    x = np.where(cross, -STREET + (m["x"] + STREET + m["dir"] * m["speed"] * t) % (2 * STREET), m["x"])
    d = np.where(walk, 12 + (m["d"] - 12 + m["dir"] * m["speed"] * t) % (ROW_END - 2), m["d"])
    fx = np.where(cross, m["dir"], 0.0)                         # which way each one faces
    fd = np.where(walk, m["dir"], np.where(photo, 1.0, 0.0))
    rx, rd = fd, -fx                                            # and their right hand side
    phi = m["speed"] * t / 0.75 * np.pi + m["phase"]
    swing = np.where(photo, 0.0, 0.42 * np.sin(phi))
    bob = np.where(photo, 0.0, 0.025 * np.abs(np.cos(phi)))

    a = SIDES[None] * swing[:, None]                            # (people, side)
    legdir = np.stack([np.zeros_like(a), -np.cos(a), np.sin(a)], -1)
    b = -0.8 * a
    armdir = unit(np.stack([np.broadcast_to(SIDES * 0.12, a.shape), -np.cos(b), np.sin(b)], -1)) * 0.6
    armdir = np.where(photo[:, None, None], REACH[None], armdir)
    legs = HIP[None, :, None] + LIMB_S[None, None] * 0.9 * legdir[:, :, None]
    arms = SHOULDER[None, :, None] + LIMB_S[None, None] * armdir[:, :, None]
    P = len(x)
    loc = np.concatenate([np.broadcast_to(HEAD_T, (P, NH, 3)), np.broadcast_to(TORSO_T, (P, NT, 3)),
                          legs.reshape(P, -1, 3), arms.reshape(P, -1, 3), np.broadcast_to(PHONE_T, (P, 12, 3))], 1)
    loc = loc * m["scale"][:, None, None] + (bob[:, None, None] * [0, 1, 0])

    def turn(v):                                                # person space -> street space
        return np.stack([v[..., 0] * rx[:, None] + v[..., 2] * fx[:, None], v[..., 1],
                         v[..., 0] * rd[:, None] + v[..., 2] * fd[:, None]], -1)

    st = turn(loc) + np.stack([x, np.zeros(P), d], 1)[:, None]
    cam = street_cam(st[..., 0], st[..., 1], st[..., 2])

    shade = np.clip(turn(np.broadcast_to(BODY_N, (P, NH + NT, 3))) @ STREETLIGHT, 0, 1)
    lum_body = 0.45 + 0.5 * shade
    limbs = turn(np.concatenate([legdir, armdir], 1))          # legs and arms as strokes
    stroke = np.repeat(slope_char(limbs[..., 0], limbs[..., 1]), NL, axis=1)
    glyph = np.concatenate([np.full((P, NH + NT), -1), stroke, np.full((P, 12), C("#"))], 1)
    lum = np.concatenate([lum_body, np.full((P, 4 * NL), 0.7), np.full((P, 12), 1.4)], 1)
    coat = m["coat"][:, None] * 0.8                             # a little below the tower: it is the star
    rgb = np.concatenate([np.broadcast_to(SKIN * 0.8, (P, NH, 3)), np.broadcast_to(coat, (P, NT, 3)),
                          np.broadcast_to(LEGS, (P, 2 * NL, 3)), np.broadcast_to(coat * 0.9, (P, 2 * NL, 3)),
                          np.broadcast_to(PHONE, (P, 12, 3))], 1)
    part = np.broadcast_to(100 + np.arange(P)[:, None], glyph.shape)
    keep = np.ones(glyph.shape, bool)
    keep[:, -12:] = photo[:, None]                              # only the photographers hold a glowing phone
    return cam[keep], lum[keep], rgb[keep], part[keep], glyph[keep]


# from points to letters

def outline_letter(gx, gy):
    ax, ay = np.abs(gx), np.abs(gy)
    c = np.where(ax > 2 * ay, C("|"), np.where(ay > 2 * ax, np.where(gy > 0, C("_"), C("-")),
                 np.where(gx * gy > 0, C("/"), C("\\"))))
    return np.where(ax + ay == 0, C("+"), c)


def bodies(cam, lum, rgb, part, glyph, cols, rows, aspect, t):
    # nearest point per cell; outlines where a body meets empty space or something further back,
    # iron and limbs keep their own strokes, the rest is filled with letters by brightness
    sx, sy, z = project_cam(cam, cols, rows, aspect)
    ok = np.flatnonzero((sx >= 0) & (sx < cols) & (sy >= 0) & (sy < rows) & (z > 1e-3))
    order = ok[np.argsort(-z[ok])]
    gi = np.full((rows, cols), -1)
    gi[sy[order].astype(int), sx[order].astype(int)] = order
    body = gi >= 0
    g = np.maximum(gi, 0)
    prt = np.where(body, part[g], -1)
    dep = np.where(body, z[g], np.inf)
    pp, pd = np.pad(prt, 1, constant_values=-1), np.pad(dep, 1, constant_values=np.inf)
    edge = np.zeros_like(body)
    gx, gy = np.zeros((rows, cols)), np.zeros((rows, cols))
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dx == dy == 0:
                continue
            nb, nz = pp[1 + dy:rows + 1 + dy, 1 + dx:cols + 1 + dx], pd[1 + dy:rows + 1 + dy, 1 + dx:cols + 1 + dx]
            out = body & ((nb < 0) | ((nb != prt) & (nz > dep * 1.012 + 0.004)))
            gx += dx * out
            gy += dy * out
            if dx == 0 or dy == 0:
                edge |= out
    h = HASH(rows, cols)
    L = np.where(body, lum[g], 0.0)
    level = np.clip((L * 3.2).astype(int), 0, 3)
    inside = FILL[level, (h + (t * 4 + h % 11).astype(int)) % 12]
    own = np.where(body, glyph[g], -1)
    char = np.where(body, np.where(own >= 0, own, np.where(edge, outline_letter(gx, gy), inside)), 0)
    bright = np.where(edge | (own >= 0), np.maximum(0.85, L), np.clip(0.45 + 0.55 * L / 0.9, 0.45, 1.0))
    col = np.where(body[..., None], rgb[g] * np.minimum(bright, 1.5)[..., None], 0.0)
    return char, col, dep


_HASH = {}


def HASH(rows, cols):
    if (rows, cols) not in _HASH:
        r, c = np.mgrid[0:rows, 0:cols]
        _HASH[rows, cols] = (r * 7919 + c * 104729) % 9973
    return _HASH[rows, cols]


# (c) @dwcminh.ascii, see LICENSE.txt. Not for use with AI tools: no feeding this code to
# AI models, no training on it, no having an AI rework it.

# the street: houses, lamps and the park trees never move, so they are drawn once

def make_houses():
    rng = np.random.default_rng(17)
    sides = []
    for _ in range(2):
        start, out = -20.0, []
        while start < ROW_END:
            w = rng.uniform(14, 24)
            out.append((start, w, rng.uniform(17.5, 22.5), rng.random()))
            start += w
        sides.append(np.array(out))
    return sides


HOUSES = make_houses()
SHOP = 10_000_000                                               # window ids above this are shop fronts
_STREET = {}


def street_layer(cols, rows, aspect):
    if (cols, rows) in _STREET:
        return _STREET[cols, rows]
    rr, cc = np.mgrid[0:rows, 0:cols]
    u = ((cc + 0.5) / cols - 0.5) / (ZOOM * 0.5)               # across / ahead, for each cell's ray
    v = (HORIZON - (rr + 0.5) / rows) / (ZOOM * 0.5 * aspect)  # up / ahead
    char = np.zeros((rows, cols), int)
    col = np.zeros((rows, cols, 3))
    depth = np.full((rows, cols), np.inf)
    win = np.full((rows, cols), -1)
    hsh = HASH(rows, cols)

    # house fronts, drawn as line work: follow each cell's ray to the wall and see what it lands on.
    # A cell covers a slice of wall dy metres tall and da metres long; thin lines are drawn
    # wherever they pass through that slice, so they stay unbroken in the distance.
    d = STREET / np.maximum(np.abs(u), 1e-6)
    y = EYE_H + v * d
    dy = d / (ZOOM * 0.5 * aspect * rows)
    da = d * d / (STREET * ZOOM * 0.5 * cols)
    lo, hi = y - dy / 2, y + dy / 2
    across = lambda level: (lo <= level) & (level < hi)
    for si, side in enumerate((-1, 1)):
        hs = HOUSES[si]
        k = np.clip(np.searchsorted(hs[:, 0], d, side="right") - 1, 0, len(hs) - 1)
        a, top, tone = d - hs[k, 0], hs[k, 2], hs[k, 3]
        fa = lambda step: (a / step) % 1.0
        m = (np.sign(u) == side) & (d < ROW_END) & (hi >= 0) & (lo < top + ROOF)
        fy = ((y - 4.2) / 3.1) % 1.0
        band = np.floor((hi - 4.2) / 3.1) != np.floor((lo - 4.2) / 3.1)
        roof = y >= top
        ground = y < 4.2
        edge_w = np.clip(0.5 * da, 0.4, 1.5)
        label = np.select([
            across(top + ROOF),                                                     # 1 roof ridge
            (a < edge_w) | (ROW_END - d < edge_w),                                  # 2 party wall
            across(top),                                                            # 3 cornice
            roof & (np.abs(fa(3.6) - 0.5) < 0.16) & (y - top > 1.0) & (y - top < 2.8),   # 4 dormer
            band & (np.floor((hi - 4.2) / 3.1) == 1),                               # 5 balcony
            np.zeros_like(band),                                                    # 6 (unused)
            ground & (np.abs(fa(6.5) - 0.5) < 0.40) & across(3.4),                  # 7 awning
            ground & (np.abs(fa(6.5) - 0.5) < 0.34) & (y > 0.3) & (y < 3.0),        # 8 shop window
            ~ground & ~roof & (np.abs(fa(3.6) - 0.5) < 0.2) & (fy > 0.2) & (fy < 0.85),  # 9 window
        ], np.arange(1, 10), 0)
        persp = slope_char(side * STREET, y - EYE_H)            # lines along the street head for the tower
        fade = np.clip(1.15 - d / 260, 0.5, 1)[..., None]
        awn = np.array([(1.0, 0.25, 0.25), (0.25, 0.75, 0.45), (0.35, 0.45, 1.0)])[(tone * 3).astype(int) % 3]
        looks = {1: (persp, ZINC * 0.62), 2: (np.full_like(hsh, C("|")), STONE * 0.55),
                 3: (persp, STONE * 0.7), 5: (persp, IRON * 0.55), 6: (persp, STONE * 0.55),
                 7: (persp, awn * 0.85)}
        for lab, (g, c) in looks.items():
            sel = m & (label == lab)
            char[sel] = g[sel]
            col[sel] = (np.broadcast_to(c, col.shape) * fade)[sel]
        wid = ((si * 100 + k) * 100 + np.floor((y - 4.2) / 3.1).astype(int) + 10) * 100 + (a / 3.6).astype(int)
        wid = np.where(label == 8, SHOP + (si * 100 + k) * 100 + (a / 6.5).astype(int), wid)
        sel = m & np.isin(label, (4, 8, 9))
        win[sel] = wid[sel]
        depth[m] = d[m] * S                                     # blank wall still hides what is behind

    # the street is dark and wet; a few lines run off towards the tower
    g = (v < 0) & (depth == np.inf)
    dg = EYE_H / np.maximum(-v, 1e-6)
    x = u * dg
    dx = dg / (ZOOM * 0.5 * cols)
    for x0 in (-11.0, -3.5, 3.5, 11.0):
        sel = g & (np.abs(x - x0) < 0.5 * dx) & (dg < ROW_END)
        char[sel] = slope_char(np.full(sel.sum(), x0), np.full(sel.sum(), -EYE_H))
        col[sel] = STONE * 0.4 * np.clip(1.2 - dg[sel, None] / ROW_END, 0.3, 1)
    pool = np.zeros((rows, cols))
    for lx in (-LAMP_X, LAMP_X):
        for ld in LAMP_D:
            pool += np.exp(-((x - lx) ** 2 + (dg - ld) ** 2) / (2 * 3.0 ** 2))
    sel = g & (char == 0) & (pool > 0.25)
    char[sel] = FILL[0, hsh % 12][sel]
    col[sel] = LAMP[None] * (0.25 + 0.4 * np.clip(pool[sel, None], 0, 1))

    # trees in the park round the foot of the tower, and the street lamps: solid little bodies
    rng = np.random.default_rng(23)
    ball = fib_sphere(160)
    pts, lum, rgb, part, glyph = [], [], [], [], []
    n = 0
    for side in (-1, 1):
        for row_x in (30.0, 42.0):
            for td in np.arange(ROW_END + 30, CAM_DIST - 70, 10.0):
                r = rng.uniform(3.8, 5.2)
                c0 = np.array([side * (row_x + rng.normal(0, 1.5)), rng.uniform(6, 7.5), td + rng.normal(0, 2)])
                pts.append(c0 + ball * r * rng.uniform(0.85, 1.0, (len(ball), 1)))
                lum.append(0.35 + 0.45 * np.clip(ball[:, 1] * 0.6 + 0.4, 0, 1))
                rgb.append(np.tile([0.18, 0.55, 0.36], (len(ball), 1)))
                part.append(np.full(len(ball), n))
                glyph.append(np.full(len(ball), -1))
                n += 1
    for lx in (-LAMP_X, LAMP_X):
        for ld in LAMP_D:
            yy = np.linspace(0, 4.4, 60)
            pts.append(np.stack([np.full(60, lx), yy, np.full(60, ld)], 1))
            lum.append(np.full(60, 0.6))
            rgb.append(np.tile(IRON * 0.7, (60, 1)))
            part.append(np.full(60, n))
            glyph.append(np.full(60, C("|")))
            pts.append(np.array([[lx, 4.7, ld]]))
            lum.append(np.array([1.4]))
            rgb.append(LAMP[None])
            part.append(np.array([n]))
            glyph.append(np.array([C("@")]))
            n += 1
    pts = np.concatenate(pts)
    bc, bcol, bdep = bodies(street_cam(pts[:, 0], pts[:, 1], pts[:, 2]), np.concatenate(lum),
                            np.concatenate(rgb), np.concatenate(part), np.concatenate(glyph), cols, rows, aspect, 0.0)
    near = bdep < depth
    char[near], col[near], depth[near] = bc[near], bcol[near], bdep[near]

    wet = g & (char == 0)                                       # where the tower can shine in the street
    _STREET[cols, rows] = char, col, depth, win, wet, u, v
    return _STREET[cols, rows]


def window_lit(ids, t):
    # about half the windows are lit; a few switch on or off as the evening goes on
    h1, h2, h3 = (ids * 0.7548776662) % 1, (ids * 0.5698402910) % 1, (ids * 0.4142135624) % 1
    shop = ids >= SHOP
    on = np.where(shop, h1 < 0.8, h1 < 0.45)
    flip = ~shop & (h2 < 0.25) & (t > 1.0 + 19 * h3)
    return on ^ flip, h2


def reflection(char, col, wet, u, v, t, rows, cols):
    # the tower upside down in the wet street, stretched and broken up by ripples
    r = np.arange(rows)[:, None]
    hm = -v * CAM_DIST * 2.2                                    # which height of the tower each cell mirrors
    xr = np.abs(u * CAM_DIST + 5 * np.sin(t * 1.7 + r * 1.9) + 2 * np.sin(t * 3.1 + r * 0.7))
    w, s = half_width(hm), leg_size(hm)
    shape = np.where(hm < H_MERGE, (xr <= w) & (xr >= w - 2 * s), (xr <= w) & (hm < 300))
    shape |= ((hm > 54) & (hm < 66) & (xr <= half_width(57) + 3)) | ((hm > 113) & (hm < 123) & (xr <= 21))
    shape &= wet & (hm < build_time(TOWER_M) * 0 + 400) & (hm < TOWER_M * np.clip((t - T_BUILD[0]) / 6.4, 0, 1))
    h = HASH(rows, cols)
    broken = (h + int(t * 9)) % 4 != 0
    m = shape & broken
    lit, _ = lit_level(hm, t)
    tint = STEEL + (GOLD - STEEL) * lit[..., None]
    k = (0.12 + 0.22 * (h % 5) / 4) * np.exp(-(-v) * 10)       # fades towards the camera
    char[m] = FILL[0, (h + int(t * 6)) % 12][m]
    col[m] = (tint * (k * (0.5 + 0.8 * lit))[..., None])[m]


# things in the sky

def put(char, col, y, x, ch, rgb, k):
    if 0 <= y < char.shape[0] and 0 <= x < char.shape[1]:
        char[y, x], col[y, x] = C(ch), np.asarray(rgb) * k


def rays(char, col, cy, cx, reach, rgb, strength=1.0):
    # a four-pointed flare: long arms sideways and up/down, short diagonals
    rows, cols = char.shape
    for dist in range(1, reach + 1):
        fade = (1 - dist / (reach + 1)) * strength
        arms = [(0, 1, "-"), (0, -1, "-"), (1, 0, "|"), (-1, 0, "|")]
        if dist <= reach // 2:
            arms += [(1, 1, "\\"), (-1, -1, "\\"), (1, -1, "/"), (-1, 1, "/")]
        for dy, dx, ch in arms:
            yy, xx = cy + dy * dist, cx + dx * dist * (2 if dy == 0 else 1)
            k = fade * (0.7 if dx and dy else 1.0)
            if 0 <= yy < rows and 0 <= xx < cols and col[yy, xx].max() < k:
                char[yy, xx], col[yy, xx] = C(ch), rgb * k
    put(char, col, cy, cx, "*", rgb, 1.3 * strength)


def beacon(char, col, sky, steady, t, cols, rows, aspect, cell):
    # the searchlight on the summit: two beams sweeping round over the city
    # (marked steady: a sweeping beam must not smear into a fan of trails)
    on = float(smooth((t - T_BEACON) / 0.8))
    top = np.array([0, GROUND + 291 * S, 0])
    tx, ty, _ = project(top[None], cols, rows, aspect)
    to_eye = unit(EYE - top)
    s = np.linspace(6.0, 0.12, 420)                             # far to near, so the bright end wins
    flare = 0.0
    for j in range(2):
        ang = t * 0.9 + j * np.pi
        for off, k in ((0.0, 1.0),):                            # one clean stroke per beam
            d = unit([np.cos(ang + off), 0.035, np.sin(ang + off)])
            sx, sy, z = project(top + d * s[:, None], cols, rows, aspect)
            ch = slope_char((sx[0] - sx[-1]) * cell, -(sy[0] - sy[-1]))
            if np.hypot((sx[0] - sx[-1]) * cell, sy[0] - sy[-1]) < 2:
                ch = C(".")
            b = on * k * 0.85 * np.exp(-s / 2.4) * smooth((z - 1.2) / 1.5)   # fades out near the camera
            ok = (sx >= 0) & (sx < cols) & (sy >= 0) & (sy < rows) & (z > 0.3) & (b > 0.05)
            ix, iy, b = sx[ok].astype(int), sy[ok].astype(int), b[ok]
            free = sky[iy, ix]
            ix, iy, b = ix[free], iy[free], b[free]
            char[iy, ix] = np.where(b < 0.18, C("."), ch)
            col[iy, ix] = BEAM * b[:, None]
            steady[iy, ix] = True
        flare = max(flare, float(np.clip(d @ to_eye, 0, 1)) ** 10)
    flare *= on
    if flare > 0.1:                                             # a beam swinging past the camera
        rays(char, col, int(ty[0]), int(tx[0]), int(3 + 6 * flare), BEAM, flare)


FW_EVERY, FW_RISE, FW_LIFE = 0.55, 0.75, 1.9


def fireworks(t):
    # rockets climb from behind the houses and burst into falling, fading sparks
    pts, glyph, rgb, flashes = [], [], [], []
    if t < T_FIREWORKS:
        return None, None, None, flashes
    last = int((t - T_FIREWORKS) / FW_EVERY)
    for b in range(max(0, last - 6), last + 1):
        rng = np.random.default_rng(1000 + b)
        t0 = T_FIREWORKS + b * FW_EVERY + rng.uniform(0, 0.3)
        if t < t0:
            continue
        burst = np.array([rng.choice([-1, 1]) * rng.uniform(0.35, 1.7), rng.uniform(-0.1, 1.3), rng.uniform(-1.0, 0.5)])
        launch = burst * [1, 0, 1] + [rng.normal(0, 0.06), GROUND, 0]
        palette = FIREWORK[rng.choice(len(FIREWORK), 2, replace=False)]
        if t < t0 + FW_RISE:                                    # the rocket and its trail
            for k in range(6):
                u = np.clip((t - k * 0.04 - t0) / FW_RISE, 0, 1)
                pts.append(launch + (burst - launch) * (1 - (1 - u) ** 2))
                glyph.append(C("|") if k == 0 else C("."))
                rgb.append(LAMP * (1.2 - 0.18 * k))
            continue
        age = t - t0 - FW_RISE
        if age > FW_LIFE:
            continue
        n = int(rng.integers(36, 56))
        dirs = unit(fib_sphere(n) + rng.normal(0, 0.10, (n, 3)))
        speed = rng.uniform(0.5, 0.7) * rng.uniform(0.9, 1.05, (n, 1, 1))
        drag = 1.8
        # each spark is a head with a short tail behind it along its path: a chrysanthemum
        ages = np.maximum(age - np.array([0.0, 0.05, 0.10, 0.15, 0.20]), 0)[None, :, None]
        p = burst + dirs[:, None] * speed * (1 - np.exp(-drag * ages)) / drag - [0, 1, 0] * (0.12 * ages ** 2)
        vel = dirs * speed[:, 0] * np.exp(-drag * age) - [0, 0.24 * age, 0]
        fade = (1 - age / FW_LIFE) ** 1.4
        tw = np.where(age > 0.9, 0.5 + 0.5 * np.sin(age * 40 + np.arange(n) * 2.3), 1.0)
        k = 1.5 * fade * tw[:, None] * np.array([1.0, 0.75, 0.55, 0.38, 0.24])[None]
        c = np.where((np.arange(n) % 3 == 0)[:, None], palette[1], palette[0])
        c = c + (1 - c) * np.clip(1 - age / 0.25, 0, 1)         # white hot when it bursts
        vc = vel @ BASIS.T
        streak = slope_char(vc[:, 0], vc[:, 1])
        head = np.where(k[:, 0] > 0.8, C("*"), np.where(k[:, 0] > 0.35, C("+"), C(".")))
        g = np.concatenate([head[:, None], np.repeat(streak[:, None], 4, 1)], 1)
        g[:, 1:] = np.where(age > 1.1, C("."), g[:, 1:])         # late tails crumble to dust
        pts.extend(p[:, ::-1].reshape(-1, 3))                   # tails first, so heads win the cell
        glyph.extend(g[:, ::-1].ravel())
        rgb.extend((c[:, None] * k[..., None])[:, ::-1].reshape(-1, 3))
        if age < 0.18:
            flashes.append((burst, 1 - age / 0.18, palette[0]))
    if not pts:
        return None, None, None, flashes
    return np.array(pts), np.array(glyph), np.array(rgb), flashes


def frame(t, cols, rows, aspect, cell):
    s_char, s_col, s_depth, win, wet, u, v = street_layer(cols, rows, aspect)

    # what moves: the tower and the people, drawn as solid letter bodies
    parts = [tower(t), crowd(t)]
    cam, lum, rgb, part, glyph = [np.concatenate(a) for a in zip(*parts)]
    d_char, d_col, d_depth = bodies(cam, lum, rgb, part, glyph, cols, rows, aspect, t)

    char, col = s_char.copy(), s_col.copy()
    w = win >= 0
    lit, h2 = window_lit(win[w], t)
    h = HASH(rows, cols)[w]
    shop = win[w] >= SHOP                                       # windows read as windows: # and =
    char[w] = np.where(lit, np.where(shop, FILL[2, h % 12], np.where(h2 < 0.7, C("#"), C("="))), 0)
    col[w] = np.where(lit[:, None], np.where((h2 < 0.85)[:, None], WARM, COOL) * 0.85, 0)
    reflection(char, col, wet, u, v, t, rows, cols)
    front = d_depth < s_depth
    char = np.where(front, d_char, char)
    col = np.where(front[..., None], d_col, col)
    depth = np.minimum(d_depth, s_depth)
    col *= smooth(t / 0.8)

    # the sky: stars, the beacon, fireworks
    horizon = int(HORIZON * rows)
    sky = (char == 0) & (np.arange(rows)[:, None] < horizon)
    sk_x, sk_y = (SKY[:, 0] * cols).astype(int), (SKY[:, 1] * max(horizon - 1, 1)).astype(int)
    tw = 0.12 + 0.6 * np.clip(np.sin(t * (1 + 2 * SKY[:, 2]) + SKY[:, 2] * 50), 0, 1) ** 4
    free = sky[sk_y, sk_x]
    sk_x, sk_y, tw = sk_x[free], sk_y[free], tw[free]
    char[sk_y, sk_x] = np.where(tw < 0.35, C("."), np.where(tw < 0.6, C("+"), C("*")))
    col[sk_y, sk_x] = WHITE * tw[:, None]

    steady = np.zeros((rows, cols), bool)
    if t > T_BEACON:
        beacon(char, col, sky, steady, t, cols, rows, aspect, cell)

    fp, fg, fc, flashes = fireworks(t)
    if fp is not None:
        sx, sy, z = project(fp, cols, rows, aspect)
        ok = (sx >= 0) & (sx < cols) & (sy >= 0) & (sy < rows) & (z > 0.3)
        ix, iy = sx[ok].astype(int), sy[ok].astype(int)
        seen = z[ok] < depth[iy, ix]
        ix, iy = ix[seen], iy[seen]
        char[iy, ix], col[iy, ix] = fg[ok][seen], fc[ok][seen]
        for burst, k, c in flashes:
            bx, by, bz = project(burst[None], cols, rows, aspect)
            if bz[0] < depth[min(max(int(by[0]), 0), rows - 1), min(max(int(bx[0]), 0), cols - 1)]:
                rays(char, col, int(by[0]), int(bx[0]), int(2 + 5 * k), c, k)

    # the sparkle: white bulbs flashing over the gold, the brightest with a flare
    on = np.zeros(len(TW), bool)
    if t > T_SPARKLE:
        rate = 0.075 * smooth((t - T_SPARKLE) / 1.5)
        ph = (t * TW_RATE + TW_PHASE) % 1.0
        on = ph < rate
        sx, sy, z = project_cam(CAM_T[TW[on]], cols, rows, aspect)
        ix, iy = sx.astype(int), sy.astype(int)
        ok = (ix >= 0) & (ix < cols) & (iy >= 0) & (iy < rows)
        ix, iy, z, fresh = ix[ok], iy[ok], z[ok], ph[on][ok] / max(rate, 1e-6)
        seen = z <= depth[iy, ix] + 0.06
        ix, iy, fresh = ix[seen], iy[seen], fresh[seen]
        char[iy, ix] = np.where(fresh < 0.5, C("*"), C("+"))
        col[iy, ix] = WHITE * 1.3
        for j in np.argsort(fresh)[:3]:
            rays(char, col, int(iy[j]), int(ix[j]), 4, WHITE, 0.9)

    if t > T_GLOW[1]:
        # red aviation light on the antenna
        ax, ay, _ = project(np.array([[0, GROUND + TOWER_M * S + 0.02, 0]]), cols, rows, aspect)
        blink = np.sin(t * 3.5) > 0.2
        put(char, col, int(ay[0]), int(ax[0]), "@" if blink else "o", RED, 1.3 if blink else 0.35)

    info = {"sparkles": int(on.sum()), "fireworks": 0 if fp is None else int(len(fp)),
            "letters": int((char > 0).sum())}
    return char, col, steady, info


SKY = np.random.default_rng(5).random((220, 3))


# (c) @dwcminh.ascii, see LICENSE.txt. Not for use with AI tools: no feeding this code to
# AI models, no training on it, no having an AI rework it.

# window

TITLE = "ASCII Eiffel Tower"
CW, CH, FONT_PX = 9, 14, 15
COLS, ROWS = 88, 74
W, H = COLS * CW, ROWS * CH
MONO = "consolas,menlo,dejavusansmono,couriernew,monospace"
HINT = "Space pause · R restart · S screenshot · Esc quit"
DIM, ACCENT, SIGN = (110, 104, 120), (255, 196, 90), (176, 168, 196)
TRAIL = 0.45                                    # how much of the last frame stays behind (motion trails)


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
        self.trail = pygame.Surface((self.w, self.h))
        self.out = pygame.Surface((self.w, self.h))
        self.small = pygame.font.SysFont(MONO, hud_px)
        self.hud_gap = int(hud_px * 1.45)
        self.hint = hint
        self.last_t = None

    @staticmethod
    def blur(src, size, radius):
        small = pygame.transform.smoothscale(src, size)
        if hasattr(pygame.transform, "gaussian_blur"):
            small = pygame.transform.gaussian_blur(small, max(1, radius))
        return small

    def glow(self, src):
        # a tight glow and a wide one; the wide one is made from the tight one
        w, h = self.w, self.h
        tight = self.blur(src, (w // 4, h // 4), 2)
        wide = self.blur(tight, (w // 8, h // 8), 3)
        for layer, amount in ((tight, 0.75), (wide, 0.45)):
            layer = pygame.transform.smoothscale(layer, (w, h))
            layer.fill((int(255 * amount),) * 3, special_flags=pygame.BLEND_MULT)
            self.out.blit(layer, (0, 0), special_flags=pygame.BLEND_ADD)

    def tinted(self, glyphs, col):
        out = glyphs.copy()
        tint = pygame.surfarray.make_surface((np.clip(col, 0, 1) * 255).astype(np.uint8).transpose(1, 0, 2))
        out.blit(pygame.transform.scale(tint, (self.w, self.h)), (0, 0), special_flags=pygame.BLEND_MULT)
        return out

    def draw(self, t):
        w, h = self.w, self.h
        char, col, steady, info = frame(t, self.cols, self.rows, w / h, self.cw / self.ch)
        pygame.surfarray.blit_array(self.art, self.atlas[char].transpose(1, 3, 0, 2, 4).reshape(w, h, 3))
        if self.last_t is None or t < self.last_t:
            self.trail.fill((0, 0, 0))                          # restarted: no trails from before
        self.last_t = t
        # everything leaves a short fading trail, except what is marked steady (the beacon)
        self.trail.fill((int(TRAIL * 255),) * 3, special_flags=pygame.BLEND_MULT)
        self.trail.blit(self.tinted(self.art, col * ~steady[..., None]), (0, 0), special_flags=pygame.BLEND_MAX)
        self.out.fill((0, 0, 0))
        self.out.blit(self.trail, (0, 0))
        if steady.any():
            self.out.blit(self.tinted(self.art, col * steady[..., None]), (0, 0), special_flags=pygame.BLEND_MAX)
        self.glow(self.out)
        lines = [f"sparkles {info['sparkles']:>4}      fireworks {info['fireworks']:>4}",
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
                pygame.image.save(screen, str(Path(__file__).with_name(f"eiffel_{int(time.time())}.png")))
        dt = clock.tick(30) / 1000
        if not paused:
            t += min(dt, 1 / 15)
            screen = renderer.draw(t)
        window.blit(screen if size == (W, H) else pygame.transform.smoothscale(screen, size), (0, 0))
        pygame.display.flip()


if __name__ == "__main__":
    sys.exit(main())
