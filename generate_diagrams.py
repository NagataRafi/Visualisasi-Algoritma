"""
generate_diagrams.py
=====================

Generator diagram untuk materi presentasi "Shortest Path and Widest Path
Algorithms" — Mata kuliah Jaringan Telekomunikasi.

Setiap algoritma diimplementasikan ulang secara instrumented (merekam
langkah/urutan proses, bukan sekadar memanggil fungsi siap pakai) lalu
divisualisasikan dengan matplotlib + networkx sehingga angka yang tampil
di setiap diagram dijamin konsisten dengan hasil komputasi aktual.

Menghasilkan 8 file PNG (300 dpi, background putih) siap tempel ke slide:
  GRUP 1 - Shortest Path:
    01_bellman_ford.png
    02_dijkstra.png
    03_floyd_warshall.png
    04_bfs.png
    05_johnson.png
  GRUP 2 - Widest Path:
    06_modified_dijkstra.png
    07_maximum_capacity_path.png
    08_suurballe.png

Jalankan:
    python generate_diagrams.py

Dependency: matplotlib, networkx  (lihat requirements.txt)

Author : <nama-anda>
NIM    : <nim-anda>
Tanggal: 2026-08-18
"""

import copy
import heapq
import math
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, Circle
from matplotlib.lines import Line2D
import networkx as nx

# --------------------------------------------------------------------------
# 0. Konfigurasi umum: palet warna, style, direktori output
# --------------------------------------------------------------------------

OUTDIR = os.path.dirname(os.path.abspath(__file__))
DPI = 300

# Palet kategorikal (urutan tetap, tidak boleh diacak - lihat skill dataviz)
BLUE = "#2a78d6"
ORANGE = "#eb6834"
AQUA = "#1baf7a"
YELLOW = "#eda100"
MAGENTA = "#e87ba4"
GREEN = "#008300"
VIOLET = "#4a3aa7"
RED = "#e34948"

CATEGORICAL = [BLUE, ORANGE, AQUA, YELLOW, MAGENTA, GREEN, VIOLET, RED]

SURFACE = "#fcfcfb"
INK_PRIMARY = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#898781"
GRIDLINE = "#e1e0d9"
BASELINE = "#c3c2b7"

NODE_DEFAULT = "#d7e6f9"      # node belum diproses (light blue tint)
NODE_DEFAULT_EDGE = BLUE
NODE_VISITED = BLUE           # node sudah difinalisasi
NODE_SOURCE = VIOLET
NODE_TARGET = ORANGE
HIGHLIGHT = RED                # jalur akhir / hasil algoritma
HIGHLIGHT2 = ORANGE             # jalur kedua (mis. Suurballe backup path)
EDGE_DEFAULT = "#b9b8b1"
EDGE_NEGATIVE = "#8a3a3a"

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 11,
    "text.color": INK_PRIMARY,
    "axes.edgecolor": GRIDLINE,
    "figure.facecolor": SURFACE,
    "savefig.facecolor": SURFACE,
    "axes.facecolor": SURFACE,
})


def new_fig(nrows, ncols, figsize, title, height_ratios=None, width_ratios=None):
    fig = plt.figure(figsize=figsize, dpi=DPI, facecolor=SURFACE)
    gs = fig.add_gridspec(nrows, ncols, height_ratios=height_ratios, width_ratios=width_ratios)
    fig.suptitle(title, fontsize=18, fontweight="bold", color=INK_PRIMARY, y=0.985)
    return fig, gs


def save(fig, filename, pad=1.5):
    path = os.path.join(OUTDIR, filename)
    fig.savefig(path, dpi=DPI, facecolor=SURFACE, bbox_inches="tight", pad_inches=0.25)
    plt.close(fig)
    print(f"  -> saved {filename}")


# --------------------------------------------------------------------------
# 1. Helper untuk menggambar graf pada satu Axes
# --------------------------------------------------------------------------

def draw_nodes(ax, pos, node_colors, node_edgecolors=None, labels=None,
               node_size=1400, font_size=13, font_color=None, zorder=4,
               linewidths=2.0):
    node_edgecolors = node_edgecolors or {n: INK_PRIMARY for n in pos}
    for n, (x, y) in pos.items():
        fc = node_colors.get(n, NODE_DEFAULT)
        ec = node_edgecolors.get(n, INK_PRIMARY)
        circ = Circle((x, y), radius=_node_radius(node_size), facecolor=fc,
                       edgecolor=ec, linewidth=linewidths, zorder=zorder)
        ax.add_patch(circ)
        fc_text = font_color if font_color else _text_color_for(fc)
        ax.text(x, y, str(n), ha="center", va="center", fontsize=font_size,
                fontweight="bold", color=fc_text, zorder=zorder + 1)


def _node_radius(node_size):
    # node_size ~ area units used elsewhere; convert to a data-coordinate radius
    return 0.055 * math.sqrt(node_size / 1400.0)


def _text_color_for(hexcolor):
    hexcolor = hexcolor.lstrip("#")
    r, g, b = (int(hexcolor[i:i + 2], 16) for i in (0, 2, 4))
    luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    return "#ffffff" if luminance < 0.55 else INK_PRIMARY


def draw_edges(ax, pos, edges, directed=True, color_fn=None, width_fn=None,
               label_fn=None, node_size=1400, style_fn=None, zorder=2,
               label_offset=0.06, connectionstyle_fn=None):
    """edges: iterable of (u, v, weight) or (u, v, weight, extra_dict)."""
    color_fn = color_fn or (lambda u, v, w: EDGE_DEFAULT)
    width_fn = width_fn or (lambda u, v, w: 1.8)
    style_fn = style_fn or (lambda u, v, w: "-")
    connectionstyle_fn = connectionstyle_fn or (lambda u, v, w: "arc3,rad=0.0")
    r = _node_radius(node_size)

    for e in edges:
        u, v, w = e[0], e[1], e[2]
        x1, y1 = pos[u]
        x2, y2 = pos[v]
        color = color_fn(u, v, w)
        lw = width_fn(u, v, w)
        ls = style_fn(u, v, w)
        conn = connectionstyle_fn(u, v, w)

        if directed:
            arrow = FancyArrowPatch(
                (x1, y1), (x2, y2),
                connectionstyle=conn,
                arrowstyle="-|>", mutation_scale=16 + 2 * lw,
                shrinkA=r * 72 * 1.05, shrinkB=r * 72 * 1.15,
                linewidth=lw, color=color, linestyle=ls, zorder=zorder,
            )
        else:
            arrow = FancyArrowPatch(
                (x1, y1), (x2, y2),
                connectionstyle=conn,
                arrowstyle="-", mutation_scale=1,
                shrinkA=r * 72 * 1.05, shrinkB=r * 72 * 1.05,
                linewidth=lw, color=color, linestyle=ls, zorder=zorder,
            )
        ax.add_patch(arrow)

        if label_fn is not None:
            label = label_fn(u, v, w)
            if label is not None:
                mx, my = (x1 + x2) / 2, (y1 + y2) / 2
                dx, dy = x2 - x1, y2 - y1
                dist = math.hypot(dx, dy) or 1.0
                nx_, ny_ = -dy / dist, dx / dist
                # curve offset roughly follows connectionstyle rad
                rad = _extract_rad(conn)
                mx += rad * dy * 0.5
                my -= rad * dx * 0.5
                lx, ly = mx + nx_ * label_offset, my + ny_ * label_offset
                ax.text(lx, ly, label, fontsize=10.5, color=color if color != EDGE_DEFAULT else INK_SECONDARY,
                         ha="center", va="center", fontweight="bold", zorder=zorder + 1,
                         bbox=dict(boxstyle="round,pad=0.12", fc=SURFACE, ec="none", alpha=0.85))


