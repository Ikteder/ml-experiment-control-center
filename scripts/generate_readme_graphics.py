from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PIL import Image, ImageDraw
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"
DEMO_ROOT = PROJECT_ROOT / ".demo-runtime"
DEMO_DATABASE = DEMO_ROOT / "app.db"
DEMO_STORAGE = DEMO_ROOT / "storage"
sys.path.insert(0, str(BACKEND_ROOT))

from app.models import Run  # noqa: E402


matplotlib.use("Agg")


def load_runs() -> pd.DataFrame:
    if not DEMO_DATABASE.exists():
        raise RuntimeError("No isolated demo database. Run scripts/seed_demo_runs.py first.")
    engine = create_engine(f"sqlite:///{DEMO_DATABASE.as_posix()}")
    sessions = sessionmaker(bind=engine)
    with sessions() as session:
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
    engine.dispose()
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
    axis.text(
        0.03,
        0.48,
        "Launch, track, compare, and export reproducible experiments from one evidence-first dashboard",
        color="#dbe7f2",
        fontsize=12,
    )
    axis.text(0.03, 0.18, f"Best classification F1  {best_classification:.3f}", color="#ffd166", fontsize=14)
    axis.text(0.54, 0.18, f"Demand forecast RMSE  {best_regression:.2f}", color="#80ed99", fontsize=14)
    plt.tight_layout()
    plt.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close()


def create_scorecard_plot(run_frame: pd.DataFrame, output_path: Path) -> None:
    classifications = run_frame[run_frame["task_type"] == "classification"].copy()
    forecasts = run_frame[run_frame["task_type"] == "regression"].copy()
    figure, axes = plt.subplots(1, 2, figsize=(13, 5.2), gridspec_kw={"width_ratios": [1.35, 1]})
    figure.patch.set_facecolor("#f8fafc")

    metric_names = ["f1", "precision", "recall"]
    colors = ["#2a9d8f", "#457b9d", "#f4a261"]
    positions = np.arange(len(classifications))
    width = 0.23
    for index, (metric, color) in enumerate(zip(metric_names, colors, strict=True)):
        values = classifications[metric].astype(float).to_numpy()
        bars = axes[0].bar(positions + (index - 1) * width, values, width, label=metric.title(), color=color)
        axes[0].bar_label(bars, fmt="%.2f", padding=3, fontsize=8)
    axes[0].set_xticks(positions, ["Customer churn", "Predictive maintenance"][: len(classifications)])
    axes[0].set_ylim(0, 1.08)
    axes[0].set_ylabel("Holdout score")
    axes[0].set_title("Classification quality", loc="left", fontweight="bold")
    axes[0].legend(frameon=False, ncol=3, loc="lower left")
    axes[0].grid(axis="y", alpha=0.18)

    if not forecasts.empty:
        forecast = forecasts.iloc[0]
        rmse_values = [float(forecast["rmse"]), float(forecast["seasonal_naive_rmse"])]
        bars = axes[1].bar(["Gradient boosting", "Seasonal naive"], rmse_values, color=["#2a9d8f", "#94a3b8"])
        axes[1].bar_label(bars, fmt="%.2f", padding=4, fontsize=9)
        axes[1].set_ylim(0, max(rmse_values) * 1.25)
        axes[1].text(
            0.02,
            0.93,
            f"{float(forecast['rmse_improvement_pct']):.1f}% lower RMSE",
            transform=axes[1].transAxes,
            color="#0f766e",
            fontweight="bold",
        )
    axes[1].set_ylabel("RMSE, lower is better")
    axes[1].set_title("Demand forecast vs baseline", loc="left", fontweight="bold")
    axes[1].grid(axis="y", alpha=0.18)

    figure.suptitle("Evaluation evidence from isolated demo runs", x=0.055, ha="left", fontsize=16, fontweight="bold")
    figure.tight_layout(rect=(0, 0, 1, 0.93))
    figure.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(figure)


def create_artifact_gallery(output_path: Path) -> None:
    run_dirs = sorted((DEMO_STORAGE / "runs").glob("run-*"))
    image_paths: list[Path] = []
    for run_dir in run_dirs:
        for file_name in ["metric_curves.png", "confusion_matrix.png", "forecast_scatter.png"]:
            candidate = run_dir / file_name
            if candidate.exists():
                image_paths.append(candidate)
    tiles = [Image.open(path).convert("RGB").resize((520, 360), Image.Resampling.LANCZOS) for path in image_paths[:4]]
    canvas = Image.new("RGB", (1040, 720), color="#0f172a")
    draw = ImageDraw.Draw(canvas)
    positions = [(0, 0), (520, 0), (0, 360), (520, 360)]
    for tile, path, position in zip(tiles, image_paths, positions, strict=False):
        canvas.paste(tile, position)
        draw.rectangle((position[0], position[1], position[0] + 520, position[1] + 30), fill="#0f172a")
        draw.text((position[0] + 12, position[1] + 8), path.name.replace("_", " ").title(), fill="white")
    canvas.save(output_path)


def main() -> None:
    graphics_root = PROJECT_ROOT / "docs" / "graphics"
    graphics_root.mkdir(parents=True, exist_ok=True)
    run_frame = load_runs()
    create_banner(run_frame, graphics_root / "control_center_banner.png")
    create_scorecard_plot(run_frame, graphics_root / "demo_run_comparison.png")
    create_artifact_gallery(graphics_root / "artifact_gallery.png")
    print("Generated README graphics from isolated demo output.")


if __name__ == "__main__":
    main()
