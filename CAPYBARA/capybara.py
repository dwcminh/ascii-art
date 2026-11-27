# ASCII Capybara
# @dwcminh.ascii, 2026
# Terms in LICENSE.txt: personal, non-commercial use only. Not for use with AI tools:
# do not feed this code to an AI model, train on it, or have an AI rework it.
#
#   pip install numpy pygame-ce
#   python capybara.py
#
# A capybara in a hot spring on a winter night, an orange on its head. Snow is falling, steam
# curls up off the water and leaves come drifting down the whole time. It begins with the orange:
# a spark falls out of the dark, swells into an orange and drops into the black water. Bubbles
# come up, and then so does something else, right under it: two ears, a broad brown crown with
# the orange sitting on top, eyes, the great square snout, water streaming off it and its
# reflection rising out of the water to meet it. It shakes the water off its ears and opens its
# eyes. After that it only floats there, bobbing on every beat, while things happen to it: yuzu
# drop into the water all round it, another orange lands on the first, then another, fireworks
# start going off over the water, and a kumquat crowns the stack. It does not mind at all: in
# the middle of the fireworks it gives an enormous yawn, big front teeth and all, and dozes off
# while the floating yuzu light up like lanterns, opening its eyes again for the last of them.
#
# Space pause, R restart, S screenshot, Esc quit

import sys
import time
from pathlib import Path

import numpy as np
import pygame

CREDIT = "@dwcminh.ascii"

TAU = np.pi * 2
GOLDEN = np.pi * (3 - np.sqrt(5))
LOOP = 20.0                                     # length of one run (s)
PERIOD = 2.0                                    # one slow bob in the water (s)
BEAT0 = 0.2                                     # the beats: 0.2, 2.2, 4.2 ...

# timeline (s)
T_SPARK = 0.38                                  # a spark falls out of the dark and swells into an orange...
T_PLOP = 0.45                                   # ...which drops into the water
T_BUBBLES = (0.62, 0.74, 0.86)                  # bubbles: something is coming up
T_RISE = 0.45                                   # the capybara comes up under the orange and lifts it on its head
T_SHAKE = 2.5                                   # it shakes the water off its ears...
T_WAKE = 2.8                                    # ...and opens its eyes
T_YUZU = (4.2, 5.4)                             # yuzu drop into the water all round it, one after another
T_STACK = (6.2, 8.2, 10.2)                      # an orange lands on the orange, then another, then a kumquat
T_FIREWORKS = (8.9, 9.6, 11.0, 12.6, 13.4, 14.9, 16.2, 17.1, 18.2, 18.9)   # fireworks over the water, from 8 s on
T_YAWN = (12.0, 13.5)                           # in the middle of them it yawns, and dozes off...
T_ROUSE = 16.0                                  # ...until it opens its eyes again for the last of them
T_LANTERNS = (14.2, 15.4)                       # the floating yuzu light up like lanterns, one by one
FALL = 0.5                                      # how long an orange takes to drop in from the top of the frame (s)
YUZU_FALL = 0.65                                # ...and a yuzu, which falls from higher up
FLASH = 0.6                                     # how long something new glows white (s)

N_STACK, N_YUZU = 4, 7
FUR, BACK, EYE, EAR, ORANGE = 0, 1, 2, 3, 4     # FUR is its head; ORANGE + k: the k-th orange of the stack
LEAF = ORANGE + N_STACK
YUZU = LEAF + 1                                 # YUZU + k: the k-th floating yuzu
INSIDE = YUZU + N_YUZU                          # inside its mouth
TEETH = INSIDE + 1
MARK = TEETH + 1                                # strokes and marks that keep their own letter
HARD = np.arange(MARK + 1) < MARK               # every part gets an outline where it meets another
POOLS = ["1il!;:", "rtfjcvxz=+", "aeoun0{}[]<>", "08B$#&%Q"]   # fill letters, dark -> bright
C = lambda ch: ord(ch) - 32                     # character -> glyph index
FILL = np.array([[C(p[k % len(p)]) for k in range(12)] for p in POOLS])
SLOPE = np.array([C(c) for c in "-/|\\-"])

FUR_INK = np.array([1.00, 0.68, 0.34])          # golden caramel
SNOUT_INK = np.array([0.80, 0.48, 0.30])        # the darker front of the snout
EAR_INK = np.array([0.80, 0.42, 0.32])          # inside the ears
EYE_INK = np.array([0.14, 0.08, 0.06])
PALATE_INK = np.array([0.45, 0.08, 0.12])       # inside its mouth...
TONGUE_INK = np.array([1.00, 0.46, 0.56])
TOOTH_INK = np.array([1.00, 0.94, 0.80])        # ...and its big front teeth
ORANGE_INK = np.array([1.00, 0.45, 0.04])
KUMQUAT_INK = np.array([1.00, 0.60, 0.06])
YUZU_INK = np.array([1.00, 0.80, 0.14])
LEAF_INK = np.array([0.30, 0.92, 0.34])
STEM_INK = np.array([0.52, 0.66, 0.22])
WATER = np.array([0.30, 0.72, 1.00])
FOAM = np.array([0.80, 0.95, 1.00])
WHITE = np.array([1.00, 0.98, 0.94])
GOLD = np.array([1.00, 0.84, 0.42])
SNOW_INK = np.array([0.88, 0.94, 1.00])
STEAM_INK = np.array([0.78, 0.84, 0.94])
STAR_INK = np.array([0.70, 0.80, 1.00])
PINK, CYAN, EMBER = np.array([1.00, 0.36, 0.62]), np.array([0.30, 0.86, 1.00]), np.array([1.00, 0.45, 0.10])
LIME, VIOLET, RED = np.array([0.45, 1.00, 0.45]), np.array([0.74, 0.46, 1.00]), np.array([1.00, 0.26, 0.26])
SPARK_INK = np.array([GOLD, EMBER, PINK, CYAN, WHITE])
PALE = lambda rgb, k: rgb + (WHITE - rgb) * k


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
    return np.stack([r * np.cos(GOLDEN * i), y, r * np.sin(GOLDEN * i)], 1)


def slope_char(dx, dy):
    # screen direction (y up) -> the ASCII stroke that looks most like it
    ang = np.degrees(np.arctan2(dy, dx)) % 180
    return SLOPE[np.digitize(ang, [25, 72, 108, 155])]


def outline_letter(gx, gy):
    ax, ay = np.abs(gx), np.abs(gy)
    c = np.where(ax > 2 * ay, C("|"), np.where(ay > 2 * ax, np.where(gy > 0, C("_"), C("-")),
                 np.where(gx * gy > 0, C("/"), C("\\"))))
    return np.where(ax + ay == 0, C("+"), c)


def rot_x(a):
    c, s = np.cos(a), np.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])


def rot_y(a):
    c, s = np.cos(a), np.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])


def rot_z(a):
    c, s = np.cos(a), np.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


def rot_axis(axis, a):
    k = unit(axis)
    K = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
    return np.eye(3) + np.sin(a) * K + (1 - np.cos(a)) * K @ K


def smin(a, b, k):
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0, 1)
    return b + (a - b) * h - k * h * (1 - h)


def smax(a, b, k):
    return -smin(-a, -b, k)


# the capybara, built in its own space: x across, y up, z out along its nose. When it floats at
# rest the water is at y = 0: its head and the top of its back stand out of it, the rest is under.
# The shape is a few soft solids melted together; its skin is a cloud of points pulled onto it.

def sd_ellipsoid(p, c, r):
    q = (p - c) / r
    k0 = np.linalg.norm(q, axis=-1)
    return k0 * (k0 - 1) / np.maximum(np.linalg.norm(q / r, axis=-1), 1e-9)


def sd_box(p, c, half, rad):
    q = np.abs(p - c) - (half - rad)
    return np.linalg.norm(np.maximum(q, 0), axis=-1) + np.minimum(q.max(-1), 0) - rad


def head_sdf(p):
    # a long rounded brick, narrowing a little towards the blunt square snout, a dome on top
    # between the ears, and deep cheeks underneath
    q = p * np.stack([1 / (1 - 0.20 * np.clip(p[..., 2] / 0.5, 0, 1)), np.ones(p.shape[:-1]), np.ones(p.shape[:-1])], -1)
    brick = sd_box(q, np.array([0, 0.31, 0.10]), np.array([0.215, 0.215, 0.40]), 0.16)
    dome = sd_ellipsoid(p, np.array([0, 0.37, -0.10]), np.array([0.235, 0.20, 0.24]))
    cheek = sd_ellipsoid(p, np.array([0, 0.17, -0.06]), np.array([0.255, 0.17, 0.24]))
    return smin(smin(brick, dome, 0.08), cheek, 0.08)


def back_sdf(p):
    # sitting in the water up to its chin: only the top of its neck and shoulders ever comes out
    neck = sd_ellipsoid(p, np.array([0, -0.06, -0.24]), np.array([0.27, 0.24, 0.30]))
    body = sd_ellipsoid(p, np.array([0, -0.46, -0.50]), np.array([0.38, 0.40, 0.60]))
    return smin(neck, body, 0.16)


def capy_sdf(p):
    return smin(head_sdf(p), back_sdf(p), 0.10)


def gradient(f, p, e=1e-3):
    return np.stack([f(p + d) - f(p - d) for d in np.eye(3) * e], -1) / (2 * e)


