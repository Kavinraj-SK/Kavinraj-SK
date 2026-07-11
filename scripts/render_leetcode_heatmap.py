#!/usr/bin/env python3
"""
Render data/leetcode.json (produced by fetch_leetcode.py) as a GitHub-style
heatmap grid -- but of LeetCode submission activity instead of git commits --
with a Less->More legend and a real stats footer (solved counts by
difficulty, streak, active days).

Same one-shot diagonal reveal as the original contribution heatmap; single
accent hue (LeetCode orange) instead of green, per the "monochrome, no
rainbow" house style.

Run by .github/workflows/update-profile-art.yml after fetch_leetcode.py.
"""
import datetime
import json
import os

HERE = os.path.dirname(__file__)
IN_PATH = os.path.join(HERE, "..", "data", "leetcode.json")
OUT_PATH = os.path.join(HERE, "..", "leetcode-heatmap.svg")

# LeetCode-orange ramp: empty -> brightest.
PALETTE = ["#161b22", "#4d2e0a", "#8a4b0f", "#c96f16", "#ffa116", "#ffc966"]

CELL = 12
GAP = 3
STEP = CELL + GAP
PAD = 22
LEFT_LABEL_W = 30
TOP_LABEL_H = 20
TITLEBAR_H = 30

BG = "#0a0e14"
BG2 = "#0d1420"
FRAME = "#c96f16"
MUTED = "#7d8590"
TEXT = "#e6edf3"
ACCENT = "#ffa116"
ORANGE = "#ffa116"
GOLD = "#f2cc60"

# reveal timing (one-shot)
COL_T = 0.018
ROW_T = 0.045
CELL_DUR = 0.42

WINDOW_DAYS = 365


def level_for(count):
    if count == 0:
        return 0
    if count <= 1:
        return 1
    if count <= 3:
        return 2
    if count <= 6:
        return 3
    if count <= 10:
        return 4
    return 5


def fill_window(days):
    """Turn the sparse {date: count} submission calendar into a dense,
    continuous run of the last WINDOW_DAYS days (missing days = 0)."""
    by_date = {d["date"]: d["count"] for d in days}
    if by_date:
        end = datetime.date.fromisoformat(max(by_date.keys()))
    else:
        end = datetime.date.today()
    start = end - datetime.timedelta(days=WINDOW_DAYS - 1)
    out = []
    cur = start
    while cur <= end:
        key = cur.isoformat()
        out.append({"date": key, "count": by_date.get(key, 0)})
        cur += datetime.timedelta(days=1)
    return out


def build_grid(days):
    first = datetime.date.fromisoformat(days[0]["date"])
    lead_pad = (first.weekday() + 1) % 7  # sunday=0
    grid = []
    col = [None] * lead_pad
    for d in days:
        date = datetime.date.fromisoformat(d["date"])
        weekday = (date.weekday() + 1) % 7
        while len(col) < weekday:
            col.append(None)
        col.append((d["date"], d["count"], level_for(d["count"])))
        if len(col) == 7:
            grid.append(col)
            col = []
    if col:
        while len(col) < 7:
            col.append(None)
        grid.append(col)
    return grid


