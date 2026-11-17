# ASCII Duo (fan art of the Duolingo owl, the one with the big behind)
# @dwcminh.ascii, 2026
#
#   pip install numpy pygame-ce
#   python duo_owl.py
#
# The owl sits on the floor, feet out in front, the famous behind out at the back. It rises from
# the floor up, held at a slant so you see its side and its sidelong look; once it is whole it
# winks (confetti!), and only then starts to turn. Hearts and the flags of many countries float
# up, each flag just once; a streak flame counts up to 365; a shake when its back comes round,
# another wink when it faces you. Its eyes follow you all the way.
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
FLOOR, TOP = -0.70, 0.98                        # floor and the tips of the ears
SPIN = 0.56                                     # turntable speed once it is turning (rad/s)
HOLD = np.radians(45)                           # the slant it is held at while it rises: side on, face to the right

# timeline (s)
T_BUILD = (-0.5, 6.0)                           # rising from the floor up, standing still
T_WINK = 6.5                                    # whole: the wink
T_HEARTS = 6.9                                  # hearts and flags start floating up
T_SPIN = 7.8                                    # ...and only now does it start to turn
T_BACK = T_SPIN + 0.5 + (np.pi - HOLD) / SPIN   # the back faces the camera (~12 s)
T_FRONT = T_BACK + np.pi / SPIN                 # the face looks straight at the camera (~17.6 s)
T_SHAKE = (T_BACK - 1.1, T_BACK + 1.2)          # a little shake as the back comes round
T_WINK2 = T_FRONT - 0.4                         # a second wink, face on
T_BLINK = 15.2                                  # an ordinary blink
T_STREAK = (9.6, 15.8)                          # the streak flame: appears, and leaves
T_COUNT = (10.0, 12.4)                          # its counter rolls up from 1 to STREAK_DAYS
STREAK_DAYS = 365
BADGE_ROW = 11                                  # the row the streak flame and number stand on
N_CONFETTI = 150                                # pieces in each burst (one at each wink)
FLASH = 0.6                                     # how long a new eye, beak or foot glows white (s)

BODY, CHEEK_L, CHEEK_R, WING_L, WING_R, FOOT_L, FOOT_R, BEAK, EYE = range(9)
POOLS = ["1il!;:", "rtfjcvxz=+", "aeoun0{}[]<>", "08B$#&%Q"]   # fill letters, dark -> bright
C = lambda ch: ord(ch) - 32                     # character -> glyph index
FILL = np.array([[C(p[k % len(p)]) for k in range(12)] for p in POOLS])
SLOPE = np.array([C(c) for c in "-/|\\-"])

GREEN = np.array([0.36, 0.86, 0.02])
LIGHT = np.array([0.62, 0.96, 0.16])            # face and belly
CREASE = np.array([0.85, 1.00, 0.55])           # creases, lids, brows: pale strokes that stand out
HARD = np.isin(np.arange(9), (1, 2, 3, 4))      # cheeks and wings always get an outline
LID_LOW = np.array([0.78, 1.00, 0.32])          # the lower lid, pushed up under the eye
WING = np.array([0.28, 0.76, 0.02])
ORANGE = np.array([1.00, 0.60, 0.05])
YELLOW = np.array([1.00, 0.80, 0.10])
WHITE = np.array([0.96, 0.97, 1.00])
IRIS = np.array([0.13, 0.14, 0.18])             # black eyes, a touch lighter in the middle
IRIS_RIM = np.array([0.05, 0.05, 0.07])
BROW = np.array([0.10, 0.50, 0.02])             # brows: darker than the face
MOUTH = np.array([0.50, 0.20, 0.02])            # the line of the mouth: dark on the orange beak
PINK = np.array([1.00, 0.36, 0.56])
RED = np.array([1.00, 0.20, 0.30])


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
    # screen direction (y up) -> the ASCII stroke that looks most like it
    ang = np.degrees(np.arctan2(dy, dx)) % 180
    return SLOPE[np.digitize(ang, [25, 72, 108, 155])]


def outline_letter(gx, gy):
    ax, ay = np.abs(gx), np.abs(gy)
    c = np.where(ax > 2 * ay, C("|"), np.where(ay > 2 * ax, np.where(gy > 0, C("_"), C("-")),
                 np.where(gx * gy > 0, C("/"), C("\\"))))
    return np.where(ax + ay == 0, C("+"), c)


def pulse(t, t0, down, hold, up):
    # 0 -> 1 -> 0: closes over `down`, stays for `hold`, opens over `up`
    return float(smooth((t - t0) / down) * (1 - smooth((t - t0 - down - hold) / up)))


# the owl's shape. It SITS: a rounded box of a body resting on the floor, facing +z, with its
# feet sticking out in front and the two big cheeks of its behind out at the back.

BODY_R = np.array([0.55, 0.72, 0.52])
BODY_C = np.array([0.0, FLOOR + BODY_R[1], 0.0])
BODY_P = 3.4                                    # how boxy the body is (2 = an egg)
EAR_H = 0.26                                    # how far the top corners are pulled up into ears
EAR_P = 1.2                                     # how the top dips between them (1 = a straight V, 2 = a U)
EAR_Y0 = BODY_C[1] + 0.40                       # the pull starts above here (well above the eyes)
CHEEK_R3 = np.array([0.37, 0.33, 0.36])
CHEEK_C = np.array([0.25, FLOOR + CHEEK_R3[1], -0.38])
EYE_X, EYE_Y, EYE_R = 0.31, FLOOR + 1.00, 0.21
# the look: half-moon eyes under heavy lids that droop towards the beak, one eye lazier than the other
UPPER = (0.052, 0.070)                          # upper lid above each eye's centre: [eye at x < 0, eye at x > 0]
LOWER = (-0.160, -0.300)                        # lower lid (the lazy eye has one pushed up; -0.3 = none)
SLANT = 0.050                                   # how much the upper lids droop towards the beak
IRIS_R, GAZE = 0.105, 0.135                     # iris size, and how far it slides towards the viewer
SMIRK = 1                                       # which corner of the mouth is higher: 1 = at x > 0, -1 = at x < 0, 0 = even
WINK_EYE = 0                                    # which eye winks: 0 = the one at x < 0 (the near one while it is held), 1 = at x > 0