def pull(f, p, steps=4):
    # move points onto the surface f = 0, and give them its normal there
    for _ in range(steps):
        g = gradient(f, p)
        p = p - (f(p) / np.maximum((g * g).sum(-1), 1e-9))[:, None] * g
    return p, unit(gradient(f, p))


def skin(f, lo, hi, step):
    # points spread evenly over the surface: the corners of a fine grid close to it, pulled onto
    # it, one kept in every little cube
    big = 4 * step
    grid = np.stack(np.meshgrid(*[np.arange(a, b, big) for a, b in zip(lo, hi)], indexing="ij"), -1).reshape(-1, 3)
    grid = grid[np.abs(f(grid)) < 1.2 * big]
    fine = np.stack(np.meshgrid(*[np.arange(4) - 1.5] * 3, indexing="ij"), -1).reshape(-1, 3) * step
    p = (grid[:, None] + fine[None]).reshape(-1, 3)
    p = p[np.abs(f(p)) < 0.75 * step]
    p, n = pull(f, p)
    ok = np.abs(f(p)) < 1e-3
    p, n = p[ok], n[ok]
    _, keep = np.unique(np.floor(p / step).astype(np.int64), axis=0, return_index=True)
    shuffle = np.random.default_rng(1).permutation(len(keep))       # so every other point is a fair half
    return p[keep][shuffle], n[keep][shuffle]


CAPY_P, CAPY_N = skin(capy_sdf, (-0.40, -0.15, -0.70), (0.40, 0.62, 0.58), 0.0075)
CAPY_PART = np.where(head_sdf(CAPY_P) <= back_sdf(CAPY_P) + 0.004, FUR, BACK)
_rng = np.random.default_rng(7)
_snout = smooth((CAPY_P[:, 2] - 0.40) / 0.10) * smooth((CAPY_P[:, 1] - 0.08) / 0.10)
FUR_RGB = (FUR_INK + (SNOUT_INK - FUR_INK) * _snout[:, None]) * (0.90 + 0.18 * _rng.random(len(CAPY_P)))[:, None]
GLISTEN = _rng.random(len(CAPY_P)) < 0.02                      # drops of water caught in its fur as it comes up
GLISTEN_PH = _rng.random(len(CAPY_P)) * TAU
HEAD_TOP = pull(head_sdf, np.array([[0.0, 0.80, 0.02]]), 8)[0][0]   # where the first orange sits


def on_head(pts, lift=0.006):
    p, n = pull(head_sdf, np.asarray(pts, float).reshape(-1, 3), 8)
    return (p + lift * n).reshape(np.shape(pts))


# eyes: small dark beads high up at the corners of the head, each with a glint

EYE_C, EYE_N = pull(head_sdf, np.array([[0.30, 0.54, 0.16], [-0.30, 0.54, 0.16]]), 8)
EYE_R = 0.047
EYE_C = EYE_C - 0.012 * EYE_N                   # sunk a little into the head
_e = fib_sphere(260)
EYE_P = (EYE_C[:, None] + EYE_R * _e[None]).reshape(-1, 3)
_s = np.linspace(-1, 1, 11)[:, None]


def lids(curve):
    # a closed eye: a curved stroke across it (+1 arches up, a happy squint; -1 hangs down, shut)
    out = []
    for c, n in zip(EYE_C, EYE_N):
        ue = unit(np.cross([0, 1.0, 0], n))
        ve = np.cross(n, ue)
        out.append(c + n * EYE_R * 0.9 + ue * EYE_R * 1.1 * _s + ve * (curve * 0.016 * (1 - _s ** 2) - 0.004))
    return np.array(out)


LID_HAPPY, LID_SHUT = lids(1.0), lids(-1.0)
LID_SLEEPY = lids(0.0)                          # drowsy: a heavy lid straight across the middle...
EYE_LOW = np.concatenate([(_e @ np.cross(n, unit(np.cross([0, 1.0, 0], n)))) < -0.15 for n in EYE_N])   # ...over the lower half

# ears: small round flaps at the top back of the head, flicking now and then

EAR_BASE, _ebn = pull(head_sdf, np.array([[0.26, 0.60, -0.31], [-0.26, 0.60, -0.31]]), 8)
EAR_RAD = np.array([0.070, 0.080, 0.026])
_ear = fib_sphere(700)
EAR_Q, EAR_QN = _ear * EAR_RAD, unit(_ear / EAR_RAD)            # in the ear's own axes: across, up, out of its face
EAR_INNER = (_ear[:, 2] > 0.2) & (_ear[:, 0] ** 2 + (_ear[:, 1] + 0.1) ** 2 < 0.55)
EAR_UVW = []
for _b, _n, _side in zip(EAR_BASE, _ebn, (1, -1)):
    _v = unit(_n + np.array([0, 0.9, 0]))
    _w = unit(np.array([0.5 * _side, 0.0, 1.0]))
    _w = unit(_w - _v * (_w @ _v))
    EAR_UVW.append(np.stack([np.cross(_v, _w), _v, _w]))
EAR_UVW = np.array(EAR_UVW)

# the face: slits of nostrils at the top of the snout; the split lip running down the front from
# them, and from its foot the line of the mouth curving back along each side, a little smile

_k = np.linspace(-1, 1, 7)[:, None]
NOSTRILS = np.array([on_head(np.array([0.085, 0.44, 0.62]) + _k * [0.024, -0.036, -0.012]),
                     on_head(np.array([-0.085, 0.44, 0.62]) + _k * [-0.024, -0.036, -0.012])])
_m = np.linspace(0, 1, 15)[:, None]
MOUTH = np.array([on_head(np.array([0, 0.39, 0.62]) + _m * [0, -0.20, 0]),
                  on_head(np.array([0, 0.19, 0.62]) + _m * [0.30, 0, -0.30] + _m ** 0.5 * [0, -0.050, 0]),
                  on_head(np.array([0, 0.19, 0.62]) + _m * [-0.30, 0, -0.30] + _m ** 0.5 * [0, -0.050, 0])])

# the yawn: everything below the line of its mouth swings down about a hinge at the back of the
# jaw, all of it at the front and less and less towards the hinge. Hidden inside the closed
# mouth there is a palate and a tongue, and two pairs of big front teeth.

JAW_Y, HINGE = 0.15, np.array([0.16, -0.12])    # the line of the mouth; the hinge (y, z)
JAW_OPEN = 0.55                                 # how far it drops at the height of the yawn (rad)


def jaw_weight(p, below):
    return np.where(below, smooth((p[:, 2] + 0.10) / 0.22), 0.0)


def open_jaw(p, n, w, angle):
    # swing the points by angle * w about the hinge
    a = angle * w
    c, s = np.cos(a), np.sin(a)
    dy, dz = p[:, 1] - HINGE[0], p[:, 2] - HINGE[1]
    q = p.copy()
    q[:, 1], q[:, 2] = HINGE[0] + c * dy - s * dz, HINGE[1] + s * dy + c * dz
    if n is None:
        return q
    m = n.copy()
    m[:, 1], m[:, 2] = c * n[:, 1] - s * n[:, 2], s * n[:, 1] + c * n[:, 2]
    return q, m


CAPY_JAW = jaw_weight(CAPY_P, (CAPY_P[:, 1] < JAW_Y) & (CAPY_PART == FUR))
_mo = fib_sphere(1400)
MOUTH_P = _mo * [0.10, 0.045, 0.24] + [0, 0.16, 0.20]                  # a hollow inside the snout
MOUTH_N = unit(_mo / [0.10, 0.045, 0.24])
MOUTH_JAW = jaw_weight(MOUTH_P, MOUTH_P[:, 1] < 0.16)
MOUTH_RGB = np.where((MOUTH_P[:, 1] < 0.16)[:, None], TONGUE_INK, PALATE_INK) \
    * (0.30 + 0.70 * smooth((MOUTH_P[:, 2] + 0.02) / 0.32))[:, None]    # darker down towards its throat


def incisors(y0, y1, inset):
    # a pair of front teeth just inside the front of the snout, between heights y0 and y1 (they
    # are only drawn while its mouth is open): find the front of the snout straight ahead of each
    # point, and step back from it
    g = np.stack(np.meshgrid(np.linspace(0.005, 0.044, 6), np.linspace(y0, y1, 10), [0.0], indexing="ij"), -1).reshape(-1, 3)
    g = np.concatenate([g, g * [-1, 1, 1]])
    zs = np.linspace(0.70, 0.20, 501)
    inside = head_sdf(g[:, None, :] + zs[None, :, None] * [0, 0, 1]) < 0
    g[:, 2] = zs[np.argmax(inside, axis=1)] - inset
    return g, np.tile([0, 0, 1.0], (len(g), 1))


TEETH_UP, TEETH_DOWN = incisors(0.100, 0.158, 0.012), incisors(0.098, 0.148, 0.030)   # the lower pair rides on the jaw


# how it floats: it comes up out of the deep slowly, overshoots a little and settles; then it
# bobs on every beat, nods and rolls a little, and turns slowly round in the water the whole time

DEEP = 0.82                                     # how far under the water it starts


def rise(t):
    # ears break the water about 0.65 s after it starts up, eyes 1.0 s, its mouth 1.3 s
    a = max(t - T_RISE, 0.0)
    return -DEEP * np.exp(-a / 0.88) * (np.cos(1.31 * a) + np.sin(1.31 * a) / 1.153)