def _extract_rad(conn_str):
    try:
        return float(conn_str.split("rad=")[1])
    except Exception:
        return 0.0


def style_axes(ax, xlim=(-1.2, 1.2), ylim=(-1.2, 1.2)):
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    ax.set_aspect("equal")
    ax.axis("off")


def legend_swatch(ax, items, loc="lower center", ncol=None, fontsize=10.5, bbox=(0.5, -0.06)):
    handles = []
    for label, color, kind in items:
        if kind == "node":
            handles.append(Line2D([0], [0], marker="o", color="none", markerfacecolor=color,
                                   markeredgecolor=INK_PRIMARY, markersize=13, label=label))
        else:
            handles.append(Line2D([0], [0], color=color, lw=3.2, label=label))
    ax.legend(handles=handles, loc=loc, bbox_to_anchor=bbox, ncol=ncol or len(items),
              frameon=False, fontsize=fontsize, handletextpad=0.6, columnspacing=1.3)


print("Generating diagrams for 'Shortest Path and Widest Path Algorithms'...")

# ==========================================================================
# 1. BELLMAN-FORD ALGORITHM
# ==========================================================================

def bellman_ford_steps(nodes, edges, source):
    """edges: list of (u, v, w). Returns list of passes; each pass is a list
    of relaxation events (u, v, w, old_dist, new_dist, improved:bool),
    plus the list of dist-dicts snapshotted after each pass."""
    dist = {n: math.inf for n in nodes}
    dist[source] = 0
    passes = []
    dist_snapshots = [dict(dist)]

    for i in range(len(nodes) - 1):
        events = []
        changed = False
        for (u, v, w) in edges:
            old = dist[v]
            if dist[u] + w < dist[v]:
                dist[v] = dist[u] + w
                events.append((u, v, w, old, dist[v], True))
                changed = True
            else:
                events.append((u, v, w, old, dist[v], False))
        passes.append(events)
        dist_snapshots.append(dict(dist))
        if not changed:
            break
    return passes, dist_snapshots, dist


def draw_bellman_ford():
    nodes = ["A", "B", "C", "D", "E"]
    edges = [
        ("A", "B", 6), ("A", "C", 7),
        ("B", "D", 5), ("B", "C", 8), ("B", "E", -4),
        ("D", "B", -2),
        ("C", "D", -3), ("C", "E", 9),
        ("E", "D", 7), ("E", "A", 2),
    ]
    source = "A"
    pos = {
        "A": (-1.0, 0.55), "B": (0.0, 1.0), "C": (0.0, -1.0),
        "D": (1.0, 0.55), "E": (1.0, -0.55),
    }

    passes, snapshots, final_dist = bellman_ford_steps(nodes, edges, source)
    n_panels = 1 + len(passes)  # initial + each pass (final pass already converged state)
    n_panels_total = n_panels + 1  # + a summary "shortest path tree" panel

    ncols = 3
    nrows = math.ceil(n_panels_total / ncols)
    fig, gs = new_fig(nrows, ncols, (5.2 * ncols, 4.6 * nrows),
                       "Bellman-Ford Algorithm — Proses Relaksasi Edge dari Source A\n"
                       "(graf berarah, mengandung bobot negatif, tanpa siklus negatif)")

    def dist_label(n, d):
        v = d.get(n, math.inf)
        return "0" if n == source and v == 0 else ("∞" if math.isinf(v) else str(v))

    def draw_panel(ax, dist_now, relaxed_edges=None, improved_edges=None, panel_title=""):
        relaxed_edges = relaxed_edges or set()
        improved_edges = improved_edges or set()

        node_colors = {}
        for n in nodes:
            if n == source:
                node_colors[n] = NODE_SOURCE
            elif math.isinf(dist_now.get(n, math.inf)):
                node_colors[n] = "#ffffff"
            else:
                node_colors[n] = NODE_DEFAULT

        def color_fn(u, v, w):
            if (u, v) in improved_edges:
                return HIGHLIGHT
            if (u, v) in relaxed_edges:
                return INK_SECONDARY
            return EDGE_NEGATIVE if w < 0 else EDGE_DEFAULT

        def width_fn(u, v, w):
            return 3.4 if (u, v) in improved_edges else (2.2 if (u, v) in relaxed_edges else 1.6)

        def conn_fn(u, v, w):
            # avoid overlapping A-B/B-A style pairs by curving one direction
            if (v, u, ) in [(e[1], e[0]) for e in edges if e[0] == v and e[1] == u]:
                pass
            return "arc3,rad=0.18" if (u, v) in [("D", "B")] else "arc3,rad=0.0"

        draw_edges(ax, pos, edges, directed=True, color_fn=color_fn, width_fn=width_fn,
                   label_fn=lambda u, v, w: f"{w:+d}" if w < 0 else str(w),
                   connectionstyle_fn=conn_fn, label_offset=0.09)
        node_ec = {n: (HIGHLIGHT if n in improved_edges_nodes(improved_edges) else INK_PRIMARY) for n in nodes}
        draw_nodes(ax, pos, node_colors, node_edgecolors=node_ec)
        for n in nodes:
            x, y = pos[n]
            ax.text(x, y - 0.24, dist_label(n, dist_now), ha="center", va="center",
                    fontsize=12, fontweight="bold", color=HIGHLIGHT if n != source else VIOLET,
                    bbox=dict(boxstyle="round,pad=0.18", fc=SURFACE, ec=BASELINE, lw=0.8))
        style_axes(ax)
        ax.set_title(panel_title, fontsize=12.5, color=INK_PRIMARY, fontweight="bold", pad=6)

    def improved_edges_nodes(improved_edges):
        return {v for (u, v) in improved_edges}

    panel_idx = 0
    # Panel 0: initial state
    ax = fig.add_subplot(gs[0, 0])
    draw_panel(ax, snapshots[0], panel_title=f"Inisialisasi: dist[{source}]=0, lainnya=\u221e")
    panel_idx += 1

    # Panels for each pass
    for i, events in enumerate(passes):
        row, col = divmod(panel_idx, ncols)
        ax = fig.add_subplot(gs[row, col])
        improved = {(u, v) for (u, v, w, old, new, imp) in events if imp}
        relaxed = {(u, v) for (u, v, w, old, new, imp) in events}
        draw_panel(ax, snapshots[i + 1], relaxed_edges=relaxed, improved_edges=improved,
                   panel_title=f"Iterasi {i + 1}: {len(improved)} edge di-update"
                   if improved else f"Iterasi {i + 1}: konvergen (tidak ada update)")
        panel_idx += 1

    # Final panel: shortest-path tree summary
    row, col = divmod(panel_idx, ncols)
    ax = fig.add_subplot(gs[row, col])
    # reconstruct predecessor for SPT using final_dist
    pred = {}
    for v in nodes:
        if v == source:
            continue
        for (u, uu, w) in edges:
            pass
    # simple predecessor recompute
    for (u, v, w) in edges:
        if final_dist[u] + w == final_dist[v]:
            pred[v] = u
    tree_edges = {(pred[v], v) for v in pred}

    def color_fn_final(u, v, w):
        return HIGHLIGHT if (u, v) in tree_edges else EDGE_DEFAULT

    def width_fn_final(u, v, w):
        return 3.6 if (u, v) in tree_edges else 1.3

    draw_edges(ax, pos, edges, directed=True, color_fn=color_fn_final, width_fn=width_fn_final,
               label_fn=lambda u, v, w: f"{w:+d}" if w < 0 else str(w), label_offset=0.09,
               connectionstyle_fn=lambda u, v, w: "arc3,rad=0.18" if (u, v) == ("D", "B") else "arc3,rad=0.0")
    node_colors_final = {n: (NODE_SOURCE if n == source else NODE_DEFAULT) for n in nodes}
    draw_nodes(ax, pos, node_colors_final)
    for n in nodes:
        x, y = pos[n]
        ax.text(x, y - 0.24, dist_label(n, final_dist), ha="center", va="center",
                fontsize=12, fontweight="bold", color=HIGHLIGHT if n != source else VIOLET,
                bbox=dict(boxstyle="round,pad=0.18", fc=SURFACE, ec=BASELINE, lw=0.8))
    style_axes(ax)
    ax.set_title("Hasil Akhir: Shortest-Path Tree dari A", fontsize=12.5,
                 color=INK_PRIMARY, fontweight="bold", pad=6)
    legend_swatch(ax, [
        ("Source", NODE_SOURCE, "node"),
        ("Belum terjangkau", "#ffffff", "node"),
        ("Shortest-path tree", HIGHLIGHT, "line"),
        ("Bobot negatif", EDGE_NEGATIVE, "line"),
    ], loc="lower center", bbox=(0.5, -0.18), ncol=4, fontsize=9.5)

    fig.text(0.5, 0.005,
              "Bellman-Ford melakukan relaksasi seluruh edge sebanyak |V|-1 kali; mampu menangani bobot negatif "
              "selama tidak ada siklus negatif. Angka di bawah tiap node = estimasi jarak terpendek saat ini dari source.",
              ha="center", fontsize=9.5, color=INK_SECONDARY, wrap=True)

    save(fig, "01_bellman_ford.png")