def render(data):
    days = fill_window(data["days"])
    grid = build_grid(days)
    n_cols = len(grid)
    art_w = n_cols * STEP
    art_h = 7 * STEP

    month_labels = []
    seen_months = set()
    for ci, column in enumerate(grid):
        for cell in column:
            if cell is None:
                continue
            date = datetime.date.fromisoformat(cell[0])
            key = (date.year, date.month)
            if key not in seen_months and date.day <= 7:
                seen_months.add(key)
                month_labels.append((ci, date.strftime("%b")))
            break

    canvas_w = PAD + LEFT_LABEL_W + art_w + PAD
    stats_h = 88
    canvas_h = TITLEBAR_H + TOP_LABEL_H + art_h + stats_h + PAD

    css = f"""
@keyframes cell {{
  0%   {{ opacity: 0; transform: translateY(-6px); }}
  100% {{ opacity: 1; transform: translateY(0); }}
}}
.c {{ opacity: 0; animation: cell {CELL_DUR:.2f}s cubic-bezier(.2,.8,.2,1) both; }}
""".strip()

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{canvas_w}" height="{canvas_h}" '
        f'viewBox="0 0 {canvas_w} {canvas_h}" font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace">',
        f'<style>{css}</style>',
        '<defs>'
        f'<linearGradient id="hbg" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{BG2}"/><stop offset="1" stop-color="{BG}"/></linearGradient>'
        '</defs>',
        f'<rect width="{canvas_w}" height="{canvas_h}" rx="12" fill="url(#hbg)"/>',
        f'<rect x="0.5" y="0.5" width="{canvas_w-1}" height="{canvas_h-1}" rx="12" '
        f'fill="none" stroke="{FRAME}" stroke-width="1" stroke-opacity="0.55"/>',
        f'<line x1="0" y1="{TITLEBAR_H}" x2="{canvas_w}" y2="{TITLEBAR_H}" stroke="{FRAME}" stroke-opacity="0.35"/>',
    ]
    for i, dotcol in enumerate(["#ff5f56", "#ffbd2e", "#27c93f"]):
        parts.append(f'<circle cx="{PAD + i*16}" cy="{TITLEBAR_H/2}" r="5" fill="{dotcol}"/>')
    parts.append(f'<text x="{canvas_w/2}" y="{TITLEBAR_H/2 + 4}" fill="{MUTED}" font-size="12" '
                 f'text-anchor="middle">kavinraj@github: ~/leetcode --graph</text>')

    grid_top = TITLEBAR_H + TOP_LABEL_H
    grid_left = PAD + LEFT_LABEL_W

    for ci, label in month_labels:
        x = grid_left + ci * STEP
        parts.append(f'<text x="{x}" y="{TITLEBAR_H + 14}" fill="{MUTED}" font-size="10">{label}</text>')

    for wi, wname in [(1, "Mon"), (3, "Wed"), (5, "Fri")]:
        y = grid_top + wi * STEP + CELL * 0.78
        parts.append(f'<text x="{PAD}" y="{y:.1f}" fill="{MUTED}" font-size="9">{wname}</text>')

    for ci, column in enumerate(grid):
        gx = grid_left + ci * STEP
        for ri, cell in enumerate(column):
            if cell is None:
                continue
            date_s, count, lvl = cell
            gy = grid_top + ri * STEP
            delay = ci * COL_T + ri * ROW_T
            plural = "s" if count != 1 else ""
            parts.append(
                f'<rect class="c" x="{gx}" y="{gy}" width="{CELL}" height="{CELL}" rx="2.5" '
                f'fill="{PALETTE[lvl]}" style="animation-delay:{delay:.3f}s">'
                f'<title>{date_s}: {count} submission{plural}</title></rect>'
            )

    leg_y = grid_top + art_h + 6
    leg_x = canvas_w - PAD - (len(PALETTE) * (CELL - 1) + 70)
    parts.append(f'<text x="{leg_x}" y="{leg_y + CELL*0.8:.1f}" fill="{MUTED}" font-size="10" text-anchor="end">Less</text>')
    lx = leg_x + 8
    for lvl, color in enumerate(PALETTE):
        parts.append(f'<rect x="{lx}" y="{leg_y}" width="{CELL-1}" height="{CELL-1}" rx="2.2" fill="{color}"/>')
        lx += CELL
    parts.append(f'<text x="{lx + 4}" y="{leg_y + CELL*0.8:.1f}" fill="{MUTED}" font-size="10">More</text>')

    sep_y = leg_y + CELL + 14
    parts.append(f'<line x1="0" y1="{sep_y}" x2="{canvas_w}" y2="{sep_y}" stroke="{FRAME}" stroke-opacity="0.25"/>')

    total = data["total_solved"]
    easy, medium, hard = data["easy"], data["medium"], data["hard"]
    streak = data["streak"]
    active = data["total_active_days"]
    rng_start, rng_end = days[0]["date"], days[-1]["date"]

    ly = sep_y + 24
    parts.append(f'<text x="{PAD}" y="{ly}" font-size="13" fill="{ORANGE}">'
                 f'<tspan font-weight="700">{total:,}</tspan>'
                 f'<tspan fill="{MUTED}"> problems solved on LeetCode</tspan></text>')
    parts.append(f'<text x="{canvas_w - PAD}" y="{ly}" font-size="12" fill="{MUTED}" text-anchor="end">'
                 f'{rng_start} &#8594; {rng_end}</text>')
    ly += 24
    parts.append(f'<text x="{PAD}" y="{ly}" font-size="13" fill="{MUTED}">'
                 f'<tspan fill="#3fb950" font-weight="700">{easy}</tspan> easy   '
                 f'<tspan fill="{GOLD}" font-weight="700">{medium}</tspan> medium   '
                 f'<tspan fill="#f85149" font-weight="700">{hard}</tspan> hard</text>')
    parts.append(f'<text x="{canvas_w - PAD}" y="{ly}" font-size="12" fill="{MUTED}" text-anchor="end">'
                 f'streak <tspan fill="{ACCENT}" font-weight="700">{streak}d</tspan>'
                 f'   &#183;   active <tspan fill="{ACCENT}" font-weight="700">{active}d</tspan></text>')

    parts.append("</svg>")
    return "".join(parts)


if __name__ == "__main__":
    data = json.load(open(IN_PATH))
    svg = render(data)
    with open(OUT_PATH, "w") as f:
        f.write(svg)
    print(f"wrote {OUT_PATH} ({len(svg)} bytes)")