def settled(t):
    return smooth((t - 2.2) / 1.4)


def yawn(t):
    # how wide its mouth is open (0..1): it opens slowly, holds it, and shuts it quickly
    return float(smooth((t - T_YAWN[0]) / 0.5) * (1 - smooth((t - T_YAWN[1] + 0.35) / 0.35)))


def knocks(t, size, freq, phase=0.0, decay=0.35):
    # every orange that lands on the stack: a jolt that rings away
    out = 0.0
    for T in T_STACK:
        a = t - T
        if a > 0:
            out += size * np.exp(-a / decay) * np.sin(freq * a + phase)
    return out


def shake(t):
    a = t - T_SHAKE
    return 0.10 * np.exp(-a / 0.22) * np.sin(26 * a) if 0 < a < 1.2 else 0.0


def capy_yaw(t):
    # nearly side on, the way a capybara is easiest to know, turning slowly round towards us
    return 1.15 - 0.35 * smooth(t / LOOP) + 0.08 * np.sin(TAU * t / 9.0) * smooth((t - 3) / 2)


def capy_pose(t):
    s = settled(t)
    beat = TAU * (t - BEAT0) / PERIOD
    y = yawn(t)                                 # it lifts its nose to yawn
    lift = rise(t) + 0.026 * s * np.sin(beat) - knocks(t, 0.045, 7.5) + 0.13 * y
    pitch = 0.20 * (1 - smooth((t - T_RISE) / 2.0)) + 0.03 * s * np.cos(beat) - knocks(t, 0.05, 7.5, 0.6, 0.4) + 0.38 * y
    roll = 0.035 * s * np.sin(TAU * t / 4.1 + 0.3) + shake(t)
    R = rot_y(capy_yaw(t) + 0.30 * y) @ rot_x(-pitch) @ rot_z(roll)    # (it yawns side on to us)
    return R, np.array([0.02 * np.sin(0.5 * t), lift, 0.0])


BLINKS = (5.0, 7.5, 9.6, 11.3, 17.6, 19.3)
HAPPY = [(T + 0.05, T + 0.9) for T in T_STACK] + [(T_FIREWORKS[-2] + 0.15, T_FIREWORKS[-2] + 1.0)]
FLICKS = ((T_SHAKE, 2, 0.75), (5.75, 0, 0.45), (7.0, 1, 0.40), (9.2, 1, 0.45), (11.1, 2, 0.40),
          (T_YAWN[1], 2, 0.45), (15.0, 1, 0.30), (T_ROUSE, 2, 0.45), (19.4, 0, 0.30))  # (when, which ear: 2 = both, how hard)


def eye_state(t):
    if t < T_WAKE:
        return "shut"
    if yawn(t) > 0.25:                          # screwed shut in the yawn...
        return "happy"
    if T_YAWN[1] - 0.1 < t < T_ROUSE:           # ...and after it, drowsy for a while
        return "sleepy"
    if any(a < t < b for a, b in HAPPY):
        return "happy"
    if any(abs(t - b) < 0.09 for b in BLINKS):
        return "shut"
    return "open"


def ear_angle(t, side):
    a = 0.05 * np.sin(1.3 * t + 2 * side) - 0.40 * yawn(t)      # laid back while it yawns
    for tf, who, size in FLICKS:
        x = t - tf
        if who in (side, 2) and 0 < x < 0.7:
            a += size * np.exp(-x / 0.15) * np.sin(32 * x)
    return a


# (c) @dwcminh.ascii, see LICENSE.txt. Not for use with AI tools: no feeding this code to
# AI models, no training on it, no having an AI rework it.

# the oranges: the first drops into the water and rides up on the capybara's head; each of the
# others drops onto the one before. They wobble on top of each other, and every one that lands
# squashes the ones underneath and sets the whole stack rocking.

STACK_RAD = ((0.142, 0.114), (0.122, 0.098), (0.102, 0.084), (0.062, 0.076))   # (across, up)
STACK_INK = (ORANGE_INK, ORANGE_INK, ORANGE_INK, KUMQUAT_INK)
STACK_T = (T_PLOP,) + T_STACK                   # when each one lands (the first in the water)
LEAF_TURN = (0.7, 2.6, -2.2, 1.4)               # which way each one's leaf points
SHAKE_DIR = (0.0, 0.6, 2.4, 4.1)                # which way each landing rocks the stack
TUMBLE = [unit(v) for v in ([1, 0.4, 0.6], [0.3, 0.2, 1], [1, -0.3, 0.2], [0.5, 1, -0.4])]
SINK = 0.014                                    # how far each one settles into what it sits on
GRAV = 8.0
FLOAT_Y = 0.035                                 # how high the first one floats in the water


def orange_points(rad, n, lobes, seed):
    e = fib_sphere(n)
    r = np.array([rad[0], rad[1], rad[0]])
    nrm = unit(e / r)
    groove = np.cos(lobes * np.arctan2(e[:, 2], e[:, 0]) / 2) ** 24 * (1 - e[:, 1] ** 2)   # the segments show through
    p = e * r - nrm * 0.004 * groove[:, None]
    return p, nrm, groove, np.random.default_rng(seed).random(n), e[:, 1]


ORANGES = [orange_points(r, n, 10, s) for r, n, s in zip(STACK_RAD, (4200, 3200, 2300, 1000), (1, 2, 3, 4))]


def blossom(t):
    # the first orange: a spark that swells into an orange as it falls, a little too big, then settles
    return 0.06 + 0.94 * smooth(t / T_SPARK) + 0.18 * np.sin(np.pi * np.clip((t - 0.2) / 0.4, 0, 1))


def stack(t, R, T):
    out = []
    contact, orient = HEAD_TOP @ R.T + T, R
    s = settled(t)
    for k in range(N_STACK):
        a = t - STACK_T[k]
        if k > 0 and a < -FALL:
            break
        ry = STACK_RAD[k][1]
        wx = 0.035 * (k + 1) * s * np.sin(TAU * (t - BEAT0) / PERIOD - 1.0 - 0.7 * k)
        snap = t - (T_YAWN[1] - 0.15)                           # its mouth snapping shut sets it rocking
        if snap > 0:
            wx += 0.05 * (k + 1) * np.exp(-snap / 0.5) * np.sin(8 * snap - 0.5 * k)
        wz = 0.022 * (k + 1) * np.sin(TAU * t / 3.3 + 1.3 * k) + 1.6 * shake(t - 0.06 * (k + 1))
        sq = 1.0
        for j in range(max(k, 1), N_STACK):             # every landing from here up rocks it and squashes it
            aj = t - STACK_T[j]
            if aj > 0:
                amp = 0.12 * 0.75 ** (j - k) * np.exp(-aj / 0.55) * np.sin(8.5 * aj + 0.5 * (j - k))
                wx, wz = wx + amp * np.cos(SHAKE_DIR[j]), wz + amp * np.sin(SHAKE_DIR[j])
                sq -= 0.22 * 0.5 ** (j - k) * np.exp(-aj / 0.16) * np.cos(17 * aj)
        o = orient @ rot_x(wx) @ rot_z(wz)
        scale, hot = 1.0, 0.0
        if k == 0:
            # it falls into the water and floats, until the head comes up under it and lifts it
            scale = blossom(t)
            hot = float(np.clip(1 - t / 0.55, 0, 1) ** 1.2)
            if a < 0:
                y = FLOAT_Y + 0.5 * GRAV * a * a
            else:
                y = FLOAT_Y - 0.10 * np.exp(-a / 0.28) * np.sin(9 * a) + 0.008 * np.sin(2.4 * a)
                hot += 0.6 * float(np.clip(1 - a / 0.4, 0, 1) ** 2)
            y = smax(y, contact[1] + ry * sq - SINK, 0.05)
            centre = np.array([contact[0], y, contact[2]])
        else:
            centre = contact + o[:, 1] * (ry * sq - SINK)
            if a < 0:                                   # still falling, turning over as it comes
                o = o @ rot_axis(TUMBLE[k], 7.0 * a)
                centre = centre + np.array([0, 0.5 * GRAV * a * a, 0])
                sq = 1.06
            else:
                hot = 0.75 * float(np.clip(1 - a / FLASH, 0, 1) ** 2)
        out.append({"k": k, "centre": centre, "o": o, "sq": sq, "scale": scale, "hot": hot, "landed": a >= 0})
        contact, orient = centre + o[:, 1] * (ry * sq - SINK) * scale, o
    return out


# the leaf: a small curled blade on top of whichever orange is highest. When the next one lands
# it knocks the leaf off, and the leaf flutters down to the water and floats away.

LEAF_LEN, LEAF_WIDE = 0.150, 0.048
LEAF_S, LEAF_W = np.meshgrid(np.linspace(0, 1, 30), np.linspace(-1, 1, 11), indexing="ij")
_wide = LEAF_WIDE * np.sin(np.pi * LEAF_S ** 0.75) ** 0.9
_leaf = np.stack([0.010 + LEAF_LEN * LEAF_S, 0.30 * LEAF_LEN * LEAF_S ** 2 + 0.35 * (_wide * LEAF_W) ** 2 / LEAF_WIDE,
                  _wide * LEAF_W], -1)