draw_bellman_ford()

# ==========================================================================
# 2. DIJKSTRA'S ALGORITHM
# ==========================================================================

def dijkstra_with_order(nodes, edges, source):
    """edges: list of (u, v, w) representing an UNDIRECTED graph (both dirs)."""
    adj = {n: [] for n in nodes}
    for (u, v, w) in edges:
        adj[u].append((v, w))
        adj[v].append((u, w))

    dist = {n: math.inf for n in nodes}
    dist[source] = 0
    pred = {}
    visited = set()
    order = []
    heap = [(0, source)]
    while heap:
        d, u = heapq.heappop(heap)
        if u in visited:
            continue
        visited.add(u)
        order.append(u)
        for (v, w) in adj[u]:
            if v in visited:
                continue
            nd = d + w
            if nd < dist[v]:
                dist[v] = nd
                pred[v] = u
                heapq.heappush(heap, (nd, v))
    return order, dist, pred


def draw_dijkstra():
    nodes = ["A", "B", "C", "D", "E", "F"]
    edges = [
        ("A", "B", 4), ("A", "C", 2), ("B", "C", 1), ("B", "D", 5),
        ("C", "D", 8), ("C", "E", 10), ("D", "E", 2), ("D", "F", 6), ("E", "F", 3),
    ]
    source = "A"
    pos = {
        "A": (-1.05, 0.35), "B": (-0.35, 1.0), "C": (-0.35, -0.55),
        "D": (0.55, 0.75), "E": (0.55, -0.75), "F": (1.15, 0.0),
    }

    order, dist, pred = dijkstra_with_order(nodes, edges, source)
    tree_edges = set()
    for v, u in pred.items():
        tree_edges.add((u, v))
        tree_edges.add((v, u))

    fig, gs = new_fig(1, 2, (13.5, 6.3),
                       "Dijkstra's Algorithm — Non-negative Weighted Graph")

    # ---- Panel 1: visiting order ----
    ax1 = fig.add_subplot(gs[0, 0])
    visit_rank = {n: i for i, n in enumerate(order)}
    ramp = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95"]

    def node_color_visit(n):
        idx = visit_rank[n]
        return ramp[min(idx, len(ramp) - 1)]

    node_colors1 = {n: (NODE_SOURCE if n == source else node_color_visit(n)) for n in nodes}
    draw_edges(ax1, pos, edges, directed=False,
               color_fn=lambda u, v, w: EDGE_DEFAULT, width_fn=lambda u, v, w: 1.6,
               label_fn=lambda u, v, w: str(w))
    draw_nodes(ax1, pos, node_colors1)
    for n in nodes:
        x, y = pos[n]
        ax1.text(x, y + 0.20, f"#{visit_rank[n] + 1}", ha="center", va="center",
                  fontsize=10.5, fontweight="bold", color=INK_SECONDARY,
                  bbox=dict(boxstyle="round,pad=0.12", fc=SURFACE, ec=BASELINE, lw=0.7))
    style_axes(ax1)
    ax1.set_title("Urutan Node di-Visit (Finalisasi)\n#1 = pertama diproses (jarak terkecil)",
                   fontsize=12.5, fontweight="bold", pad=8)
    legend_swatch(ax1, [
        ("Source", NODE_SOURCE, "node"),
        ("Visit awal", ramp[0], "node"),
        ("Visit akhir", ramp[-1], "node"),
    ], loc="lower center", bbox=(0.5, -0.10), ncol=3, fontsize=9.5)

    # ---- Panel 2: final shortest path tree ----
    ax2 = fig.add_subplot(gs[0, 1])

    def color_fn2(u, v, w):
        return HIGHLIGHT if (u, v) in tree_edges else EDGE_DEFAULT

    def width_fn2(u, v, w):
        return 3.6 if (u, v) in tree_edges else 1.4

    draw_edges(ax2, pos, edges, directed=False, color_fn=color_fn2, width_fn=width_fn2,
               label_fn=lambda u, v, w: str(w))
    node_colors2 = {n: (NODE_SOURCE if n == source else NODE_VISITED) for n in nodes}
    draw_nodes(ax2, pos, node_colors2)
    for n in nodes:
        x, y = pos[n]
        ax2.text(x, y - 0.24, str(dist[n]), ha="center", va="center", fontsize=12,
                  fontweight="bold", color=HIGHLIGHT if n != source else VIOLET,
                  bbox=dict(boxstyle="round,pad=0.18", fc=SURFACE, ec=BASELINE, lw=0.8))
    style_axes(ax2)
    ax2.set_title("Shortest Path Tree Akhir dari Source A\n(angka di bawah node = total jarak terpendek)",
                   fontsize=12.5, fontweight="bold", pad=8)
    legend_swatch(ax2, [
        ("Source", NODE_SOURCE, "node"),
        ("Node terfinalisasi", NODE_VISITED, "node"),
        ("Jalur terpendek", HIGHLIGHT, "line"),
    ], loc="lower center", bbox=(0.5, -0.10), ncol=3, fontsize=9.5)

    fig.text(0.5, 0.01,
              "Dijkstra memproses node dengan jarak sementara terkecil terlebih dahulu (greedy) dan hanya valid untuk bobot non-negatif.",
              ha="center", fontsize=9.5, color=INK_SECONDARY)

    save(fig, "02_dijkstra.png")


