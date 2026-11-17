# The Heart in ASCII
# @dwcminh.ascii, 2026
#
#   pip install numpy pygame-ce
#   python heart.py
#
# The famous Valentine's graph  y = x^(2/3) + 0.9 sin(kx) sqrt(3 - x^2)  drawn in letters. At k = 0
# it is a plain V on the axes; as k climbs to 100 the sine wiggles faster and faster inside the
# heart-shaped envelope, the strokes / | \ crowd together, and the curve condenses into a solid
# red heart of letters. At k = 100, once, a white pulse with a flare at its head sweeps across the
# finished heart and sparks burst out of it; then sparkles twinkle on it.
#
# Space pause, R restart, S screenshot, Esc quit

import sys
import time
from pathlib import Path

import numpy as np
import pygame

CREDIT = "@dwcminh.ascii"
HERE = Path(__file__).parent

TAU = np.pi * 2
LOOP = 20.0                                     # length of one run (s)

# timeline (s)
T_K = (0.3, 11.4)                               # k climbs 0 -> 100: slowly, then fast, then creeping up on 100
T_LOCK = 11.5                                   # k = 100: one white pulse sweeps the heart, sparks burst out
PULSE = 0.9                                     # how long the pulse takes to cross the heart (s)
T_SPARKLE = 12.6                                # sparkles twinkle on the heart
T_GLEAM = (15.2, 16.6)                          # a band of light runs across the heart

# the curve
AMP = 0.9                                       # y = x^(2/3) + AMP sin(kx) sqrt(3 - x^2)
R3 = np.sqrt(3.0)                               # it lives on -sqrt(3) <= x <= sqrt(3)
K_START, K_END = 0.15, 100.0
MIDDLE_Y = 0.36                                 # the heart's middle (graph units), where the sparks fly from
UNIT = 160                                      # px per graph unit, at 1036 px high
ORIGIN_ROW = 37 / 74                            # the x axis sits on this share of the rows

# colours: 0..1 for letters, 0..255 for text
HEART = np.array([1.0, 0.13, 0.24])             # the solid heart
LINE = np.array([1.0, 0.30, 0.38])              # the curve while it is still a line
EDGE = np.array([1.0, 0.60, 0.66])              # the heart's outline
PINK = np.array([1.0, 0.45, 0.62])              # sparks cooling down
WHITE = np.array([1.0, 0.97, 0.94])
# the stars in the black all round: mostly white glints, some pink, blue and gold (as in ROSE-BOUQUET)
STAR_COLOURS = np.array([[1.0, 1.0, 1.0], [1.0, 0.59, 0.75], [0.67, 0.80, 1.0], [1.0, 0.84, 0.59]])
N_STARS = 220
STAR_FLARES = 3                                 # how many of the brightest stars throw rays at once
AXIS, NUMBERS = 0.36, 0.50                      # grey levels of the axes and their numbers
EQ_C, K_C = (206, 108, 120), np.array([236, 120, 134])
DIM, ACCENT, SIGN = (118, 104, 112), (255, 112, 140), (190, 170, 182)

POOLS = ["1il!;:", "rtfjcvxz=+", "aeoun0{}[]<>", "08B$#&%Q"]   # fill letters, dark -> bright
C = lambda ch: ord(ch) - 32                     # character -> glyph index
FILL = np.array([[C(p[k % len(p)]) for k in range(12)] for p in POOLS])
SLOPE = np.array([C(c) for c in "-/|\\-"])
MONO = "consolas,menlo,dejavusansmono,couriernew,monospace"
MATH, MATH_ITALIC = "C:/Windows/Fonts/times.ttf", "C:/Windows/Fonts/timesi.ttf"


def smooth(x):
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3 - 2 * x)


def k_at(t):
    # k over time: smootherstep, so it starts slowly and creeps up on 100 at the end, as in the video
    u = np.clip((np.asarray(t, float) - T_K[0]) / (T_K[1] - T_K[0]), 0.0, 1.0)
    return K_START + (K_END - K_START) * u ** 3 * (u * (6 * u - 15) + 10)


