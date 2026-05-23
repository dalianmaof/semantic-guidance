from pathlib import Path

from semantic_guidance.experiment import load_scenes_from_annotations, run_batch_experiment


def main() -> None:
    annotation_dir = Path("data/annotations")
    output_dir = Path("output/debug")
    scenes = load_scenes_from_annotations(annotation_dir)
    if not scenes:
        raise SystemExit("No annotations found in data/annotations")
    report = run_batch_experiment(scenes, sigmas=[5.0, 15.0], seeds=[1, 2, 3], output_dir=output_dir)
    print(f"wrote {report['rows']} rows to {output_dir}")


if __name__ == "__main__":
    main()