def front(x, y):
    # z of the body's front surface above (x, y)
    s = 1 - np.abs(x / BODY_R[0]) ** BODY_P - np.abs((y - BODY_C[1]) / BODY_R[1]) ** BODY_P
    return BODY_R[2] * np.clip(s, 0, 1) ** (1 / BODY_P)


def side(y, z):
    # x of the body's side surface at (y, z)
    s = 1 - np.abs((y - BODY_C[1]) / BODY_R[1]) ** BODY_P - np.abs(z / BODY_R[2]) ** BODY_P
    return BODY_R[0] * np.clip(s, 0, 1) ** (1 / BODY_P)


def body_normal(p):
    q = p - BODY_C
    return unit(np.sign(q) * np.abs(q) ** (BODY_P - 1) / BODY_R ** BODY_P)


def ear_lift(p):
    # how far a point of the body is pulled up: nothing low down or in the middle, the most at the
    # top outer corners, halfway back, so each ear rises to a point; returns the lift and its
    # slopes across (d/dx), up (d/dy) and back (d/dz)
    x, y, z = p[:, 0], p[:, 1], p[:, 2]
    top = BODY_C[1] + BODY_R[1]
    u = np.clip((y - EAR_Y0) / (top - EAR_Y0), 0, 1)
    wy, dwy = u * u * (3 - 2 * u), 6 * u * (1 - u) / (top - EAR_Y0)
    ax = np.abs(x) / BODY_R[0]
    wx, dwx = ax ** EAR_P, EAR_P * np.sign(x) * ax ** (EAR_P - 1) / BODY_R[0]
    rz = 1.15 * BODY_R[2]
    wz, dwz = np.clip(1 - (z / rz) ** 2, 0, 1), np.where(np.abs(z) < rz, -2 * z / rz ** 2, 0)
    return EAR_H * wx * wy * wz, EAR_H * dwx * wy * wz, EAR_H * wx * dwy * wz, EAR_H * wx * wy * dwz


def body_shell(n):
    d = fib_sphere(n)
    r = ((np.abs(d) / BODY_R) ** BODY_P).sum(1) ** (-1 / BODY_P)
    p = d * r[:, None] + BODY_C
    return p, body_normal(p)


def ellipsoid(n, centre, radii):
    d = fib_sphere(n)
    return d * radii + centre, unit(d / np.asarray(radii))


def on_face(side_sign, ex, ey, lift=0.0):
    # a point of an eye (ex, ey from its centre) -> where that is on the body's front
    x, y = side_sign * EYE_X + ex, EYE_Y + ey
    return np.stack([x, y, front(x, y) + lift], -1)


BEAK_R = np.array([0.13, 0.10, 0.16])
BEAK_C = np.array([0.0, EYE_Y - 0.15, float(front(0, EYE_Y - 0.15)) + 0.05])


def mouth(x):
    # the line of the mouth across the beak: a little smile, one corner higher than the other (a smirk)
    u = np.asarray(x, float) / BEAK_R[0]
    return BEAK_C[1] - 0.035 + 0.055 * u ** 2 + 0.022 * SMIRK * u


def build_time(y):
    u = np.clip((np.asarray(y, float) - FLOOR) / (TOP - FLOOR), 0, 1)
    return T_BUILD[0] + (T_BUILD[1] - T_BUILD[0]) * u ** 0.85


def build():
    rng = np.random.default_rng(7)
    parts = []

    def add(p, n, rgb, part, group=0, pop=False, eye=None):
        m = len(p)
        ex, ey, sgn = eye if eye is not None else (np.zeros(m), np.zeros(m), np.zeros(m))
        parts.append((p, n, np.broadcast_to(rgb, (m, 3)).copy(), np.full(m, part), np.full(m, group),
                      np.full(m, pop), ex, ey, sgn))

    # feet: two orange ovals on the floor, sticking out in front of the body
    for s, part in ((-1, FOOT_L), (1, FOOT_R)):
        p, n = ellipsoid(1500, (s * 0.25, FLOOR + 0.085, 0.62), (0.15, 0.085, 0.24))
        add(p, n, ORANGE, part, pop=True)

    # the behind: two big round cheeks on the floor behind the body, wider than the body itself,
    # each with a lighter patch where the light catches it
    for s, part in ((-1, CHEEK_L), (1, CHEEK_R)):
        d = fib_sphere(8000)
        shine = d @ unit([0.25 * s, 0.72, -0.62]) > 0.86
        add(d * CHEEK_R3 + CHEEK_C * [s, 1, 1], unit(d / CHEEK_R3), np.where(shine[:, None], LIGHT, GREEN),
            part, group=1 if s < 0 else 2)

    # body: a rounded box, with the lighter face wrapping round its front and a light belly;
    # its top corners are pulled up into the two pointed ears, and the top dips between them
    p, n = body_shell(19000)
    x, y, z = p.T
    lift, fx, fy, fz = ear_lift(p)
    n = unit(np.stack([n[:, 0] - fx / (1 + fy) * n[:, 1], n[:, 1] / (1 + fy), n[:, 2] - fz / (1 + fy) * n[:, 1]], 1))
    p = p + np.stack([0 * lift, lift, 0 * lift], 1)
    face = (z > 0.16) & ((x / 0.90) ** 4 + ((y - EYE_Y - 0.01) / 0.36) ** 4 < 1)
    belly = (z > 0) & ((x / 0.30) ** 2 + ((y - FLOOR - 0.30) / 0.22) ** 2 < 1)
    add(p, n, np.where((face | belly)[:, None], LIGHT, GREEN), BODY)

    # wings: a low bulge hanging on each side
    for s, part in ((-1, WING_L), (1, WING_R)):
        p, n = ellipsoid(1800, (s * 0.56, FLOOR + 0.62, 0.10), (0.07, 0.30, 0.24))
        add(p, n, WING, part)

    # beak, under the eyes
    p, n = ellipsoid(1300, BEAK_C, BEAK_R)
    add(p, n, np.where((p[:, 1] > mouth(p[:, 0]))[:, None], YELLOW, ORANGE), BEAK, pop=True)

    # eyes: discs on the face; what is lid, white or pupil is decided every frame
    for s in (-1, 1):
        m = 2600
        r, th = EYE_R * np.sqrt(rng.random(m)), rng.random(m) * TAU
        ex, ey = r * np.cos(th), r * np.sin(th)
        p = on_face(s, ex, ey, 0.012 + 0.03 * (1 - (r / EYE_R) ** 2))
        add(p, body_normal(p), WHITE, EYE, pop=True, eye=(ex, ey, np.full(m, s)))

    # two little feather tufts above each eye, at the top of the face
    for s in (-1, 1):
        for tx, ty, th in ((0.25, 0.385, 0.10), (0.35, 0.375, 0.13), (0.45, 0.33, 0.10)):
            p, n = ellipsoid(350, (s * tx, EYE_Y + ty, float(front(s * tx, EYE_Y + ty)) + 0.01), (0.045, th, 0.05))
            add(p, n, LIGHT, BODY)

    return [np.concatenate(c) for c in zip(*parts)]


