# -*- coding: utf-8 -*-
"""Tiny server-side SVG charts — no JavaScript libraries, no CDN.

The whole UI must work with the network unplugged, so charts are
generated as inline SVG from the data (same shapes the step reports draw
with matplotlib, kept deliberately simple).
"""

from __future__ import annotations

from typing import List, Optional, Sequence, Tuple

# Okabe-Ito colourblind-safe palette, fixed order (same as STEP 6 figures)
PALETTE = ["#0072B2", "#E69F00", "#009E73", "#CC79A7", "#56B4E9",
           "#D55E00", "#F0E442", "#666666"]


def _esc(s) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;"))


def line_chart(series: Sequence[dict], width: int = 720, height: int = 240,
               title: str = "", y_label: str = "",
               fill: bool = True) -> str:
    """series = [{"name": str, "points": [(index, value), ...]}, ...]"""
    pts_all = [(x, y) for s in series for x, y in s["points"]
               if y is not None]
    if not pts_all:
        return _empty(width, height, title)
    # x may be a date string (the live UI) or a number (reports): map
    # non-numeric x onto its position, keeping the series order
    xs = [p[0] for p in pts_all]
    numeric_x = all(isinstance(x, (int, float)) for x in xs)
    pos = {x: i for i, x in enumerate(dict.fromkeys(xs))}
    x_of = (lambda v: float(v)) if numeric_x else (lambda v: float(pos[v]))
    ys = [p[1] for p in pts_all]
    x0 = min(x_of(x) for x in xs)
    x1 = max(x_of(x) for x in xs)
    y0, y1 = min(ys), max(ys)
    if y1 == y0:
        y1 = y0 + 1
    pad_l, pad_r, pad_t, pad_b = 56, 12, 26, 26
    w = width - pad_l - pad_r
    h = height - pad_t - pad_b

    def sx(x):
        xv = x_of(x)
        return pad_l + (0 if x1 == x0 else (xv - x0) / (x1 - x0) * w)

    def sy(y):
        return pad_t + h - (y - y0) / (y1 - y0) * h

    out = [f'<svg viewBox="0 0 {width} {height}" class="chart" '
           f'role="img" aria-label="{_esc(title)}">',
           f'<text x="8" y="16" class="chart-title">{_esc(title)}</text>']
    # y grid (4 lines)
    for i in range(5):
        yv = y0 + (y1 - y0) * i / 4
        yy = sy(yv)
        out.append(f'<line x1="{pad_l}" y1="{yy:.1f}" '
                   f'x2="{width-pad_r}" y2="{yy:.1f}" class="grid"/>')
        out.append(f'<text x="{pad_l-6}" y="{yy+3:.1f}" class="axis" '
                   f'text-anchor="end">{yv:,.0f}</text>')
    for i, s in enumerate(series):
        color = PALETTE[i % len(PALETTE)]
        pts = [(sx(x), sy(y)) for x, y in s["points"] if y is not None]
        if not pts:
            continue
        d = " ".join(f"{'M' if j == 0 else 'L'}{x:.1f},{y:.1f}"
                     for j, (x, y) in enumerate(pts))
        if fill and len(series) == 1 and len(pts) > 1:
            area = (d + f" L{pts[-1][0]:.1f},{pad_t+h:.1f}"
                    f" L{pts[0][0]:.1f},{pad_t+h:.1f} Z")
            out.append(f'<path d="{area}" fill="{color}" opacity="0.10"/>')
        out.append(f'<path d="{d}" fill="none" stroke="{color}" '
                   f'stroke-width="2"/>')
    if len(series) > 1:
        for i, s in enumerate(series):
            lx = pad_l + i * 130
            out.append(f'<rect x="{lx}" y="{height-16}" width="10" '
                       f'height="10" fill="{PALETTE[i % len(PALETTE)]}"/>')
            out.append(f'<text x="{lx+14}" y="{height-7}" class="axis">'
                       f'{_esc(s["name"])}</text>')
    if y_label:
        out.append(f'<text x="{pad_l}" y="{height-2}" class="axis">'
                   f'{_esc(y_label)}</text>')
    out.append("</svg>")
    return "".join(out)


