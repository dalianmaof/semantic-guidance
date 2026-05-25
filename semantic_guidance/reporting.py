import csv
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt


def write_rows(path: Path, rows: list[dict]) -> None:
    # Build fieldnames dynamically so extra score_* columns are included
    base_fields = ["scene_id", "sigma", "seed", "method", "selected_id", "success"]
    extra = sorted({k for row in rows for k in row if k not in base_fields})
    fieldnames = base_fields + extra

    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def summarize(rows: list[dict]) -> list[dict]:
    buckets = defaultdict(list)
    for row in rows:
        buckets[(row["sigma"], row["method"])].append(int(row["success"]))
    summary = []
    for (sigma, method), values in sorted(buckets.items()):
        successes = sum(values)
        total = len(values)
        summary.append({
            "sigma": sigma,
            "method": method,
            "success_rate": successes / total,
            "mislock_rate": 1.0 - successes / total,
        })
    return summary


def write_summary(path: Path, rows: list[dict]) -> list[dict]:
    summary = summarize(rows)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["sigma", "method", "success_rate", "mislock_rate"])
        writer.writeheader()
        writer.writerows(summary)
    return summary


def write_chart(path: Path, summary: list[dict]) -> None:
    """Generate two charts: success rate and mislock rate side by side."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

    methods = sorted({row["method"] for row in summary})

    # Success rate chart
    for method in methods:
        subset = [row for row in summary if row["method"] == method]
        ax1.plot(
            [row["sigma"] for row in subset],
            [row["success_rate"] for row in subset],
            marker="o",
            label=method,
        )
    ax1.set_xlabel("Sigma")
    ax1.set_ylabel("Success Rate")
    ax1.set_title("Target Acquisition Success Rate")
    ax1.legend()

    # Mislock rate chart
    for method in methods:
        subset = [row for row in summary if row["method"] == method]
        ax2.plot(
            [row["sigma"] for row in subset],
            [row["mislock_rate"] for row in subset],
            marker="s",
            label=method,
        )
    ax2.set_xlabel("Sigma")
    ax2.set_ylabel("Mislock Rate")
    ax2.set_title("Target Mislock Rate")
    ax2.legend()

    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)

    # Also save individual chart images for convenience
    stem = path.stem
    parent = path.parent

    fig_sr, ax_sr = plt.subplots(figsize=(6, 5))
    for method in methods:
        subset = [row for row in summary if row["method"] == method]
        ax_sr.plot(
            [row["sigma"] for row in subset],
            [row["success_rate"] for row in subset],
            marker="o",
            label=method,
        )
    ax_sr.set_xlabel("Sigma")
    ax_sr.set_ylabel("Success Rate")
    ax_sr.set_title("Target Acquisition Success Rate")
    ax_sr.legend()
    fig_sr.tight_layout()
    fig_sr.savefig(parent / f"{stem}_only.png")
    plt.close(fig_sr)

    fig_ml, ax_ml = plt.subplots(figsize=(6, 5))
    for method in methods:
        subset = [row for row in summary if row["method"] == method]
        ax_ml.plot(
            [row["sigma"] for row in subset],
            [row["mislock_rate"] for row in subset],
            marker="s",
            label=method,
        )
    ax_ml.set_xlabel("Sigma")
    ax_ml.set_ylabel("Mislock Rate")
    ax_ml.set_title("Target Mislock Rate")
    ax_ml.legend()
    fig_ml.tight_layout()
    fig_ml.savefig(parent / "mislock_rate.png")
    plt.close(fig_ml)