POS, N0, RGB, PART, GROUP, POP, EX, EY, ESIDE = build()
APPEAR = build_time(POS[:, 1]) + 0.05 * np.random.default_rng(2).random(len(POS))
IS_EYE = PART == EYE
IS_CHEEK = (PART == CHEEK_L) | (PART == CHEEK_R)


def polyline(pts, step=0.012):
    pts = np.asarray(pts, float)
    d = np.linalg.norm(np.diff(pts, axis=0), axis=1)
    s = np.concatenate([[0], np.cumsum(d)])
    u = np.linspace(0, s[-1], max(2, int(s[-1] / step)))
    return np.stack([np.interp(u, s, pts[:, i]) for i in range(3)], 1)


def creases():
    # lines drawn on the owl that never change: the cleft, the wing outlines, the little tail tick
    out = []
    ph = np.linspace(0.10 * np.pi, 0.97 * np.pi, 80)
    k = np.sqrt(1 - (CHEEK_C[0] / CHEEK_R3[0]) ** 2) * 1.02
    out.append((np.stack([0 * ph, CHEEK_C[1] + CHEEK_R3[1] * k * np.cos(ph),
                          CHEEK_C[2] - CHEEK_R3[2] * k * np.sin(ph)], 1), CHEEK_L, CREASE))
    th = np.linspace(0.30 * np.pi, 1.70 * np.pi, 90)
    y, z = FLOOR + 0.62 + 0.31 * np.cos(th), 0.10 + 0.25 * np.sin(th)
    for s, part in ((-1, WING_L), (1, WING_R)):
        out.append((np.stack([s * (side(y, z) + 0.02), y, z], 1), part, CREASE))
    tick = np.array([(-0.10, 1.00), (-0.03, 0.90), (0.12, 1.03)]) + [0, FLOOR]
    out.append((polyline(np.stack([tick[:, 0], tick[:, 1], -front(tick[:, 0], tick[:, 1]) - 0.015], 1)), BODY, CREASE))
    # the smile: along the mouth line over the beak, then on up the face a little past each corner
    x = np.linspace(-1.25, 1.25 + 0.2 * abs(SMIRK), 70) * BEAK_R[0] * (1 if SMIRK >= 0 else -1)
    y = mouth(x)
    inside = 1 - (x / BEAK_R[0]) ** 2 - ((y - BEAK_C[1]) / BEAK_R[1]) ** 2
    z = np.where(inside > 0, BEAK_C[2] + BEAK_R[2] * np.sqrt(np.clip(inside, 0, 1)), front(x, y)) + 0.03
    out.append((np.stack([x, y, z], 1), BEAK, MOUTH))
    return out


CREASES = creases()

# camera
EYE_POS, TARGET = np.array([0.0, 0.42, 4.8]), np.array([0.0, 0.06, -0.05])
FWD = unit(TARGET - EYE_POS)
RIGHT = unit(np.cross(FWD, [0, 1.0, 0]))
UP = np.cross(RIGHT, FWD)
BASIS = np.stack([RIGHT, UP, FWD])                      # world -> camera axes
EYE_CAM = BASIS @ EYE_POS
ZOOM = 4.3
VIEW = unit(EYE_POS - TARGET)
KEY = unit([-0.5, 0.65, 0.6])
HALF = unit(KEY + VIEW)


def project_cam(cam, cols, rows, aspect):
    z = cam[..., 2]
    zz = np.maximum(z, 0.2)
    return (0.5 + cam[..., 0] / zz * ZOOM * 0.5) * cols, (0.5 - cam[..., 1] / zz * ZOOM * 0.5 * aspect) * rows, z


def shake(t):
    return float(smooth((t - T_SHAKE[0]) / 0.4) * (1 - smooth((t - T_SHAKE[1] + 0.4) / 0.4)))


def pose(p, group, t):
    # the shake: the cheeks bounce in turn, and the whole owl hops a little with them
    k = shake(t)
    if k == 0:
        return p
    beat = t * 13.0
    dy = 0.03 * k * abs(np.sin(beat / 2)) + 0.06 * k * np.where(
        group == 0, 0.0, np.abs(np.sin(beat / 2 + (group == 2) * np.pi / 2)))
    return p + np.stack([0 * dy, dy, 0 * dy], -1) * np.ones((len(p), 1))


def lids(t):
    # for each eye, where its upper lid sits (at the eye's centre). At rest: heavy-lidded, the
    # look. A blink or the wink brings the lid right down over the eye.
    blink = pulse(t, T_BLINK, 0.07, 0.05, 0.10)
    wink = max(pulse(t, T_WINK, 0.12, 0.55, 0.18), pulse(t, T_WINK2, 0.12, 0.55, 0.18))
    shut = np.array([blink, blink])
    shut[WINK_EYE] = max(blink, wink)
    rest = np.array(UPPER, float)
    rest[1 - WINK_EYE] += 0.035 * wink                          # the other eye opens a little wider
    return rest * (1 - shut) - (EYE_R + 0.03) * shut, shut, wink