def envelope(x):
    # the heart the curve fills: below and above the line x^(2/3)
    base = np.cbrt(x * x)
    a = AMP * np.sqrt(np.clip(3 - x * x, 0, None))
    return base - a, base + a


def box3(a):
    # sum over each cell and its 8 neighbours
    p = np.pad(a, 1)
    return sum(p[1 + dy:p.shape[0] - 1 + dy, 1 + dx:p.shape[1] - 1 + dx] for dy in (-1, 0, 1) for dx in (-1, 0, 1))


def slope_char(dx, dy):
    # screen direction (y up) -> the ASCII stroke that looks most like it
    ang = np.degrees(np.arctan2(dy, dx)) % 180
    return SLOPE[np.digitize(ang, [25, 72, 108, 155])]


def font_file(paths):
    for p in paths:
        if Path(p).exists():
            return p
    return None


class Grid:
    # the letters of one frame: a character and a colour per cell, and whether it may leave a trail
    def __init__(self, rows, cols):
        self.char = np.zeros((rows, cols), int)
        self.col = np.zeros((rows, cols, 3))
        self.moving = np.zeros((rows, cols), bool)

    def put(self, r, c, glyph, rgb, moving=False):
        rows, cols = self.char.shape
        r, c = np.atleast_1d(np.asarray(r, int)), np.atleast_1d(np.asarray(c, int))
        glyph = np.broadcast_to(np.asarray(glyph), r.shape)
        rgb = np.broadcast_to(np.asarray(rgb, float), r.shape + (3,))
        ok = (r >= 0) & (r < rows) & (c >= 0) & (c < cols)
        self.char[r[ok], c[ok]] = glyph[ok]
        self.col[r[ok], c[ok]] = rgb[ok]
        self.moving[r[ok], c[ok]] = moving


# the window

CW, CH, FONT_PX = 9, 14, 15
COLS, ROWS = 88, 74                             # 792 x 1036 px