LEAF_NRM = unit(np.cross(np.gradient(_leaf, axis=0), np.gradient(_leaf, axis=1))).reshape(-1, 3)
LEAF_LOCAL = _leaf.reshape(-1, 3)
LEAF_RIB = ((np.abs(LEAF_W) < 0.12) & (LEAF_S > 0.05) & (LEAF_S < 0.93)).ravel()
LEAF_FLOAT = 0.006
LEAF_STAY = 6.0                                 # how long a leaf floats on the water before it sinks (s)


def leaf_rgb(ink):
    return np.where(LEAF_RIB[:, None], PALE(ink, 0.45), ink * (0.80 + 0.25 * np.abs(LEAF_W.ravel()))[:, None])


LEAF_RGB = leaf_rgb(LEAF_INK)


def leaf_on(e, t):
    # the leaf on top of orange e: where its points are, and its frame (to knock it off from)
    k = e["k"]
    lift = 0.45 + 0.10 * np.sin(3.3 * t + k) + 0.25 * knocks(t, 1.0, 9.0, 0.3, 0.4)
    M = e["o"] @ rot_y(LEAF_TURN[k]) @ rot_z(lift)
    top = e["centre"] + e["o"][:, 1] * (STACK_RAD[k][1] * e["sq"] - 0.004) * e["scale"]
    return LEAF_LOCAL * e["scale"] @ M.T + top, LEAF_NRM @ M.T, top, M


LEAF_OUT = unit(np.array([[-0.85, -0.55], [0.95, -0.30], [-0.95, 0.15]]))     # which way each one flies off


def leaf_height(p0, a, pop, speed):
    return p0[1] + pop * (1 - np.exp(-a / 0.16)) - speed * a


def leaf_drop(p0, yaw0, out, a, pop, speed, sway, rate):
    # a leaf let go from p0 a moment a ago: it pops up first if it was knocked off, falls rocking
    # from side to side, settles flat on the water, drifts a little, and after a while sinks
    h = leaf_height(p0, a, pop, speed)
    rock = smooth((h - LEAF_FLOAT) / 0.15) * (np.exp(-a / 1.4) if pop else 1.0)
    side = np.array([-out[1], out[0]])
    go = 0.75 * (1 - np.exp(-a / 0.6)) if pop else 0.0
    xz = p0[[0, 2]] + out * (go + 0.03 * a) + side * sway * np.sin(rate * a) * rock
    wet = max(LEAF_FLOAT - h, 0.0) / speed                      # how long it has been on the water
    y = max(h, LEAF_FLOAT) - 0.05 * max(wet - LEAF_STAY, 0.0)
    M = rot_y(yaw0 + 1.2 * a * rock + 0.1 * a) @ rot_x(0.7 * np.sin(1.1 * rate * a) * rock) @ rot_z(0.55 * np.cos(rate * a) * rock)
    return (LEAF_LOCAL - [0.010 + LEAF_LEN / 2, 0, 0]) @ M.T + [xz[0], y, xz[1]], LEAF_NRM @ M.T


def leaf_flight(k, a):
    # the leaf knocked off orange k a moment a ago: up and off to one side, then down
    p0, yaw0, out = LEAF_GO[k]
    return leaf_drop(p0, yaw0, out, a, 0.18, 0.70, 0.08, 5.0)


def _leaf_go():
    out = []
    for k in range(N_STACK - 1):
        T = STACK_T[k + 1]
        R, Tr = capy_pose(T)
        e = stack(T, R, Tr)[k]
        _, _, top, M = leaf_on(e, T)
        d = M[:, 0]
        out.append((top, np.arctan2(d[0], d[2]) - np.pi / 2, LEAF_OUT[k]))
    return out


LEAF_GO = _leaf_go()
LEAF_LAND = [STACK_T[k + 1] + next(a for a in np.arange(0.05, 5, 0.01) if leaf_height(LEAF_GO[k][0], a, 0.18, 0.70) <= LEAF_FLOAT)
             for k in range(N_STACK - 1)]

# falling leaves: all the while, leaves come drifting down out of the dark, rocking from side to
# side as they fall, and settle on the water round it

_go = [-2.0]
while _go[-1] < LOOP - 3.0:                     # one every 1.15 s; fewer once the fireworks are on
    _go.append(_go[-1] + (1.15 if _go[-1] < T_FIREWORKS[0] - 1.5 else 1.75))
N_DRIFT = len(_go)
_dr = np.random.default_rng(31).random((N_DRIFT, 8))
DRIFT_T0 = np.array(_go) + 0.4 * _dr[:, 0]                         # when each one lets go, high up
_x, _z = (_dr[:, 1] - 0.5) * 1.7, -1.2 + 2.0 * _dr[:, 2]
_near = (np.abs(_x - 0.1) < 0.45) & (np.abs(_z) < 0.55)             # none comes down through its head
_x = np.where(_near, 0.1 + np.where(_x > 0.1, 0.55, -0.55), _x)
DRIFT_P0 = np.stack([_x, 1.55 + 0.5 * _dr[:, 3], _z], 1)
DRIFT_OUT = unit(np.stack([_x - 0.1, _z], 1))                       # on the water they drift away from it
DRIFT_SPEED = 0.30 + 0.12 * _dr[:, 4]
DRIFT_YAW, DRIFT_RATE = _dr[:, 5] * TAU, 2.0 + 1.0 * _dr[:, 6]
DRIFT_RGB = [leaf_rgb(np.array(ink)) for ink in
             np.array([LEAF_INK, [0.62, 0.95, 0.25], [0.95, 0.84, 0.24]])[(_dr[:, 7] * 3).astype(int)]]   # green, lime, gold
DRIFT_LAND = DRIFT_T0 + (DRIFT_P0[:, 1] - LEAF_FLOAT) / DRIFT_SPEED


# the floating yuzu: they drop out of the dark all round it, tumbling, plunge into the water and
# bob up again; then they drift slowly round and bob, and later light up like lanterns

YUZU_AT = np.array([[-0.50, 0.30], [0.72, -0.25], [-0.74, -0.55], [0.76, -0.85], [-0.24, 0.66], [0.30, 0.62], [-0.36, -1.05]])
YUZU_R = np.array([0.080, 0.076, 0.086, 0.084, 0.068, 0.072, 0.090])
YUZU_T0 = T_YUZU[0] + (T_YUZU[1] - T_YUZU[0]) * np.array([0, 3, 5, 1, 4, 2, 6]) / 6
YUZU_LIT = T_LANTERNS[0] + (T_LANTERNS[1] - T_LANTERNS[0]) * np.array([2, 4, 0, 6, 3, 1, 5]) / 6
YUZU_PH = np.random.default_rng(15).random(N_YUZU) * TAU
YUZU_TUMBLE = unit(np.random.default_rng(18).random((N_YUZU, 3)) - 0.5)
_yz = fib_sphere(950)
YUZU_PORES = np.random.default_rng(16).random(len(_yz))


def yuzu_at(k, t):
    # where yuzu k is: falling (before YUZU_T0), then plunging under and bobbing up, then floating
    a = t - YUZU_T0[k]
    th = 0.012 * t
    x, z = YUZU_AT[k]
    x, z = x * np.cos(th) + z * np.sin(th), -x * np.sin(th) + z * np.cos(th)
    rest = 0.2 * YUZU_R[k]
    if a < 0:
        y = rest + 0.5 * GRAV * a * a
    else:
        y = rest - 0.16 * np.exp(-a / 0.3) * np.sin(8.5 * a) + 0.012 * np.sin(2.1 * t + YUZU_PH[k]) * smooth(a / 0.6)
    return np.array([x, y, z])


# ripples: rings on the water. Each spreads out from where it started: round from something
# small dropped in, and from the capybara the shape of its waterline, growing rounder as it goes

RING_LIFE, RING_SPEED = 2.6, 0.50


def capy_ring(t0, strength):
    R, T = capy_pose(t0)
    c = np.array([0, 0, -0.10]) @ R.T + T
    return (t0, c[[0, 2]], capy_yaw(t0), 0.28, 0.36, strength)


def _rings():
    R, T = capy_pose(T_PLOP)
    plop = stack(T_PLOP, R, T)[0]["centre"]
    out = [(T_PLOP, plop[[0, 2]], 0.0, 0.10, 0.10, 1.0)]
    out += [(tb + 0.15, plop[[0, 2]] + off, 0.0, 0.02, 0.02, 0.5) for tb, off in
            zip(T_BUBBLES, ([0.13, 0.05], [-0.11, 0.10], [0.02, -0.15]))]
    out += [capy_ring(t0, s) for t0, s in ((1.1, 0.8), (1.5, 0.7), (2.0, 0.6))]
    out += [capy_ring(t0, 0.45) for t0 in np.arange(BEAT0 + 1.5 * PERIOD + PERIOD, LOOP, PERIOD)]
    out += [capy_ring(T + 0.05, 0.75) for T in T_STACK]
    out += [(t0, yuzu_at(k, t0)[[0, 2]], 0.0, YUZU_R[k], YUZU_R[k], 0.8) for k, t0 in enumerate(YUZU_T0)]
    for k, tl in enumerate(LEAF_LAND):
        p, _ = leaf_flight(k, tl - STACK_T[k + 1])
        out.append((tl, p.mean(0)[[0, 2]], 0.0, 0.05, 0.05, 0.35))
    for k, tl in enumerate(DRIFT_LAND):                                  # every leaf that settles
        p, _ = leaf_drop(DRIFT_P0[k], DRIFT_YAW[k], DRIFT_OUT[k], tl - DRIFT_T0[k], 0.0, DRIFT_SPEED[k], 0.14, DRIFT_RATE[k])
        out.append((tl, p.mean(0)[[0, 2]], 0.0, 0.04, 0.04, 0.30))
    return out


