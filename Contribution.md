## Team 07 - Contribution 


### Joshua Lee
#### BU Email: leejosh@bu.edu
#### BU ID: U09221943
### NIFI deployment
- Worked with the deployment and processors in Nifi. This included consuming from kafka, separating by event type, enriching with metadata, and publishing the new data to kafka.
- Ensure every event type was mapped correctly and ensured the data was correct by checking the ```data_provence`` tab.
- Exported the nifi flow to JSON and made it pretty using prettyprint.
- Included screenshots for each event type json file.
### Phase 2 Analytics
- After Shravani finished phase 2, I checked to make sure spark_job.py was running correctly and the analytics were written back to the database.
- Created a comprehensive README.md for the nifi data flow to make sure everything was documented accordingly.
- I wanted to know how the flow worked from part 1 so I did my own separate analytics for a separate topic "environmental_conditions"
- Followed off Shravini's code but did my analytics based on average temperature by region, air quality summary by region, and hourly weather trend.
- Created ```spark_job_pt2``` for the environmental_conditions and built the image using a new docker file and used the local image to then move it to the ```spark_environment_deployment.yaml``` in order to deploy it on openshift.

### Phase 3 Analytics
- Assisted Sam in backtesting and slack webhook to ensure it was functional and understood how the alerts worked within the world of event driven architecture.
- Helped with the HTTP POST requests for basic analytics and devised the threshold for when slack should recieve alerts.
- Deployed the Jupyter Notebook for visualizations and the comparison of ML models under different thresholds.
- Created the extra credit ML model that incorporated a gradient boosting decision tree method under features/Extra_Credit_Category. This would then be used to compare to the linear regression model my partner created.

##
### Pranshu Swaroop
#### BU Email: [spranshu@bu.edu](mailto:spranshu@bu.edu)
#### BU ID: U95062215

### Cross-Phase Contributions: Infrastructure, Data Quality, ML & Visualization

**Phase 1: NiFi Exploration & Early Pipeline Design**

* Initially designed and implemented an **independent NiFi ingestion and routing pipeline** to explore Kafka consumption, event-type branching, schema normalization, and metadata enrichment.
* Evaluated processor configurations for routing, validation, and enrichment across symptom and environmental streams.
* Although this NiFi design was not used in the final integrated pipeline, it helped **identify early architectural constraints** and informed later decisions on schema enforcement and streaming reliability.

**Phase 2: Database Integration & Storage Experiments**

* Took ownership of **database integration and persistence strategy** for Spark analytics outputs.
* Deployed and configured **PostgreSQL on OpenShift with persistent storage**, which became the system’s primary feature store.
* Experimented with **MongoDB as an alternative analytics backend**, including deployment YAMLs and PVC configuration.
* Diagnosed repeated MongoDB pod failures caused by **OpenShift resource quota limitations** and instability under streaming workloads.
* Based on these findings, pivoted the architecture to **standardize on PostgreSQL**, prioritizing reliability and queryability for downstream analytics.

**Phase 3: Data Quality, ML Models, Infrastructure & Visualization**

- **Database Deployment & Resource Management**

   * Managed PostgreSQL operations as the **central analytics, ML, and alerting datastore**.
   * Tuned CPU and memory limits across Spark, PostgreSQL, Grafana, and auxiliary services to resolve **quota-related pod crashes**.
   * Ensured stable operation of long-running Spark Structured Streaming jobs.

- **Category D: Comprehensive Testing & Data Quality Monitoring**

   * Designed and implemented the **complete Data Quality Monitoring framework (Category D)** using Spark Structured Streaming.
   * Built reusable **validation utilities** to detect:
     * Null and missing fields
     * Invalid categorical values
     * Out-of-range numerical measurements
   * Implemented a **micro-batch DQ pipeline** using `foreachBatch`, computing quality metrics every 30 seconds.
   * Persisted aggregated DQ metrics into PostgreSQL for historical tracking and visualization.
   * Authored **unit and integration tests** using `pytest` and local Spark sessions, validating:
     * Validation logic correctness
     * Failure counting accuracy
     * Edge-case handling and schema robustness
   * Debugged and resolved Spark testing issues including Java compatibility, driver bind failures, schema inference errors, and pytest discovery problems, resulting in all DQ tests passing.

- **Extra Credit: Machine Learning Models & Comparison**

  * Implemented an **additional ML model (Extra Credit)** to complement the baseline outbreak prediction pipeline.
  * Built a **lightweight regression-based model** (rolling average / linear regression style) using aggregated temporal features from PostgreSQL.
  * Compared multiple modeling approaches using **RMSE and MAE**, enabling quantitative evaluation of prediction accuracy across runs.
  * Persisted model outputs and evaluation metrics to PostgreSQL for reproducibility and visualization.
  * Supported **model comparison workflows** using Jupyter and Grafana, allowing side-by-side inspection of prediction quality over time.

- **Extra Credit: Grafana Deployment & Visualization** 

  * Deployed **Grafana on OpenShift**, configured services and routes, and connected it securely to PostgreSQL.
  * Designed a **lightweight Grafana dashboard** visualizing:
  
    * Data quality metrics over time
    * Outbreak and severity trends
    * Environmental and temporal analytics
    * ML prediction outputs and error metrics
  * Enabled near-real-time observability into **pipeline health, data correctness, and model performance**.

- **Documentation**

  * Wrote and maintained the main README.md ,testing/README.md,integration/README.md,architecture/README.md.
  * Created the System Architecture Diagram (mentioned in architecture.md).
  * Edited and published the presentation video on  youtube

#### Summary of Contribution

* Contributed across **all phases**: ingestion exploration, storage design, analytics, ML, and visualization
* Led **Category D (Testing + Data Quality)** end-to-end
* Delivered **Extra Credit ML modeling and comparison**
* Ensured system reliability under real OpenShift constraints
* Added observability through **Grafana dashboards**


##
### Samritha Aadhi Ravikumar
#### BU Email: samritha@bu.edu
#### BU ID: U51656773
#### Database Infrastructure, Modeling & Alerting
- **Phase 1**
  - Built the Enriched Symptom Clinical Events and Environmental Events streams from the raw Kafka topics. 
  - Made sure every event type was mapped into the correct enriched schema, spot-checking records and validating that the transformed data looked consistent. 
- **Phase 2**
  - Worked on adding a MongoDB storage layer, writing the Kubernetes deployment YAML and PVC configuration. The pod repeatedly crashed due to OpenShift resource quota limits (outside our control), so I cleaned up the deployment after confirming the issue.
  - Kept an eye on the Spark Symptom Analytics deployment, checking logs and restarting the pod when needed so that analytics stayed in a healthy Running state.
- **Phase 3**
  - Connected the Spark Symptom Analytics job to PostgreSQL so that aggregated metrics are continuously written into a relational database for downstream features.
  - Built and published the Docker image `samritha03/features-team07:latest` for the Phase 3 feature services and deployed the `feature` pod using `features/features.py` and `k8s/features-deployment.yaml` that runs Category A and B jobs end-to-end.
  - Implemented both (Category A) *Basic and Advanced Real-Time Alerting* services that read from PostgreSQL and send human-readable alerts
  - Created a dedicated “DS551 Fall ’25 Team 7” Slack channel to stream alerts via Webhook in `#team-07-alerts` reliably.
  - Designed and implemented the (Category B) *Anomaly Detection pipeline*: a Python job that reads `symptom_by_region`, computes Z-score–based `anomalies`, and persists results into a dedicated anomalies table with timestamps and metadata for later consumption.
  - Built the (Category B) *Outbreak Prediction Model* job using scikit-learn: engineered lagged features from `temporal_patterns`, trained and evaluated a regression model, and stored model outputs in an o`utbreak_predictions` table to support forecasting use cases.
  - Deployed the (Category C) *Visualization notebook* inside the existing `Jupyter` pod (so graphs, plots and interactive plots can be run directly against Postgres outputs).
