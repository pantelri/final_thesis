"""Gravity view: three circles (Sie / andere Annotator·innen / gewähltes KI-Modell).

Flat, abstract 2D chart modelled on gravitation: the more two parties agree, the
closer they are pulled together.

Distance rule (author spec): the GAP between two circles is K · (1 − agreement)²,
so at 100 % agreement the circles touch. Centre distance = r_i + r_j + gap. K is one
scale per page (``scale_for``): chosen so the largest gap on the page fills the
canvas, which keeps gaps comparable across model selections while making small
differences visible. The three pairwise distances define a triangle (law of
cosines); if they violate the triangle inequality the angle is clamped and the
third side is approximate — the chart then says so.
"""
import math
from html import escape

from ..agreement import Stats

W, H = 800, 480                 # svg viewBox
K_MAX_GAP = 460                 # px the largest gap on the page may take
K_CAP = 20000                   # upper bound for K (near-perfect agreement everywhere)
R_MIN, R_MAX = 14, 38           # circle radii
COL = {"me": "#1e1b4b", "human": "#0d9488", "model": "#4f46e5"}
INK, MUTED, LINE = "#111827", "#6b7280", "#cbd5e1"


def scale_for(agreements: list[float]) -> float:
    """K such that the largest (1 − a)² among `agreements` maps to K_MAX_GAP px."""
    worst = max([(1 - a) ** 2 for a in agreements] + [1e-9])
    return min(K_CAP, K_MAX_GAP / worst)


def gap(agreement: float, k: float) -> float:
    return k * (1 - agreement) ** 2


def triangle(d_ab: float, d_ac: float, d_bc: float) -> tuple[tuple, tuple, tuple]:
    """Points A, B, C with |AB|=d_ab, |AC|=d_ac, |BC|≈d_bc (A at origin, B on x-axis)."""
    cos_a = (d_ab ** 2 + d_ac ** 2 - d_bc ** 2) / (2 * d_ab * d_ac) if d_ab and d_ac else 1.0
    ang = math.acos(max(-1.0, min(1.0, cos_a)))
    return (0.0, 0.0), (d_ab, 0.0), (d_ac * math.cos(ang), -d_ac * math.sin(ang))


def _radius(n: int, n_max: int) -> float:
    return R_MIN + (R_MAX - R_MIN) * math.sqrt(n / n_max) if n_max else R_MIN


def _circle(x: float, y: float, r: float, kind: str, name: str, sub: str,
            away: tuple[float, float]) -> str:
    """Flat circle with its label pushed outward along `away` (unit vector)."""
    ux, uy = away
    lx, ly = x + ux * (r + 12), y + uy * (r + 12)
    anchor = "middle" if abs(ux) < 0.4 else ("start" if ux > 0 else "end")
    ly += 12 if uy > 0.4 else (-10 if uy < -0.4 else 0)
    return (f'<g><title>{escape(name)}: {escape(sub)}</title>'
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="{COL[kind]}" '
            'stroke="white" stroke-width="2"/>'
            f'<text x="{lx:.1f}" y="{ly:.1f}" text-anchor="{anchor}" font-size="13" '
            f'font-weight="600" fill="{INK}">{escape(name)}</text>'
            f'<text x="{lx:.1f}" y="{ly + 15:.1f}" text-anchor="{anchor}" font-size="11" '
            f'fill="{MUTED}">{escape(sub)}</text></g>')


def _pill(x: float, y: float, text: str) -> str:
    w = 8 + 7 * len(text)
    return (f'<rect x="{x - w / 2:.1f}" y="{y - 10:.1f}" width="{w}" height="20" rx="10" '
            f'fill="white" stroke="{LINE}"/>'
            f'<text x="{x:.1f}" y="{y + 4:.1f}" text-anchor="middle" font-size="11" '
            f'font-weight="600" fill="{INK}">{escape(text)}</text>')