draw_dijkstra()

# ==========================================================================
# 3. FLOYD-WARSHALL ALGORITHM
# ==========================================================================

def floyd_warshall(nodes, edges):
    dist = {u: {v: math.inf for v in nodes} for u in nodes}
    nxt = {u: {v: None for v in nodes} for u in nodes}
    for n in nodes:
        dist[n][n] = 0
        nxt[n][n] = n
    for (u, v, w) in edges:
        dist[u][v] = w
        nxt[u][v] = v

    dist_init = copy.deepcopy(dist)

    for k in nodes:
        for i in nodes:
            for j in nodes:
                if dist[i][k] + dist[k][j] < dist[i][j]:
                    dist[i][j] = dist[i][k] + dist[k][j]
                    nxt[i][j] = nxt[i][k]
    return dist_init, dist, nxt


def fw_path(nxt, u, v):
    if nxt[u][v] is None:
        return None
    path = [u]
    while u != v:
        u = nxt[u][v]
        path.append(u)
    return path


def matrix_table(ax, nodes, dist, title):
    ax.axis("off")
    cell_text = []
    for i in nodes:
        row = []
        for j in nodes:
            d = dist[i][j]
            row.append("0" if i == j else ("\u221e" if math.isinf(d) else str(d)))
        cell_text.append(row)
    tbl = ax.table(cellText=cell_text, rowLabels=nodes, colLabels=nodes,
                    cellLoc="center", loc="center", bbox=[0.08, 0.05, 0.92, 0.82])
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(12)
    for (r, c), cell in tbl.get_celld().items():
        cell.set_edgecolor(GRIDLINE)
        if r == 0 or c == -1:
            cell.set_facecolor("#eef2f8")
            cell.set_text_props(fontweight="bold", color=INK_PRIMARY)
        else:
            cell.set_facecolor(SURFACE)
            cell.set_text_props(color=INK_PRIMARY)
    ax.set_title(title, fontsize=13, fontweight="bold", pad=10)


def draw_floyd_warshall():
    nodes = ["A", "B", "C", "D", "E"]
    edges = [
        ("A", "B", 3), ("A", "D", 7), ("B", "C", 1),
        ("C", "D", 2), ("C", "E", 5), ("D", "E", 4), ("E", "B", 6),
    ]
    pos = {
        "A": (-1.05, 0.15), "B": (-0.35, 1.05), "C": (0.75, 0.75),
        "D": (0.55, -0.85), "E": (-0.55, -0.95),
    }

    dist_init, dist_final, nxt = floyd_warshall(nodes, edges)

    fig, gs = new_fig(2, 3, (17.5, 11.0),
                       "Floyd-Warshall Algorithm — All-Pairs Shortest Path (5 node)",
                       height_ratios=[1.15, 1.0])

    # Panel A: original graph
    axg = fig.add_subplot(gs[0, 0])
    draw_edges(axg, pos, edges, directed=True,
               color_fn=lambda u, v, w: EDGE_DEFAULT, width_fn=lambda u, v, w: 1.8,
               label_fn=lambda u, v, w: str(w))
    draw_nodes(axg, pos, {n: NODE_DEFAULT for n in nodes})
    style_axes(axg)
    axg.set_title("Graf Asli (berarah, berbobot)", fontsize=13, fontweight="bold", pad=10)

    # Panel B: initial distance matrix
    axm1 = fig.add_subplot(gs[0, 1])
    matrix_table(axm1, nodes, dist_init, "Matriks Jarak — Sebelum\n(D\u2070 = bobot edge langsung)")

    # Panel C: final distance matrix
    axm2 = fig.add_subplot(gs[0, 2])
    matrix_table(axm2, nodes, dist_final, "Matriks Jarak — Sesudah\n(D\u207f = shortest path semua pasangan)")

    # Panel D: graph with union of all shortest paths highlighted
    axp = fig.add_subplot(gs[1, :])
    used_edges = set()
    for i in nodes:
        for j in nodes:
            if i == j or math.isinf(dist_final[i][j]):
                continue
            p = fw_path(nxt, i, j)
            for a, b in zip(p, p[1:]):
                used_edges.add((a, b))

    def color_fn(u, v, w):
        return HIGHLIGHT if (u, v) in used_edges else EDGE_DEFAULT

    def width_fn(u, v, w):
        return 3.2 if (u, v) in used_edges else 1.4

    pos_wide = {k: (v[0] * 0.55, v[1]) for k, v in pos.items()}
    draw_edges(axp, pos_wide, edges, directed=True, color_fn=color_fn, width_fn=width_fn,
               label_fn=lambda u, v, w: str(w), label_offset=0.07)
    draw_nodes(axp, pos_wide, {n: NODE_VISITED for n in nodes})
    style_axes(axp, xlim=(-0.75, 0.75))
    axp.set_title("Graf dengan Semua Shortest Path Antar Pasangan Node\n"
                   "(edge merah = digunakan pada shortest path setidaknya satu pasangan node)",
                   fontsize=13, fontweight="bold", pad=10)
    legend_swatch(axp, [
        ("Edge asli", EDGE_DEFAULT, "line"),
        ("Digunakan pada shortest path", HIGHLIGHT, "line"),
    ], loc="lower center", bbox=(0.5, -0.08), ncol=2, fontsize=10.5)

    fig.text(0.5, 0.005,
              "Floyd-Warshall menghitung shortest path SEMUA pasangan node sekaligus dengan pemrograman dinamis: "
              "D[i][j] = min(D[i][j], D[i][k] + D[k][j]) untuk setiap node perantara k.",
              ha="center", fontsize=9.5, color=INK_SECONDARY)

    save(fig, "03_floyd_warshall.png")