def upper_lid(up, s, ex):
    # the upper lid is a straight edge, lower at the end nearest the beak
    return up + SLANT * s * ex / EYE_R


def lower_lid(i, s, ex):
    # the lazy eye's lower lid bulges up towards its outer corner
    return np.asarray(LOWER)[i] + 0.07 * np.clip(s * ex / EYE_R, 0, 1)


def eye_lines(t):
    # lids and brows as strokes: the straight upper lid, the lazy eye's lower lid, a smiling arc
    # over a shut eye, and short dark brows raised at their inner ends
    upper, shut, wink = lids(t)
    out = []
    ex = np.linspace(-1, 1, 40)
    for i, s in enumerate((-1, 1)):
        if shut[i] > 0.85:
            for drop in (0.0, 0.022):                               # a shut eye: a thick smiling arc
                out.append((on_face(s, ex * 0.18, 0.045 - drop - 0.085 * (1 - ex ** 2), 0.09), WHITE))
        else:
            x = ex * 0.97 * EYE_R
            y = upper_lid(upper[i], s, x)
            keep = np.hypot(x, y) < EYE_R
            out.append((on_face(s, x[keep], y[keep] + 0.03, 0.07), BROW))     # a dark lash line just above the white
        lift = 0.03 * wink * (1 if i != WINK_EYE else -0.6)     # one brow up, the winking one down
        bx = -s * (0.02 + 0.11 * (ex + 1) / 2)                      # from above the eye in towards the beak
        out.append((on_face(s, bx, EYE_R + 0.075 + lift + 0.05 * (ex + 1) / 2, 0.02), BROW))
    return out


def yaw_at(t):
    # held at a slant until T_SPIN, then eases into a steady turn
    u = max(t - T_SPIN, 0.0)
    return HOLD + SPIN * (0.5 * u * u if u < 1 else u - 0.5)


def scene(t):
    # the owl at time t, as camera-space points with their colour, brightness, part and own glyph
    yaw = yaw_at(t)
    c, s = np.cos(yaw), np.sin(yaw)
    R = np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
    M = BASIS @ R
    toward = R.T @ VIEW
    # built, and not facing away; while it is still rising the far wall shows too, like a shell
    facing = N0 @ toward > (-0.25 if t > T_BUILD[1] + 0.2 else -2)
    vis = np.flatnonzero((t >= APPEAR) & facing)
    age = t - APPEAR[vis]
    n = N0[vis]
    cam = pose(POS[vis], GROUP[vis], t) @ M.T - EYE_CAM
    diff = np.clip(n @ (R.T @ KEY), 0, 1)
    spec = np.clip(n @ (R.T @ HALF), 0, 1) ** 24
    lum = 0.62 + 0.50 * diff + 0.50 * spec
    rgb = RGB[vis].copy()
    part = PART[vis]
    glyph = np.full(len(vis), -1)

    # eyes: white half-moons under the lids, with big blue irises tucked up under the lid. The
    # irises follow the viewer: straight ahead when the owl faces the camera, slid over to one
    # side (a sidelong look) when it is side on.
    e = IS_EYE[vis]
    if e.any():
        upper, shut, wink = lids(t)
        ex, ey, sg = EX[vis][e], EY[vis][e], ESIDE[vis][e]
        i = (sg > 0).astype(int)
        up = upper_lid(upper[i], sg, ex)
        low = lower_lid(i, sg, ex)
        lid = (ey > up) | (ey < low)
        look = GAZE * float(np.clip(1.5 * toward[0], -1, 1))
        px, py = ex - look + sg * 0.015, ey - (upper[i] - 0.055)
        r = np.hypot(px, py)
        iris = r < IRIS_R
        glint = np.hypot(px + 0.035, py - 0.02) < 0.028
        blue = np.where((r > 0.72 * IRIS_R)[:, None], IRIS_RIM, IRIS)
        skin = np.where((ey < low)[:, None], LID_LOW, LIGHT)
        rgb[e] = np.where(lid[:, None], skin, np.where((iris & ~glint)[:, None], blue, WHITE))
        lum[e] = np.where(lid, lum[e], np.where(iris & ~glint, np.where(r > 0.72 * IRIS_R, 0.55, 0.95), 1.25))
        g = glyph[e]
        g[glint & iris & ~lid] = C("*")
        glyph[e] = g

    if t < T_BUILD[1] + FLASH + 0.2:
        # eyes, beak and feet pop in white-hot; the rising edge throws white sparks
        f = np.where(POP[vis], np.clip(1 - age / FLASH, 0, 1) ** 2, 0.0)
        rgb += (1 - rgb) * f[:, None]
        lum += 0.8 * f
        fresh = age < 0.12
        glyph[fresh], lum[fresh], rgb[fresh] = C("*"), 1.25, WHITE

    # the shine on the behind: the brightest spot of each cheek gets a flare
    flares = []
    if t > T_BUILD[1]:
        for cheek in (CHEEK_L, CHEEK_R):
            m = np.flatnonzero(part == cheek)
            if len(m) and spec[m].max() > 0.55:
                j = m[np.argmax(spec[m])]
                flares.append((cam[j], float(spec[j])))
                glyph[m[spec[m] > 0.92]] = C("*")

    # strokes: creases, wing outlines, lids and brows, each drawn along its own direction
    lines = [(pose(p, np.zeros(len(p), int), t), colour, prt) for p, prt, colour in CREASES]
    lines += [(pose(p, np.zeros(len(p), int), t), colour, BODY) for p, colour in eye_lines(t)]
    P, L, RGBs, PRT, G = [cam], [lum], [rgb], [part], [glyph]
    for p, colour, prt in lines:
        keep = build_time(p[:, 1]) <= t
        if keep.sum() < 3:
            continue
        pc = p[keep] @ M.T - EYE_CAM
        dx, dy = np.gradient(pc[:, 0] / pc[:, 2]), np.gradient(pc[:, 1] / pc[:, 2])
        P.append(pc)
        L.append(np.full(len(pc), 1.0))
        RGBs.append(np.tile(colour, (len(pc), 1)))
        PRT.append(np.full(len(pc), prt))
        G.append(slope_char(dx, dy))
    wink_at = on_face(1 if WINK_EYE else -1, (1 if WINK_EYE else -1) * 0.19, 0.03, 0.06) @ M.T - EYE_CAM
    info = {"deg": float(np.degrees(yaw) % 360), "M": M}
    return [np.concatenate(a) for a in (P, L, RGBs, PRT, G)], flares, wink_at, info


