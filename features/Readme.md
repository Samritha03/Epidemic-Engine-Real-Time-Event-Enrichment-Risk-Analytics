## Phase 3 – Features Pod Deployment (`features`)

The `features` pod is a standalone service that runs all Phase 3 feature logic on top of the epidemic database:

- **Category A1:** Basic Real-Time Alerting (`category_a/basic_alerting.py`)
- **Category A2:** Advanced Real-Time Alerting (`category_a/advanced_alerting.py`)
- **Category B1:** Anomaly Detection (`category_b/anomaly_detection.py`)
- **Category B2:** Outbreak Prediction (`category_b/outbreak_prediction.py`)

All of these are orchestrated by `features/features.py` and share the same Postgres database and Slack webhook.

##
### Layout of the Features Service

Repository paths:
- `features/features.py`  
  Orchestrator script; main entrypoint for the container.
- `features/Dockerfile.features`  
  Dockerfile used to build the `features` image.
- `features/requirements.txt`  
  Python dependencies (psycopg2, pandas, numpy, requests, python-dotenv, etc.).
- `features/category_a/basic_alerting.py`  
- `features/category_a/advanced_alerting.py`  
- `features/category_a/advanced_alert_config.json`  
- `features/category_b/anomaly_detection.py`  
- `features/category_b/outbreak_prediction.py`  
- `k8s/features-deployment.yaml`  
  OpenShift Deployment manifest for the `features` pod.

##
### What the `features` Pod Does

- When the container starts, it runs:
  ```bash
  python features.py
  ```
- Starts four threads:
  - basic-alerting-thread → run_basic_alerting(...) | Polls recent metrics and sends basic alerts to Slack.
  - advanced-alerting-thread → run_advanced_alerting() | Runs advanced, config-driven alerting with severity + cooldown.
  - anomaly-loop-thread → anomaly_loop(interval_seconds=300) | Every 5 minutes runs a one-shot anomaly detection pass, writing rows into anomalies.
  - outbreak-loop-thread → outbreak_loop(interval_seconds=600) | Every 10 minutes runs the outbreak prediction model and writes rows into outbreak_predictions.

- Keeps the main process alive so the pod runs indefinitely.
- Slack alerts are sent using the environment variable: `ALERT_WEBHOOK_URL` – Slack Incoming Webhook URL for the `#team-07-alerts` channel.

##
### Deploying the `features` Pod in OpenShift

- Building and Pushing the Docker Image: `docker.io/samritha03/features-team07:latest`
- OpenShift Deployment Manifest: The `k8s/features-deployment.yaml` file defines the Deployment
- From the repository root, Make sure you are logged into OpenShift and in the correct project:
  ```bash
  oc whoami
  oc project ds551-2025fall-fd672e
  ```
- Apply the Deployment:
  ```bash
  oc apply -f k8s/features-deployment.yaml
  ```
- Confirm that the features pod is running:
  ```bash
  oc get pods
  ```
- Verifying That the Features Service Is Working:
  ```bash
  oc logs deployment/features --tail=50 -f      #Tail the logs from the Deployment
  ```
- From the postgres pod:
  ```bash
  oc rsh deployment/postgres

  psql -U ds551 -d epidemic

  \dt
  SELECT COUNT(*) FROM anomalies;
  SELECT COUNT(*) FROM outbreak_predictions;
  ```

