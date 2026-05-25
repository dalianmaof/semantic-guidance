from pathlib import Path

import yaml

from semantic_guidance.experiment import load_scenes_from_annotations, run_batch_experiment


def main() -> None:
    config_path = Path("experiment_config.yaml")
    if config_path.exists():
        with config_path.open("r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
    else:
        # Fallback defaults matching the standard experiment_config.yaml
        config = {
            "sigmas": [5.0, 15.0, 30.0, 50.0],
            "seeds_per_sigma": 10,
            "output_dir": "output/results",
            "scoring_weights": {
                "coordinate": 0.05,
                "category": 20.0,
                "attribute": 5.0,
                "relation": 15.0,
                "scene": 3.0
            },
        }

    sigmas = [float(s) for s in config.get("sigmas", [5.0, 15.0, 30.0, 50.0])]
    seeds_per_sigma = int(config.get("seeds_per_sigma", 10))
    seeds = list(range(1, seeds_per_sigma + 1))
    weights = config.get("scoring_weights", None)
    output_dir = Path(config.get("output_dir", "output/results"))
    annotation_dir = Path(config.get("annotation_dir", "data/annotations"))

    print(f"Configuration:")
    print(f"  Sigmas:          {sigmas}")
    print(f"  Seeds per sigma: {seeds_per_sigma}  →  seeds = {seeds}")
    print(f"  Scoring weights: {weights}")
    print(f"  Annotation dir:  {annotation_dir}")
    print(f"  Output dir:      {output_dir}")
    print()

    scenes = load_scenes_from_annotations(annotation_dir)
    if not scenes:
        raise SystemExit(f"No annotations found in {annotation_dir}")

    report = run_batch_experiment(
        scenes,
        sigmas=sigmas,
        seeds=seeds,
        output_dir=output_dir,
        weights=weights,
    )

    print(f"Wrote {report['rows']} rows to {output_dir}")
    print()
    print("Summary:")
    print(f"  {'Method':<12} {'Sigma':>6} {'Success':>9} {'Mislock':>9}")
    print(f"  {'-'*12} {'-'*6} {'-'*9} {'-'*9}")
    for row in report["summary"]:
        print(
            f"  {row['method']:<12} {row['sigma']:>6.0f} "
            f"{row['success_rate']:>8.1%} {row['mislock_rate']:>8.1%}"
        )


if __name__ == "__main__":
    main()
