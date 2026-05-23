import csv
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt


def write_rows(path: Path, rows: list[dict]) -> None:
    fieldnames = ["scene_id", "sigma", "seed", "method", "selected_id", "success"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def summarize(rows: list[dict]) -> list[dict]:
    buckets = defaultdict(list)
    for row in rows:
        buckets[(row["sigma"], row["method"])].append(int(row["success"]))
    summary = []
    for (sigma, method), values in sorted(buckets.items()):
        summary.append({"sigma": sigma, "method": method, "success_rate": sum(values) / len(values)})
    return summary


def write_summary(path: Path, rows: list[dict]) -> list[dict]:
    summary = summarize(rows)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["sigma", "method", "success_rate"])
        writer.writeheader()
        writer.writerows(summary)
    return summary


def write_chart(path: Path, summary: list[dict]) -> None:
    methods = sorted({row["method"] for row in summary})
    for method in methods:
        subset = [row for row in summary if row["method"] == method]
        plt.plot(
            [row["sigma"] for row in subset],
            [row["success_rate"] for row in subset],
            marker="o",
            label=method,
        )
    plt.xlabel("Sigma")
    plt.ylabel("Success Rate")
    plt.legend()
    plt.tight_layout()
    plt.savefig(path)
    plt.close()
