"""Urban-growth cellular automaton (corrected 2026 version) and a synthetic-town generator."""
import numpy as np
from scipy.ndimage import distance_transform_edt, convolve, gaussian_filter

RNG = np.random.default_rng(42)
N = 200            # grid size (pixels)
CELL = 30.0        # pixel size in metres (used for slope)

KERNEL = np.array([[1, 1, 1], [1, 0, 1], [1, 1, 1]])   # Moore neighbourhood


# ---------------------------------------------------------------- synthetic data
def make_terrain():
    yy, xx = np.mgrid[0:N, 0:N]
    elev = 1200 + 0.4 * yy                                   # gentle rise northwards
    for cy, cx, h, s in [(30, 160, 700, 22), (60, 40, 500, 18), (135, 160, 450, 12), (140, 30, 380, 10)]:
        elev += h * np.exp(-((yy - cy) ** 2 + (xx - cx) ** 2) / (2 * s ** 2))
    elev += gaussian_filter(RNG.normal(0, 25, (N, N)), 4)
    gy, gx = np.gradient(elev, CELL)
    slope = np.degrees(np.arctan(np.hypot(gx, gy)))
    return elev, slope


def make_roads():
    roads = np.zeros((N, N), bool)
    for r in range(110, 196, 18):        # downtown grid
        roads[r, 60:190] = True
    for c in range(60, 191, 22):
        roads[110:196, c] = True
    t = np.linspace(0, 1, 600)           # two curved arterials
    for x0, y0, x1, y1, bend in [(5, 180, 195, 95, 30), (100, 195, 120, 5, -25)]:
        xs = x0 + (x1 - x0) * t
        ys = y0 + (y1 - y0) * t + bend * np.sin(np.pi * t)
        roads[np.clip(ys.astype(int), 0, N - 1), np.clip(xs.astype(int), 0, N - 1)] = True
    return roads


def make_buildings(roads, slope):
    d = distance_transform_edt(~roads)
    p = np.zeros((N, N))
    for cy, cx, s, a in [(160, 130, 22, 0.55), (125, 80, 10, 0.35), (178, 35, 9, 0.35)]:
        yy, xx = np.mgrid[0:N, 0:N]
        p += a * np.exp(-((yy - cy) ** 2 + (xx - cx) ** 2) / (2 * s ** 2))
    p *= np.exp(-d / 6) * (slope < 12)
    return (RNG.random((N, N)) < p) & ~roads


# ---------------------------------------------------------------- the model
def neighbours(urban):
    return convolve(urban.astype(int), KERNEL, mode="constant")


def step(urban, dist=None, slope=None, road_px=4, max_slope=15):
    """One CA iteration. Built cells persist; only birth rules apply.

    Stage 1 (dist=None, slope=None): birth with exactly 3 built neighbours.
    Stage 2 (+dist):  ... or within `road_px` of a road with >=1 built neighbour.
    Stage 3 (+slope): every birth additionally requires slope <= `max_slope`.
    """
    n = neighbours(urban)
    birth = n == 3
    if dist is not None:
        birth |= (dist <= road_px) & (n >= 1)
        birth &= dist > 0                     # roads themselves are not buildable
    if slope is not None:
        birth &= slope <= max_slope
    return urban | (birth & ~urban)


def run(urban, steps, **kw):
    out = [urban]
    for _ in range(steps):
        out.append(step(out[-1], **kw))
    return out