draw_floyd_warshall()

# ==========================================================================
# 4. BREADTH-FIRST SEARCH (BFS)
# ==========================================================================

def bfs_levels(nodes, edges, source):
    adj = {n: [] for n in nodes}
    for (u, v) in edges:
        adj[u].append(v)
        adj[v].append(u)
    level = {source: 0}
    pred = {}
    order = [source]
    frontier = [source]
    while frontier:
        nxt_frontier = []
        for u in frontier:
            for v in adj[u]:
                if v not in level:
                    level[v] = level[u] + 1
                    pred[v] = u
                    order.append(v)
                    nxt_frontier.append(v)
        frontier = nxt_frontier
    return level, pred, order


def draw_bfs():
    nodes = ["A", "B", "C", "D", "E", "F", "G"]
    edges = [
        ("A", "B"), ("A", "C"), ("B", "D"), ("B", "E"),
        ("C", "E"), ("C", "F"), ("D", "G"), ("E", "G"), ("F", "G"),
    ]
    source = "A"
    pos = {
        "A": (-1.15, 0.0), "B": (-0.55, 0.85), "C": (-0.55, -0.85),
        "D": (0.15, 1.15), "E": (0.15, 0.0), "F": (0.15, -1.15),
        "G": (0.95, 0.0),
    }

    level, pred, order = bfs_levels(nodes, edges, source)
    tree_edges = {(pred[v], v) for v in pred} | {(v, pred[v]) for v in pred}

    level_colors = {0: NODE_SOURCE, 1: BLUE, 2: ORANGE, 3: AQUA, 4: YELLOW}
    max_level = max(level.values())

    fig, gs = new_fig(1, 1, (10.5, 8.0),
                       "Breadth-First Search (BFS) — Traversal Level-by-Level dari Source A\n"
                       "(graf tidak berbobot)")
    ax = fig.add_subplot(gs[0, 0])

    def color_fn(u, v, w=None):
        if (u, v) in tree_edges:
            return INK_SECONDARY
        return EDGE_DEFAULT

    def width_fn(u, v, w=None):
        return 2.6 if (u, v) in tree_edges else 1.3

    def style_fn(u, v, w=None):
        return "-" if (u, v) in tree_edges else "--"

    edges3 = [(u, v, None) for (u, v) in edges]
    draw_edges(ax, pos, edges3, directed=False, color_fn=color_fn, width_fn=width_fn,
               style_fn=style_fn)
    node_colors = {n: level_colors.get(level[n], VIOLET) for n in nodes}
    draw_nodes(ax, pos, node_colors)
    for n in nodes:
        x, y = pos[n]
        ax.text(x, y - 0.26, f"level {level[n]} | urutan #{order.index(n) + 1}",
                ha="center", va="center", fontsize=9.5, fontweight="bold", color=INK_SECONDARY,
                bbox=dict(boxstyle="round,pad=0.15", fc=SURFACE, ec=BASELINE, lw=0.7))
    style_axes(ax, xlim=(-1.55, 1.55), ylim=(-1.55, 1.55))

    legend_items = [("Source (level 0)", NODE_SOURCE, "node")]
    level_names = {1: "Level 1", 2: "Level 2", 3: "Level 3", 4: "Level 4"}
    for lv in range(1, max_level + 1):
        legend_items.append((level_names.get(lv, f"Level {lv}"), level_colors.get(lv, VIOLET), "node"))
    legend_items.append(("BFS tree edge", INK_SECONDARY, "line"))
    legend_swatch(ax, legend_items, loc="lower center", bbox=(0.5, -0.10),
                  ncol=len(legend_items), fontsize=9.5)

    fig.text(0.5, 0.01,
              "BFS menjelajah graf per-level menggunakan queue (FIFO); garis putus-putus abu = edge non-tree "
              "(menghubungkan node yang sudah dikunjungi, tidak dipakai untuk traversal).",
              ha="center", fontsize=9.5, color=INK_SECONDARY)

    save(fig, "04_bfs.png")


draw_bfs()

# ==========================================================================
# 5. JOHNSON'S ALGORITHM
# ==========================================================================

def bellman_ford_dist(nodes, edges, source):
    dist = {n: math.inf for n in nodes}
    dist[source] = 0
    for _ in range(len(nodes) - 1):
        changed = False
        for (u, v, w) in edges:
            if dist[u] + w < dist[v]:
                dist[v] = dist[u] + w
                changed = True
        if not changed:
            break
    return dist


def dijkstra_dist(nodes, edges, source):
    adj = {n: [] for n in nodes}
    for (u, v, w) in edges:
        adj[u].append((v, w))
    dist = {n: math.inf for n in nodes}
    dist[source] = 0
    visited = set()
    heap = [(0, source)]
    while heap:
        d, u = heapq.heappop(heap)
        if u in visited:
            continue
        visited.add(u)
        for (v, w) in adj[u]:
            nd = d + w
            if nd < dist.get(v, math.inf):
                dist[v] = nd
                heapq.heappush(heap, (nd, v))
    return dist


