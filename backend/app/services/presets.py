from __future__ import annotations

from copy import deepcopy


PRESETS = {
    "customer-churn": {
        "display_name": "Customer Churn Baseline",
        "description": "Binary churn classification with gradient boosting and structured business features.",
        "dataset_name": "Synthetic Customer Churn",
        "task_type": "classification",
        "model_name": "Gradient Boosting Classifier",
        "config": {
            "config_version": "1.0.0",
            "samples": 2200,
            "features": 18,
            "informative": 8,
            "class_sep": 1.25,
            "weights": [0.68, 0.32],
            "epochs": 16,
            "learning_rate": 0.08,
            "max_depth": 3,
            "test_size": 0.24,
            "seed": 13,
        },
    },
    "predictive-maintenance": {
        "display_name": "Predictive Maintenance Classifier",
        "description": "Failure risk prediction from synthetic multivariate sensor windows inspired by machine telemetry workloads.",
        "dataset_name": "Synthetic Sensor Degradation",
        "task_type": "classification",
        "model_name": "Gradient Boosting Classifier",
        "config": {
            "config_version": "1.0.0",
            "samples": 2600,
            "features": 24,
            "informative": 10,
            "class_sep": 1.45,
            "weights": [0.76, 0.24],
            "flip_y": 0.02,
            "epochs": 18,
            "learning_rate": 0.07,
            "max_depth": 3,
            "test_size": 0.22,
            "seed": 29,
        },
    },
    "demand-forecasting": {
        "display_name": "Demand Forecasting Regressor",
        "description": "Forecasting-style regression workload with seasonality, promotions, and pricing effects.",
        "dataset_name": "Synthetic Retail Demand",
        "task_type": "regression",
        "model_name": "Gradient Boosting Regressor",
        "config": {
            "config_version": "1.0.0",
            "samples": 1800,
            "features": 12,
            "noise": 1.8,
            "epochs": 20,
            "learning_rate": 0.06,
            "max_depth": 3,
            "test_size": 0.2,
            "seed": 7,
        },
    },
}


def get_presets() -> dict[str, dict]:
    return deepcopy(PRESETS)


def get_preset(key: str) -> dict:
    presets = get_presets()
    if key not in presets:
        available = ", ".join(sorted(presets))
        raise KeyError(f"Unknown preset '{key}'. Available presets: {available}")
    return presets[key]