def bar_chart(labels: Sequence[str], values: Sequence[float],
              width: int = 720, height: int = 240, title: str = "",
              positive_color: str = "#0072B2",
              negative_color: str = "#999999") -> str:
    if not len(values):
        return _empty(width, height, title)
    pad_l, pad_r, pad_t, pad_b = 56, 12, 26, 40
    w = width - pad_l - pad_r
    h = height - pad_t - pad_b
    vmax = max(max(values), 0.0)
    vmin = min(min(values), 0.0)
    if vmax == vmin:
        vmax = vmin + 1
    y0, y1 = vmin, vmax

    def sy(v):
        return pad_t + h - (v - y0) / (y1 - y0) * h

    bw = w / max(len(values), 1) * 0.7
    step = w / max(len(values), 1)
    out = [f'<svg viewBox="0 0 {width} {height}" class="chart" role="img" '
           f'aria-label="{_esc(title)}">',
           f'<text x="8" y="16" class="chart-title">{_esc(title)}</text>']
    zero = sy(0.0)
    out.append(f'<line x1="{pad_l}" y1="{zero:.1f}" x2="{width-pad_r}" '
               f'y2="{zero:.1f}" class="grid"/>')
    for i, (lab, v) in enumerate(zip(labels, values)):
        x = pad_l + i * step + (step - bw) / 2
        y = sy(v)
        hh = abs(zero - y)
        color = positive_color if v >= 0 else negative_color
        out.append(f'<rect x="{x:.1f}" y="{min(y, zero):.1f}" '
                   f'width="{bw:.1f}" height="{max(hh, 1):.1f}" '
                   f'fill="{color}"/>')
        if i % max(1, len(values) // 12) == 0:
            out.append(f'<text x="{x + bw/2:.1f}" y="{height-8}" '
                       f'class="axis" text-anchor="middle">'
                       f'{_esc(lab)}</text>')
    out.append("</svg>")
    return "".join(out)


def donut(parts: Sequence[Tuple[str, float]], width: int = 260,
          height: int = 260, title: str = "") -> str:
    total = sum(v for _, v in parts if v > 0)
    if total <= 0:
        return _empty(width, height, title)
    cx, cy, r, thick = width / 2, height / 2 + 6, 80, 28
    out = [f'<svg viewBox="0 0 {width} {height}" class="chart" role="img" '
           f'aria-label="{_esc(title)}">',
           f'<text x="8" y="16" class="chart-title">{_esc(title)}</text>']
    import math

    ang = -math.pi / 2
    for i, (name, v) in enumerate(parts):
        if v <= 0:
            continue
        frac = v / total
        a2 = ang + frac * 2 * math.pi
        large = 1 if frac > 0.5 else 0
        x1, y1 = cx + r * math.cos(ang), cy + r * math.sin(ang)
        x2, y2 = cx + r * math.cos(a2), cy + r * math.sin(a2)
        color = PALETTE[i % len(PALETTE)]
        out.append(
            f'<path d="M {x1:.1f} {y1:.1f} A {r} {r} 0 {large} 1 '
            f'{x2:.1f} {y2:.1f}" fill="none" stroke="{color}" '
            f'stroke-width="{thick}"/>')
        ang = a2
    for i, (name, v) in enumerate(parts):
        if v <= 0:
            continue
        ly = height - 12 - (len(parts) - i - 1) * 14
        out.append(f'<rect x="6" y="{ly-9}" width="9" height="9" '
                   f'fill="{PALETTE[i % len(PALETTE)]}"/>')
        out.append(f'<text x="20" y="{ly}" class="axis">{_esc(name)} '
                   f'{v/total*100:.1f}%</text>')
    out.append(f'<text x="{cx}" y="{cy-4}" class="donut-center" '
               f'text-anchor="middle">{total:,.0f}</text>')
    out.append(f'<text x="{cx}" y="{cy+14}" class="axis" '
               f'text-anchor="middle">total</text>')
    out.append("</svg>")
    return "".join(out)


def _empty(width: int, height: int, title: str) -> str:
    return (f'<svg viewBox="0 0 {width} {height}" class="chart">'
            f'<text x="8" y="16" class="chart-title">{_esc(title)}</text>'
            f'<text x="{width/2}" y="{height/2}" class="axis" '
            f'text-anchor="middle">no data yet</text></svg>')
