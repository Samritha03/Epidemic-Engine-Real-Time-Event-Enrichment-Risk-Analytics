# Extra Credit: ML Model Comparison & Visualization

## Overview

As an extra credit enhancement, we implemented and compared multiple lightweight machine learning models for outbreak prediction and integrated their evaluation into Grafana for continuous performance monitoring and analysis.

---

## Models Implemented

We evaluated the following models using features derived from the `temporal_patterns` table:

1. **Baseline Model (Rolling Average)**

   * Uses historical rolling averages of event counts
   * Serves as a simple benchmark for comparison

2. **Linear Regression**

   * Predicts event counts using temporal and population features
   * Provides a fast and interpretable model

3. **Gradient Boosting / Random Forest Regressor**

   * Captures non-linear relationships and temporal patterns
   * Achieved the strongest predictive performance

---

## Feature Engineering

* Temporal features: `day_of_week`, `hour_of_day`
* Population signal: `unique_patients`
* Cyclical encoding of hour-of-day using sine and cosine transformations
* Consistent train/test split to prevent data leakage

---

## Evaluation Metrics

All models were evaluated using:

* **RMSE (Root Mean Squared Error)**
* **MAE (Mean Absolute Error)**

Metrics and predictions were persisted in the `outbreak_predictions` table for downstream analysis.

---

## Grafana Integration

Grafana dashboards were created to visualize and compare model performance in real time, including:

* RMSE and MAE trends over time
* Model stability across prediction runs
* Detection of performance degradation or drift

This integration allows model evaluation to be treated as an operational monitoring problem rather than a one-time offline analysis.

username: admin \
password: admin \
Dashboard: DS551 

---

## Results

* The rolling average baseline provided a reference but had the highest error.
* Linear regression reduced error while remaining simple and interpretable.
* The gradient boosting / random forest model achieved the lowest RMSE and MAE, demonstrating the benefit of non-linear modeling.

---

## Key Takeaways

* Comparing multiple models provides a principled basis for model selection.
* Lightweight ML models can significantly improve prediction accuracy with minimal operational overhead.
* Grafana-based visualization transforms model evaluation into a continuous, production-style monitoring workflow.