def draw_johnson():
    nodes = ["A", "B", "C", "D"]
    edges = [
        ("A", "B", 3), ("A", "C", 8),
        ("B", "D", 1),
        ("C", "B", -3),
        ("D", "A", 2), ("D", "C", 5),
    ]
    VQ = "q"
    pos = {
        "A": (-0.85, 0.85), "B": (0.85, 0.85),
        "C": (-0.85, -0.85), "D": (0.85, -0.85),
    }
    pos_q = dict(pos)
    pos_q[VQ] = (0.0, 2.05)

    # --- step 1: h(v) via Bellman-Ford from virtual node q ---
    aug_edges = edges + [(VQ, n, 0) for n in nodes]
    h = bellman_ford_dist(nodes + [VQ], aug_edges, VQ)

    # sanity: no negative cycle -> h finite for all
    assert all(math.isfinite(h[n]) for n in nodes)

    # --- step 2: reweight ---
    reweighted = [(u, v, w + h[u] - h[v]) for (u, v, w) in edges]
    assert all(w >= -1e-9 for (_, _, w) in reweighted)

    # --- step 3: Dijkstra from A on reweighted graph, convert back ---
    source = "A"
    dprime = dijkstra_dist(nodes, reweighted, source)
    true_dist = {v: dprime[v] + h[v] - h[source] for v in nodes}

    # cross-check against direct Bellman-Ford on the original graph
    check = bellman_ford_dist(nodes, edges, source)
    for v in nodes:
        assert abs(true_dist[v] - check[v]) < 1e-6, (v, true_dist[v], check[v])

    fig, gs = new_fig(2, 2, (13.5, 12.0),
                       "Johnson's Algorithm — Reweighting untuk Graf dengan Bobot Negatif")

    def panel(ax, use_edges, positions, node_color_fn, edge_label_fn, title,
              highlight_edges=None, extra_node=None, dist_labels=None, ylim=None):
        highlight_edges = highlight_edges or set()

        def color_fn(u, v, w):
            if (u, v) in highlight_edges:
                return HIGHLIGHT
            if extra_node is not None and (u == extra_node or v == extra_node):
                return AQUA
            return EDGE_NEGATIVE if w < 0 else EDGE_DEFAULT

        def width_fn(u, v, w):
            return 3.2 if (u, v) in highlight_edges else 1.7

        def conn_fn(u, v, w):
            return "arc3,rad=0.15" if {u, v} == {"A", "D"} or {u, v} == {"B", "C"} else "arc3,rad=0.0"

        draw_edges(ax, positions, use_edges, directed=True, color_fn=color_fn, width_fn=width_fn,
                   label_fn=edge_label_fn, connectionstyle_fn=conn_fn, label_offset=0.10)
        all_nodes = list(positions.keys())
        node_colors = {n: node_color_fn(n) for n in all_nodes}
        draw_nodes(ax, positions, node_colors, node_size=1250, font_size=12)
        if dist_labels:
            for n, val in dist_labels.items():
                x, y = positions[n]
                ax.text(x, y - 0.30, val, ha="center", va="center", fontsize=10.5,
                        fontweight="bold", color=INK_SECONDARY,
                        bbox=dict(boxstyle="round,pad=0.14", fc=SURFACE, ec=BASELINE, lw=0.7))
        style_axes(ax, xlim=(-1.35, 1.35), ylim=ylim or (-1.35, 1.35))
        ax.set_title(title, fontsize=12.5, fontweight="bold", pad=8)

    # Panel A: original graph with negative edge
    ax1 = fig.add_subplot(gs[0, 0])
    panel(ax1, edges, pos,
          lambda n: NODE_SOURCE if n == source else NODE_DEFAULT,
          lambda u, v, w: f"{w:+d}" if w < 0 else str(w),
          "1. Graf Asli (mengandung bobot negatif)")

    # Panel B: with virtual node q
    ax2 = fig.add_subplot(gs[0, 1])
    aug_edges_disp = edges + [(VQ, n, 0) for n in nodes]
    panel(ax2, aug_edges_disp, pos_q,
          lambda n: (VIOLET if n == VQ else (NODE_SOURCE if n == source else NODE_DEFAULT)),
          lambda u, v, w: (f"{w:+d}" if w < 0 else str(w)) if u != VQ else "0",
          "2. Tambah Virtual Node q\n(edge q\u2192semua node, bobot 0)",
          extra_node=VQ,
          dist_labels={n: f"h={h[n]}" for n in nodes},
          ylim=(-1.35, 2.55))

    # Panel C: reweighted graph
    ax3 = fig.add_subplot(gs[1, 0])
    panel(ax3, reweighted, pos,
          lambda n: NODE_SOURCE if n == source else NODE_DEFAULT,
          lambda u, v, w: f"{w:.0f}",
          "3. Graf Setelah Reweighting\nw'(u,v) = w(u,v) + h(u) \u2212 h(v)  \u2265 0")

    # Panel D: final shortest paths (Dijkstra on reweighted, converted back)
    pred = {}
    for v in nodes:
        if v == source:
            continue
        for (u, vv, w) in edges:
            if vv == v and abs(true_dist[u] + w - true_dist[v]) < 1e-6:
                pred[v] = u
                break
    tree_edges = {(pred[v], v) for v in pred}
    ax4 = fig.add_subplot(gs[1, 1])
    panel(ax4, edges, pos,
          lambda n: NODE_SOURCE if n == source else NODE_VISITED,
          lambda u, v, w: f"{w:+d}" if w < 0 else str(w),
          f"4. Shortest Path Final dari {source}\n(dihitung via Dijkstra pada graf reweighted, dikonversi kembali)",
          highlight_edges=tree_edges,
          dist_labels={n: f"dist={true_dist[n]:.0f}" for n in nodes})

    legend_swatch(fig.axes[-1], [
        ("Source", NODE_SOURCE, "node"),
        ("Virtual node q", VIOLET, "node"),
        ("Shortest path", HIGHLIGHT, "line"),
        ("Bobot negatif", EDGE_NEGATIVE, "line"),
    ], loc="lower center", bbox=(-0.15, -0.30), ncol=4, fontsize=10)

    fig.text(0.5, 0.01,
              "Johnson's Algorithm menggabungkan Bellman-Ford (sekali, dari node virtual, untuk menghitung h) dan "
              "Dijkstra (dari setiap node, pada graf ter-reweight) sehingga all-pairs shortest path pada graf "
              "berbobot negatif tetap bisa dihitung secepat Dijkstra.",
              ha="center", fontsize=9.5, color=INK_SECONDARY)

    save(fig, "05_johnson.png")


draw_johnson()

# ==========================================================================
# 6. MODIFIED DIJKSTRA'S ALGORITHM (WIDEST PATH / MAX BOTTLENECK)
# ==========================================================================

def widest_path_all(nodes, edges, source):
    """edges: undirected (u, v, capacity). Maximize the MIN capacity along path."""
    adj = {n: [] for n in nodes}
    for (u, v, w) in edges:
        adj[u].append((v, w))
        adj[v].append((u, w))

    bottleneck = {n: -math.inf for n in nodes}
    bottleneck[source] = math.inf
    pred = {}
    visited = set()
    heap = [(-math.inf, source)]  # max-heap via negation
    while heap:
        neg_b, u = heapq.heappop(heap)
        b = -neg_b
        if u in visited:
            continue
        visited.add(u)
        for (v, w) in adj[u]:
            if v in visited:
                continue
            cand = min(b, w)
            if cand > bottleneck[v]:
                bottleneck[v] = cand
                pred[v] = u
                heapq.heappush(heap, (-cand, v))
    return bottleneck, pred


