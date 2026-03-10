#  Kubernetes YAML Files


## Deployment Order

Run these files in the following order:

### 1. postgres.yaml (Deploy First)
### 2. spark-deployment.yaml (Deploy Second)



**Resources Defined:**
- **Requests:** 1.5Gi memory, 500m CPU (minimum guaranteed)
- **Limits:** 3Gi memory, 1 CPU (maximum allowed)
- **Replicas:** 1000m (ensures exactly-once processing)
- **ImagePullSecrets:** dockerhub-secret (for authenticated Docker Hub access)

---

## Deployment Instructions

### Step 1: Deploy PostgreSQL
```bash
oc apply -f k8s/postgres.yaml

# Wait for pod to be ready
oc get pods -l app=postgres -w
```

### Step 2: Configure PostgreSQL Network Access
```bash
# Allow pod network connections
oc exec -it deployment/postgres -- bash -c \
  "echo 'host all all 10.128.0.0/14 md5' >> /var/lib/postgresql/data/pgdata/pg_hba.conf"

# Reload configuration
oc exec -it deployment/postgres -- psql -U ds551 -d epidemic -c "SELECT pg_reload_conf();"
```

### Step 3: Create Docker Hub Secret (Important!)
```bash
# Required to avoid Docker Hub rate limits
oc create secret docker-registry dockerhub-secret \
  --docker-server=docker.io \
  --docker-username=YOUR_DOCKERHUB_USERNAME \
  --docker-password=YOUR_DOCKERHUB_PASSWORD \
  --docker-email=YOUR_EMAIL
```

### Step 4: Deploy Spark Analytics
```bash
oc apply -f k8s/spark-deployment.yaml

# Wait for pod to be ready
oc get pods -l app=spark-analytics -w
```

### Step 5: Verify Deployment
```bash
# Check logs
oc logs -f deployment/spark-symptom-analytics

# Expected output:
# ✅ Data Quality Monitoring - STARTED
# ✅ Analytic 1: Symptom Count by Region - STARTED
# ✅ Analytic 2: Severity Distribution - STARTED
# ✅ Analytic 3: Temporal Patterns - STARTED
```

---

## Resource Allocation Summary

| Component | Memory Request | Memory Limit | CPU Request | CPU Limit | Notes |
|-----------|---------------|--------------|-------------|-----------|-------|
| PostgreSQL | Default | Default | Default | Default | Uses namespace defaults |
| Spark Analytics | 1.5Gi | 3Gi | 500m | 1000m CPU | Optimized through testing |

**Total Namespace Usage:**
- Memory: 14.8Gi / 16Gi (93%)
- CPU: 6 / 6 cores (100%)

**Resource Optimization Process:**
1. Initial: 2Gi memory → OOM crashes during processing
2. Adjusted: 3Gi memory → Stable operation with zero restarts
3. Requests: 1.5Gi to allow scheduling while reserving capacity

---

## Why This Order?

1. **PostgreSQL must deploy first** - Spark requires database connection to write analytics
2. **ConfigMap and Secret before Deployment** - Environment variables must exist when pod starts
3. **Docker Hub secret before Spark** - Prevents ImagePullBackOff due to rate limits
4. **Single replica for Spark** - Ensures exactly-once processing semantics for streaming

---

## Additional Configuration Files

**Complete documentation:** `spark/README.md`  
**GitHub Repository:** https://github.com/BU-CDS-DS551-2025-Fall/epidemic-engine-team-7

---

**Deployment Status:** ✅ Operational  
**Namespace:** ds551-2025fall-fd672e  
