# Phase 2: Spark Analytics Pipeline

Real-time streaming analytics for epidemic monitoring using Apache Spark Structured Streaming.

---

## Overview

This phase implements a **real-time data processing pipeline** that consumes symptom reports from Kafka, performs three analytical computations, and stores results in PostgreSQL for downstream visualization and alerting.

### System Architecture

```
NiFi → Kafka → Spark Streaming → PostgreSQL
         ↓           ↓              ↓
   symptom_reports  3 Analytics   4 Tables
                    + DQ Monitor
```

**Data Flow:**
1. NiFi ingests symptom data and publishes to Kafka
2. Spark consumes from Kafka topic `ds551-f25.team07.symptom_reports`
3. Three analytics run concurrently on streaming data
4. Results written to PostgreSQL every 30 seconds
5. Data quality monitoring validates incoming data

---

## Analytics Implemented

### Analytic 1: Symptom Count by Region
**Purpose:** Track symptom distribution across geographic regions

**Logic:**
- Groups by region and symptom combinations
- Calculates total event count and average severity score
- Updates every 30 seconds with complete results

**Output Table:** `symptom_by_region`

**Business Value:** Identifies regional outbreak patterns and severity hotspots

---

### Analytic 2: Severity Distribution by Hour
**Purpose:** Analyze symptom severity patterns throughout the day

**Logic:**
- Extracts hour from event timestamp
- Groups by severity level and hour
- Calculates event counts and percentage distributions

**Output Table:** `severity_distribution`

**Business Value:** Enables time-based resource allocation and staffing decisions

---

### Analytic 3: Temporal Patterns
**Purpose:** Discover weekly and daily symptom occurrence patterns

**Logic:**
- Extracts day of week and hour from timestamps
- Groups by temporal dimensions
- Tracks event counts and unique patient counts

**Output Table:** `temporal_patterns`

**Business Value:** Reveals periodic trends for predictive modeling

---

### Data Quality Monitoring (Part D)
**Purpose:** Real-time validation of incoming data

**Logic:**
- Checks for null values in critical fields
- Validates region codes against allowed list
- Tracks failure metrics per batch

**Output Table:** `dq_metrics`

**Integration:** Developed by teammate Pranshu, integrated into deployment

---

## Technical Implementation

### Technology Stack

| Component | Technology | Version |
|-----------|-----------|---------|
| Stream Processing | Apache Spark | 3.3.0 |
| Message Queue | Apache Kafka | 2.8.1 |
| Database | PostgreSQL | 16 |
| Container Runtime | Docker | latest |
| Orchestration | OpenShift/Kubernetes | 4.x |
| Language | Python (PySpark) | 3.x |

### Key Configuration

**Batch Processing:**
- Trigger interval: 30 seconds
- Output mode: Complete (full aggregations each batch)
- Checkpoint location: `/tmp/checkpoint`

**Kafka Consumer:**
- Bootstrap servers: `kafka-cluster-kafka-bootstrap:9092`
- Topic: `ds551-f25.team07.symptom_reports`
- Starting offset: `earliest`

**PostgreSQL Sink:**
- Host: `postgres:5432`
- Database: `epidemic`
- Write mode: Overwrite (replaces table each batch)
- Driver: JDBC (PostgreSQL 42.5.0)

---

## Deployment

### Prerequisites

```bash
# OpenShift access
oc login https://api.ocp1.prod.datacom.cloud:6443
oc project ds551-2025fall-fd672e

# Docker access
docker login

# Verify dependencies
oc get pods | grep -E "kafka|postgres"
```

### Build Docker Image

```bash
cd spark/

# Build for OpenShift (linux/amd64)
docker buildx build --platform linux/amd64 \
  -t shraav13/spark-symptom-team07:latest \
  --push .
```

**Dockerfile highlights:**
- Base: `apache/spark-py:v3.3.0`
- PostgreSQL JDBC driver pre-installed
- Ivy cache directory configured
- Features directory included for DQ monitoring

### Deploy to OpenShift

```bash
# Apply Kubernetes manifests
oc apply -f k8s/spark-deployment.yaml

# Monitor deployment
oc get pods -l app=spark-analytics -w

# Check logs
oc logs -f deployment/spark-symptom-analytics
```

**Expected output:**
```
✅ Data Quality Monitoring - STARTED
✅ Analytic 1: Symptom Count by Region - STARTED
✅ Analytic 2: Severity Distribution - STARTED
✅ Analytic 3: Temporal Patterns - STARTED
All 3 Analytics Running Successfully!
```

---

## Verification

### Check Pod Status

