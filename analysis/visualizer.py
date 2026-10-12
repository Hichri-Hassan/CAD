"""Generate publication-quality matplotlib figures."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from analysis.aggregator import numeric_summary, top_items
from analysis.models import DatasetStats

FIGURE_DPI = 200
FIGURE_STYLE = {
    "figure.figsize": (10, 6),
    "axes.grid": True,
    "grid.alpha": 0.3,
    "font.size": 11,
}


def _save_figure(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(path, dpi=FIGURE_DPI, bbox_inches="tight")
    plt.close()


def plot_operation_distribution(dataset: DatasetStats, path: Path, top_n: int = 15) -> None:
    """Bar chart of operation type frequencies."""
    plt.style.use("seaborn-v0_8-whitegrid")
    plt.rcParams.update(FIGURE_STYLE)

    items = top_items(dataset.operation_counts, top_n)
    if not items:
        return

    labels, values = zip(*items)
    fig, ax = plt.subplots()
    ax.barh(list(reversed(labels)), list(reversed(values)), color="#2E86AB")
    ax.set_title("PartDesign Operation Distribution")
    ax.set_xlabel("Count")
    ax.set_ylabel("Operation Type")
    _save_figure(path)


def plot_geometry_distribution(dataset: DatasetStats, path: Path, top_n: int = 12) -> None:
    """Bar chart of sketch geometry entity frequencies."""
    plt.style.use("seaborn-v0_8-whitegrid")
    plt.rcParams.update(FIGURE_STYLE)

    items = top_items(dataset.geometry_counts, top_n)
    if not items:
        return

    labels, values = zip(*items)
    fig, ax = plt.subplots()
    ax.bar(labels, values, color="#A23B72")
    ax.set_title("Sketch Geometry Distribution")
    ax.set_xlabel("Geometry Type")
    ax.set_ylabel("Count")
    plt.xticks(rotation=35, ha="right")
    _save_figure(path)


def plot_constraint_distribution(dataset: DatasetStats, path: Path, top_n: int = 12) -> None:
    """Bar chart of sketch constraint frequencies."""
    plt.style.use("seaborn-v0_8-whitegrid")
    plt.rcParams.update(FIGURE_STYLE)

    items = top_items(dataset.constraint_counts, top_n)
    if not items:
        return

    labels, values = zip(*items)
    fig, ax = plt.subplots()
    ax.bar(labels, values, color="#F18F01")
    ax.set_title("Sketch Constraint Distribution")
    ax.set_xlabel("Constraint Type")
    ax.set_ylabel("Count")
    plt.xticks(rotation=35, ha="right")
    _save_figure(path)


def plot_operations_per_model(dataset: DatasetStats, path: Path) -> None:
    """Histogram of feature-tree depth / operations per model."""
    plt.style.use("seaborn-v0_8-whitegrid")
    plt.rcParams.update(FIGURE_STYLE)

    if not dataset.operations_per_model:
        return

    fig, ax = plt.subplots()
    ax.hist(dataset.operations_per_model, bins=30, color="#3A86FF", edgecolor="white")
    summary = numeric_summary(dataset.operations_per_model)
    ax.axvline(summary["median"], color="#FB5607", linestyle="--", label=f"Median={summary['median']:.1f}")
    ax.set_title("Operations per Model")
    ax.set_xlabel("Feature Tree Depth")
    ax.set_ylabel("Number of Models")
    ax.legend()
    _save_figure(path)


def plot_feature_distribution(dataset: DatasetStats, path: Path) -> None:
    """Pie chart of parser coverage categories."""
    plt.style.use("seaborn-v0_8-whitegrid")
    plt.rcParams.update(FIGURE_STYLE)

    labels = [
        "Fully Parsed",
        "Partially Parsed",
        "Unsupported",
        "Corrupted / Failed",
    ]
    values = [
        dataset.successfully_parsed - dataset.partially_parsed,
        dataset.partially_parsed,
        dataset.unsupported_models,
        dataset.corrupted_files + max(0, dataset.parser_failures - dataset.corrupted_files),
    ]
    values = [max(0, v) for v in values]
    if sum(values) == 0:
        return

    fig, ax = plt.subplots()
    ax.pie(values, labels=labels, autopct="%1.1f%%", startangle=140, colors=[
        "#06A77D",
        "#F5B700",
        "#D62828",
        "#6C757D",
    ])
    ax.set_title("Parser Coverage Across Dataset")
    _save_figure(path)


def plot_parameter_histograms(dataset: DatasetStats, path: Path) -> None:
    """Grid of parameter histograms for numeric CAD parameters."""
    plt.style.use("seaborn-v0_8-whitegrid")
    plt.rcParams.update(FIGURE_STYLE)

    numeric_params = {
        name: [float(v) for v in values if isinstance(v, (int, float))]
        for name, values in dataset.parameters.items()
        if any(isinstance(v, (int, float)) for v in values)
    }
    if not numeric_params:
        return

    count = len(numeric_params)
    cols = 2
    rows = (count + cols - 1) // cols
    fig, axes = plt.subplots(rows, cols, figsize=(12, 4 * rows))
    axes_list = axes.flatten() if count > 1 else [axes]

    for ax, (name, values) in zip(axes_list, sorted(numeric_params.items())):
        ax.hist(values, bins=30, color="#8338EC", edgecolor="white")
        ax.set_title(name.replace("_", " ").title())
        ax.set_xlabel("Value (mm)")
        ax.set_ylabel("Frequency")

    for ax in axes_list[len(numeric_params) :]:
        ax.axis("off")

    fig.suptitle("Parameter Value Distributions", fontsize=14, y=1.02)
    _save_figure(path)


def plot_operation_histogram(dataset: DatasetStats, path: Path) -> None:
    """Histogram of total PartDesign operations per model."""
    plt.style.use("seaborn-v0_8-whitegrid")
    plt.rcParams.update(FIGURE_STYLE)

    totals = [sum(model.operation_counts.values()) for model in dataset.model_stats]
    if not totals:
        return

    fig, ax = plt.subplots()
    ax.hist(totals, bins=30, color="#118AB2", edgecolor="white")
    ax.set_title("Total Body Features per Model")
    ax.set_xlabel("Feature Count")
    ax.set_ylabel("Number of Models")
    _save_figure(path)


def generate_all_figures(output_dir: Path, dataset: DatasetStats) -> list[Path]:
    """Generate all analysis figures."""
    figures = {
        "feature_distribution.png": plot_feature_distribution,
        "operation_histogram.png": plot_operation_histogram,
        "geometry_distribution.png": plot_geometry_distribution,
        "constraint_distribution.png": plot_constraint_distribution,
        "operations_per_model.png": plot_operations_per_model,
        "parameter_histograms.png": plot_parameter_histograms,
        "operation_distribution.png": plot_operation_distribution,
    }

    generated: list[Path] = []
    for filename, plot_fn in figures.items():
        target = output_dir / filename
        plot_fn(dataset, target)
        if target.exists():
            generated.append(target)
    return generated
