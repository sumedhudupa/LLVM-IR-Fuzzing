"""
Generate publication-ready figures from experiment_results.json.

Usage:
    python scripts/generate_paper_figures.py
    python scripts/generate_paper_figures.py --input results/experiment_results.json --output results/figures
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List, Tuple

import matplotlib.pyplot as plt
import numpy as np


COLORS = {
    "llm": "#2A9D8F",
    "grammar": "#E9C46A",
    "random": "#E76F51",
    "accent": "#264653",
    "muted": "#8A8F98",
}


def _load_results(path: Path) -> Dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _set_plot_style() -> None:
    plt.style.use("seaborn-v0_8-whitegrid")
    plt.rcParams.update(
        {
            "figure.dpi": 180,
            "axes.titlesize": 14,
            "axes.labelsize": 11,
            "xtick.labelsize": 10,
            "ytick.labelsize": 10,
            "legend.fontsize": 10,
        }
    )


def _save(fig: plt.Figure, output_dir: Path, stem: str) -> None:
    png_path = output_dir / f"{stem}.png"
    svg_path = output_dir / f"{stem}.svg"
    fig.savefig(png_path, bbox_inches="tight")
    fig.savefig(svg_path, bbox_inches="tight")
    plt.close(fig)


def _short_mutation_label(name: str) -> str:
    return (
        name.replace("grammar_", "g:")
        .replace("random_", "r:")
        .replace("_", " ")
        .title()
    )


def _plot_validity_and_interest(data: Dict, output_dir: Path) -> None:
    stats = data["validity_by_source"]
    labels = ["LLM", "Grammar", "Random"]
    sources = ["llm", "grammar", "random"]

    valid_pct = [stats[s]["valid_pct"] for s in sources]
    interest_pct = [stats[s]["interesting_pct"] for s in sources]

    x = list(range(len(labels)))
    width = 0.36

    fig, ax = plt.subplots(figsize=(8, 4.8))
    ax.bar([i - width / 2 for i in x], valid_pct, width=width, color=[COLORS[s] for s in sources], alpha=0.95, label="Validity %")
    ax.bar([i + width / 2 for i in x], interest_pct, width=width, color=COLORS["accent"], alpha=0.35, label="Interesting %")

    for i, v in enumerate(valid_pct):
        ax.text(i - width / 2, v + 1.3, f"{v:.1f}", ha="center", va="bottom")
    for i, v in enumerate(interest_pct):
        ax.text(i + width / 2, v + 1.3, f"{v:.1f}", ha="center", va="bottom")

    ax.set_title("Validity and Semantic Interest by Generation Source")
    ax.set_ylabel("Percentage")
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylim(0, 110)
    ax.legend(loc="upper right")

    _save(fig, output_dir, "fig_validity_interest")


def _plot_error_distribution(data: Dict, output_dir: Path) -> None:
    errors = data["error_distribution"]

    items: List[Tuple[str, int, float]] = []
    for name, values in errors.items():
        pretty = name.replace("_", " ").title()
        items.append((pretty, values["count"], values["pct"]))

    items.sort(key=lambda t: t[1], reverse=True)

    labels = [t[0] for t in items]
    counts = [t[1] for t in items]
    pct = [t[2] for t in items]

    fig, ax = plt.subplots(figsize=(9.2, 5.2))
    bars = ax.barh(labels, counts, color=COLORS["accent"], alpha=0.88)
    ax.invert_yaxis()
    ax.set_title("Invalid IR Error Distribution")
    ax.set_xlabel("Count")

    for i, bar in enumerate(bars):
        ax.text(bar.get_width() + 0.35, bar.get_y() + bar.get_height() / 2, f"{counts[i]} ({pct[i]:.1f}%)", va="center")

    _save(fig, output_dir, "fig_error_distribution")


def _plot_error_distribution_donut(data: Dict, output_dir: Path) -> None:
    errors = data["error_distribution"]
    items = sorted(errors.items(), key=lambda item: item[1]["count"], reverse=True)

    labels = [name.replace("_", " ").title() for name, _ in items]
    counts = [values["count"] for _, values in items]
    colors = [
        "#264653",
        "#2A9D8F",
        "#E9C46A",
        "#F4A261",
        "#E76F51",
        "#7B8CDE",
        "#8A8F98",
    ][: len(labels)]

    fig, ax = plt.subplots(figsize=(7.2, 5.6))
    wedges, texts, autotexts = ax.pie(
        counts,
        labels=labels,
        autopct=lambda pct: f"{pct:.1f}%" if pct >= 4 else "",
        startangle=100,
        colors=colors,
        wedgeprops={"width": 0.42, "edgecolor": "white"},
        pctdistance=0.8,
        labeldistance=1.06,
    )

    ax.set_title("Invalid IR Error Share")
    centre = plt.Circle((0, 0), 0.38, color="white")
    ax.add_artist(centre)
    ax.text(0, 0.05, f"{sum(counts)}", ha="center", va="center", fontsize=18, fontweight="bold")
    ax.text(0, -0.1, "total errors", ha="center", va="center", fontsize=9, color=COLORS["muted"])

    _save(fig, output_dir, "fig_error_distribution_donut")


def _plot_mutation_effectiveness(data: Dict, output_dir: Path) -> None:
    effects = data["mutation_effectiveness"]

    def mutation_family(name: str) -> str:
        if name.startswith("grammar_"):
            return "grammar"
        if name.startswith("random_"):
            return "random"
        return "llm"

    names = list(effects.keys())
    valid_pct = [effects[n]["valid_pct"] for n in names]
    interesting_pct = [effects[n]["interesting_pct"] for n in names]
    totals = [effects[n]["total"] for n in names]
    colors = [COLORS[mutation_family(n)] for n in names]

    fig, ax = plt.subplots(figsize=(9.2, 6.2))
    scatter = ax.scatter(
        valid_pct,
        interesting_pct,
        s=[t * 20 for t in totals],
        c=colors,
        alpha=0.8,
        edgecolors="black",
        linewidths=0.6,
    )

    for i, n in enumerate(names):
        short = n.replace("grammar_", "g_").replace("random_", "r_")
        ax.annotate(short, (valid_pct[i], interesting_pct[i]), fontsize=8, xytext=(4, 3), textcoords="offset points")

    ax.set_title("Mutation Effectiveness: Validity vs Semantic Interest")
    ax.set_xlabel("Validity %")
    ax.set_ylabel("Interesting %")
    ax.set_xlim(-3, 103)
    ax.set_ylim(-3, 103)

    llm_proxy = plt.Line2D([0], [0], marker="o", color="w", markerfacecolor=COLORS["llm"], markeredgecolor="black", markersize=8, label="LLM strategies")
    grammar_proxy = plt.Line2D([0], [0], marker="o", color="w", markerfacecolor=COLORS["grammar"], markeredgecolor="black", markersize=8, label="Grammar mutations")
    random_proxy = plt.Line2D([0], [0], marker="o", color="w", markerfacecolor=COLORS["random"], markeredgecolor="black", markersize=8, label="Random mutations")

    ax.legend(handles=[llm_proxy, grammar_proxy, random_proxy], loc="lower right")

    _save(fig, output_dir, "fig_mutation_effectiveness")


def _plot_mutation_validity_ranking(data: Dict, output_dir: Path) -> None:
    effects = data["mutation_effectiveness"]
    items = sorted(
        effects.items(),
        key=lambda item: (item[1]["valid_pct"], item[1]["interesting_pct"]),
        reverse=True,
    )

    labels = [_short_mutation_label(name) for name, _ in items]
    valid_pct = [values["valid_pct"] for _, values in items]
    colors = [
        COLORS["llm"] if not name.startswith(("grammar_", "random_"))
        else COLORS["grammar"] if name.startswith("grammar_")
        else COLORS["random"]
        for name, _ in items
    ]
    y = np.arange(len(labels))

    fig, ax = plt.subplots(figsize=(10.4, 7.2))
    ax.hlines(y, 0, valid_pct, color=colors, linewidth=2.6, alpha=0.9)
    ax.scatter(valid_pct, y, color=colors, s=56, edgecolors="black", linewidths=0.5, zorder=3)

    for ypos, value in zip(y, valid_pct):
        ax.text(value + 1.2, ypos, f"{value:.1f}%", va="center", fontsize=8)

    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.invert_yaxis()
    ax.set_xlim(0, 108)
    ax.set_xlabel("Validity %")
    ax.set_title("Mutation Strategy Validity Ranking")

    _save(fig, output_dir, "fig_mutation_validity_ranking")


def _plot_valid_vs_interesting_breakdown(data: Dict, output_dir: Path) -> None:
    semantic = data["semantic_interest"]

    interesting = semantic["interesting"]
    trivial = semantic["trivial"]

    fig, ax = plt.subplots(figsize=(6.8, 4.6))
    bars = ax.bar(["Valid IR"], [interesting + trivial], color=COLORS["muted"], alpha=0.25)
    ax.bar(["Valid IR"], [interesting], color=COLORS["llm"], alpha=0.9)

    ax.text(0, interesting / 2, f"Interesting: {interesting}", ha="center", va="center", color="white", fontweight="bold")
    ax.text(0, interesting + trivial / 2, f"Trivial: {trivial}", ha="center", va="center")

    total_valid = interesting + trivial
    pct = 0.0 if total_valid == 0 else (interesting / total_valid) * 100.0
    ax.set_title(f"Semantic Interest Among Valid IR ({pct:.1f}% interesting)")
    ax.set_ylabel("Number of Valid Samples")

    _save(fig, output_dir, "fig_semantic_interest_breakdown")


def _plot_source_outcome_stack(data: Dict, output_dir: Path) -> None:
    stats = data["validity_by_source"]
    sources = ["llm", "grammar", "random"]
    labels = ["LLM", "Grammar", "Random"]
    valid = [stats[source]["valid"] for source in sources]
    invalid = [stats[source]["total"] - stats[source]["valid"] for source in sources]

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(labels, valid, color=[COLORS[source] for source in sources], alpha=0.95, label="Valid")
    ax.bar(labels, invalid, bottom=valid, color=COLORS["muted"], alpha=0.35, label="Invalid")

    for i, (v, inv) in enumerate(zip(valid, invalid)):
        ax.text(i, v / 2, str(v), ha="center", va="center", color="white", fontweight="bold")
        if inv:
            ax.text(i, v + inv / 2, str(inv), ha="center", va="center")

    ax.set_title("Valid vs Invalid Samples by Source")
    ax.set_ylabel("Sample Count")
    ax.legend(loc="upper right")

    _save(fig, output_dir, "fig_source_outcome_stack")


def _plot_semantic_feature_heatmap(data: Dict, output_dir: Path) -> None:
    semantic = data["semantic_interest"]
    interesting_total = semantic["interesting"]
    trivial_total = semantic["trivial"]
    interesting = semantic["interesting_feature_dist"]
    trivial = semantic["trivial_feature_dist"]

    features = sorted(set(interesting) | set(trivial))
    feature_labels = [feature.replace("_", " ").title() for feature in features]
    matrix = np.array(
        [
            [100.0 * interesting.get(feature, 0) / max(interesting_total, 1) for feature in features],
            [100.0 * trivial.get(feature, 0) / max(trivial_total, 1) for feature in features],
        ]
    )

    fig, ax = plt.subplots(figsize=(10.8, 4.8))
    im = ax.imshow(matrix, cmap="YlGnBu", aspect="auto", vmin=0, vmax=100)

    ax.set_xticks(np.arange(len(feature_labels)))
    ax.set_xticklabels(feature_labels, rotation=35, ha="right")
    ax.set_yticks([0, 1])
    ax.set_yticklabels(["Interesting IR", "Trivial IR"])
    ax.set_title("Semantic Feature Prevalence Heatmap")

    for row in range(matrix.shape[0]):
        for col in range(matrix.shape[1]):
            value = matrix[row, col]
            ax.text(
                col,
                row,
                f"{value:.0f}",
                ha="center",
                va="center",
                color="white" if value > 55 else "black",
                fontsize=8,
            )

    cbar = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02)
    cbar.set_label("Presence within group (%)")

    _save(fig, output_dir, "fig_semantic_feature_heatmap")


def _write_manifest(data: Dict, output_dir: Path) -> None:
    manifest = output_dir / "figure_manifest.md"
    metadata = data.get("metadata", {})
    lines = [
        "# Figure Manifest",
        "",
        "Generated figures for the research paper.",
        "",
        f"- Timestamp: {metadata.get('timestamp', 'N/A')}",
        f"- Total samples: {metadata.get('total_samples', 'N/A')}",
        f"- Valid samples: {metadata.get('valid_total', 'N/A')}",
        "",
        "## Files",
        "",
        "- fig_validity_interest.png / .svg",
        "- fig_error_distribution.png / .svg",
        "- fig_error_distribution_donut.png / .svg",
        "- fig_mutation_effectiveness.png / .svg",
        "- fig_mutation_validity_ranking.png / .svg",
        "- fig_semantic_interest_breakdown.png / .svg",
        "- fig_source_outcome_stack.png / .svg",
        "- fig_semantic_feature_heatmap.png / .svg",
    ]
    manifest.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate paper figures from experiment results")
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("results") / "experiment_results.json",
        help="Path to experiment_results.json",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results") / "figures",
        help="Output directory for generated figures",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if not args.input.exists():
        raise FileNotFoundError(f"Input file not found: {args.input}")

    args.output.mkdir(parents=True, exist_ok=True)

    data = _load_results(args.input)
    _set_plot_style()

    _plot_validity_and_interest(data, args.output)
    _plot_error_distribution(data, args.output)
    _plot_error_distribution_donut(data, args.output)
    _plot_mutation_effectiveness(data, args.output)
    _plot_mutation_validity_ranking(data, args.output)
    _plot_valid_vs_interesting_breakdown(data, args.output)
    _plot_source_outcome_stack(data, args.output)
    _plot_semantic_feature_heatmap(data, args.output)
    _write_manifest(data, args.output)

    print(f"Figures generated in: {args.output}")


if __name__ == "__main__":
    main()