class Renderer:
    def __init__(self, cols=COLS, rows=ROWS, cw=CW, ch=CH, font_px=FONT_PX, hud_px=15, hint=True):
        pygame.font.init()
        self.cols, self.rows, self.cw, self.ch = cols, rows, cw, ch
        self.w, self.h = cols * cw, rows * ch
        self.s = s = self.h / 1036
        self.unit = UNIT * s
        self.c0, self.r0 = cols // 2, round(rows * ORIGIN_ROW)
        self.ox, self.oy = (self.c0 + 0.5) * cw, (self.r0 + 0.5) * ch     # the origin, on a cell's middle
        font = pygame.font.SysFont(MONO, font_px, bold=True)
        cells = []
        for code in range(32, 127):
            surf = pygame.Surface((cw, ch))
            g = font.render(chr(code), True, (255, 255, 255))
            surf.blit(g, ((cw - g.get_width()) // 2, (ch - g.get_height()) // 2))
            cells.append(pygame.surfarray.array3d(surf).transpose(1, 0, 2)[..., 0])
        self.atlas = np.stack(cells)
        self.greys = [(i, i, i) for i in range(256)]
        w, h = self.w, self.h
        self.art, self.trail, self.out = pygame.Surface((w, h)), pygame.Surface((w, h)), pygame.Surface((w, h))
        self.tint = pygame.Surface((cols, rows))
        self.moving_s, self.still_s = pygame.Surface((w, h)), pygame.Surface((w, h))
        self.hint = hint
        self.last_t = None
        self.small = pygame.font.SysFont(MONO, hud_px)
        self.hud_gap = int(hud_px * 1.45)

        rng = np.random.default_rng(14)
        self.hash = rng.integers(0, 9973, (rows, cols))                # each cell's own letter, no stripes
        self.rand = rng.random((rows, cols))                           # each cell's turn to condense
        gr, gc = np.mgrid[0:rows, 0:cols]
        self.px, self.py = (gc + 0.5) * cw, (gr + 0.5) * ch
        self.gx, self.gy = (self.px - self.ox) / self.unit, (self.oy - self.py) / self.unit
        # the light on the heart: a highlight on each lobe, brighter at the top than at the tip
        gx, gy = self.gx, self.gy
        self.light = (0.32 * np.clip((gy + 1.6) / 3.8, 0, 1)
                      + 0.38 * (np.exp(-((gx + 0.72) ** 2 + (gy - 1.62) ** 2) / 0.30)
                                + 0.6 * np.exp(-((gx - 0.78) ** 2 + (gy - 1.66) ** 2) / 0.40)))

        self.axes_layer()
        self.make_stars(rng)
        self.make_sparks(rng)
        self.make_sparkles(rng)

        self.eq_up = pygame.font.Font(font_file([MATH]), round(36 * s))
        self.eq_it = pygame.font.Font(font_file([MATH_ITALIC, MATH]), round(36 * s))
        self.eq_sup = pygame.font.Font(font_file([MATH]), round(22 * s))
        self.k_up = pygame.font.Font(font_file([MATH]), round(34 * s))
        self.k_it = pygame.font.Font(font_file([MATH_ITALIC, MATH]), round(34 * s))
        self.equation = self.equation_surface()

    # setup: the axes, stars, sparks and sparkle spots (made once)

    def axes_layer(self):
        # the graph's axes in letters: - and | with + at each unit, arrowheads, and the numbers
        rows, cols, c0, r0 = self.rows, self.cols, self.c0, self.r0
        char, lum = np.zeros((rows, cols), int), np.zeros((rows, cols))
        u = self.unit
        char[r0, 2:cols - 2] = C("-")
        char[r0, cols - 3] = C(">")
        top, bottom = int((self.oy - 2.62 * u) / self.ch), int((self.oy + 1.82 * u) / self.ch)
        char[top:bottom + 1, c0] = C("|")
        char[top, c0] = C("^")
        lum[char > 0] = AXIS
        for i in (-2, -1, 1, 2):
            c = int((self.ox + i * u) / self.cw)
            char[r0, c] = C("+")
            label = str(i)
            for j, letter in enumerate(label):
                char[r0 + 1, c - len(label) + 1 + j] = C(letter)
                lum[r0 + 1, c - len(label) + 1 + j] = NUMBERS
        for i in (-1, 1, 2):
            r = int((self.oy - i * u) / self.ch)
            char[r, c0] = C("+")
            label = str(i)
            for j, letter in enumerate(label):
                char[r, c0 - 1 - len(label) + j] = C(letter)
                lum[r, c0 - 1 - len(label) + j] = NUMBERS
        char[r0, c0] = C("+")
        self.axis_char, self.axis_lum = char, lum

    def make_stars(self, rng):
        # the stars: where each starts, how fast it rises, its own beat, how bright it rests, its colour
        g = rng.random((N_STARS, 6))
        self.star_seed = g
        self.star_kind = np.select([g[:, 5] < 0.10, g[:, 5] < 0.17, g[:, 5] < 0.22], [1, 2, 3], 0)

    def stars(self, g_, t):
        # stars all round, rising very slowly: each is faint most of the time and flares up for a
        # moment on its own beat; the brightest throw four-pointed rays. Kept off the equation and HUD
        g = self.star_seed
        top = 0.78 * self.rows
        x = (g[:, 0] * self.cols + 0.6 * np.sin(t * 0.5 + g[:, 4] * TAU)) % self.cols
        y = top * ((g[:, 1] - t * 0.006 * (0.5 + g[:, 3])) % 1.0)
        beat = 2.5 + 4.5 * g[:, 3]                                      # seconds between its flares
        peak = np.clip(1 - np.abs((t / beat + g[:, 2]) % 1.0 - 0.5) * beat / 0.24, 0, 1)
        s = 0.15 + 0.20 * g[:, 4] + peak ** 1.5                          # mostly a faint dot
        glyph = np.where(s > 0.8, C("*"), np.where(s > 0.5, C("+"), C(".")))
        rgb = STAR_COLOURS[self.star_kind] * np.clip(0.2 + 0.8 * s, 0, 1.0)[:, None]
        r, c = y.astype(int), x.astype(int)
        g_.put(r, c, glyph, rgb, moving=True)
        hot = np.flatnonzero(s > 0.9)
        for j in hot[np.argsort(-s[hot])[:STAR_FLARES]]:
            self.cell_rays(g_, r[j], c[j], int(1 + 3 * min(s[j], 1.2) ** 2 / 1.2), STAR_COLOURS[self.star_kind[j]], 0.5 * min(s[j], 1.2))

    @staticmethod
    def cell_rays(g, cy, cx, reach, rgb, strength):
        # a four-pointed flare in letters: long arms - and |, short diagonals; an arm only shows where
        # it outshines what is there
        rows, cols = g.char.shape
        for dist in range(1, reach + 1):
            fade = (1 - dist / (reach + 1)) * strength
            arms = [(0, 1, "-"), (0, -1, "-"), (1, 0, "|"), (-1, 0, "|")]
            if dist <= reach // 2:
                arms += [(1, 1, "\\"), (-1, -1, "\\"), (1, -1, "/"), (-1, 1, "/")]
            for dy, dx, stroke in arms:
                yy, xx = cy + dy * dist, cx + dx * dist * (2 if dy == 0 else 1)
                k = fade * (0.7 if dx and dy else 1.0)
                if 0 <= yy < rows and 0 <= xx < cols and g.col[yy, xx].max() < k:
                    g.char[yy, xx], g.col[yy, xx], g.moving[yy, xx] = C(stroke), rgb * k, True
        if 0 <= cy < rows and 0 <= cx < cols:
            g.char[cy, cx], g.col[cy, cx] = C("*"), rgb * 1.3 * strength

    def inside_points(self, rng, n):
        # n random points inside the heart (graph units)
        x = rng.uniform(-R3, R3, n * 4)
        y = rng.uniform(-1.6, 2.3, n * 4)
        lo, hi = envelope(x)
        ok = (y > lo + 0.05) & (y < hi - 0.05)
        return x[ok][:n], y[ok][:n]

    def make_sparks(self, rng):
        # the burst at k = 100: sparks thrown out from all over the heart
        x, y = self.inside_points(rng, 160)
        ang = np.arctan2(y - MIDDLE_Y, x) + rng.normal(0, 0.35, x.size)
        speed = (240 + 340 * rng.random(x.size)) * self.s
        self.sparks = dict(x=self.ox + x * self.unit, y=self.oy - y * self.unit,
                           vx=np.cos(ang) * speed, vy=-np.sin(ang) * speed,
                           life=1.1 + 0.7 * rng.random(x.size), hot=rng.random(x.size))

    def make_sparkles(self, rng):
        x, y = self.inside_points(rng, 400)
        self.sparkle_spots = np.stack([x, y], 1)
        self.sparkle_beat = np.stack([1.7 + 1.6 * rng.random(16), rng.random(16)], 1)   # period, offset

    def equation_surface(self):
        # y = x^(2/3) + 0.9 sin(kx) sqrt(3 - x^2), set like the video: x, y and k in italics
        up, it, sup = self.eq_up, self.eq_it, self.eq_sup
        k = up.get_height() / 28                                    # the root sign's size follows the type
        lift = round(0.42 * up.get_ascent())                        # a power's baseline sits this far up
        pieces = [("y", it, 0), (" = ", up, 0), ("x", it, 0), ("2/3", sup, 1), (" + 0.9 sin(", up, 0),
                  ("kx", it, 0), (")", up, 0), ("ROOT", None, 0), ("3 \u2212 ", up, 0), ("x", it, 0), ("2", sup, 1)]
        base = round(6 * k)                                         # room above for the bar of the root
        height = up.get_height() + base
        width = sum(f.size(t)[0] + (2 if r else 0) for t, f, r in pieces if f) + round(16 * k) + 4
        surf = pygame.Surface((width, height), pygame.SRCALPHA)
        x, root_at = 2, None
        for text, f, raised in pieces:
            if f is None:
                root_at = x
                x += round(16 * k)
                continue
            y = base + (up.get_ascent() - f.get_ascent() - lift if raised else 0)
            surf.blit(f.render(text, True, EQ_C), (x + (1 if raised else 0), y))
            x += f.size(text)[0] + (2 if raised else 0)
        base -= round(4 * k)
        # the radical sign: a short tick, down to the foot, up to the bar over 3 - x^2
        top, foot, mid = base + round(2 * k), base + up.get_ascent() + round(2 * k), base + round(15 * k)
        pts = [(root_at + 1, mid), (root_at + 4 * k, mid - 2 * k), (root_at + 8 * k, foot), (root_at + 14 * k, top), (x + 2, top)]
        pygame.draw.lines(surf, EQ_C, False, pts, max(1, round(1.4 * k)))
        return surf

    # one frame

    def curve_cells(self, k, t):
        # sample the curve finely and add up, per cell, how much of it passes through and which way
        n = int(3000 + 460 * k)
        x = np.linspace(-R3, R3, n)
        y = np.cbrt(x * x) + AMP * np.sin(k * x) * np.sqrt(np.clip(3 - x * x, 0, None))
        px, py = self.to_screen(x, y)
        mx, my, xm = (px[1:] + px[:-1]) / 2, (py[1:] + py[:-1]) / 2, (x[1:] + x[:-1]) / 2
        dx, dy = np.diff(px), -np.diff(py)                              # y up
        ds = np.hypot(dx, dy) + 1e-9
        ix, iy = np.floor(mx / self.cw).astype(int), np.floor(my / self.ch).astype(int)
        ok = (ix >= 0) & (ix < self.cols) & (iy >= 0) & (iy < self.rows)
        mx, my, xm, dx, dy, ds, ix, iy = mx[ok], my[ok], xm[ok], dx[ok], dy[ok], ds[ok], ix[ok], iy[ok]
        idx = iy * self.cols + ix
        size = self.rows * self.cols

        def add(weights):
            return np.bincount(idx, weights, size).reshape(self.rows, self.cols)

        length = add(ds)
        vx, vy = add((dx * dx - dy * dy) / ds), add(2 * dx * dy / ds)  # direction, doubled angle: / and \ cancel
        low = add(ds * ((my / self.ch) % 1))                            # how low in the cell it runs
        turn = add(np.sign(dy) * (mx - (ix + 0.5) * self.cw) * ds)     # < 0 a peak /\, > 0 a valley \/
        heat = add(ds * self.pulse_heat(xm, t))
        return length, vx, vy, low, turn, heat, n

    @staticmethod
    def pulse_front(t):
        # where the one white pulse is (graph x), sweeping left to right as the heart is finished
        return -R3 - 0.4 + (2 * R3 + 0.8) * (t - T_LOCK) / PULSE

    def pulse_heat(self, x, t):
        # the white pulse that runs along the finished heart, once
        if not 0 <= t - T_LOCK < PULSE + 0.4:
            return np.zeros_like(x)
        return 0.95 * np.exp(-((x - self.pulse_front(t)) / 0.14) ** 2)

    def to_screen(self, x, y):
        return self.ox + x * self.unit, self.oy - y * self.unit

    def scene(self, t):
        rows, cols, cw, ch = self.rows, self.cols, self.cw, self.ch
        g = Grid(rows, cols)
        rays = []

        # the twinkling black behind everything
        self.stars(g, t)

        # axes: grey, under the heart
        on = self.axis_char > 0
        g.char[on] = self.axis_char[on]
        g.col[on] = self.axis_lum[on, None]

        # the curve: how much of it falls in each cell
        k = float(k_at(t))
        lock = t - T_LOCK
        length, vx, vy, low, turn, pheat, samples = self.curve_cells(k, t)
        dens = length / ch                                              # 1 = one stroke straight down the cell
        lit = dens > 0.22

        # condensing: where the strokes crowd together they turn into a solid of letters, cell by cell
        near = box3(dens) / np.maximum(box3(lit.astype(float)), 1)     # how crowded the lit cells round it are
        lo, hi = envelope(np.clip(self.gx, -R3, R3))
        inside = (np.abs(self.gx) < R3) & (self.gy > lo) & (self.gy < hi)
        crowd = smooth((near - 0.95) / 0.65)
        fill = (crowd > self.rand) & (lit | inside)
        stroke = lit & ~fill
        occ = fill | stroke
        p = np.pad(~occ, 1, constant_values=True)
        outline = fill & (p[:-2, 1:-1] | p[2:, 1:-1] | p[1:-1, :-2] | p[1:-1, 2:])

        # strokes: the direction the curve takes through the cell; a turn is ^ or v
        safe = np.maximum(length, 1e-9)
        ang = np.degrees(0.5 * np.arctan2(vy, vx)) % 180
        sc = SLOPE[np.digitize(ang, [25, 72, 108, 155])]
        flat = (ang < 25) | (ang >= 155)
        sc = np.where(flat & (low / safe > 0.62), C("_"), sc)
        sc = np.where(np.hypot(vx, vy) / safe < 0.5, np.where(turn < 0, C("^"), C("v")), sc)

        # outline: along the edge of the solid, by the slope of the edge
        os_ = box3(occ.astype(float))
        po = np.pad(os_, 1)
        gxs, gys = po[1:-1, 2:] - po[1:-1, :-2], po[2:, 1:-1] - po[:-2, 1:-1]    # points into the heart
        oc = slope_char(-gys, -gxs)
        eang = np.degrees(np.arctan2(-gxs, -gys)) % 180
        oc = np.where(((eang < 25) | (eang >= 155)) & (gys > 0), C("_"), oc)

        # the solid: letters by brightness
        shade = self.light + 0.30 * np.clip((near - 1.2) / 1.5, 0, 1)
        lum = np.clip(0.45 + 0.55 * shade / 0.9, 0.45, 1.0)
        pool = np.digitize(lum, [0.58, 0.72, 0.86])
        letters = FILL[pool, (self.hash + int(t * 4)) % 12]

        col = np.where(fill[..., None], (HEART * lum[..., None] + (PINK - HEART) * np.clip(lum - 0.75, 0, 1)[..., None] * 1.2), 0)
        col = np.where(outline[..., None], EDGE * np.maximum(0.85, lum)[..., None], col)
        col = np.where(stroke[..., None], LINE * (0.88 + 0.12 * np.minimum(dens, 1))[..., None], col)
        char = np.where(outline, oc, np.where(fill, letters, sc))

        # white heat: the pulse across the finished heart, the gleam
        heat = pheat / safe
        gl = (t - T_GLEAM[0]) / (T_GLEAM[1] - T_GLEAM[0])
        if 0 < gl < 1.2:
            u = self.px + 0.6 * self.py
            front = (-0.15 + 1.3 * gl) * (self.w + 0.6 * self.h)
            heat = np.maximum(heat, fill * 0.8 * np.exp(-((u - front) / (48 * self.s)) ** 2))
        heat = np.clip(heat, 0, 1)[..., None]
        col = col + (WHITE - col) * heat
        g.char[occ] = char[occ]
        g.col[occ] = col[occ]
        g.moving[occ] = stroke[occ] & (t < T_LOCK)

        # the head of the pulse: a white spark with rays where it meets the curve
        front = self.pulse_front(t)
        if lock >= 0 and abs(front) < R3 * 0.97:
            fy = np.cbrt(front * front) + AMP * np.sin(k * front) * np.sqrt(3 - front * front)
            sx, sy = self.to_screen(front, fy)
            g.put(int(sy / ch), int(sx / cw), C("*"), WHITE * 1.3, moving=True)
            rays.append((sx, sy, 12, 1.0))

        # the burst at k = 100: sparks fly out, white-hot, cooling to pink, falling, flickering out
        if 0 <= lock < 2.0:
            sp = self.sparks
            a = lock
            drag = 2.4
            gone = (1 - np.exp(-drag * a)) / drag
            x = sp["x"] + sp["vx"] * gone
            y = sp["y"] + sp["vy"] * gone + 0.5 * 420 * self.s * a * a
            alive = a < sp["life"]
            fade = np.clip(1 - a / sp["life"], 0, 1) ** 1.2
            flicker = np.where(a > 0.65 * sp["life"], (np.floor(a * 18 + sp["hot"] * 7) % 2) * 0.7 + 0.3, 1.0)
            cool = smooth(a / 0.5)
            rgb = (WHITE * 1.3 + (np.where(sp["hot"][:, None] > 0.5, EDGE, PINK) - WHITE * 1.3) * cool) * (fade * flicker)[:, None]
            glyph = C("*") if a < 0.3 else (C("+") if a < 0.8 else C("."))
            g.put((y / ch)[alive], (x / cw)[alive], glyph, rgb[alive], moving=True)

        # sparkles twinkling on the heart, each at a new spot every time it comes back
        sparkles = 0
        if t > T_SPARKLE:
            lit_now = []
            for i, (period, off) in enumerate(self.sparkle_beat):
                phase = (t - T_SPARKLE) / period + off
                age = (phase % 1.0) * period
                if age > 0.8 or (t - T_SPARKLE) < off * period:
                    continue
                b = np.sin(np.pi * age / 0.8)
                spot = self.sparkle_spots[(i * 37 + int(phase) * 101) % len(self.sparkle_spots)]
                sx, sy = self.to_screen(spot[0], spot[1])
                g.put(int(sy / ch), int(sx / cw), C("*") if b > 0.5 else C("+"), WHITE * (0.6 + 0.7 * b))
                lit_now.append((b, sx, sy))
                sparkles += 1
            for b, sx, sy in sorted(lit_now, reverse=True)[:3]:
                if b > 0.55:
                    rays.append((sx, sy, 8 + 6 * b, b))

        info = dict(k=k, samples=samples, letters=int(occ.sum()), sparkles=sparkles)
        return g, rays, info

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
        for layer, k in ((tight, 0.75), (wide, 0.45)):
            layer = pygame.transform.smoothscale(layer, (w, h))
            layer.fill((int(255 * k),) * 3, special_flags=pygame.BLEND_MULT)
            self.out.blit(layer, (0, 0), special_flags=pygame.BLEND_ADD)

    def rays(self, x, y, reach, strength):
        # a four-pointed flare: long arms sideways and up and down, short diagonals
        step = 3 * self.s
        for dx, dy, length in ((1, 0, 1.0), (0, 1, 0.8), (0.7, 0.7, 0.45), (0.7, -0.7, 0.45)):
            steps = int(reach * length)
            for i in range(1, steps):
                k = (1 - i / steps) * strength
                c = tuple(int(min(255, v * 255 * k)) for v in WHITE)
                for sgn in (1, -1):
                    self.out.fill(c, (int(x + sgn * dx * i * step), int(y + sgn * dy * i * step), 2, 2), special_flags=pygame.BLEND_MAX)
        pygame.draw.circle(self.out, tuple(int(min(255, 255 * v * strength)) for v in WHITE), (int(x), int(y)), max(2, int(3 * self.s)))

    def tinted(self, col, into):
        pygame.surfarray.blit_array(self.tint, (np.clip(col, 0, 1) * 255).astype(np.uint8).transpose(1, 0, 2))
        pygame.transform.scale(self.tint, (self.w, self.h), into)
        into.blit(self.art, (0, 0), special_flags=pygame.BLEND_MULT)
        return into

    def draw_equation(self, t, k):
        # the equation under the graph, and k counting up beneath it; k flashes as it reaches 100
        eq = self.equation
        y = 0.792 * self.h
        self.out.blit(eq, (round((self.w - eq.get_width()) / 2), round(y)))
        hot = float(np.clip(1 - (t - T_LOCK) / 0.6, 0, 1)) if t >= T_LOCK else 0.0
        c = K_C + (np.array([255, 250, 245]) - K_C) * hot
        c = tuple(int(v) for v in c)
        parts = [(self.k_it.render("k", True, c)), self.k_up.render(f" = {k:.2f}", True, c)]
        width = sum(p.get_width() for p in parts)
        x = (self.w - width) / 2
        for p in parts:
            self.out.blit(p, (round(x), round(y + eq.get_height() + 6 * self.s)))
            x += p.get_width()

    def draw(self, t):
        g, rays, info = self.scene(t)
        w, h = self.w, self.h
        grey = pygame.image.frombuffer(self.atlas[g.char].transpose(0, 2, 1, 3).tobytes(), (w, h), "P")
        grey.set_palette(self.greys)
        self.art.blit(grey, (0, 0))
        if self.last_t is None or t < self.last_t:
            self.trail.fill((0, 0, 0))                                  # restarted: no trails from before
        self.last_t = t
        col = g.col * (g.char > 0)[..., None]
        # trails: moving letters fade out behind them; the solid heart stays crisp
        self.trail.fill((int(0.45 * 255),) * 3, special_flags=pygame.BLEND_MULT)
        self.trail.blit(self.tinted(col * g.moving[..., None], self.moving_s), (0, 0), special_flags=pygame.BLEND_MAX)
        self.out.blit(self.trail, (0, 0))
        self.out.blit(self.tinted(col * ~g.moving[..., None], self.still_s), (0, 0), special_flags=pygame.BLEND_MAX)
        for x, y, reach, strength in rays:
            self.rays(x, y, reach, strength)
        self.draw_equation(t, info["k"])
        self.glow(self.out)

        # HUD: credit and counts at the bottom left, the clock at the top right
        lines = [f"k {info['k']:6.2f}    waves {info['k'] * R3 / np.pi:4.1f}    samples {info['samples']}",
                 f"letters {info['letters']}" + (f"    sparkles {info['sparkles']}" if t > T_SPARKLE else "")]
        if self.hint:
            lines.append("Space pause · R restart · S screenshot · Esc quit")
        gp = self.hud_gap
        for i, text in enumerate(lines):
            self.out.blit(self.small.render(text, True, DIM), (24, h - 18 - gp * (len(lines) - i)))
        self.out.blit(self.small.render(CREDIT, True, SIGN), (24, h - 18 - gp * (len(lines) + 1) - gp // 3))
        tt = self.small.render(f"{'●' if int(t * 2) % 2 == 0 else ' '} t {t:05.2f}s", True, ACCENT)
        self.out.blit(tt, (w - 24 - tt.get_width(), 14))
        return self.out


def window_size(w, h):
    info = pygame.display.Info()
    k = 1.0
    if info.current_w > 0 and info.current_h > 0:
        k = min(1.0, 0.88 * info.current_h / h, 0.95 * info.current_w / w)
    return int(w * k), int(h * k)


def main():
    pygame.init()
    renderer, clock = Renderer(), pygame.time.Clock()
    size = window_size(renderer.w, renderer.h)
    window = pygame.display.set_mode(size)
    pygame.display.set_caption("The Heart in ASCII")
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
                pygame.image.save(screen, str(HERE / f"heart_{int(time.time())}.png"))
        dt = clock.tick(30) / 1000
        if not paused:
            t += min(dt, 1 / 15)
            if t > LOOP:
                t = 0.0
            screen = renderer.draw(t)
        window.blit(screen if size == (renderer.w, renderer.h) else pygame.transform.smoothscale(screen, size), (0, 0))
        pygame.display.flip()


if __name__ == "__main__":
    sys.exit(main())