_HASH = {}


def HASH(rows, cols):
    if (rows, cols) not in _HASH:
        r, c = np.mgrid[0:rows, 0:cols]
        _HASH[rows, cols] = (r * 7919 + c * 104729) % 9973
    return _HASH[rows, cols]


def bodies(cam, lum, rgb, part, glyph, cols, rows, aspect, t):
    # nearest point per cell; outlines where a part meets empty space or another part further back,
    # strokes keep their own glyph, the rest is filled with letters chosen by brightness
    if len(cam) == 0:                                           # nothing built yet
        return np.zeros((rows, cols), int), np.zeros((rows, cols, 3)), np.full((rows, cols), np.inf)
    sx, sy, z = project_cam(cam, cols, rows, aspect)
    ok = np.flatnonzero((sx >= 0) & (sx < cols) & (sy >= 0) & (sy < rows) & (z > 0.3))
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
            other = (nb >= 0) & (nb != prt)
            seam = HARD[np.maximum(prt, 0)] & other & (~HARD[np.maximum(nb, 0)] | (prt < nb))
            out = body & ((nb < 0) | (other & (nz > dep + 0.035)) | seam)
            gx += dx * out
            gy += dy * out
            if dx == 0 or dy == 0:
                edge |= out
    h = HASH(rows, cols)
    L = np.where(body, lum[g], 0.0)
    level = np.clip(((L - 0.42) * 4.6).astype(int), 0, 3)
    inside = FILL[level, (h + (t * 4 + h % 11).astype(int)) % 12]
    own = np.where(body, glyph[g], -1)
    char = np.where(body, np.where(own >= 0, own, np.where(edge, outline_letter(gx, gy), inside)), 0)
    bright = np.where(edge | (own >= 0), np.maximum(0.85, L), np.clip(0.45 + 0.55 * L / 0.9, 0.45, 1.0))
    col = np.where(body[..., None], rgb[g] * np.minimum(bright, 1.4)[..., None], 0.0)
    return char, col, dep


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


HEART = np.array([[c == "#" for c in row] for row in (" ## ## ", "#######", " ##### ", "  ###  ", "   #   ")])
RING = np.random.default_rng(4).random((260, 3))
HEART_SEED = np.random.default_rng(6).random((60, 4))


# little flags, 7 x 3 cells: each letter is a colour; the marks are drawn as a character
FLAG_INK = {"R": (1.00, 0.20, 0.25), "W": (0.95, 0.96, 1.00), "Y": (1.00, 0.84, 0.10), "B": (0.22, 0.42, 1.00),
            "G": (0.10, 0.78, 0.32), "K": (0.36, 0.36, 0.42), "O": (1.00, 0.55, 0.12), "L": (0.50, 0.78, 1.00)}
FLAG_MARKS = {"*": ("*", (1.00, 0.90, 0.20)),    # yellow star / sun
              "@": ("@", (1.00, 0.20, 0.25)),    # red sun
              "+": ("+", (0.95, 0.96, 1.00)),    # white cross
              "c": ("C", (0.95, 0.96, 1.00)),    # white crescent
              "s": ("*", (0.95, 0.96, 1.00)),    # white star
              "o": ("o", (0.22, 0.42, 1.00)),    # blue wheel
              "m": ("*", (1.00, 0.20, 0.25))}    # red maple leaf
FLAGS = [("RRRRRRR", "RRR*RRR", "RRRRRRR"),      # Vietnam
         ("BBWWWRR", "BBWWWRR", "BBWWWRR"),      # France
         ("WWWWWWW", "WWW@WWW", "WWWWWWW"),      # Japan
         ("KKKKKKK", "RRRRRRR", "YYYYYYY"),      # Germany
         ("RRRRRRR", "YYYYYYY", "RRRRRRR"),      # Spain
         ("GGWWWRR", "GGWWWRR", "GGWWWRR"),      # Italy
         ("BBBRRRR", "BBBWWWW", "RRRRRRR"),      # USA
         ("GGGYGGG", "GGYBYGG", "GGGYGGG"),      # Brazil
         ("R*RRRRR", "RRRRRRR", "RRRRRRR"),      # China
         ("WWWWWWW", "BBBBBBB", "RRRRRRR"),      # Russia
         ("BBBBBBB", "BBBBBBB", "YYYYYYY"),      # Ukraine
         ("RRRRRRR", "WWWWWWW", "BBBBBBB"),      # Netherlands
         ("RRRRRRR", "RRRRRRR", "WWWWWWW"),      # Indonesia
         ("GGWWWOO", "GGWWWOO", "GGWWWOO"),      # Ireland
         ("KKYYYRR", "KKYYYRR", "KKYYYRR"),      # Belgium
         ("OOOOOOO", "WWWoWWW", "GGGGGGG"),      # India
         ("LLLLLLL", "WWW*WWW", "LLLLLLL"),      # Argentina
         ("RRWWWRR", "RRWmWRR", "RRWWWRR"),      # Canada
         ("RRRRRRR", "RRR+RRR", "RRRRRRR"),      # Switzerland
         ("RRRRRRR", "RRcsRRR", "RRRRRRR"),      # Turkey
         ("BBYBBBB", "YYYYYYY", "BBYBBBB")]      # Sweden