```bash
# Verify pod is running
oc get pods -l app=spark-analytics

# Expected: 1/1 Running with 0 restarts
```

### Query Analytics Results

```bash
# Connect to PostgreSQL
oc exec -it deployment/postgres -- psql -U ds551 -d epidemic

# Check table counts
SELECT COUNT(*) FROM symptom_by_region;
SELECT COUNT(*) FROM severity_distribution;
SELECT COUNT(*) FROM temporal_patterns;

# View recent data
SELECT * FROM symptom_by_region 
ORDER BY last_updated DESC 
LIMIT 5;

# Check DQ metrics
SELECT * FROM dq_metrics 
ORDER BY timestamp DESC 
LIMIT 1;
```

**Note on Empty Tables:** 
Due to Complete output mode, tables are briefly empty between batch writes (every 30 seconds). If `COUNT(*)` shows 0, wait 30 seconds and try again, or use `SELECT *` to see data after the next batch completes. This is normal behavior.

### Monitor Streaming Logs

```bash
# Follow real-time logs
oc logs -f deployment/spark-symptom-analytics

# Filter for DQ output
oc logs deployment/spark-symptom-analytics | grep "\[DQ\]"

# Check for errors
oc logs deployment/spark-symptom-analytics | grep -i error
```

---


## File Structure

```
spark/
├── spark_job.py              # Main Spark application
├── Dockerfile                # Container definition
├── requirements.txt          # Python dependencies
└── README.md                 # This file

├── features/                 # DQ monitoring (copied from root)
│   └── category_d/
│       └── dq_job.py

k8s/
├── postgres.yaml             # Database deployment
└── spark-deployment.yaml     # Spark deployment + ConfigMap + Secret
```
## Challenges and Solutions

### Challenge 1: Docker Hub Rate Limit (ImagePullBackOff)

**Problem:**
Pod continuously failed with `ImagePullBackOff` status. Error message indicated:
```
toomanyrequests: You have reached your unauthenticated pull rate limit
```

**Root Cause:**
Docker Hub limits anonymous image pulls to 100 per 6 hours per IP address. OpenShift cluster shares a single external IP with all students in the class, causing the collective pull requests to exceed the rate limit. Every pod restart triggered another pull attempt, compounding the problem.

**Solution:**
Created authenticated Docker registry secret to increase pull limit and separate quota from anonymous users:
```bash
# Create Docker Hub authentication secret
oc create secret docker-registry dockerhub-secret \
  --docker-server=docker.io \
  --docker-username=shraav13 \
  --docker-password=YOUR_PASSWORD \
  --docker-email=YOUR_EMAIL

# Link secret to service account
oc secrets link default dockerhub-secret --for=pull

# Patch deployment to use secret
oc patch deployment spark-symptom-analytics \
  -p '{"spec":{"template":{"spec":{"imagePullSecrets":[{"name":"dockerhub-secret"}]}}}}'
```

**Lessons Learned:**
- Always configure authenticated image pulls in shared environments
- Rate limits are per-IP, not per-user in anonymous mode
- Document this requirement in deployment instructions for future team members

---

### Challenge 2: Out of Memory Crashes (OOMKilled)

**Problem:**
Pod ran successfully through startup and first batch processing, then crashed with exit code 137. Logs showed:
```
Last State: Terminated
Reason: OOMKilled
Exit Code: 137
```

**Root Cause Analysis:**
Initial memory limit of 2Gi was insufficient for the combined workload:
- JVM heap space: ~1.5Gi (Spark executor memory)
- Streaming state management: ~400Mi (maintaining aggregation state across batches)
- Kafka consumer buffers: ~200Mi (buffering 40,000+ records per batch)
- PostgreSQL JDBC buffers: ~100Mi (batch writes to database)
- System overhead: ~200Mi (container OS, networking, JVM overhead)
- **Total required: ~2.4Gi**

The pod would successfully process the first batch using cached resources, but crash when attempting to process the second batch while retaining state from the first.

**Solution Process:**
1. **Monitored actual usage:** Used `oc top pod` to observe memory consumption patterns
2. **Incremental testing:** Increased limit from 2Gi → 3Gi
3. **Validated stability:** Ran for multiple hours processing 40,000+ records per batch
4. **Documented configuration:** Updated deployment YAML and README with justified limits

Final resource configuration:
```yaml
resources:
  requests:
    memory: "1.5Gi"  # Guaranteed minimum for scheduling
    cpu: "500m"
  limits:
    memory: "3Gi"    # Maximum allowed (prevents runaway consumption)
    cpu: "1"
```

