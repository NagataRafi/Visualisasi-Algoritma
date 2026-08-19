"""
combine_diagrams.py
====================

Menggabungkan 8 file diagram PNG hasil `generate_diagrams.py`
(01_bellman_ford.png ... 08_suurballe.png) menjadi SATU gambar besar
berlayout grid, dikelompokkan menjadi dua bagian:

    - Shortest Path Algorithms : Bellman-Ford, Dijkstra, Floyd-Warshall,
                                  BFS, Johnson's Algorithm
    - Widest Path Algorithms   : Modified Dijkstra, Maximum Capacity Path,
                                  Suurballe's Algorithm

Script ini TIDAK menghitung ulang graf/algoritma apa pun — ia hanya
me-load 8 file PNG yang sudah ada (via `matplotlib.image.imread`) dan
menyusunnya sebagai subplot grid, lengkap dengan judul utama, section
header per grup, nomor urut, dan judul tiap sub-gambar.

Cara pakai:
    1. Jalankan `python generate_diagrams.py` terlebih dahulu (jika 8 file
       PNG individual belum ada di folder ini).
    2. Jalankan `python combine_diagrams.py`.
    3. Hasil disimpan sebagai `09_all_algorithms_comparison.png`
       (300 dpi, background putih), siap dipakai sebagai 1 slide
       presentasi atau 1 lampiran laporan.
"""

import os
import sys

import matplotlib

matplotlib.use("Agg")

import matplotlib.image as mpimg
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(SCRIPT_DIR, "09_all_algorithms_comparison.png")

NAVY = "#1F3564"
BLUE = "#2E74B5"
ORANGE = "#C55A11"

# (nomor, file, judul, grup)
GROUP_1_SHORTEST_PATH = [
    (1, "01_bellman_ford.png", "Bellman-Ford Algorithm"),
    (2, "02_dijkstra.png", "Dijkstra's Algorithm"),
    (3, "03_floyd_warshall.png", "Floyd-Warshall Algorithm"),
    (4, "04_bfs.png", "Breadth-First Search (BFS)"),
    (5, "05_johnson.png", "Johnson's Algorithm"),
]

GROUP_2_WIDEST_PATH = [
    (6, "06_modified_dijkstra.png", "Modified Dijkstra's Algorithm"),
    (7, "07_maximum_capacity_path.png", "Maximum Capacity Path"),
    (8, "08_suurballe.png", "Suurballe's Algorithm"),
]

ALL_ITEMS = GROUP_1_SHORTEST_PATH + GROUP_2_WIDEST_PATH


def check_missing_files():
    """Kembalikan list path yang hilang dari kedelapan file PNG sumber."""
    missing = []
    for _, filename, _ in ALL_ITEMS:
        path = os.path.join(SCRIPT_DIR, filename)
        if not os.path.isfile(path):
            missing.append(filename)
    return missing


def draw_section_banner(fig, gs_row, label, color):
    """Gambar banner section header (garis + label) yang membentang penuh 2 kolom."""
    ax = fig.add_subplot(gs_row)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.add_patch(
        plt.Rectangle((0, 0.15), 1, 0.7, facecolor=color, edgecolor="none", zorder=1)
    )
    ax.text(
        0.5,
        0.5,
        label,
        transform=ax.transAxes,
        ha="center",
        va="center",
        fontsize=18,
        fontweight="bold",
        color="white",
        zorder=2,
    )


def draw_image_cell(fig, gs_cell, number, filename, title):
    """Gambar satu sub-gambar (image + nomor + judul) di dalam grid cell."""
    path = os.path.join(SCRIPT_DIR, filename)
    img = mpimg.imread(path)

    ax = fig.add_subplot(gs_cell)
    ax.imshow(img, aspect="auto")
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)

    ax.set_xlabel(title, fontsize=13, fontweight="bold", color=NAVY, labelpad=8)

    ax.text(
        -0.025,
        1.045,
        str(number),
        transform=ax.transAxes,
        ha="center",
        va="center",
        fontsize=13,
        fontweight="bold",
        color="white",
        bbox=dict(boxstyle="circle,pad=0.35", facecolor=NAVY, edgecolor="white", linewidth=1.2),
        zorder=3,
        clip_on=False,
    )


def build_combined_figure():
    fig = plt.figure(figsize=(16, 24), facecolor="white")

    # Baris grid: [judul utama, banner grup1, img,img,img (grup1),
    #              banner grup2, img,img (grup2)]
    height_ratios = [0.55, 0.45, 3, 3, 3, 0.45, 3, 3]
    gs = GridSpec(
        nrows=8,
        ncols=2,
        figure=fig,
        height_ratios=height_ratios,
        hspace=0.35,
        wspace=0.12,
        left=0.03,
        right=0.97,
        top=0.965,
        bottom=0.02,
    )

    # --- Judul utama ---
    title_ax = fig.add_subplot(gs[0, :])
    title_ax.axis("off")
    title_ax.text(
        0.5,
        0.5,
        "Perbandingan Algoritma Shortest Path & Widest Path",
        transform=title_ax.transAxes,
        ha="center",
        va="center",
        fontsize=24,
        fontweight="bold",
        color=NAVY,
    )

    # --- Grup 1: Shortest Path ---
    draw_section_banner(fig, gs[1, :], "Shortest Path Algorithms", BLUE)

    group1_cells = [gs[2, 0], gs[2, 1], gs[3, 0], gs[3, 1], gs[4, 0]]
    empty_cell_g1 = gs[4, 1]
    for cell, (number, filename, title) in zip(group1_cells, GROUP_1_SHORTEST_PATH):
        draw_image_cell(fig, cell, number, filename, title)
    fig.add_subplot(empty_cell_g1).axis("off")

    # --- Grup 2: Widest Path ---
    draw_section_banner(fig, gs[5, :], "Widest Path Algorithms", ORANGE)

    group2_cells = [gs[6, 0], gs[6, 1], gs[7, 0]]
    empty_cell_g2 = gs[7, 1]
    for cell, (number, filename, title) in zip(group2_cells, GROUP_2_WIDEST_PATH):
        draw_image_cell(fig, cell, number, filename, title)
    fig.add_subplot(empty_cell_g2).axis("off")

    return fig


def main():
    missing = check_missing_files()
    if missing:
        print("ERROR: File diagram berikut belum ditemukan di folder project:", file=sys.stderr)
        for f in missing:
            print(f"  - {f}", file=sys.stderr)
        print(
            "\nJalankan 'python generate_diagrams.py' terlebih dahulu untuk "
            "men-generate seluruh 8 file diagram, lalu jalankan ulang "
            "'python combine_diagrams.py'.",
            file=sys.stderr,
        )
        sys.exit(1)

    print("Menggabungkan 8 diagram menjadi satu gambar...")
    fig = build_combined_figure()
    fig.savefig(OUTPUT_FILE, dpi=300, facecolor="white")
    plt.close(fig)
    print(f"  -> saved {os.path.basename(OUTPUT_FILE)}")
    print(f"\nSelesai! Gambar gabungan tersimpan di: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