def _floaters():
    # everything that floats up, fixed once: when and where it is born, and what it is. About
    # two in three are flags; the flags come in a shuffled order and none of them comes twice
    rng = np.random.default_rng(100)
    n = int((LOOP - T_HEARTS) / 0.42) + 1
    order = rng.permutation(len(FLAGS))
    out, used = [], 0
    for k in range(n):
        a, b, c, d, e, f = rng.random(6)
        if e < 0.22:                                            # above its head
            x, y = -0.55 + 1.10 * a, 0.95 + 0.20 * b
        else:                                                   # beside it, left or right
            x, y = (0.62 + 0.75 * a) * (1 if f < 0.5 else -1), -0.55 + 1.35 * b
        flag = None
        if d < 0.64 and used < len(FLAGS):
            flag, used = FLAGS[order[used]], used + 1
        out.append((T_HEARTS + 0.42 * k, x, y, -0.6 + 1.2 * c, c, flag, PINK if d < 0.85 else RED))
    return out


FLOATERS = _floaters()


def hearts(t):
    # the hearts and flags in the air at time t, drifting up and swaying
    out = []
    for k, (t0, x, y, z, c, flag, colour) in enumerate(FLOATERS):
        age = t - t0
        if not 0 <= age < 3.0:
            continue
        p = np.array([x + 0.06 * np.sin(age * 2.5 + c * TAU), y + 0.40 * age, z])
        fade = smooth(age / 0.12) * (1 - smooth((age - 2.2) / 0.8))
        out.append((p, fade, flag, colour, k, age))
    return out


CONFETTI_INK = np.array([(1.00, 0.25, 0.30), (1.00, 0.85, 0.15), (0.30, 0.75, 1.00), (1.00, 0.45, 0.85),
                         (0.70, 0.45, 1.00), (1.00, 0.60, 0.15), (0.96, 0.97, 1.00)])
CONFETTI = [np.random.default_rng(31 + b).random((N_CONFETTI, 7)) for b in range(2)]


def confetti(char, col, t, cols, rows, cw, ch, origin):
    # a burst at each wink from the top of its head: strips of paper thrown up and out, spinning
    # (- / | \) and fluttering as they fall, white-hot for an instant, fading at the end
    for b, t0 in enumerate((T_WINK, T_WINK2)):
        age = t - t0
        if not 0 <= age < 5.0:
            continue
        r = CONFETTI[b]
        a = -np.pi * (0.08 + 0.84 * r[:, 0])                    # upward half, a little spread
        speed = 260 + 480 * r[:, 1]
        drag = 1.7
        tau = (1 - np.exp(-drag * age)) / drag
        x = origin[0] * cw + np.cos(a) * speed * tau + 16 * np.sin(age * (5 + 4 * r[:, 2]) + r[:, 3] * TAU) * min(age, 1)
        y = origin[1] * ch + np.sin(a) * speed * tau + 0.5 * 380 * age ** 2 * (0.6 + 0.4 * r[:, 4])
        life = 3.6 + 1.2 * r[:, 5]
        fade = np.clip((life - age) / 0.6, 0, 1)
        hot = max(0.0, 1 - age / 0.15)
        strokes = np.array([C(c) for c in "-/|\\"])
        spin = strokes[(age * (6 + 10 * r[:, 6]) + r[:, 3] * 4).astype(int) % 4]
        ink = CONFETTI_INK[(r[:, 2] * len(CONFETTI_INK)).astype(int) % len(CONFETTI_INK)]
        ix, iy = (x / cw).astype(int), (y / ch).astype(int)
        for i in np.flatnonzero((ix >= 0) & (ix < cols) & (iy >= 0) & (iy < rows) & (fade > 0.03)):
            char[iy[i], ix[i]] = spin[i]
            col[iy[i], ix[i]] = (ink[i] + (WHITE - ink[i]) * hot) * fade[i] * 1.15


DIGITS = {"0": ("###", "#.#", "#.#", "#.#", "###"), "1": (".#.", "##.", ".#.", ".#.", "###"),
          "2": ("###", "..#", "###", "#..", "###"), "3": ("###", "..#", "###", "..#", "###"),
          "4": ("#.#", "#.#", "###", "..#", "..#"), "5": ("###", "#..", "###", "..#", "###"),
          "6": ("###", "#..", "###", "#.#", "###"), "7": ("###", "..#", ".#.", ".#.", ".#."),
          "8": ("###", "#.#", "###", "#.#", "###"), "9": ("###", "#.#", "###", "..#", "###")}
FLAME_CORE, FLAME_MID, FLAME_EDGE = np.array([1.0, 0.95, 0.60]), np.array([1.0, 0.62, 0.10]), np.array([1.0, 0.28, 0.05])


def outlined(mask):
    # cells on the edge of a shape, and which way its outside lies (for outline_letter)
    rows, cols = mask.shape
    pm = np.pad(mask, 1)
    edge = np.zeros_like(mask)
    gx, gy = np.zeros(mask.shape), np.zeros(mask.shape)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dx == dy == 0:
                continue
            out = mask & ~pm[1 + dy:rows + 1 + dy, 1 + dx:cols + 1 + dx]
            gx += dx * out
            gy += dy * out
            if dx == 0 or dy == 0:
                edge |= out
    return edge, outline_letter(gx, gy)


