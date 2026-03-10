from sklearn.linear_model import LinearRegression
"""
Phase 3: Category 
Phase 3 - Category B2 (Additional Features for Extra Credit) 
Outbreak Prediction Model (Linear Regression)

Uses aggregated temporal patterns to train a Linear Regression model that predicts
event_count based on day_of_week, hour_of_day, and unique_patients.

This model serves as a baseline comparison against the Random Forest model.

Steps:
  1) Load data from `temporal_patterns`
  2) Build features (basic + simple cyclical encoding of hour_of_day)
  3) Train/test split and train a LinearRegression model
  4) Compute RMSE and MAE
  5) Store predictions in `outbreak_predictions` table with a distinct run_id

Run locally (with oc port-forward):
  1) oc port-forward svc/postgres 5432:5432
  2) python features/category_b/outbreak_prediction_linear.py
"""

import os
from datetime import datetime, timezone
import numpy as np
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, mean_absolute_error
from sklearn.model_selection import train_test_split

def get_engine():
    load_dotenv()
    host=os.getenv("DB_HOST", "localhost")
    port=os.getenv("DB_PORT", "5432")
    db_name=os.getenv("DB_NAME", "epidemic")
    user=os.getenv("DB_USER", "ds551")
    password=os.getenv("DB_PASSWORD", "ds551pw")
    url=f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db_name}"
    return create_engine(url)

def fetch_temporal_patterns(engine) -> pd.DataFrame:
    """
    Load temporal pattern data from Postgres.
    Expected columns:
      - day_of_week
      - hour_of_day
      - event_count
      - unique_patients
      - last_updated
    """
    query = """
        SELECT
            day_of_week,
            hour_of_day,
            event_count,
            unique_patients,
            last_updated
        FROM temporal_patterns;
    """
    with engine.connect() as conn:
        df=pd.read_sql(query, conn)

    return df
def build_features(df: pd.DataFrame):
    """
    Convert raw temporal patterns into X (features) and y (targets).
    Returns (X, y) or (None, None) if there's no usable data.
    """
    if df.empty:
        print("No rows in temporal_patterns; cannot train model.")
        return None, None
    print(f"Loaded {len(df)} rows from temporal_patterns into DataFrame.")
    # Defensive numeric casting
    for col in ["day_of_week", "hour_of_day", "unique_patients", "event_count"]:
        df[col]=pd.to_numeric(df[col], errors="coerce")
    df=df.dropna(
        subset=["day_of_week", "hour_of_day", "unique_patients", "event_count"]
    )
    if df.empty:
        print("All rows became NaN after casting; cannot train model.")
        return None, None
    # Base features
    X=df[["day_of_week", "hour_of_day", "unique_patients"]].copy()

    # Cyclical encoding for hour_of_day
    X["hour_sin"]=np.sin(2 * np.pi * X["hour_of_day"] / 24.0)
    X["hour_cos"]=np.cos(2 * np.pi * X["hour_of_day"] / 24.0)

    y=df["event_count"].astype(float)

    return X, y

def train_and_evaluate_linear_regression(X, y, test_size: float = 0.2, random_state: int = 42):
    """
    Train a Linear Regression model that differs from the random forest model and compute evaluation metrics.
    """
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=test_size, random_state=random_state)
    model = LinearRegression()
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    mse = mean_squared_error(y_test, y_pred)
    rmse = mse ** 0.5
    mae = mean_absolute_error(y_test, y_pred)
    print("Linear Regression Outbreak Prediction Metrics:")
    print(f"  RMSE = {rmse:.3f}")
    print(f"  MAE  = {mae:.3f}")

    return model, X_test, y_test, y_pred, rmse, mae

# -------------------------------------------------------------------
# Persistence
# -------------------------------------------------------------------
def write_predictions(engine,X_test: pd.DataFrame,y_test: pd.Series,y_pred: np.ndarray,rmse: float,mae: float,):
    """
    Store predictions in `outbreak_predictions` table.
    Uses a distinct run_id to differentiate from Random Forest runs.
    """
    if X_test.empty:
        print("No test data to write predictions.")
        return
    run_id = f"linear_regression_{datetime.now(timezone.utc).isoformat()}"

    df_pred = X_test[["day_of_week", "hour_of_day", "unique_patients"]].copy()
    df_pred["event_count_true"] = y_test.values
    df_pred["event_count_pred"] = y_pred
    df_pred["rmse"] = rmse
    df_pred["mae"] = mae
    df_pred["run_id"] = run_id
    df_pred["predicted_at"] = datetime.now(timezone.utc)

    records = df_pred.to_dict(orient="records")

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS outbreak_predictions (
                    id SERIAL PRIMARY KEY,
                    day_of_week INTEGER,
                    hour_of_day INTEGER,
                    unique_patients INTEGER,
                    event_count_true DOUBLE PRECISION,
                    event_count_pred DOUBLE PRECISION,
                    rmse DOUBLE PRECISION,
                    mae DOUBLE PRECISION,
                    run_id TEXT,
                    predicted_at TIMESTAMP
                );
                """
            )
        )

        conn.execute(
            text(
                """
                INSERT INTO outbreak_predictions (
                    day_of_week,
                    hour_of_day,
                    unique_patients,
                    event_count_true,
                    event_count_pred,
                    rmse,
                    mae,
                    run_id,
                    predicted_at
                )
                VALUES (
                    :day_of_week,
                    :hour_of_day,
                    :unique_patients,
                    :event_count_true,
                    :event_count_pred,
                    :rmse,
                    :mae,
                    :run_id,
                    :predicted_at
                );
                """
            ),
            records,
        )

    print(
        f"Wrote {len(df_pred)} Linear Regression predictions "
        f"to 'outbreak_predictions' (run_id={run_id})."
    )


# -------------------------------------------------------------------
# Entry point
# -------------------------------------------------------------------

def main():
    print("=== Phase 3: Outbreak Prediction (Linear Regression Baseline) ===")
    engine = get_engine()
    df = fetch_temporal_patterns(engine)

    print(f"Loaded {len(df)} rows from temporal_patterns.")

    X, y = build_features(df)
    if X is None or y is None:
        print("Skipping outbreak prediction run because there is no usable data.")
        print("=== Outbreak prediction run complete (no data) ===")
        return

    model, X_test, y_test, y_pred, rmse, mae = train_and_evaluate_linear_regression(X, y)
    write_predictions(engine, X_test, y_test, y_pred, rmse, mae)

    print("=== Linear Regression outbreak prediction run complete ===")


if __name__ == "__main__":
    main()