RINGS = _rings()


def ring_points(t):
    out = []
    for t0, c, yaw, a0, b0, strength in RINGS:
        age = t - t0
        if not 0 < age < RING_LIFE:
            continue
        grow = RING_SPEED * age * (1 - 0.18 * age / RING_LIFE)
        fade = strength * 0.6 * (1 - age / RING_LIFE) ** 1.4 * smooth(age / 0.12)
        cy, sy = np.cos(yaw), np.sin(yaw)
        for lag, w in ((0.0, 1.0), (0.07, 0.55), (0.14, 0.3)):  # a little train of rings, the first the brightest
            g = grow - lag
            if g <= 0:
                continue
            a, b = a0 + g, b0 + g
            n = int(np.clip(300 * (a + b), 60, 1000))
            th = np.linspace(0, TAU, n, endpoint=False)
            lx, lz = a * np.cos(th), b * np.sin(th)
            out.append((np.stack([c[0] + lx * cy + lz * sy, np.zeros(n), c[1] - lx * sy + lz * cy], 1), fade * w))
    return out


# splashes: drops thrown up out of the water (or off the capybara), falling back under gravity

def spray(t0, p0, n, speed, up, spread, life, seed, g=6.0, ink=FOAM, out=None):
    rng = np.random.default_rng(seed)
    a = rng.random(n) * TAU
    s = speed * (0.5 + 0.5 * rng.random(n))
    v = np.stack([np.cos(a) * spread * s, up * s * (0.6 + 0.4 * rng.random(n)), np.sin(a) * spread * s], 1)
    if out is not None:
        v = v + out * s[:, None]
    return (t0, np.broadcast_to(np.asarray(p0, float), (n, 3)).copy(), v, life * (0.7 + 0.3 * rng.random(n)), g, ink)


def _splashes():
    R, T = capy_pose(T_PLOP)
    plop = stack(T_PLOP, R, T)[0]["centre"] * [1, 0, 1]
    out = [spray(T_PLOP, plop, 36, 1.6, 1.0, 0.45, 0.9, 1)]
    # the shake: water flies off its head and ears
    R, T = capy_pose(T_SHAKE + 0.05)
    rng = np.random.default_rng(2)
    pick = rng.choice(np.flatnonzero((CAPY_P[:, 1] > 0.22) & (CAPY_P[:, 2] > -0.3)), 30, replace=False)
    p, n = CAPY_P[pick] @ R.T + T, CAPY_N[pick] @ R.T
    out.append((T_SHAKE + 0.05, p, n * 1.1 + [0, 0.5, 0] + 0.3 * (rng.random((30, 3)) - 0.5), 0.8 + 0.3 * rng.random(30), 5.0, FOAM))
    for k, t0 in enumerate(YUZU_T0):                                    # each yuzu hitting the water
        out.append(spray(t0, yuzu_at(k, t0) * [1, 0, 1], 16, 1.3, 1.0, 0.45, 0.75, 10 + k))
    # each landing: a burst of sparkles off the top of the stack
    for j, T in enumerate(T_STACK):
        R, Tr = capy_pose(T)
        e = stack(T, R, Tr)[j + 1]
        c = e["centre"] - e["o"][:, 1] * STACK_RAD[j + 1][1]
        out.append(spray(T, c, 18, 1.0, 0.45, 1.0, 0.75, 20 + j, g=1.2, ink=WHITE))
    return out


SPLASHES = _splashes()


def _drips():
    # water running off its head as it comes up: drops that slide off and fall back in
    rng = np.random.default_rng(4)
    out = []
    cand = np.flatnonzero(CAPY_P[:, 1] > 0.12)
    for i in rng.choice(cand, 80, replace=False):
        t0 = 1.3 + 2.0 * rng.random()
        R, T = capy_pose(t0)
        p = CAPY_P[i] @ R.T + T + 0.02 * (CAPY_N[i] @ R.T)
        if p[1] > 0.03:
            out.append((t0, p))
    return out


DRIPS = _drips()


def droplets(t):
    out = []
    for t0, p0, v, life, g, ink in SPLASHES:
        a = t - t0
        if not 0 < a < life.max():
            continue
        p = p0 + v * a
        p[:, 1] -= 0.5 * g * a * a
        vy = v[:, 1] - g * a
        live = (a < life) & (p[:, 1] > 0)
        glyph = np.where(a < 0.12, C("*"), np.where(vy > 0.25, C("'"), np.where(vy < -0.25, C("."), C("+"))))
        if ink is WHITE:
            glyph = np.where(np.sin(a * 40 + np.arange(len(p))) > 0, C("*"), C("+"))
        out.append((p[live], glyph[live], np.tile(ink, (live.sum(), 1)), (1.0 - 0.6 * a / life[live]) * (0.9 if ink is FOAM else 1.2)))
    if DRIPS:
        t0 = np.array([d[0] for d in DRIPS])
        a = t - t0
        on = np.flatnonzero((a > 0) & (a < 0.6))
        if len(on):
            p = np.array([DRIPS[i][1] for i in on])
            p[:, 1] -= 0.10 * a[on] + 2.5 * a[on] ** 2
            live = p[:, 1] > 0
            out.append((p[live], np.where(a[on][live] < 0.25, C("'"), C(".")), np.tile(FOAM, (live.sum(), 1)),
                        np.full(live.sum(), 0.75)))
    # bubbles coming up just before it does
    R, T = capy_pose(T_PLOP)
    plop = stack(T_PLOP, R, T)[0]["centre"]
    for tb, off in zip(T_BUBBLES, ([0.13, 0.05], [-0.11, 0.10], [0.02, -0.15])):
        a = t - tb
        if 0 < a < 0.22:
            p = np.array([[plop[0] + off[0], 0.012, plop[2] + off[1]]])
            out.append((p, np.array([C("o") if a < 0.1 else C("O")]), FOAM[None], np.array([0.9])))
    return out


# (c) @dwcminh.ascii, see LICENSE.txt. Not for use with AI tools: no feeding this code to
# AI models, no training on it, no having an AI rework it.

# snow: the whole time, flakes drift down out of the dark and melt into the hot water; once the
# fireworks start a third of them fade away, to leave the sky to them

N_SNOW, SNOW_TOP = 260, 2.6
SNOW = np.random.default_rng(3).random((N_SNOW, 7))


def snowfall(t):
    x = -2.0 + 4.0 * SNOW[:, 0] + 0.06 * np.sin(1.1 * t + 9 * SNOW[:, 3])
    z = -2.8 + 4.6 * SNOW[:, 1] + 0.04 * np.sin(0.8 * t + 7 * SNOW[:, 4])
    y = SNOW_TOP - (SNOW[:, 5] * SNOW_TOP + t * (0.20 + 0.16 * SNOW[:, 2])) % SNOW_TOP
    thin = 1 - (SNOW[:, 6] < 0.35) * smooth((t - T_FIREWORKS[0] + 0.8) / 1.5)
    k = smooth(y / 0.10) * (0.45 + 0.45 * SNOW[:, 4]) * thin
    size = SNOW[:, 4] + 0.25 * np.sin(2.3 * t + 11 * SNOW[:, 2])
    glyph = np.where(size > 0.78, C("*"), np.where(size > 0.40, C("+"), C(".")))
    return np.stack([x, y, z], 1), glyph, np.tile(SNOW_INK, (N_SNOW, 1)), k


# steam: soft wisps curling up off the hot water the whole time

N_WISP = 10
WISP = np.random.default_rng(17).random((N_WISP, 5))
WISP_S = np.linspace(0, 1, 40)


def steam(t):
    ang = (WISP[:, 0] - 0.5) * 3.6
    rad = 0.60 + 0.80 * WISP[:, 1]
    bx, bz = rad * np.sin(ang), rad * np.cos(ang) - 0.35
    h = WISP_S[None, :] * (0.55 + 0.35 * WISP[:, 4, None])
    sway = (0.03 + 0.12 * h) * np.sin(5.5 * h - 1.6 * t + WISP[:, 2, None] * TAU)
    p = np.stack([bx[:, None] + sway, 0.02 + h + 0 * sway, bz[:, None] + 0.4 * sway], -1)
    k = 0.32 * np.sin(np.pi * WISP_S[None, :]) ** 1.2 \
        * (0.45 + 0.55 * np.sin(9 * h - 2.6 * t + WISP[:, 3, None] * TAU) ** 2) * (0.6 + 0.4 * WISP[:, 4, None])
    return p, k


# fireworks: from 10 s, shell after shell goes up over the water, left and right and far and near,
# each in its own colours; each spark is a head with a tail behind it along its own path,
# slowing, sinking, flickering out. The water below shows them again.