def streak(char, col, t, cols, rows, h):
    # the streak badge in the empty space above the owl: a flickering flame and a big counter
    # rolling up to STREAK_DAYS (the flame outlined, the digits solid with dense letters);
    # when the count lands it flashes and the flame flares
    if not T_STREAK[0] <= t < T_STREAK[1] + 0.7:
        return
    grow = float(smooth((t - T_STREAK[0]) / 0.45))
    leave = 1 - float(smooth((t - T_STREAK[1]) / 0.6))
    born = float(np.clip(1 - (t - T_STREAK[0]) / FLASH, 0, 1) ** 2)
    landed = float(np.clip(1 - (t - T_COUNT[1]) / FLASH, 0, 1) ** 2) if t >= T_COUNT[1] else 0.0
    hot = max(born, landed)
    u = np.clip((t - T_COUNT[0]) / (T_COUNT[1] - T_COUNT[0]), 0, 1)
    n_digits = len(str(STREAK_DAYS))
    days = str(1 + int(round((STREAK_DAYS - 1) * (1 - (1 - u) ** 3)))).rjust(n_digits)
    PX, PY = 2.0, 1.4                                           # one pixel of a digit, in cells
    dgw, dgh = int(round(3 * PX)), int(round(5 * PY))           # one digit, in cells
    dw = n_digits * dgw + (n_digits - 1) * 2
    left = cols // 2 - (11 + dw) // 2
    base, fc = BADGE_ROW, left + 5                              # the flame's foot (row), its centre column
    top = base - dgh + 1                                        # the digits sit on the same line as the flame

    # the flame: a flickering teardrop with a hot core
    r, c = np.mgrid[0:base + 1, 0:cols]
    height = 8.0 * grow * (1 + 0.3 * landed)
    v = (base + 0.5 - r) / max(height, 1e-3)
    half = 4.6 * (1 + 0.2 * landed)
    sway = 0.16 * v ** 1.6 * np.sin(t * 7 + v * 3) + 0.05 * np.sin(t * 13 + v * 9)
    du = (c + 0.5 - fc) / half - sway
    vv = 0.10 + 0.90 * np.clip(v, 0, 1)
    w = 1.0 * np.sin(np.pi * vv ** 0.55) * (1 - vv) ** 0.22 * (1 + 0.07 * np.sin(t * 17 + v * 11))
    flame = (v >= 0) & (v <= 1) & (np.abs(du) < w)
    q = np.clip(1 - np.abs(du) / np.maximum(w, 1e-3), 0, 1)
    heat = np.clip(q * 1.3 * (1 - 0.45 * np.clip(v, 0, 1)), 0, 1)
    tint = FLAME_EDGE + (FLAME_MID - FLAME_EDGE) * np.clip(heat * 2, 0, 1)[..., None]
    tint = tint + (FLAME_CORE - tint) * np.clip(heat * 2 - 1, 0, 1)[..., None]
    edge, stroke = outlined(flame)
    level = np.clip(1 + (heat * 3).astype(int), 1, 3)
    letters = np.where(edge, stroke, FILL[level, (h[:base + 1] + int(t * 9)) % 12])
    glow = np.where(edge, 0.95, 0.75 + 0.45 * heat)
    for y, x in zip(*np.nonzero(flame)):
        char[y, x] = letters[y, x]
        ink = (FLAME_EDGE if edge[y, x] else tint[y, x])
        col[y, x] = (ink + (WHITE - ink) * hot) * glow[y, x] * leave
    for k in range(7):                                          # embers off the tip
        e_age = (t * 0.9 + k / 7) % 1.0
        ey = int(base - height - e_age * 5)
        ex = int(fc + 3 * np.sin(t * 3 + k * 2.1) * e_age)
        if 0 <= ey < rows and 0 <= ex < cols and grow > 0.9:
            put(char, col, ey, ex, "*" if e_age < 0.4 else ".", FLAME_MID, (1 - e_age) * leave)

    # the counter: block digits, outlined, dense letters inside, gold fading to orange downwards
    x0, y0 = left + 11, top
    digits = np.zeros((rows, cols), bool)
    for n, digit in enumerate(days):
        if digit == " ":
            continue
        bitmap = DIGITS[digit]
        for dy in range(dgh):                                   # each cell looks up its pixel of the digit
            for dx in range(dgw):
                if bitmap[min(int(dy / PY), 4)][min(int(dx / PX), 2)] == "#":
                    digits[y0 + dy, x0 + n * (dgw + 2) + dx] = True
    edge, stroke = outlined(digits)
    for y, x in zip(*np.nonzero(digits)):
        ink = FLAME_CORE + (FLAME_MID - FLAME_CORE) * (y - y0) / dgh
        char[y, x] = FILL[3, (h[y, x] + int(t * 4)) % 12]           # solid: thin strokes read better filled
        bright = 1.0 if edge[y, x] else 1.1
        col[y, x] = (ink + (WHITE - ink) * hot) * bright * (1 + 0.4 * hot) * grow * leave
    if landed > 0.05:                                           # the moment it lands
        rays(char, col, y0 + dgh // 2, x0 + dw // 2, int(3 + 5 * landed), WHITE, landed)
        rays(char, col, max(int(base - height), 0), fc, int(2 + 4 * landed), FLAME_CORE, landed)
    if born > 0.05:
        rays(char, col, base - 3, fc, int(2 + 4 * born), WHITE, born)


def frame(t, cols, rows, aspect, cell):
    (cam, lum, rgb, part, glyph), flares, wink_at, info = scene(t)
    char, col, dep = bodies(cam, lum, rgb, part, glyph, cols, rows, aspect, t)
    h = HASH(rows, cols)
    built = float(smooth((t - T_BUILD[0]) / 1.0))

    # a faint reflection on the polished floor, straight below the owl
    fy = project_cam((np.array([[0, FLOOR, 0.0]]) @ BASIS.T - EYE_CAM), cols, rows, aspect)[1][0]
    floor_row = int(fy)
    body = char > 0
    top = np.argmax(body, 0)                                    # first row of the owl in each column
    has = body.any(0)
    for dist in range(1, 9):
        src = floor_row + 1 - dist
        dst = floor_row + dist
        if 0 <= src < rows and dst < rows:
            m = has & (src >= top) & body[src] & ~body[dst]
            k = 0.26 * (1 - dist / 9) * built
            char[dst, m] = FILL[0, (h[dst, m] + int(t * 3)) % 12]
            col[dst, m] = col[src, m] * k

    # the ring of sparkles it rises out of (there from the very first frame, gone once it stands)
    ring = 1 - float(smooth((t - T_BUILD[1] + 1.5) / 2.0))
    if ring > 0:
        a = RING[:, 0] * TAU + t * 0.6
        r = 0.80 + 0.45 * RING[:, 1]
        p = np.stack([r * np.cos(a), FLOOR + 0.02 + 0.5 * RING[:, 2] * smooth(t / 0.8) * (0.5 + 0.5 * np.sin(t * 2 + a)),
                      r * np.sin(a)], 1)
        sx, sy, z = project_cam(p @ BASIS.T - EYE_CAM, cols, rows, aspect)
        tw = np.clip(np.sin(t * (3 + 4 * RING[:, 2]) + RING[:, 1] * 40), 0, 1) ** 2 * ring
        for x, y, zz, w in zip(sx.astype(int), sy.astype(int), z, tw):
            if 0 <= y < rows and 0 <= x < cols and w > 0.08 and zz < dep[y, x]:
                put(char, col, y, x, "*" if w > 0.6 else ("+" if w > 0.3 else "."), LIGHT if w < 0.8 else WHITE,
                    0.35 + 0.9 * w)

    # hearts and flags, behind the owl. Each pops in like the decorations on the Christmas tree:
    # a white star with a flare first, then the shape, white-hot, cooling to its own colours
    live = hearts(t)
    for p, fade, flag, colour, k, age in live:
        sx, sy, z = project_cam((p[None] @ BASIS.T - EYE_CAM), cols, rows, aspect)
        cx, cy = int(sx[0]), int(sy[0])
        hot = float(np.clip(1 - age / FLASH, 0, 1) ** 2)
        if age >= 0.08:
            shape = HEART.shape if flag is None else (3, 7)
            for dy in range(shape[0]):
                for dx in range(shape[1]):
                    y, x = cy + dy - shape[0] // 2, cx + dx - 3
                    if not (0 <= y < rows and 0 <= x < cols) or body[y, x]:
                        continue
                    if flag is None:
                        if not HEART[dy, dx]:
                            continue
                        ink, k_ = colour, (1.0 if 0 < dy < 3 else 0.8)
                        char[y, x] = FILL[3, (h[y, x] + k) % 12]
                    else:
                        mark = flag[dy][dx]
                        if mark in FLAG_MARKS:
                            glyph_, ink = FLAG_MARKS[mark]
                            char[y, x], ink = C(glyph_), np.array(ink)
                        else:
                            char[y, x], ink = FILL[3, (h[y, x] + k) % 12], np.array(FLAG_INK[mark])
                        k_ = 1.0
                    col[y, x] = (ink + (WHITE - ink) * 0.85 * hot) * fade * k_ * (1 + 0.6 * hot)
        if age < 0.45 and 0 <= cy < rows and 0 <= cx < cols and not body[cy, cx]:
            rays(char, col, cy, cx, int(2 + 3 * hot), WHITE, max(hot, 0.35))

    # flares: the shine on each cheek, and the spark of the wink
    for n, (pc, strength) in enumerate(flares):
        sx, sy, z = project_cam(pc[None], cols, rows, aspect)
        y, x = int(sy[0]), int(sx[0])
        if 0 <= y < rows and 0 <= x < cols and z[0] <= dep[y, x] + 0.05:
            beat = 0.5 + 0.5 * np.sin(t * 6 + n * 2.1)
            rays(char, col, y, x, int(2 + 3 * beat + 3 * shake(t)), WHITE, 0.55 + 0.45 * strength)
    spark = max(np.exp(-((t - T_WINK - 0.32) / 0.22) ** 2), np.exp(-((t - T_WINK2 - 0.32) / 0.22) ** 2))
    if spark > 0.05:
        sx, sy, z = project_cam(wink_at[None], cols, rows, aspect)
        rays(char, col, int(sy[0]), int(sx[0]), int(2 + 5 * spark), WHITE, float(spark))

    # confetti from the top of its head at each wink, and the streak badge above it
    hx, hy, _ = project_cam((np.array([[0, TOP - 0.05, 0.0]]) @ BASIS.T - EYE_CAM), cols, rows, aspect)
    confetti(char, col, t, cols, rows, 9, 9 / cell, (hx[0], hy[0]))
    streak(char, col, t, cols, rows, h)

    out = {"deg": info["deg"], "hearts": len(live), "letters": int((char > 0).sum())}
    return char, col, out


# window

TITLE = "ASCII Duo"
CW, CH, FONT_PX = 9, 14, 15
COLS, ROWS = 88, 74
W, H = COLS * CW, ROWS * CH
MONO = "consolas,menlo,dejavusansmono,couriernew,monospace"
HINT = "Space pause · R restart · S screenshot · Esc quit"
DIM, ACCENT, SIGN = (110, 104, 120), (150, 230, 60), (176, 168, 196)
TRAIL = 0.40                                    # how much of the last frame stays behind (motion trails)


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
        for layer, amount in ((tight, 0.70), (wide, 0.45)):
            layer = pygame.transform.smoothscale(layer, (w, h))
            layer.fill((int(255 * amount),) * 3, special_flags=pygame.BLEND_MULT)
            self.out.blit(layer, (0, 0), special_flags=pygame.BLEND_ADD)

    def draw(self, t):
        w, h = self.w, self.h
        char, col, info = frame(t, self.cols, self.rows, w / h, self.cw / self.ch)
        pygame.surfarray.blit_array(self.art, self.atlas[char].transpose(1, 3, 0, 2, 4).reshape(w, h, 3))
        tint = pygame.surfarray.make_surface((np.clip(col, 0, 1) * 255).astype(np.uint8).transpose(1, 0, 2))
        self.art.blit(pygame.transform.scale(tint, (w, h)), (0, 0), special_flags=pygame.BLEND_MULT)
        if self.last_t is None or t < self.last_t:
            self.trail.fill((0, 0, 0))                          # restarted: no trails from before
        self.last_t = t
        self.trail.fill((int(TRAIL * 255),) * 3, special_flags=pygame.BLEND_MULT)
        self.trail.blit(self.art, (0, 0), special_flags=pygame.BLEND_MAX)
        self.out.fill((0, 0, 0))
        self.out.blit(self.trail, (0, 0))
        self.glow(self.out)
        lines = [f"rotation {info['deg']:06.2f}°      hearts & flags {info['hearts']:>2}", f"letters {info['letters']:,}"]
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
                pygame.image.save(screen, str(Path(__file__).with_name(f"duo_{int(time.time())}.png")))
        dt = clock.tick(30) / 1000
        if not paused:
            t += min(dt, 1 / 15)
            if t > LOOP:
                t = 0.0
            screen = renderer.draw(t)
        window.blit(screen if size == (W, H) else pygame.transform.smoothscale(screen, size), (0, 0))
        pygame.display.flip()


if __name__ == "__main__":
    sys.exit(main())