- **Documentation** 
  - Wrote and maintained the `main README.md` with setup steps, project overview, and run instructions.
  - Authored structured documentation across feature modules: `features/README.md`, `features/category_a/README.md`, `features/category_b/README.md`, `features/category_c/README.md`. 
  - Created the `.env` listing all required environment variables for local and cluster runs.  
  - Configured the project-wide `.gitignore` to keep secrets, local configs, and build artifacts out of version control.
  - Completed the final presentation slides `DS 551 Final Presentation.pptx` (end-to-end system + features + results)


##
### Shravani Maskar
#### BU Email: shraav@bu.edu
#### BU ID: U97663450

### Phase 2: Spark Analytics Pipeline

**Analytics Development**
- Designed and implemented 3 streaming analytics:
  1. Symptom Count by Region - Regional outbreak detection
  2. Severity Distribution by Hour - Staffing optimization patterns
  3. Temporal Patterns - Day/hour trend analysis
- Configured Spark Structured Streaming (30-second batches, complete output mode)
- Set up Kafka consumer integration
- Implemented PostgreSQL JDBC sink

**Docker Containerization**
- Created Dockerfile with Apache Spark base image
- Integrated PostgreSQL JDBC driver
- Configured Ivy cache permissions
- Built cross-platform image (Mac ARM → Linux AMD64)
- Published to Docker Hub: `shraav13/spark-symptom-team07:latest`

**OpenShift Deployment**
- Created Kubernetes manifests (ConfigMap, Secret, Deployment)
- Deployed to namespace `ds551-2025fall-fd672e`
- Configured Docker Hub authentication (avoided rate limits)
- Optimized resources: 1.5Gi-3Gi memory, 500m-1 CPU

**Problem Resolution**
Debugged and fixed 6 critical production issues:
1. Ivy cache permission errors → Added directory creation in Dockerfile
2. Architecture mismatch (ARM/AMD64) → Rebuilt with platform flag
3. Database connection refused → Configured PostgreSQL network rules
4. Out of memory (OOMKilled) → Increased from 2Gi to 3Gi
5. ModuleNotFoundError → Integrated features directory
6. Docker Hub rate limit → Added registry secret

**Collaboration**
- Integrated teammate's data quality monitoring framework (Part D)
- Resolved merge conflicts during integration
- Coordinated multiple redeployments for testing
- Verified all 4 streams running successfully

**Documentation**
- Created comprehensive `spark/README.md`
- Wrote `k8s/README.md` with deployment instructions
- Documented troubleshooting guide
- Recorded GenAI usage and learnings

##