def draw_modified_dijkstra():
    nodes = ["A", "B", "C", "D", "E", "F"]
    edges = [
        ("A", "B", 10), ("A", "C", 6), ("B", "C", 5), ("B", "D", 8),
        ("C", "D", 2), ("C", "E", 9), ("D", "E", 7), ("D", "F", 4), ("E", "F", 12),
    ]
    source = "A"
    pos = {
        "A": (-1.15, 0.15), "B": (-0.45, 1.05), "C": (-0.45, -0.85),
        "D": (0.45, 0.85), "E": (0.45, -0.65), "F": (1.15, 0.15),
    }

    bottleneck, pred = widest_path_all(nodes, edges, source)
    tree_edges = {(pred[v], v) for v in pred} | {(v, pred[v]) for v in pred}

    fig, gs = new_fig(1, 1, (10.5, 8.0),
                       "Modified Dijkstra's Algorithm — Widest Path (Maximum Bottleneck Capacity)\n"
                       "graf kapasitas link, memilih jalur dengan MEMAKSIMALKAN nilai minimum (bottleneck), bukan menjumlahkan bobot")
    ax = fig.add_subplot(gs[0, 0])

    def color_fn(u, v, w):
        return HIGHLIGHT if (u, v) in tree_edges else EDGE_DEFAULT

    def width_fn(u, v, w):
        return 3.6 if (u, v) in tree_edges else 1.5

    draw_edges(ax, pos, edges, directed=False, color_fn=color_fn, width_fn=width_fn,
               label_fn=lambda u, v, w: str(w))
    node_colors = {n: (NODE_SOURCE if n == source else NODE_VISITED) for n in nodes}
    draw_nodes(ax, pos, node_colors)
    for n in nodes:
        x, y = pos[n]
        b = bottleneck[n]
        label = "\u221e" if math.isinf(b) else str(int(b))
        ax.text(x, y - 0.25, f"bottleneck={label}", ha="center", va="center", fontsize=10,
                fontweight="bold", color=HIGHLIGHT if n != source else VIOLET,
                bbox=dict(boxstyle="round,pad=0.15", fc=SURFACE, ec=BASELINE, lw=0.7))
    style_axes(ax, xlim=(-1.55, 1.55), ylim=(-1.35, 1.55))
    legend_swatch(ax, [
        ("Source", NODE_SOURCE, "node"),
        ("Node terfinalisasi", NODE_VISITED, "node"),
        ("Widest-path tree", HIGHLIGHT, "line"),
    ], loc="lower center", bbox=(0.5, -0.06), ncol=3, fontsize=10.5)

    example = (f"Contoh: rute langsung A\u2192C berkapasitas 6, tapi rute A\u2192B\u2192D\u2192E\u2192C\n"
               f"memberi bottleneck {int(bottleneck['C'])} (link terkecil di sepanjang rute = {int(bottleneck['C'])}) \u2014 lebih besar meski lebih banyak hop.\n"
               f"Modified Dijkstra memilih rute dengan bottleneck TERBESAR, bukan total kapasitas/bobot terkecil.")
    fig.text(0.5, 0.015, example, ha="center", fontsize=9.8, color=INK_SECONDARY)

    save(fig, "06_modified_dijkstra.png")


draw_modified_dijkstra()

# ==========================================================================
# 7. MAXIMUM CAPACITY PATH (WIDEST PATH, SOURCE -> SPECIFIC DESTINATION)
# ==========================================================================

def widest_path_to(nodes, edges, source, target):
    bottleneck, pred = widest_path_all(nodes, edges, source)
    path = [target]
    v = target
    while v != source:
        v = pred[v]
        path.append(v)
    path.reverse()
    return path, bottleneck[target]


def sum_shortest_path_to(nodes, edges, source, target):
    adj = {n: [] for n in nodes}
    for (u, v, w) in edges:
        adj[u].append((v, w))
        adj[v].append((u, w))
    dist = {n: math.inf for n in nodes}
    dist[source] = 0
    pred = {}
    visited = set()
    heap = [(0, source)]
    while heap:
        d, u = heapq.heappop(heap)
        if u in visited:
            continue
        visited.add(u)
        for (v, w) in adj[u]:
            nd = d + w
            if nd < dist[v]:
                dist[v] = nd
                pred[v] = u
                heapq.heappush(heap, (nd, v))
    path = [target]
    v = target
    while v != source:
        v = pred[v]
        path.append(v)
    path.reverse()
    return path, dist[target]


def draw_max_capacity_path():
    nodes = ["A", "B", "C", "D", "E", "F"]
    edges = [
        ("A", "B", 7), ("A", "C", 4), ("B", "D", 9), ("C", "D", 3),
        ("C", "E", 6), ("D", "F", 5), ("E", "F", 8), ("B", "E", 2),
    ]
    source, target = "A", "F"
    pos = {
        "A": (-1.2, 0.0), "B": (-0.45, 0.95), "C": (-0.45, -0.95),
        "D": (0.45, 0.6), "E": (0.45, -0.75), "F": (1.2, 0.0),
    }

    widest_path, bottleneck_val = widest_path_to(nodes, edges, source, target)
    widest_edges = {(u, v) for u, v in zip(widest_path, widest_path[1:])}
    widest_edges |= {(v, u) for u, v in zip(widest_path, widest_path[1:])}
    widest_bneck_seq = min(dict(((u, v), w) for u, v, w in edges + [(v, u, w) for u, v, w in edges])[e]
                            for e in zip(widest_path, widest_path[1:]))

    alt_path, alt_sum = sum_shortest_path_to(nodes, edges, source, target)
    alt_edges = {(u, v) for u, v in zip(alt_path, alt_path[1:])}
    alt_edges |= {(v, u) for u, v in zip(alt_path, alt_path[1:])}
    w_lookup = {}
    for (u, v, w) in edges:
        w_lookup[(u, v)] = w
        w_lookup[(v, u)] = w
    alt_bottleneck = min(w_lookup[e] for e in zip(alt_path, alt_path[1:]))

    fig, gs = new_fig(1, 1, (10.5, 8.6),
                       "Maximum Capacity Path — Widest Path dari Source ke Destination\n"
                       f"Source = {source}, Destination = {target}")
    ax = fig.add_subplot(gs[0, 0])

    def color_fn(u, v, w):
        if (u, v) in widest_edges:
            return HIGHLIGHT
        if (u, v) in alt_edges:
            return ORANGE
        return EDGE_DEFAULT

    def width_fn(u, v, w):
        if (u, v) in widest_edges:
            return 3.8
        if (u, v) in alt_edges:
            return 2.6
        return 1.4

    def style_fn(u, v, w):
        return "--" if ((u, v) in alt_edges and (u, v) not in widest_edges) else "-"

    draw_edges(ax, pos, edges, directed=False, color_fn=color_fn, width_fn=width_fn,
               style_fn=style_fn, label_fn=lambda u, v, w: str(w))
    node_colors = {n: NODE_DEFAULT for n in nodes}
    node_colors[source] = NODE_SOURCE
    node_colors[target] = NODE_TARGET
    draw_nodes(ax, pos, node_colors)
    style_axes(ax, xlim=(-1.55, 1.55), ylim=(-1.35, 1.35))

    legend_swatch(ax, [
        ("Source", NODE_SOURCE, "node"),
        ("Destination", NODE_TARGET, "node"),
        (f"Widest path (bottleneck={int(bottleneck_val)})", HIGHLIGHT, "line"),
        (f"Alternatif shortest-sum (bottleneck={int(alt_bottleneck)})", ORANGE, "line"),
    ], loc="lower center", bbox=(0.5, -0.08), ncol=2, fontsize=9.8)

    info = (f"Widest path: {' \u2192 '.join(widest_path)}  |  bottleneck (kapasitas minimum di jalur) = {int(bottleneck_val)}\n"
            f"Alternatif '{' \u2192 '.join(alt_path)}' (total bobot tersendah = {alt_sum}) hanya berkapasitas bottleneck {int(alt_bottleneck)} \u2014 "
            f"lebih kecil, meski total bobotnya lebih rendah.")
    fig.text(0.5, -0.05, info, ha="center", fontsize=9.8, color=INK_SECONDARY)

    save(fig, "07_maximum_capacity_path.png")