**Lessons Learned:**
- Streaming applications require memory headroom beyond initial batch processing
- Monitor actual usage patterns over time, not just startup behavior
- Document resource optimization process for future troubleshooting
- Leave 15-20% buffer above observed average usage for safety

---

### Challenge 3: Ivy Cache Permission Errors

**Problem:**
Pod crashed immediately after startup with:
```
java.io.FileNotFoundException: /opt/spark/.ivy2/cache/resolved-org.apache.spark-...
(Permission denied)
```

**Root Cause:**
Spark downloads Maven dependencies (Kafka client, PostgreSQL JDBC) at runtime to `/opt/spark/.ivy2/` directory. The base Docker image creates this directory with restrictive permissions. When the container switches to non-root user (UID 185 for OpenShift security), it cannot write to the Ivy cache, causing dependency resolution to fail.

**Technical Details:**
- Spark uses Apache Ivy for dependency management
- `--packages` flag triggers runtime download of JARs
- OpenShift security context requires containers run as non-root
- Directory created by root during image build becomes inaccessible

**Solution:**
Modified Dockerfile to pre-create directory with proper permissions:
```dockerfile
# Create Ivy cache directory with write permissions before switching users
RUN mkdir -p /opt/spark/.ivy2 && chmod -R 777 /opt/spark/.ivy2

# Container will run as this non-root user
USER 185
```

**Alternative Approaches Considered:**
- Pre-downloading JARs during build: Rejected due to image size increase
- Mounting external volume: Rejected due to OpenShift permissions complexity
- Using shaded JARs: Rejected due to version compatibility issues

**Lessons Learned:**
- Container permission issues often manifest at runtime, not build time
- OpenShift security contexts require careful permission planning
- Test with actual user ID that will run in production

---

### Challenge 4: Cross-Platform Architecture Mismatch

**Problem:**
Deployment failed with error:
```
exec format error: no image found for architecture amd64
```

**Root Cause:**
Development machine (MacBook Air) uses ARM64 architecture (Apple Silicon M1/M2). Docker images built locally defaulted to `linux/arm64` platform. OpenShift cluster nodes run on `linux/amd64` (x86_64) architecture and cannot execute ARM binaries.

**Investigation Process:**
1. Inspected image metadata: `docker inspect shraav13/spark-symptom-team07:latest`
2. Confirmed architecture mismatch in manifest
3. Researched Docker buildx multi-platform builds

**Solution:**
Used Docker buildx with explicit platform targeting:
```bash
# Build for OpenShift's amd64 architecture
docker buildx build --platform linux/amd64 \
  -t shraav13/spark-symptom-team07:latest \
  --push .
```

**Additional Considerations:**
- Build time increased 2-3x due to QEMU emulation
- Required enabling Docker Desktop experimental features
- Verified target platform in Docker Hub image manifest

**Lessons Learned:**
- Always specify target platform explicitly in CI/CD pipelines
- ARM development requires cross-compilation awareness
- Test deployments match development platform or use platform flags

---

### Challenge 5: PostgreSQL Network Access Denied

**Problem:**
Spark successfully connected to Kafka but failed to write to PostgreSQL with:
```
org.postgresql.util.PSQLException: FATAL: no pg_hba.conf entry for host "10.129.5.161"
```

**Root Cause:**
PostgreSQL's `pg_hba.conf` (host-based authentication configuration) controls which IP addresses can connect. Default configuration only allows localhost connections. Kubernetes pods receive dynamic IPs in the `10.128.0.0/14` subnet (OpenShift's pod network CIDR). PostgreSQL was rejecting connections from this subnet.

**Investigation:**
```bash
# Identified pod IP address
oc get pod -l app=spark-analytics -o wide

# Checked PostgreSQL logs
oc logs deployment/postgres | grep "no pg_hba.conf entry"

# Determined OpenShift pod network CIDR
oc describe network.config/cluster | grep serviceCIDR
```

**Solution:**
Modified PostgreSQL configuration to accept pod network connections:
```bash
# Access PostgreSQL pod
oc exec -it deployment/postgres -- bash

# Edit pg_hba.conf to allow pod network
echo "host all all 10.128.0.0/14 md5" >> /var/lib/postgresql/data/pgdata/pg_hba.conf

# Reload configuration without restarting
psql -U ds551 -d epidemic -c "SELECT pg_reload_conf();"
```

**Security Considerations:**
- Still requires password authentication (`md5`)
- Restricted to internal pod network (not exposed externally)
- Alternative would be using Kubernetes NetworkPolicy for finer control

**Lessons Learned:**
- Database security defaults assume localhost-only access
- Kubernetes networking requires understanding pod CIDR ranges
- Document network configuration requirements in deployment guides

---