def gravity_svg(me_units: int, model: Stats, others: Stats | None,
                others_vs_model: Stats | None, k: float) -> str:
    """model = Sie vs KI; others = Sie vs andere (pooled); others_vs_model = andere vs KI."""
    n_max = max(me_units, model.n_units, others.n_units if others else 0, 1)
    r_me, r_m = _radius(me_units, n_max), _radius(model.n_units, n_max)
    d_mm = r_me + r_m + gap(model.agreement, k)
    note = ""
    if others and others.n_compared and others_vs_model and others_vs_model.n_compared:
        r_o = _radius(others.n_units, n_max)
        d_mo = r_me + r_o + gap(others.agreement, k)
        d_om = r_o + r_m + gap(others_vs_model.agreement, k)
        pts = list(triangle(d_mm, d_mo, d_om))
        d_real = math.dist(pts[1], pts[2])
        if abs(d_real - d_om) > 1:
            note = ("Hinweis: Die drei Abstände passen nicht exakt in ein Dreieck – der Abstand "
                    "Andere Annotator·innen ↔ Modell ist "
                    + ("verkürzt" if d_real < d_om else "verlängert") + " dargestellt.")
        radii = [r_me, r_m, r_o]
    else:
        pts, radii = [(0.0, 0.0), (d_mm, 0.0)], [r_me, r_m]

    # fit into the viewBox (centre the bounding box, shrink uniformly if needed)
    xs0 = min(p[0] - r for p, r in zip(pts, radii)); xs1 = max(p[0] + r for p, r in zip(pts, radii))
    ys0 = min(p[1] - r for p, r in zip(pts, radii)); ys1 = max(p[1] + r for p, r in zip(pts, radii))
    s = min(1.0, (W - 320) / max(xs1 - xs0, 1), (H - 130) / max(ys1 - ys0, 1))
    y_shift = 40 if note else 0                  # arc needs headroom above
    cx, cy = (xs0 + xs1) / 2, (ys0 + ys1) / 2
    pos = [(W / 2 + (x - cx) * s, H / 2 - 8 + y_shift + (y - cy) * s) for x, y in pts]
    gx, gy = sum(p[0] for p in pos) / len(pos), sum(p[1] for p in pos) / len(pos)

    def away(i: int) -> tuple[float, float]:
        dx, dy = pos[i][0] - gx, pos[i][1] - gy
        n = (dx * dx + dy * dy) ** 0.5
        return (dx / n, dy / n) if n > radii[i] * s else (0.0, 1.0)   # middle circle: below

    parts = [f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" role="img" '
             'aria-label="Gravitationsmodell der Übereinstimmung" '
             'style="width:100%;height:auto;font-family:inherit">',
             '<defs><pattern id="grid" width="24" height="24" patternUnits="userSpaceOnUse">'
             '<circle cx="1" cy="1" r="1" fill="#e5e7eb"/></pattern></defs>',
             f'<rect width="{W}" height="{H}" rx="8" fill="#fafafa" stroke="#e5e7eb"/>',
             f'<rect width="{W}" height="{H}" rx="8" fill="url(#grid)"/>']
    pairs = [(0, 1, model.agreement)]
    if len(pos) == 3:
        pairs += [(0, 2, others.agreement), (2, 1, others_vs_model.agreement)]
    # Degenerate (collinear) case: the outer pair would run through the middle circle,
    # so draw it as an arc above the others and put its label at the apex.
    label_at = {}
    for i, j, _ in pairs:
        (x1, y1), (x2, y2) = pos[i], pos[j]
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        if note and (i, j) == (2, 1):
            lift = max(70.0, 0.3 * math.dist(pos[i], pos[j]))
            parts.append(f'<path d="M{x1:.1f},{y1:.1f} Q{mx:.1f},{my - 2 * lift:.1f} '
                         f'{x2:.1f},{y2:.1f}" fill="none" stroke="{LINE}" stroke-width="1.5" '
                         'stroke-dasharray="4 4"/>')
            label_at[(i, j)] = (mx, my - lift)
        else:
            parts.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
                         f'stroke="{LINE}" stroke-width="1.5"/>')
            label_at[(i, j)] = (mx, my)
    parts.append(_circle(*pos[0], radii[0] * s, "me", "Sie", f"{me_units} Einheiten", away(0)))
    parts.append(_circle(*pos[1], radii[1] * s, "model", model.name,
                         f"{model.n_units} gemeinsame Einheiten", away(1)))
    if len(pos) == 3:
        parts.append(_circle(*pos[2], radii[2] * s, "human", "Andere Annotator·innen",
                             f"{others.n_units} gemeinsame Urteile", away(2)))
    for i, j, agr in pairs:                     # agreement pills on top of the lines
        parts.append(_pill(*label_at[(i, j)], f"{round(100 * agr)} %"))
    if note:
        parts.append(f'<text x="{W / 2}" y="{H - 14}" text-anchor="middle" font-size="11" '
                     f'fill="{MUTED}">{escape(note)}</text>')
    parts.append("</svg>")
    return "".join(parts)