SHELL_AT = np.array([[-0.70, 0.88, -5.0], [0.80, 0.95, -5.4], [-0.15, 1.12, -6.4], [0.90, 1.02, -4.9],
                     [-0.72, 1.10, -5.4], [0.55, 1.20, -6.2], [-0.60, 1.20, -5.0], [0.85, 1.22, -5.2],
                     [-0.30, 1.32, -6.0], [0.75, 1.28, -5.4]])
SHELL_INK = ((GOLD, WHITE), (PINK, GOLD), (CYAN, WHITE), (EMBER, GOLD), (LIME, CYAN), (VIOLET, PINK), (RED, GOLD),
             (CYAN, PINK), (GOLD, WHITE, EMBER), tuple(SPARK_INK))
SHELLS = tuple(zip(T_FIREWORKS, SHELL_AT))
LAUNCH, DRAG, TAILS, TAIL_GAP = 0.65, 2.0, 6, 0.04
BURST_SPARKS, BURST_SPEED = 72, 2.3


def make_bursts():
    rng = np.random.default_rng(12)
    out = []
    for (tb, centre), inks in zip(SHELLS, SHELL_INK):
        way = unit(fib_sphere(BURST_SPARKS)[rng.permutation(BURST_SPARKS)] * [1, 1, 0.45])   # a ring facing us, not a ball
        vel = way * (BURST_SPEED * (0.85 + 0.30 * rng.random()) * (0.65 + 0.35 * rng.random(BURST_SPARKS)))[:, None]
        out.append((tb, centre, vel, np.array(inks)[rng.integers(0, len(inks), BURST_SPARKS)],
                    1.5 + 0.8 * rng.random(BURST_SPARKS), rng.random(BURST_SPARKS) * TAU))
    return out


BURSTS = make_bursts()


def fireworks(t, eye, basis):
    out = []
    for tb, centre in SHELLS:                                   # the shell climbing, trailing sparks
        a = t - (tb - LAUNCH)
        if 0 < a < LAUNCH:
            q = 1 - (1 - a / LAUNCH) ** 2
            path = centre * [1, 0, 1] + np.outer(np.clip(q - 0.035 * np.arange(7), 0, 1), [0, centre[1], 0])
            out.append((path, np.array([C("*")] + [C("|")] * 6), np.tile(GOLD, (7, 1)), 1.1 - 0.13 * np.arange(7)))
    for t0, start, vel, ink, life, seed in BURSTS:
        age = t - t0
        if not 0 <= age < 2.4:
            continue

        def at(x):
            p = start + vel * (1 - np.exp(-DRAG * max(x, 0.0))) / DRAG
            p[:, 1] -= 0.12 * x * x
            return p

        head, back = (at(age) - eye) @ basis.T, (at(age - TAIL_GAP) - eye) @ basis.T
        stroke = slope_char(head[:, 0] / head[:, 2] - back[:, 0] / back[:, 2], head[:, 1] / head[:, 2] - back[:, 1] / back[:, 2])
        dying = age > life - 0.6
        flick = np.where(dying, np.sin(age * 38 + seed) > -0.2, True)
        fade = np.clip((life - age) / 0.5, 0, 1) * flick
        rgb = ink + (WHITE - ink) * max(0.0, 1 - age / 0.3)
        for j in range(TAILS, 0, -1):                           # tails first, so the heads win the cell
            if age - TAIL_GAP * j > 0:
                out.append((at(age - TAIL_GAP * j), np.where(dying, C("."), stroke), rgb, fade * (0.85 - 0.14 * j)))
        out.append((at(age), np.where(dying, C("+"), C("*")), rgb, fade * 1.3))
    return out


# the sky: sparse stars, far away above the far shore of the water

N_STARS = 170
_st = np.random.default_rng(23).random((N_STARS, 4))
_az, _el = (_st[:, 0] - 0.5) * 1.6, 0.012 + 0.55 * _st[:, 1] ** 1.4
STAR_DIR = np.stack([np.sin(_az) * np.cos(_el), np.sin(_el), -np.cos(_az) * np.cos(_el)], 1)


# camera: a little above the water, looking down at the capybara across it; it rises with it as
# it comes up, then backs away and tips up as the stack grows, and drifts a little side to side

KEY = unit([0.20, 0.75, 0.65])                  # from up in front, so its face is lit whichever way it turns
ZOOM = 4.0


def camera(t):
    q1 = smooth((t - 0.4) / 2.6)
    q2 = smooth((t - 5.8) / 7.0)
    q3 = smooth((t - 13.0) / 5.0)
    target = np.array([0.0, 0.12 + 0.20 * q1 + 0.22 * q2 + 0.04 * q3, -0.15])
    dist = 2.9 + 0.30 * q1 + 0.70 * q2 + 0.20 * q3
    el = 0.20 + 0.03 * q2
    az = 0.10 * np.sin(TAU * t / 26 + 0.8)
    eye = target + dist * np.array([np.sin(az) * np.cos(el), np.sin(el), np.cos(az) * np.cos(el)])
    fwd = unit(target - eye)
    right = unit(np.cross(fwd, [0, 1.0, 0]))
    return eye, np.stack([right, np.cross(right, fwd), fwd])


def project(eye, basis, p, cols, rows, aspect):
    c = (np.asarray(p, float) - eye) @ basis.T
    z = c[..., 2]
    zz = np.maximum(z, 0.2)
    return (0.5 + c[..., 0] / zz * ZOOM * 0.5) * cols, (0.5 - c[..., 1] / zz * ZOOM * 0.5 * aspect) * rows, z


def strokes(p, eye, basis, axis):
    # the letter for a line of points, drawn along its own direction on screen
    c = (p - eye) @ basis.T
    px, py = c[..., 0] / c[..., 2], c[..., 1] / c[..., 2]
    if axis == "ring":
        return slope_char(np.roll(px, -1) - np.roll(px, 1), np.roll(py, -1) - np.roll(py, 1))
    return slope_char(np.gradient(px, axis=axis), np.gradient(py, axis=axis))


