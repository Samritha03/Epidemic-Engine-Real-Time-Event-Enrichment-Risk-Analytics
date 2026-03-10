# JupyterLab - Simple Deployment

Dead simple JupyterLab for Phase 3 visualizations.

---

## Quick Start

### 1. Set Your Password

**YOU MUST CHANGE THE PASSWORD**

Edit `jupyterlab.yaml` and change the password on line 41:

```yaml
- name: JUPYTER_TOKEN
  value: "ds551-jupyter"  # <-- Change this to your password
```

### 2. Deploy

```bash
kubectl apply -f jupyterlab.yaml -n <your-namespace>

# Wait for it to be ready
kubectl get pods -l app=jupyter -w
```

### 3. Get the URL

```bash
kubectl get route jupyter -o jsonpath='{.spec.host}'
```

### 4. Access

Open the URL in your browser and enter your password.

That's it!

---

## What's Included

- **Python 3.11** with pandas, numpy, matplotlib, plotly, scikit-learn
- **Pre-installed:** psycopg2-binary, pymongo, redis, plotly
- **Storage:** 2Gi persistent volume for your notebooks
- **Memory:** 1-2Gi
- **Access:** HTTPS via OpenShift Route

---

## Example: Connect to PostgreSQL

```python
import psycopg2
import pandas as pd
import plotly.express as px

# Connect (use your database service name)
conn = psycopg2.connect(
    host="postgres",
    port=5432,
    database="ds551",
    user="postgres",
    password="yourpassword"
)

# Query
df = pd.read_sql("SELECT * FROM analytics LIMIT 100", conn)

# Visualize
fig = px.line(df, x='timestamp', y='count')
fig.show()
```

---

## Troubleshooting

### Can't access the URL?

```bash
# Test directly (bypass Route)
kubectl port-forward svc/jupyterlab 8888:8888

# Then open: http://localhost:8888
# Use the password from your YAML
```

### Forgot password?

Check your YAML:

```bash
kubectl get deployment jupyter -o yaml | grep JUPYTER_TOKEN -A 1
```

### Need to change password?

Edit `jupyterlab.yaml`, change the JUPYTER_TOKEN value, then:

```bash
kubectl apply -f jupyterlab.yaml
kubectl rollout restart deployment/jupyter
```

### Install more packages?

```bash
kubectl exec -it deployment/jupyter -- pip install package-name
```

Or edit the YAML and add to the pip install line.

---

## For Phase 3

Required:

- Minimum 5 visualizations
- At least 1 interactive (Plotly)
- Connect to your database
- Export as HTML for submission

---

## Cleanup

```bash
kubectl delete -f jupyterlab.yaml
```