draw_max_capacity_path()

# ==========================================================================
# 8. SUURBALLE'S ALGORITHM (TWO EDGE-DISJOINT SHORTEST PATHS)
# ==========================================================================

def suurballe_two_paths(nodes, edges, source, target):
    """Finds the minimum-total-cost pair of EDGE-DISJOINT source->target paths
    using a min-cost-flow formulation (equivalent to what Suurballe's algorithm
    achieves): send 2 units of flow from source to target, capacity 1 per edge."""
    G = nx.DiGraph()
    for n in nodes:
        G.add_node(n, demand=0)
    G.nodes[source]["demand"] = -2
    G.nodes[target]["demand"] = 2
    for (u, v, w) in edges:
        G.add_edge(u, v, capacity=1, weight=w)

    flow_dict = nx.min_cost_flow(G)
    total_cost = sum(edata["weight"] * flow_dict[u][v]
                      for u, v, edata in G.edges(data=True) if flow_dict[u][v] > 0)

    remaining = {}
    for u in flow_dict:
        for v, f in flow_dict[u].items():
            if f > 0:
                remaining.setdefault(u, []).append(v)

    paths = []
    for _ in range(2):
        path = [source]
        cur = source
        while cur != target:
            nxt = remaining[cur].pop()
            if not remaining[cur]:
                del remaining[cur]
            path.append(nxt)
            cur = nxt
        paths.append(path)
    return paths, total_cost


def draw_suurballe():
    nodes = ["A", "B", "C", "D", "E", "F"]
    edges = [
        ("A", "B", 1), ("A", "C", 4),
        ("B", "D", 2), ("C", "D", 1),
        ("D", "F", 2), ("D", "E", 1), ("E", "F", 2),
    ]
    source, target = "A", "F"
    pos = {
        "A": (-1.3, 0.0), "B": (-0.55, 0.85), "C": (-0.55, -0.85),
        "D": (0.35, 0.0), "E": (0.95, -0.9), "F": (1.3, 0.6),
    }

    paths, total_cost = suurballe_two_paths(nodes, edges, source, target)
    w_lookup = {(u, v): w for (u, v, w) in edges}
    paths = sorted(paths, key=lambda p: sum(w_lookup[e] for e in zip(p, p[1:])))
    path1, path2 = paths[0], paths[1]  # path1 = primary (cheaper), path2 = backup
    edges1 = set(zip(path1, path1[1:]))
    edges2 = set(zip(path2, path2[1:]))
    cost1 = sum(w for (u, v, w) in edges if (u, v) in edges1)
    cost2 = sum(w for (u, v, w) in edges if (u, v) in edges2)
    shared_nodes = (set(path1) & set(path2)) - {source, target}

    fig, gs = new_fig(1, 1, (10.5, 8.4),
                       "Suurballe's Algorithm — Dua Jalur Edge-Disjoint untuk Routing Redundan\n"
                       f"Source = {source}, Destination = {target} (backup path tidak berbagi satu pun link dengan primary path)")
    ax = fig.add_subplot(gs[0, 0])

    def color_fn(u, v, w):
        if (u, v) in edges1:
            return HIGHLIGHT
        if (u, v) in edges2:
            return HIGHLIGHT2
        return EDGE_DEFAULT

    def width_fn(u, v, w):
        return 3.6 if ((u, v) in edges1 or (u, v) in edges2) else 1.4

    def conn_fn(u, v, w):
        if (u, v) in edges1 and (u, v) in edges2:
            return "arc3,rad=0.0"
        if (u, v) in edges2:
            return "arc3,rad=0.12"
        return "arc3,rad=0.0"

    draw_edges(ax, pos, edges, directed=True, color_fn=color_fn, width_fn=width_fn,
               label_fn=lambda u, v, w: str(w), connectionstyle_fn=conn_fn, label_offset=0.09)
    node_colors = {n: NODE_DEFAULT for n in nodes}
    node_colors[source] = NODE_SOURCE
    node_colors[target] = NODE_TARGET
    for n in shared_nodes:
        node_colors[n] = YELLOW
    draw_nodes(ax, pos, node_colors)
    style_axes(ax, xlim=(-1.65, 1.65), ylim=(-1.35, 1.35))

    legend_swatch(ax, [
        ("Source", NODE_SOURCE, "node"),
        ("Destination", NODE_TARGET, "node"),
        ("Node terpakai 2 jalur (bukan edge)", YELLOW, "node"),
        (f"Primary path (cost={cost1})", HIGHLIGHT, "line"),
        (f"Backup path - edge disjoint (cost={cost2})", HIGHLIGHT2, "line"),
    ], loc="lower center", bbox=(0.5, -0.11), ncol=3, fontsize=9.3)

    info = (f"Primary: {' → '.join(path1)}  (cost={cost1})   |   Backup: {' → '.join(path2)}  (cost={cost2})   |   Total cost minimum = {total_cost}\n"
            "Kedua jalur TIDAK berbagi satu edge pun (edge-disjoint) sehingga kegagalan satu link tidak memutus kedua jalur sekaligus \u2014 "
            "cocok untuk backup path routing.")
    fig.text(0.5, -0.045, info, ha="center", fontsize=9.6, color=INK_SECONDARY)

    save(fig, "08_suurballe.png")


draw_suurballe()

print("\nSelesai! Semua 8 diagram berhasil dibuat di:", OUTDIR)
