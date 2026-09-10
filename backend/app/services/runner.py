from __future__ import annotations

import json
import threading
import time
import uuid
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.datasets import make_classification
from sklearn.ensemble import GradientBoostingClassifier, GradientBoostingRegressor
from sklearn.metrics import (
    ConfusionMatrixDisplay,
    accuracy_score,
    confusion_matrix,
    f1_score,
    log_loss,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, sessionmaker

from ..core.config import settings
from ..models import ArtifactEntry, MetricPoint, Run
from ..schemas import LaunchRunRequest
from .presets import get_preset, get_presets


matplotlib.use("Agg")


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _dump_json(data: dict[str, Any]) -> str:
    return json.dumps(data, indent=2, sort_keys=True)


def _get_git_commit() -> str:
    head_path = Path(__file__).resolve().parents[3] / ".git" / "HEAD"
    if not head_path.exists():
        return "untracked"
    head_value = head_path.read_text(encoding="utf-8").strip()
    if not head_value.startswith("ref: "):
        return head_value[:12]
    ref_path = Path(__file__).resolve().parents[3] / ".git" / head_value.replace("ref: ", "")
    if ref_path.exists():
        return ref_path.read_text(encoding="utf-8").strip()[:12]
    return "untracked"


def build_demand_frame(config: dict[str, Any]) -> tuple[pd.DataFrame, list[str]]:
    """Build a deterministic demand series whose features never look ahead."""
    sample_count = int(config["samples"])
    random = np.random.default_rng(int(config["seed"]))
    dates = pd.date_range(str(config.get("start_date", "2022-01-01")), periods=sample_count, freq="D")
    day = np.arange(sample_count, dtype=float)
    promotion = random.binomial(1, float(config.get("promotion_rate", 0.14)), sample_count)
    price = 24.0 + 1.8 * np.sin(2 * np.pi * day / 30.0) + random.normal(0, 0.7, sample_count)
    weekly = float(config.get("weekly_amplitude", 24.0)) * np.sin(2 * np.pi * day / 7.0)
    monthly = 9.0 * np.cos(2 * np.pi * day / 30.0)
    trend = float(config.get("trend_per_day", 0.025)) * day
    promotion_lift = float(config.get("promotion_lift", 34.0)) * promotion
    price_effect = float(config.get("price_sensitivity", 5.5)) * (price - 24.0)
    noise = random.normal(0, float(config["noise"]), sample_count)
    demand = 210.0 + trend + weekly + monthly + promotion_lift - price_effect + noise

    frame = pd.DataFrame(
        {
            "date": dates,
            "day_index": day,
            "day_of_week_sin": np.sin(2 * np.pi * dates.dayofweek.to_numpy() / 7.0),
            "day_of_week_cos": np.cos(2 * np.pi * dates.dayofweek.to_numpy() / 7.0),
            "month_sin": np.sin(2 * np.pi * dates.month.to_numpy() / 12.0),
            "month_cos": np.cos(2 * np.pi * dates.month.to_numpy() / 12.0),
            "promotion": promotion,
            "price": price,
            "target": demand,
        }
    )
    frame["lag_1"] = frame["target"].shift(1)
    frame["lag_7"] = frame["target"].shift(7)
    frame["rolling_mean_7"] = frame["target"].shift(1).rolling(7).mean()
    frame = frame.dropna().reset_index(drop=True)
    feature_names = [
        "day_index",
        "day_of_week_sin",
        "day_of_week_cos",
        "month_sin",
        "month_cos",
        "promotion",
        "price",
        "lag_1",
        "lag_7",
        "rolling_mean_7",
    ]
    return frame, feature_names


def chronological_split(frame: pd.DataFrame, test_size: float) -> tuple[pd.DataFrame, pd.DataFrame]:
    split_index = int(len(frame) * (1 - test_size))
    if split_index < 1 or split_index >= len(frame):
        raise ValueError("test_size leaves an empty chronological train or test block")
    return frame.iloc[:split_index].copy(), frame.iloc[split_index:].copy()


def validate_run_config(task_type: str, config: dict[str, Any]) -> dict[str, Any]:
    common = {"config_version", "samples", "epochs", "learning_rate", "max_depth", "test_size", "seed"}
    classification = {"features", "informative", "class_sep", "weights", "flip_y"}
    forecasting = {
        "noise",
        "start_date",
        "promotion_rate",
        "weekly_amplitude",
        "trend_per_day",
        "promotion_lift",
        "price_sensitivity",
    }
    allowed = common | (classification if task_type == "classification" else forecasting)
    unknown = sorted(set(config) - allowed)
    if unknown:
        raise ValueError(f"Unsupported config field(s): {', '.join(unknown)}")

    def number(name: str, minimum: float, maximum: float) -> float:
        value = config.get(name)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not minimum <= float(value) <= maximum:
            raise ValueError(f"{name} must be between {minimum} and {maximum}")
        return float(value)

    number("samples", 200, 20000)
    number("epochs", 4, 40)
    number("learning_rate", 0.001, 1)
    number("max_depth", 1, 10)
    number("test_size", 0.1, 0.4)
    number("seed", 0, 4294967295)
    if not isinstance(config.get("config_version"), str) or not config["config_version"].strip():
        raise ValueError("config_version must be a non-empty string")

    if task_type == "classification":
        features = int(number("features", 4, 100))
        informative = int(number("informative", 2, 98))
        if informative + max(2, features // 6) > features:
            raise ValueError("informative plus generated redundant features cannot exceed features")
        number("class_sep", 0.1, 10)
        number("flip_y", 0, 0.3)
        weights = config.get("weights")
        if (
            not isinstance(weights, list)
            or len(weights) != 2
            or any(isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0 for value in weights)
            or not np.isclose(sum(weights), 1.0)
        ):
            raise ValueError("weights must contain two positive values that sum to 1")
    elif task_type == "regression":
        number("noise", 0, 100)
        number("promotion_rate", 0, 1)
        number("weekly_amplitude", 0, 100)
        number("trend_per_day", -1, 1)
        number("promotion_lift", -200, 200)
        number("price_sensitivity", 0, 50)
        try:
            pd.Timestamp(config.get("start_date"))
        except (TypeError, ValueError) as exc:
            raise ValueError("start_date must be a valid date") from exc
    else:
        raise ValueError(f"Unsupported task type '{task_type}'")
    return config


class RunOrchestrator:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        *,
        storage_root: Path | None = None,
        step_delay_seconds: float | None = None,
        source_revision: str | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="experiment-runner")
        self._futures: dict[str, Future[Any]] = {}
        self._lock = threading.Lock()
        self._storage_root = storage_root or settings.storage_root
        self._step_delay_seconds = settings.run_step_delay_seconds if step_delay_seconds is None else step_delay_seconds
        self._source_revision = source_revision or _get_git_commit()
        self._storage_root.mkdir(parents=True, exist_ok=True)

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=True)

    def recover_interrupted_runs(self) -> int:
        """Mark work abandoned by a previous local process as failed."""
        with self._session_factory() as session:
            interrupted = session.scalars(select(Run).where(Run.status.in_(["queued", "running"]))).all()
            for run in interrupted:
                run.status = "failed"
                run.finished_at = _utc_now()
                run.latest_message = "Run interrupted before this process started."
                run.error_message = "The previous local worker stopped before recording a terminal state."
            session.commit()
            return len(interrupted)

    def preset_summaries(self) -> list[dict[str, Any]]:
        return [{"key": key, **value} for key, value in get_presets().items()]

    def resolve_launch_config(self, request: LaunchRunRequest) -> dict[str, Any]:
        preset_key = request.preset_key or (request.config.get("preset_key") if request.config else None)
        if not preset_key:
            raise ValueError("A preset_key is required unless it is included inside config.")
        preset = get_preset(preset_key)
        config = preset["config"]
        if request.config:
            overrides = dict(request.config)
            overrides.pop("preset_key", None)
            config.update(overrides)
        if request.seed is not None:
            config["seed"] = request.seed
        if request.epochs is not None:
            config["epochs"] = request.epochs
        validate_run_config(preset["task_type"], config)
        return {
            "preset_key": preset_key,
            "display_name": request.display_name or preset["display_name"],
            "description": preset["description"],
            "dataset_name": preset["dataset_name"],
            "task_type": preset["task_type"],
            "model_name": preset["model_name"],
            "config": config,
        }

    def create_and_start_run(self, request: LaunchRunRequest) -> Run:
        payload = self.resolve_launch_config(request)
        run_id = f"run-{uuid.uuid4().hex[:10]}"
        run = Run(
            run_id=run_id,
            display_name=payload["display_name"],
            preset_key=payload["preset_key"],
            dataset_name=payload["dataset_name"],
            task_type=payload["task_type"],
            model_name=payload["model_name"],
            status="queued",
            seed=int(payload["config"]["seed"]),
            config_version=str(payload["config"]["config_version"]),
            config_json=_dump_json(payload["config"]),
            git_commit_hash=self._source_revision,
            scorecard_json="{}",
            latest_message="Queued and waiting for execution.",
        )
        with self._session_factory() as session:
            session.add(run)
            session.commit()
            session.refresh(run)
        with self._lock:
            self._futures[run_id] = self._executor.submit(self._execute_run, run_id)
        return run

    def read_logs(self, run_id: str, after_line: int = 0) -> tuple[list[dict[str, Any]], int]:
        log_path = self._run_dir(run_id) / "logs.jsonl"
        if not log_path.exists():
            return [], after_line
        lines = log_path.read_text(encoding="utf-8").splitlines()
        new_payloads = [json.loads(line) for line in lines[after_line:]]
        return new_payloads, len(lines)

    def list_runs(
        self,
        session: Session,
        *,
        limit: int,
        offset: int,
        search: str | None = None,
        preset_key: str | None = None,
        status: str | None = None,
        dataset_name: str | None = None,
    ) -> tuple[list[Run], int]:
        query = select(Run)
        count_query = select(func.count()).select_from(Run)
        filters = []
        if search:
            pattern = f"%{search.lower()}%"
            filters.append(
                or_(
                    func.lower(Run.display_name).like(pattern),
                    func.lower(Run.run_id).like(pattern),
                    func.lower(Run.model_name).like(pattern),
                )
            )
        if preset_key:
            filters.append(Run.preset_key == preset_key)
        if status:
            filters.append(Run.status == status)
        if dataset_name:
            filters.append(Run.dataset_name == dataset_name)
        for clause in filters:
            query = query.where(clause)
            count_query = count_query.where(clause)
        total = session.scalar(count_query) or 0
        items = session.scalars(query.order_by(Run.created_at.desc()).offset(offset).limit(limit)).all()
        return items, total

    def get_run(self, session: Session, run_id: str) -> Run:
        run = session.scalar(select(Run).where(Run.run_id == run_id))
        if not run:
            raise KeyError(f"Run '{run_id}' not found.")
        return run

    def get_metric_points(self, session: Session, run_id: str) -> list[MetricPoint]:
        return session.scalars(select(MetricPoint).where(MetricPoint.run_id == run_id).order_by(MetricPoint.step.asc())).all()

    def get_artifacts(self, session: Session, run_id: str) -> list[ArtifactEntry]:
        return session.scalars(select(ArtifactEntry).where(ArtifactEntry.run_id == run_id).order_by(ArtifactEntry.created_at.asc())).all()

    def is_terminal(self, run_id: str) -> bool:
        with self._session_factory() as session:
            run = self.get_run(session, run_id)
            return run.status in {"completed", "failed"}

    def _execute_run(self, run_id: str) -> None:
        with self._session_factory() as session:
            run = self.get_run(session, run_id)
            config = json.loads(run.config_json)
            run.status = "running"
            run.started_at = _utc_now()
            run.latest_message = "Bootstrapping workload."
            session.commit()

        try:
            if run.task_type == "classification":
                scorecard = self._run_classification_experiment(run_id, config)
            else:
                scorecard = self._run_regression_experiment(run_id, config)
            with self._session_factory() as session:
                run = self.get_run(session, run_id)
                run.status = "completed"
                run.finished_at = _utc_now()
                run.latest_message = "Run completed successfully."
                run.scorecard_json = _dump_json(scorecard)
                session.commit()
        except Exception as exc:  # noqa: BLE001
            with self._session_factory() as session:
                run = self.get_run(session, run_id)
                run.status = "failed"
                run.finished_at = _utc_now()
                run.latest_message = "Run failed."
                run.error_message = str(exc)
                session.commit()
            self._append_log(run_id, "error", "Run failed.", {"error": str(exc)})

    def _run_classification_experiment(self, run_id: str, config: dict[str, Any]) -> dict[str, Any]:
        x_matrix, y_vector = make_classification(
            n_samples=config["samples"],
            n_features=config["features"],
            n_informative=config["informative"],
            n_redundant=max(2, config["features"] // 6),
            class_sep=config["class_sep"],
            weights=config.get("weights", [0.7, 0.3]),
            flip_y=config.get("flip_y", 0.01),
            random_state=config["seed"],
        )
        feature_names = [f"feature_{index + 1}" for index in range(x_matrix.shape[1])]
        data_frame = pd.DataFrame(x_matrix, columns=feature_names)
        data_frame["target"] = y_vector
        x_train, x_test, y_train, y_test = train_test_split(
            data_frame[feature_names],
            data_frame["target"],
            test_size=config["test_size"],
            random_state=config["seed"],
            stratify=data_frame["target"],
        )
        model = GradientBoostingClassifier(
            n_estimators=config["epochs"],
            learning_rate=config["learning_rate"],
            max_depth=config["max_depth"],
            random_state=config["seed"],
        )
        self._append_log(run_id, "info", "Fitting classification model.", {"rows": len(data_frame)})
        model.fit(x_train, y_train)

        history_rows: list[dict[str, Any]] = []
        final_predictions = None
        final_probabilities = None
        for step, probability_matrix in enumerate(model.staged_predict_proba(x_test), start=1):
            positive_scores = probability_matrix[:, 1]
            predictions = (positive_scores >= 0.5).astype(int)
            metrics = {
                "step": step,
                "split": "validation",
                "loss": float(log_loss(y_test, probability_matrix)),
                "accuracy": float(accuracy_score(y_test, predictions)),
                "f1": float(f1_score(y_test, predictions)),
                "auroc": float(roc_auc_score(y_test, positive_scores)),
            }
            history_rows.append(metrics)
            final_predictions = predictions
            final_probabilities = positive_scores
            self._persist_metric_point(run_id, metrics)
            self._append_log(run_id, "info", f"Completed epoch {step}.", metrics)
            time.sleep(self._step_delay_seconds)

        history_frame = pd.DataFrame(history_rows)
        run_dir = self._run_dir(run_id)
        run_dir.mkdir(parents=True, exist_ok=True)
        history_frame.to_csv(run_dir / "metrics_history.csv", index=False)
        predictions_frame = pd.DataFrame(
            {
                "true_label": y_test.to_numpy(),
                "predicted_label": final_predictions,
                "positive_probability": final_probabilities,
            }
        )
        predictions_frame.to_csv(run_dir / "predictions.csv", index=False)
        config_path = run_dir / "config.json"
        config_path.write_text(_dump_json(config), encoding="utf-8")

        plt.figure(figsize=(5, 5))
        ConfusionMatrixDisplay.from_predictions(y_test, final_predictions, cmap="Blues", colorbar=False)
        plt.title("Confusion Matrix")
        confusion_path = run_dir / "confusion_matrix.png"
        plt.tight_layout()
        plt.savefig(confusion_path, dpi=220, bbox_inches="tight")
        plt.close()

        curve_path = run_dir / "metric_curves.png"
        self._plot_metric_curves(history_frame, curve_path, ["loss", "accuracy", "f1", "auroc"])
        true_negative, false_positive, false_negative, true_positive = confusion_matrix(y_test, final_predictions).ravel()
        scorecard = {
            "loss": round(float(history_frame.iloc[-1]["loss"]), 4),
            "accuracy": round(float(history_frame.iloc[-1]["accuracy"]), 4),
            "f1": round(float(history_frame.iloc[-1]["f1"]), 4),
            "auroc": round(float(history_frame.iloc[-1]["auroc"]), 4),
            "precision": round(float(precision_score(y_test, final_predictions)), 4),
            "recall": round(float(recall_score(y_test, final_predictions)), 4),
            "threshold": 0.5,
            "true_negative": int(true_negative),
            "false_positive": int(false_positive),
            "false_negative": int(false_negative),
            "true_positive": int(true_positive),
            "best_step": int(history_frame.sort_values("f1", ascending=False).iloc[0]["step"]),
        }
        evaluation = {
            "protocol": "Seeded stratified random holdout",
            "train_rows": len(x_train),
            "test_rows": len(x_test),
            "leakage_control": "The split occurs before model fitting; synthetic rows are independently generated.",
        }
        model_card_path = run_dir / "model_card.md"
        model_card_path.write_text(
            self._render_model_card(run_id, "classification", config, scorecard, evaluation), encoding="utf-8"
        )
        dataset_card_path = run_dir / "dataset_card.md"
        dataset_card_path.write_text(
            self._render_dataset_card(run_id, "classification", config, evaluation), encoding="utf-8"
        )

        summary_path = run_dir / "report.html"
        summary_path.write_text(self._render_report_html(run_id, "classification", scorecard), encoding="utf-8")

        self._register_artifact(run_id, "config.json", "config", "application/json", config_path)
        self._register_artifact(run_id, "metrics_history.csv", "metrics_csv", "text/csv", run_dir / "metrics_history.csv")
        self._register_artifact(run_id, "predictions.csv", "predictions_csv", "text/csv", run_dir / "predictions.csv")
        self._register_artifact(run_id, "confusion_matrix.png", "confusion_matrix", "image/png", confusion_path)
        self._register_artifact(run_id, "metric_curves.png", "metrics_plot", "image/png", curve_path)
        self._register_artifact(run_id, "dataset_card.md", "dataset_card", "text/markdown", dataset_card_path)
        self._register_artifact(run_id, "model_card.md", "model_card", "text/markdown", model_card_path)
        self._register_artifact(run_id, "report.html", "report", "text/html", summary_path)
        return scorecard

    def _run_regression_experiment(self, run_id: str, config: dict[str, Any]) -> dict[str, Any]:
        data_frame, feature_names = build_demand_frame(config)
        train_frame, test_frame = chronological_split(data_frame, float(config["test_size"]))
        x_train = train_frame[feature_names]
        y_train = train_frame["target"]
        x_test = test_frame[feature_names]
        y_test = test_frame["target"]
        seasonal_naive = test_frame["lag_7"].to_numpy()
        baseline_mae = float(mean_absolute_error(y_test, seasonal_naive))
        baseline_rmse = float(np.sqrt(mean_squared_error(y_test, seasonal_naive)))
        model = GradientBoostingRegressor(
            n_estimators=config["epochs"],
            learning_rate=config["learning_rate"],
            max_depth=config["max_depth"],
            random_state=config["seed"],
        )
        self._append_log(
            run_id,
            "info",
            "Fitting chronological demand forecast.",
            {
                "train_rows": len(train_frame),
                "test_rows": len(test_frame),
                "test_start": test_frame.iloc[0]["date"].date().isoformat(),
            },
        )
        model.fit(x_train, y_train)

        history_rows: list[dict[str, Any]] = []
        final_predictions = None
        for step, predictions in enumerate(model.staged_predict(x_test), start=1):
            rmse = float(np.sqrt(mean_squared_error(y_test, predictions)))
            metrics = {
                "step": step,
                "split": "validation",
                "loss": rmse,
                "mae": float(mean_absolute_error(y_test, predictions)),
                "rmse": rmse,
                "r2": float(r2_score(y_test, predictions)),
            }
            history_rows.append(metrics)
            final_predictions = predictions
            self._persist_metric_point(run_id, metrics)
            self._append_log(run_id, "info", f"Completed epoch {step}.", metrics)
            time.sleep(self._step_delay_seconds)

        history_frame = pd.DataFrame(history_rows)
        run_dir = self._run_dir(run_id)
        run_dir.mkdir(parents=True, exist_ok=True)
        history_frame.to_csv(run_dir / "metrics_history.csv", index=False)
        predictions_frame = pd.DataFrame(
            {
                "date": test_frame["date"].dt.date.astype(str),
                "actual": y_test.to_numpy(),
                "predicted": final_predictions,
                "seasonal_naive": seasonal_naive,
            }
        )
        predictions_frame.to_csv(run_dir / "predictions.csv", index=False)
        config_path = run_dir / "config.json"
        config_path.write_text(_dump_json(config), encoding="utf-8")

        forecast_path = run_dir / "forecast_scatter.png"
        plt.figure(figsize=(10, 5))
        visible = predictions_frame.tail(min(120, len(predictions_frame))).reset_index(drop=True)
        plt.plot(visible["date"], visible["actual"], label="actual", color="#102542", linewidth=2)
        plt.plot(visible["date"], visible["predicted"], label="model", color="#2A9D8F", linewidth=1.8)
        plt.plot(visible["date"], visible["seasonal_naive"], label="seasonal naive", color="#F4A261", alpha=0.85)
        plt.xlabel("Chronological holdout date")
        plt.ylabel("Synthetic daily demand")
        plt.title("Demand Forecast on Final Holdout Window")
        tick_step = max(1, len(visible) // 6)
        tick_positions = list(range(0, len(visible), tick_step))
        plt.xticks(tick_positions, visible.loc[tick_positions, "date"], rotation=20)
        plt.legend()
        plt.tight_layout()
        plt.savefig(forecast_path, dpi=220, bbox_inches="tight")
        plt.close()

        curve_path = run_dir / "metric_curves.png"
        self._plot_metric_curves(history_frame, curve_path, ["loss", "mae", "rmse", "r2"])
        scorecard = {
            "mae": round(float(history_frame.iloc[-1]["mae"]), 4),
            "rmse": round(float(history_frame.iloc[-1]["rmse"]), 4),
            "r2": round(float(history_frame.iloc[-1]["r2"]), 4),
            "seasonal_naive_mae": round(baseline_mae, 4),
            "seasonal_naive_rmse": round(baseline_rmse, 4),
            "rmse_improvement_pct": round(100 * (baseline_rmse - float(history_frame.iloc[-1]["rmse"])) / baseline_rmse, 2),
            "best_step": int(history_frame.sort_values("rmse", ascending=True).iloc[0]["step"]),
        }
        evaluation = {
            "protocol": "Final-block chronological holdout with a lag-7 seasonal-naive baseline",
            "train_rows": len(train_frame),
            "test_rows": len(test_frame),
            "train_end": train_frame.iloc[-1]["date"].date().isoformat(),
            "test_start": test_frame.iloc[0]["date"].date().isoformat(),
            "test_end": test_frame.iloc[-1]["date"].date().isoformat(),
            "leakage_control": "Lag and rolling features are shifted; every feature uses current or earlier information.",
        }
        model_card_path = run_dir / "model_card.md"
        model_card_path.write_text(
            self._render_model_card(run_id, "regression", config, scorecard, evaluation), encoding="utf-8"
        )
        dataset_card_path = run_dir / "dataset_card.md"
        dataset_card_path.write_text(
            self._render_dataset_card(run_id, "regression", config, evaluation), encoding="utf-8"
        )

        summary_path = run_dir / "report.html"
        summary_path.write_text(self._render_report_html(run_id, "regression", scorecard), encoding="utf-8")

        self._register_artifact(run_id, "config.json", "config", "application/json", config_path)
        self._register_artifact(run_id, "metrics_history.csv", "metrics_csv", "text/csv", run_dir / "metrics_history.csv")
        self._register_artifact(run_id, "predictions.csv", "predictions_csv", "text/csv", run_dir / "predictions.csv")
        self._register_artifact(run_id, "forecast_scatter.png", "forecast_plot", "image/png", forecast_path)
        self._register_artifact(run_id, "metric_curves.png", "metrics_plot", "image/png", curve_path)
        self._register_artifact(run_id, "dataset_card.md", "dataset_card", "text/markdown", dataset_card_path)
        self._register_artifact(run_id, "model_card.md", "model_card", "text/markdown", model_card_path)
        self._register_artifact(run_id, "report.html", "report", "text/html", summary_path)
        return scorecard

    def _plot_metric_curves(self, history_frame: pd.DataFrame, output_path: Path, metric_names: list[str]) -> None:
        plt.figure(figsize=(8, 4.5))
        for metric_name in metric_names:
            if metric_name not in history_frame.columns:
                continue
            plt.plot(history_frame["step"], history_frame[metric_name], marker="o", linewidth=2, label=metric_name)
        plt.xlabel("Step")
        plt.ylabel("Metric value")
        plt.title("Metric history")
        plt.legend()
        plt.tight_layout()
        plt.savefig(output_path, dpi=220, bbox_inches="tight")
        plt.close()

    def _persist_metric_point(self, run_id: str, metrics: dict[str, Any]) -> None:
        with self._session_factory() as session:
            point = MetricPoint(run_id=run_id, **metrics)
            session.add(point)
            run = self.get_run(session, run_id)
            run.latest_message = f"Latest step: {metrics['step']}"
            session.commit()

    def _append_log(self, run_id: str, level: str, message: str, payload: dict[str, Any] | None = None) -> None:
        payload = payload or {}
        log_path = self._run_dir(run_id) / "logs.jsonl"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "timestamp": _utc_now().isoformat(),
            "level": level,
            "message": message,
            "payload": payload,
        }
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry) + "\n")

    def _register_artifact(
        self,
        run_id: str,
        name: str,
        artifact_type: str,
        mime_type: str,
        absolute_path: Path,
    ) -> None:
        with self._session_factory() as session:
            artifact = ArtifactEntry(
                run_id=run_id,
                name=name,
                artifact_type=artifact_type,
                mime_type=mime_type,
                relative_path=str(absolute_path.relative_to(self._storage_root)),
            )
            session.add(artifact)
            session.commit()

    def _run_dir(self, run_id: str) -> Path:
        return self._storage_root / "runs" / run_id

    def _render_model_card(
        self,
        run_id: str,
        task_type: str,
        config: dict[str, Any],
        scorecard: dict[str, Any],
        evaluation: dict[str, Any],
    ) -> str:
        task_limit = (
            "Synthetic binary classification does not establish performance on customer or equipment data."
            if task_type == "classification"
            else "Synthetic chronological demand does not establish performance on a real product, region, or business."
        )
        return (
            f"# Model Card: {run_id}\n\n"
            "## Intended use\n\n"
            "Demonstrate local experiment tracking, artifact generation, and evaluation plumbing. "
            "The fitted estimator is not intended for operational decisions.\n\n"
            f"## Reproducibility\n\n"
            f"- Seed: `{config['seed']}`\n"
            f"- Config version: `{config['config_version']}`\n"
            f"- Git commit: `{self._source_revision}`\n"
            f"- Evaluation: {evaluation['protocol']}\n"
            f"- Train rows: `{evaluation['train_rows']}`\n"
            f"- Test rows: `{evaluation['test_rows']}`\n\n"
            "## Leakage control\n\n"
            f"{evaluation['leakage_control']}\n\n"
            "## Final scorecard\n\n"
            f"```json\n{json.dumps(scorecard, indent=2, sort_keys=True)}\n```\n\n"
            "## Limitations and risks\n\n"
            f"- {task_limit}\n"
            "- Metrics describe one seeded synthetic holdout and have not been externally validated.\n"
            "- Thresholds, costs, fairness constraints, and monitoring requirements depend on the real deployment context.\n"
        )

    def _render_dataset_card(
        self,
        run_id: str,
        task_type: str,
        config: dict[str, Any],
        evaluation: dict[str, Any],
    ) -> str:
        if task_type == "classification":
            construction = (
                "Generated in memory with scikit-learn `make_classification` using the recorded seed, "
                "class balance, separation, label-noise, and feature-count parameters."
            )
            scope = "Independent synthetic rows with a binary target and anonymous numeric features."
        else:
            construction = (
                "Generated in memory from a deterministic daily trend, weekly and monthly seasonality, "
                "seeded promotions, price variation, and Gaussian noise. Lag-1, lag-7, and shifted rolling-mean "
                "features use only current or earlier dates."
            )
            scope = (
                f"Synthetic daily series from `{config['start_date']}` with a chronological test window "
                f"from `{evaluation['test_start']}` through `{evaluation['test_end']}`."
            )
        return (
            f"# Dataset Card: {run_id}\n\n"
            "## Source and license\n\n"
            "Generated locally by this repository. No external, personal, proprietary, or scraped data is used. "
            "The fixture is distributed under the repository license.\n\n"
            "## Construction\n\n"
            f"{construction}\n\n"
            "## Scope\n\n"
            f"{scope}\n\n"
            "## Split and leakage controls\n\n"
            f"- Protocol: {evaluation['protocol']}\n"
            f"- Train rows: `{evaluation['train_rows']}`\n"
            f"- Test rows: `{evaluation['test_rows']}`\n"
            f"- Control: {evaluation['leakage_control']}\n\n"
            "## Limitations\n\n"
            "This generated dataset is a software fixture. It is not representative evidence for a population, "
            "asset fleet, customer base, or future demand process.\n"
        )

    def _render_report_html(self, run_id: str, task_type: str, scorecard: dict[str, Any]) -> str:
        metric_items = "".join(f"<li><strong>{key}</strong>: {value}</li>" for key, value in scorecard.items())
        return (
            "<!DOCTYPE html><html><head><meta charset='utf-8'><title>Run Report</title>"
            "<style>body{font-family:Arial,sans-serif;margin:40px;background:#f7f5ef;color:#14213d}"
            "h1{margin-bottom:8px}ul{line-height:1.8}code{background:#e8ebf0;padding:2px 6px;border-radius:6px}"
            ".badge{display:inline-block;background:#0f4c81;color:white;padding:6px 10px;border-radius:999px;}"
            "</style></head><body>"
            f"<span class='badge'>{task_type.title()} run</span><h1>Experiment report for {run_id}</h1>"
            "<p>Generated by the ML Experiment Control Center export endpoint.</p>"
            f"<ul>{metric_items}</ul></body></html>"
        )
