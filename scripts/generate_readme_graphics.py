from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import pandas as pd
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import settings  # noqa: E402
from app.core.database import SessionLocal  # noqa: E402
from app.models import Run  # noqa: E402


matplotlib.use("Agg")


def load_runs() -> pd.DataFrame:
    with SessionLocal() as session:
        rows = session.query(Run).all()
        payload = [
            {
                "run_id": row.run_id,
                "display_name": row.display_name,
                "preset_key": row.preset_key,
                "task_type": row.task_type,
                "status": row.status,
                **(json.loads(row.scorecard_json) if row.scorecard_json else {}),
            }
            for row in rows
        ]
    return pd.DataFrame(payload)


def create_banner(run_frame: pd.DataFrame, output_path: Path) -> None:
    if run_frame.empty:
        raise RuntimeError("No demo runs available. Run scripts/seed_demo_runs.py first.")
    best_classification = run_frame.loc[run_frame["task_type"] == "classification", "f1"].max()
    best_regression = run_frame.loc[run_frame["task_type"] == "regression", "rmse"].min()
    figure, axis = plt.subplots(figsize=(12, 4))
    figure.patch.set_facecolor("#102542")
    axis.set_facecolor("#102542")
    axis.axis("off")
    axis.text(0.03, 0.72, "ML Experiment Control Center", color="white", fontsize=25, fontweight="bold")
    axis.text(0.03, 0.48, "FastAPI + React platform for launching runs, streaming logs, comparing experiments, and exporting reports", color="#dbe7f2", fontsize=12)
    axis.text(0.03, 0.18, f"Best classification F1: {best_classification:.2f}", color="#ffd166", fontsize=14)
    axis.text(0.54, 0.18, f"Best demand RMSE: {best_regression:.2f}", color="#80ed99", fontsize=14)
    plt.tight_layout()
    plt.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close()


def create_scorecard_plot(run_frame: pd.DataFrame, output_path: Path) -> None:
    plot_frame = run_frame.copy()
    plot_frame["primary_metric"] = plot_frame["f1"].fillna(1 / plot_frame["rmse"])
    plt.figure(figsize=(10, 5))
    colors = ["#2A9D8F", "#F4A261", "#89C2D9"]
    plt.bar(plot_frame["display_name"], plot_frame["primary_metric"], color=colors[: len(plot_frame)])
    plt.ylabel("Primary metric proxy")
    plt.title("Demo run comparison")
    plt.xticks(rotation=12, ha="right")
    plt.tight_layout()
    plt.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close()


def create_artifact_gallery(output_path: Path) -> None:
    run_dirs = sorted((settings.storage_root / "runs").glob("run-*"))
    image_paths = []
    for run_dir in run_dirs:
        for file_name in ["metric_curves.png", "confusion_matrix.png", "forecast_scatter.png"]:
            candidate = run_dir / file_name
            if candidate.exists():
                image_paths.append(candidate)
    tiles = [Image.open(path).convert("RGB").resize((420, 300)) for path in image_paths[:4]]
    canvas = Image.new("RGB", (840, 600), color="#0f172a")
    positions = [(0, 0), (420, 0), (0, 300), (420, 300)]
    for tile, position in zip(tiles, positions, strict=False):
        canvas.paste(tile, position)
    canvas.save(output_path)


def main() -> None:
    graphics_root = PROJECT_ROOT / "docs" / "graphics"
    graphics_root.mkdir(parents=True, exist_ok=True)
    run_frame = load_runs()
    create_banner(run_frame, graphics_root / "control_center_banner.png")
    create_scorecard_plot(run_frame, graphics_root / "demo_run_comparison.png")
    create_artifact_gallery(graphics_root / "artifact_gallery.png")
    print("Generated README graphics.")


if __name__ == "__main__":
    main()