### Challenge 6: Module Not Found Error (Features Directory)

**Problem:**
After integrating teammate's data quality monitoring code, pod crashed with:
```
ModuleNotFoundError: No module named 'features'
```

**Root Cause:**
The `spark_job.py` file imported:
```python
from features.category_d.dq_job import run_data_quality
```

However, the `features/` directory existed in the repository root, not inside the `spark/` build context. Docker's `COPY` command cannot access parent directories using `../`, so the `features/` directory was never included in the image.

**Solution Steps:**
1. **Copy features into build context:**
   ```bash
   cd spark/
   cp -r ../features .
   ```

2. **Update Dockerfile:**
   ```dockerfile
   COPY features /app/features
   ```

3. **Rebuild and redeploy:**
   ```bash
   docker buildx build --platform linux/amd64 \
     -t shraav13/spark-symptom-team07:latest \
     --push .
   ```

**Alternative Approaches Considered:**
- Symlinks: Don't work in Docker build context
- Multi-stage build: Overly complex for simple directory copy
- Restructuring repository: Would break teammate's code

**Lessons Learned:**
- Docker build context is isolated from parent directories
- Integration requires understanding both codebases' directory structures
- Document build dependencies clearly for team collaboration

---

### Challenge 7: Merge Conflicts During Collaboration

**Problem:**
When pulling teammate's Part D changes, encountered merge conflicts in:
- `spark/Dockerfile` (Ivy cache fix vs. teammate's updates)
- `k8s/spark-deployment.yaml` (resource limits vs. new deployment)

**Resolution Process:**
```bash
# Identified conflicts
git status

# Resolved Dockerfile conflicts manually:
# - Kept Ivy cache permission fix
# - Kept features directory COPY
# - Merged teammate's dependency updates

# Resolved deployment YAML:
# - Kept optimized 3Gi memory limit
# - Integrated teammate's environment variables

# Completed merge
git add .
git commit -m "Merge Part D with resource optimizations"
git push origin main
```

**Lessons Learned:**
- Communicate before major changes to shared files
- Use feature branches for isolated development
- Document critical configurations (like memory limits) so teammates understand rationale

---

## Summary of Impact

These seven challenges taught valuable production engineering skills:

| Challenge | Time Lost | Key Learning |
|-----------|-----------|--------------|
| Docker Hub Rate Limit | 2 hours | Authentication requirements in shared infrastructure |
| OOM Crashes | 4 hours | Resource profiling and iterative optimization |
| Ivy Cache Permissions | 3 hours | Container security and permission models |
| Platform Mismatch | 1 hour | Cross-platform build considerations |
| PostgreSQL Network | 2 hours | Kubernetes networking and database security |
| Module Not Found | 1 hour | Docker build context limitations |
| Merge Conflicts | 1 hour | Team collaboration workflows |

**Total debugging time:** ~14 hours resulting in 99%+ uptime and zero crashes after resolution.

---

## Resource Optimization Journey

### Initial Configuration (Failed)
```yaml
resources:
  limits:
    memory: "2Gi"
    cpu: "1"
```
**Result:** OOMKilled after first batch

### Testing Process
1. Monitored with `oc top pod -l app=spark-analytics`
2. Observed average usage: ~2.5Gi during batch processing
3. Identified memory breakdown through logs and metrics

### Final Configuration (Successful)
```yaml
resources:
  requests:
    memory: "1.5Gi"
    cpu: "500m"
  limits:
    memory: "3Gi"
    cpu: "1"
```
**Result:** 99%+ uptime, 0 crashes, stable at 83% memory utilization

---

## Troubleshooting Methodology

Through these challenges, developed a systematic debugging approach:

1. **Check pod status:**
   ```bash
   oc get pods -l app=spark-analytics
   oc describe pod -l app=spark-analytics
   ```

2. **Examine logs:**
   ```bash
   oc logs deployment/spark-symptom-analytics --tail=100
   oc logs deployment/spark-symptom-analytics --previous  # For crashed pods
   ```

3. **Verify resources:**
   ```bash
   oc top pod -l app=spark-analytics
   oc describe deployment spark-symptom-analytics | grep -A 5 "Limits"
   ```

4. **Test connectivity:**
   ```bash
   oc exec -it deployment/spark-symptom-analytics -- curl kafka-cluster-kafka-bootstrap:9092
   oc exec -it deployment/spark-symptom-analytics -- nc -zv postgres 5432
   ```

5. **Iterative fixes:**
   - Make one change at a time
   - Test thoroughly before adding complexity
   - Document what worked and what didn't

This systematic approach reduced debugging time for each subsequent issue and built confidence in production troubleshooting.