def scene(t, eye, basis):
    # everything above the water at time t: points with brightness, colour, part and glyph
    R, T = capy_pose(t)
    P, L, RGBs, PRT, G = [], [], [], [], []
    flares = []                                                 # (point, reach, strength, colour)

    def add(p, lum, rgb, part, glyph=None):
        keep = p[:, 1] > 0                                      # under the water nothing shows
        P.append(p[keep]), L.append(np.asarray(lum)[keep]), RGBs.append(np.asarray(rgb)[keep])
        PRT.append(np.full(keep.sum(), part) if np.ndim(part) == 0 else part[keep])
        G.append(np.full(keep.sum(), -1) if glyph is None else np.asarray(glyph)[keep])

    def shade(p, n, base, diff, spec, power=16, rim=0.22):
        # one direction to the eye for the whole object: it is small next to how far away we are
        if len(p) == 0:
            return np.zeros(0)
        v = unit(eye - p.mean(0))
        nv = n @ v
        n = n * np.where(nv < 0, -1.0, 1.0)[:, None]                   # sheets are lit on both sides
        return base + diff * np.clip(n @ KEY, 0, 1) + spec * np.clip(n @ unit(KEY + v), 0, 1) ** power \
            + rim * (1 - np.abs(nv)) ** 2

    # fur: drops of water glisten in it while it comes up and dry off after. In the yawn its jaw
    # swings open, and the inside of its mouth and its big front teeth show
    gape = JAW_OPEN * yawn(t)
    local, nrm = open_jaw(CAPY_P, CAPY_N, CAPY_JAW, gape) if gape > 0 else (CAPY_P, CAPY_N)
    p = local @ R.T + T
    up = np.flatnonzero(p[:, 1] > 0)
    p, n = p[up], nrm[up] @ R.T
    lum = shade(p, n, 0.68, 0.42, 0.28) - 0.18 * (CAPY_PART[up] == BACK) \
        + 0.22 * np.clip(-n[:, 1], 0, 1)                       # warm light off the water under its chin
    rgb = FUR_RGB[up].copy()
    glyph = np.full(len(up), -1)
    wet = 1 - smooth((t - 2.6) / 1.2)
    if wet > 0.01:
        on = GLISTEN[up] & (np.sin(9 * t + GLISTEN_PH[up]) > 0.75)
        glyph[on], lum[on] = C("*"), 0.9 + 0.4 * wet
        rgb[on] = rgb[on] + (WHITE - rgb[on]) * wet
    add(p, lum, rgb, CAPY_PART[up], glyph)
    waterline = p[p[:, 1] < 0.016]
    if gape > 0.01:
        q, m = open_jaw(MOUTH_P, MOUTH_N, MOUTH_JAW, gape)
        q, m = q @ R.T + T, m @ R.T
        add(q, 0.65 * shade(q, m, 0.45, 0.35, 0.15), MOUTH_RGB, INSIDE)
        for (tp, tn), w in ((TEETH_UP, 0.0), (TEETH_DOWN, 1.0)):
            q, m = open_jaw(tp, tn, np.full(len(tp), w), gape)
            q, m = q @ R.T + T, m @ R.T
            add(q, shade(q, m, 0.75, 0.30, 0.40), np.tile(TOOTH_INK, (len(q), 1)), TEETH)

    # ears
    for side in range(2):
        u, v, w = EAR_UVW[side]
        Rk = rot_axis(u, ear_angle(t, side))
        p = (EAR_BASE[side] + (EAR_Q @ EAR_UVW[side] + v * 0.045) @ Rk.T) @ R.T + T
        n = (EAR_QN @ EAR_UVW[side]) @ Rk.T @ R.T
        lum = shade(p, n, 0.50, 0.42, 0.25) - 0.18 * EAR_INNER
        add(p, lum, np.where(EAR_INNER[:, None], EAR_INK, FUR_INK), EAR)

    # eyes: open, a happy squint, shut, or half shut and drowsy
    state = eye_state(t)
    if state in ("open", "sleepy"):
        p = (EYE_P if state == "open" else EYE_P[EYE_LOW]) @ R.T + T
        add(p, np.full(len(p), 0.2), np.tile(EYE_INK, (len(p), 1)), EYE)
    if state == "open":
        for c, n in zip(EYE_C @ R.T + T, EYE_N @ R.T):
            g = c + (EYE_R + 0.012) * unit(n + 0.8 * KEY + 0.6 * unit(eye - c))
            add(g[None], [1.35], [WHITE], MARK, [C("o")])
            a = t - (T_ROUSE if t >= T_ROUSE else T_WAKE)      # its eyes sparkle as they open
            if a < 0.5:
                flares.append((g, int(2 + 4 * (1 - a / 0.5)), 1 - a / 0.5, WHITE))
    else:
        arcs = {"happy": LID_HAPPY, "shut": LID_SHUT, "sleepy": LID_SLEEPY}[state] @ R.T + T
        glyph = strokes(arcs, eye, basis, 1)
        add(arcs.reshape(-1, 3), np.full(arcs.size // 3, 0.12), np.tile(EYE_INK, (arcs.size // 3, 1)), MARK, glyph.ravel())

    # nostrils and mouth: dark strokes (the line of the mouth is gone while it is wide open)
    for lines in (NOSTRILS, MOUTH if gape < 0.03 else MOUTH[:1]):
        p = lines @ R.T + T
        glyph = strokes(p, eye, basis, 1)
        add(p.reshape(-1, 3), np.full(p.size // 3, 0.12), np.tile(EYE_INK, (p.size // 3, 1)), MARK, glyph.ravel())

    # the stack of oranges, each with its leaf while it is on top
    entries = stack(t, R, T)
    for e in entries:
        k = e["k"]
        op, nrm, groove, pores, ey = ORANGES[k]
        sc = np.array([1 / np.sqrt(e["sq"]), e["sq"], 1 / np.sqrt(e["sq"])]) * e["scale"]
        p = (op * sc) @ e["o"].T + e["centre"]
        n = unit(nrm / sc) @ e["o"].T
        lum = shade(p, n, 0.52, 0.45, 0.55, 22) + 0.10 * (pores - 0.5) - 0.20 * groove
        rgb = np.where((ey > 0.955)[:, None], STEM_INK, STACK_INK[k])
        rgb = rgb + (WHITE - rgb) * np.clip(lum - 1.0, 0, 0.5)[:, None]
        rgb, lum = rgb + (WHITE - rgb) * 0.85 * min(e["hot"], 1.0), lum + 0.4 * e["hot"]
        add(p, lum, rgb, ORANGE + k)
        if k == N_STACK - 1 or t < STACK_T[k + 1]:
            p, n, _, _ = leaf_on(e, t)
            add(p, shade(p, n, 0.55, 0.40, 0.35), LEAF_RGB * (1 + 0.6 * min(e["hot"], 1.0)), LEAF)
        if e["landed"] and k > 0 and t - STACK_T[k] < 0.45:     # it lands: a flare where it touches
            s = 1 - (t - STACK_T[k]) / 0.45
            flares.append((e["centre"] - e["o"][:, 1] * STACK_RAD[k][1] * 0.8, int(2 + 6 * s), s, WHITE))
    leaves = 1
    for k in range(N_STACK - 1):                                # leaves knocked off: fluttering, then floating
        if STACK_T[k + 1] < t < LEAF_LAND[k] + LEAF_STAY + 1.0:
            p, n = leaf_flight(k, t - STACK_T[k + 1])
            add(p, shade(p, n, 0.50, 0.40, 0.30), LEAF_RGB * 0.9, LEAF)
            leaves += 1

    # leaves drifting down out of the dark, and floating on the water
    for k in range(N_DRIFT):
        a = t - DRIFT_T0[k]
        if a > 0 and t < DRIFT_LAND[k] + LEAF_STAY + 1.0:
            p, n = leaf_drop(DRIFT_P0[k], DRIFT_YAW[k], DRIFT_OUT[k], a, 0.0, DRIFT_SPEED[k], 0.14, DRIFT_RATE[k])
            add(p, shade(p, n, 0.50, 0.40, 0.30), DRIFT_RGB[k], LEAF)
            leaves += 1

    # the start: a spark falling out of the dark; then the plop
    if t < 0.45:
        s = 1 - t / 0.45
        flares.append((entries[0]["centre"], int(2 + 7 * s), s, WHITE))
    if 0 < t - T_PLOP < 0.45:
        s = 1 - (t - T_PLOP) / 0.45
        flares.append((entries[0]["centre"] * [1, 0, 1] + [0, 0.02, 0], int(3 + 6 * s), s, WHITE))

    # floating yuzu: they drop in tumbling, flash as they hit the water, drift and bob; later each
    # lights up like a lantern
    landed = 0
    for k in range(N_YUZU):
        a = t - YUZU_T0[k]
        if a < -YUZU_FALL:
            continue
        landed += a >= 0
        c = yuzu_at(k, t)
        r = YUZU_R[k]
        o = rot_y(YUZU_PH[k] + 0.3 * t) @ rot_x(0.15 * np.sin(1.7 * t + YUZU_PH[k]))
        if a < 0:
            o = o @ rot_axis(YUZU_TUMBLE[k], 6.0 * a)
        p = (_yz * [r, 0.92 * r, r]) @ o.T + c
        n = unit(_yz / [1, 0.92, 1]) @ o.T
        lum = shade(p, n, 0.50, 0.45, 0.50, 20) + 0.10 * (YUZU_PORES - 0.5)
        rgb = np.where((_yz[:, 1] > 0.95)[:, None], STEM_INK, YUZU_INK)
        lit = smooth((t - YUZU_LIT[k]) / 0.25)
        if lit > 0:                                             # a lantern now: glowing gold right through
            twinkle = 0.5 + 0.5 * np.sin(5 * t + 2.4 * k)
            lum = np.maximum(lum, 0.9) + lit * (0.45 + 0.15 * twinkle)
            rgb = rgb + (PALE(GOLD, 0.20) - rgb) * 0.8 * lit
            b = t - YUZU_LIT[k]
            if b < 0.5:
                flares.append((c + [0, r, 0], int(2 + 5 * (1 - b / 0.5)), 1 - b / 0.5, WHITE))
            elif twinkle > 0.985:
                flares.append((c + [0, r, 0], 3, 0.5, GOLD))
        hot = float(np.clip(1 - a / FLASH, 0, 1) ** 2) if a > 0 else 0.0
        rgb, lum = rgb + (WHITE - rgb) * 0.85 * hot, lum + 0.4 * hot
        add(p, lum, rgb, YUZU + k)
        if 0 < a < 0.35:                                        # the splash: a flare on the water
            s = 1 - a / 0.35
            flares.append((c * [1, 0, 1] + [0, 0.02, 0], int(2 + 5 * s), s, WHITE))

    beats = int((t - 2.2) / PERIOD) + 1 if t > 2.2 else 0
    oranges = sum(e["landed"] for e in entries)
    info = {"bobs": beats, "oranges": int(oranges), "yuzu": int(landed), "leaves": leaves}
    return [np.concatenate(a) for a in (P, L, RGBs, PRT, G)], waterline, flares, info


# (c) @dwcminh.ascii, see LICENSE.txt. Not for use with AI tools: no feeding this code to
# AI models, no training on it, no having an AI rework it.

_HASH = {}


def HASH(rows, cols):
    # scattered, not in a pattern: on a big even patch of fur a regular one shows up as stripes
    if (rows, cols) not in _HASH:
        _HASH[rows, cols] = np.random.default_rng(97).integers(0, 9973, (rows, cols))
    return _HASH[rows, cols]


def bodies(sx, sy, z, lum, rgb, part, glyph, dim, cols, rows, t, outline=True, sparse=0):
    # nearest point per cell; outlines where a part meets empty water or another part further back,
    # marks keep their own glyph, the rest is filled with letters chosen by brightness
    if len(sx) == 0:
        return np.zeros((rows, cols), int), np.zeros((rows, cols, 3)), np.full((rows, cols), np.inf)
    ok = np.flatnonzero((sx >= 0) & (sx < cols) & (sy >= 0) & (sy < rows) & (z > 0.3))
    order = ok[np.argsort(-z[ok])]
    gi = np.full((rows, cols), -1)
    gi[sy[order].astype(int), sx[order].astype(int)] = order
    body = gi >= 0
    g = np.maximum(gi, 0)
    prt = np.where(body, part[g], -1)
    dep = np.where(body, z[g], np.inf)
    own = np.where(body, glyph[g], -1)
    solid = body & (own < 0)                                    # marks never get an outline of their own
    edge = np.zeros_like(body)
    gx, gy = np.zeros((rows, cols)), np.zeros((rows, cols))
    if outline:
        pp, pd = np.pad(prt, 1, constant_values=-1), np.pad(dep, 1, constant_values=np.inf)
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dx == dy == 0:
                    continue
                nb, nz = pp[1 + dy:rows + 1 + dy, 1 + dx:cols + 1 + dx], pd[1 + dy:rows + 1 + dy, 1 + dx:cols + 1 + dx]
                other = (nb >= 0) & (nb != prt) & (nb != MARK)
                seam = HARD[np.maximum(prt, 0)] & other & HARD[np.maximum(nb, 0)] & (prt < nb)
                out = solid & ((nb < 0) | (other & (nz > dep + 0.035)) | seam)
                gx += dx * out
                gy += dy * out
                if dx == 0 or dy == 0:
                    edge |= out
    h = HASH(rows, cols)
    L = np.where(body, lum[g], 0.0)
    level = np.clip(((L - 0.42) * 4.6).astype(int) - sparse, 0, 3)
    inside = FILL[level, (h + (t * 4 + h % 11).astype(int)) % 12]
    char = np.where(body, np.where(own >= 0, own, np.where(edge, outline_letter(gx, gy), inside)), 0)
    bright = np.where(own >= 0, L, np.where(edge, np.maximum(0.85, L), np.clip(0.45 + 0.55 * L / 0.9, 0.45, 1.0)))
    col = np.where(body[..., None], rgb[g] * (np.minimum(bright, 1.4) * dim[g])[..., None], 0.0)
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
    if col[cy, cx].max() < 1.3 * strength:                     # a fading flare never dims what is under it
        put(char, col, cy, cx, "*", rgb, 1.3 * strength)


def dots(char, col, dep, sx, sy, z, glyph, rgb, k, slack=0.0, soft=False):
    # loose points of light, hidden where something stands in front of them
    rows, cols = char.shape
    ix, iy = np.floor(sx).astype(int), np.floor(sy).astype(int)
    glyph = np.broadcast_to(glyph, ix.shape)
    k = np.broadcast_to(k, ix.shape)
    ok = np.flatnonzero((ix >= 0) & (ix < cols) & (iy >= 0) & (iy < rows) & (k > 0.04) & (z > 0.3))
    ok = ok[z[ok] < dep[iy[ok], ix[ok]] + slack]
    if soft:                                                    # only where it is brighter than what is there
        ok = ok[col[iy[ok], ix[ok]].max(-1) < k[ok] * rgb[ok].max(-1) * 0.9]
    ok = ok[np.argsort(k[ok])]                                  # the brightest drawn last
    char[iy[ok], ix[ok]] = glyph[ok]
    col[iy[ok], ix[ok]] = rgb[ok] * k[ok, None]
    return int(((glyph[ok] == C("*")) & (k[ok] > 0.3)).sum())


def frame(t, cols, rows, aspect):
    eye, basis = camera(t)
    (P, L, RGB, PRT, G), waterline, flares, info = scene(t, eye, basis)
    sx, sy, z = project(eye, basis, P, cols, rows, aspect)
    char, col, dep = bodies(sx, sy, z, L, RGB, PRT, G, np.ones(len(P)), cols, rows, t)
    real = char > 0

    # the reflection: everything above the water, upside down in it, dim and wavering
    m = slice(None, None, 3)                                    # a third of the points will do, it wavers anyway
    Pm, h = P[m] * [1, -1, 1], P[m, 1]
    sx, sy, z = project(eye, basis, Pm, cols, rows, aspect)
    sx = sx + 0.55 * np.sin(0.9 * sy + 2.3 * t) + 0.30 * np.sin(2.6 * sy - 3.1 * t + 1.0)
    glyph = np.where(G[m] == C("*"), -1, G[m])
    rgb = RGB[m] * 0.8 + WATER * 0.2 * RGB[m].max(-1, keepdims=True)
    cm, colm, depm = bodies(sx, sy, z, L[m], rgb, PRT[m], glyph, 0.36 * np.exp(-h / 0.8), cols, rows, t, False, 1)
    r, c = np.ogrid[0:rows, 0:cols]
    colm = colm * (0.68 + 0.32 * np.sin(1.9 * r + 2.4 * t + 0.8 * np.sin(0.23 * c - 1.1 * t)))[..., None]
    char = np.where(real, char, cm)
    col = np.where(real[..., None], col, colm)
    dep = np.where(real, dep, depm)

    # stars, only where nothing else is
    sc = STAR_DIR @ basis.T
    ok = sc[:, 2] > 0.05
    ix = ((0.5 + sc[ok, 0] / sc[ok, 2] * ZOOM * 0.5) * cols).astype(int)
    iy = ((0.5 - sc[ok, 1] / sc[ok, 2] * ZOOM * 0.5 * aspect) * rows).astype(int)
    tw = (0.5 + 0.5 * np.sin(t * (0.8 + 2.2 * _st[ok, 2]) + _st[ok, 3] * 40))
    size = _st[ok, 3] * tw
    inside = (ix >= 0) & (ix < cols) & (iy >= 0) & (iy < rows)
    ix, iy, size = ix[inside], iy[inside], size[inside]
    free = char[iy, ix] == 0
    char[iy[free], ix[free]] = np.array([C("."), C("."), C("+"), C("*")])[np.clip((size[free] * 4.4).astype(int), 0, 3)]
    col[iy[free], ix[free]] = STAR_INK * (0.14 + 0.40 * size[free])[:, None]

    # steam, softly, in front of the water
    p, k = steam(t)
    g = strokes(p, eye, basis, 1).ravel()
    sx, sy, z = project(eye, basis, p.reshape(-1, 3), cols, rows, aspect)
    blank = np.where(real, -np.inf, dep)
    dots(char, col, blank, sx, sy, z, g, np.tile(STEAM_INK, (len(g), 1)), k.ravel(), soft=True)

    lights = 0
    # fireworks, and their reflection in the water
    shots = fireworks(t, eye, basis)
    for p, glyph, rgb, k in shots:
        sx, sy, z = project(eye, basis, p * [1, -1, 1], cols, rows, aspect)
        sx = sx + 0.55 * np.sin(0.9 * sy + 2.3 * t)
        rgb = np.broadcast_to(rgb, (len(p), 3))
        dots(char, col, dep, sx, sy, z, np.where(glyph == C("*"), C("+"), glyph), rgb, np.asarray(k) * 0.35, soft=True)

    # rings on the water
    for p, k in ring_points(t):
        sx, sy, z = project(eye, basis, p, cols, rows, aspect)
        dots(char, col, dep, sx, sy, z, strokes(p, eye, basis, "ring"), np.tile(WATER, (len(p), 1)), k)

    # the waterline round the capybara: water lapping at its fur (it sparkles while it comes up)
    if len(waterline):
        sx, sy, z = project(eye, basis, waterline, cols, rows, aspect)
        rising = 1 - smooth((t - 2.4) / 0.8)
        n = np.arange(len(waterline))
        glyph = np.where((rising > 0.1) & (np.sin(13 * t + n * 2.7) > 0.3), C("*"), np.where(np.sin(4 * t + n) > 0, C("~"), C("-")))
        dots(char, col, dep, sx, sy, z, glyph, np.tile(PALE(FOAM, 0.6 * rising), (len(n), 1)), 0.65 + 0.5 * rising, slack=0.02)

    # drops, snow, sparks
    flakes = snowfall(t)
    for p, glyph, rgb, k in droplets(t) + [flakes] + shots:
        if len(p) == 0:
            continue
        sx, sy, z = project(eye, basis, p, cols, rows, aspect)
        lights += dots(char, col, dep, sx, sy, z, glyph, np.broadcast_to(rgb, (len(p), 3)), np.asarray(k, float))
    for tb, centre in SHELLS:
        pop = float(np.clip(1 - (t - tb) / 0.5, 0, 1)) if t >= tb else 0.0
        if pop > 0.05:
            flares.append((centre, int(3 + 8 * pop), pop, WHITE))

    # flares: the first spark, the plop, eyes opening, each landing and pop, lanterns, shells
    for p, reach, strength, rgb in flares:
        sx, sy, z = project(eye, basis, np.asarray(p, float)[None], cols, rows, aspect)
        y, x = int(sy[0]), int(sx[0])
        if 0 <= y < rows and 0 <= x < cols:
            rays(char, col, y, x, reach, rgb, strength)

    info.update(snow=int((flakes[3] > 0.05).sum()), sparks=lights, letters=int((char > 0).sum()))
    return char, col, info


# window: small letters, so its face has room for its features

TITLE = "ASCII Capybara"
CW, CH, FONT_PX = 7, 10, 11
COLS, ROWS = 113, 103
W, H = COLS * CW, ROWS * CH
MONO = "consolas,menlo,dejavusansmono,couriernew,monospace"
HINT = "Space pause · R restart · S screenshot · Esc quit"
DIM, ACCENT, SIGN = (100, 112, 136), (255, 170, 80), (170, 184, 214)
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

    def draw(self, t):
        w, h = self.w, self.h
        char, col, info = frame(t, self.cols, self.rows, w / h)
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
        lines = [f"bobs {info['bobs']:>2}    oranges {info['oranges']}    yuzu {info['yuzu']}    leaves {info['leaves']:>2}"
                 f"    snow {info['snow']:>3}    sparks {info['sparks']:>3}",
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
                pygame.image.save(screen, str(Path(__file__).with_name(f"capybara_{int(time.time())}.png")))
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
