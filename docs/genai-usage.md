# GenAI Usage Documentation

Document your use of AI tools (ChatGPT, Claude, GitHub Copilot, etc.) throughout this project.

---

## AI Tools Used

[List the AI tools you used]

Examples:
- ChatGPT (version)
- Claude - used in phase 2 
- GitHub Copilot
- Other tools

---

## How We Used AI

### Phase 1: NiFi Pipeline

**Example prompts that worked well:**
```
What is NIFI and how does it read data from Kafka?
What are processors?
How can I route each event type to the respective titles?
Should I terminate failed and unmmatched relationships?
```

**What AI helped with:**
- The overall flow of NIFI and some symtax issues when matching the property type

**What AI got wrong:**
- A mistake AI made was creating a process group within our team07 process group. It wasn't a crucial mistake but we had to take everything out and put it outside.
- Another mistake it made was on how to export the flow to a json file. It kept leading us to a different menu on the top right corner when all we could have done was right click the white space in the background.

### Phase 2: Spark & Database

**Example prompts that worked well:**
**Prompt 1: Understanding Concepts**
```
Explain Spark Structured Streaming - what are micro-batches, checkpointing, 
and output modes? Which output mode should I use for aggregations?
```

**Prompt 2: Debugging Production Issues**
```
My Spark pod keeps crashing with "Exception in thread main java.io.FileNotFoundException: 
/opt/spark/.ivy2/cache/resolved-org.apache.spark..." 
What does this mean and how do I fix it?
```

**Prompt 3: Resource Optimization**
```
My pod shows OOMKilled with exit code 137. Logs show it processes first batch 
successfully then crashes. Current memory limit is 2Gi. What's wrong?
```

**What AI helped with:**

**Debugging Strategies:**
- Suggested checking Ivy cache permissions for FileNotFoundException
- Recommended examining pod events and logs for CrashLoopBackOff
- Provided commands to investigate OOMKilled errors (`oc describe pod`)
- Explained PostgreSQL network configuration and pg_hba.conf syntax

**Best Practices:**
- Recommended JDBC driver installation approach
- Suggested checkpoint location configuration
- Explained Docker Hub rate limits and authentication solution
- Provided resource allocation starting points (2Gi memory)

**What AI got wrong:**

**Issue 1: Initial Resource Recommendation**
- **AI suggested:** Start with 2Gi memory as sufficient
- **Reality:** 2Gi caused OOMKilled crashes after first batch
- **How I identified and fixed :** Pod kept restarting, logs showed successful start then crash, `oc describe` showed OOMKilled, so i Tested with 3Gi through trial and error, monitoring actual memory usage (~2Gi average)

**Issue 2: Dockerfile Context**
- **AI suggested:** `COPY ../features /app/features` in Dockerfile
- **Reality:** Docker can't access parent directories with `../`
- **How I identified and fixed :** Build failed with "not found" error so i Copied features directory to spark/ folder first, then `COPY features /app/features`

**Issue 3: Database Already Exists**
- **AI suggested:** Create "epidemic" database as first step
- **Reality:** Database already existed (teammate created it)
- **How I identified and fixed :** Got "database already exists" error, so i Skipped database creation, only configured pg_hba.conf


### Phase 3: Advanced Features

**Example prompts that worked well:**
**Prompt 1 Understanding Z-scores and how to structure severity levels**
```
How should I structure alert severity levels (low / medium / high) based on statistical thresholds like Z-scores?
```
**Prompt 2 System Design and Alerting**
```
What fields should a human-readable alert message include to be useful in a Slack channel?
```
**Prompt 3 Outbreak Prediction/ML**
```
How can I encode hour_of_day so taht the model captures cyclical behavior like midnight being close to 23:00?
```
**Prompt 4 Visualization**
```
Which Plotly chart type works best for exploring event counts across day-of-week and hour-of-day interactively?
```

**What AI helped with:**
- AI assisted in explaining the Z-score-based anomaly detection.
- AI suggested feature engineering ideas such as the cyclical time encoding used in our ML model.
- AI helped explaining evaluation metrics for outbreak prediciton. We understood why to use RMSE instead of MSE.

**What AI got wrong:**
- AI made a mistake of sometimes overgeneralizing alert threshold wihtout any context. We fixed this by tuning thresholds empirically using real data.
- Another thing AI got wrong was that it occasionally suggested visualization styles that obscured patterns. We fixed this by comparing the outputs visually and iterating on plots until patterns were actually interpretable. 

## Reflections

### What We Learned About Using AI

We learned that AI is the pinacle of all technology. Any new technology we didn't know such as Nifi or Plotly was explained clearly with prompt engineering. 

**When AI was most helpful:**
- AI was the most helpful with Nifi as it was completely new to us and was very helpful when it came to debugging our YAML files.

- **Explaining unfamiliar concepts** - Spark streaming, Kubernetes objects, JDBC connectivity
- **Interpreting error messages** - Translated cryptic JVM/Docker errors into actionable fixes



**When AI was least helpful:**

-  **Testing requirements** - Couldn't tell me if something would work; had to test myself
-  **Assumed Resource Definitions** - 2Gi caused OOMKilled crashes after first batch

**How we maintained control:**

- **Tested everything** - Ran commands in development/staging before production
- **Read actual logs** - Analyzed log lines myself to find root causes
- **Verified assumptions** - Checked actual file contents vs what AI assumed

### Skills We Developed

- **Apache Spark** - Structured Streaming API, DataFrame transformations, checkpoint management
- **Docker** - Multi-platform builds, dependency management, permission configuration
- **Kubernetes/OpenShift** - Pod lifecycle, resource allocation, ConfigMaps/Secrets, debugging
- **Production Debugging** - Log analysis, systematic troubleshooting, root cause identification
- **Resource Monitoring** - Understanding memory/CPU usage patterns, quota management

[How did AI help or hinder skill development?]

**Shravani**
- Accelerated learning by explaining concepts I could then apply
- Enabled faster iteration by reducing research time
**Joshua**
- It helped my learning process speed up by a lot as without AI, I would've had trouble with all of the phases.
- My research was done pretty easily.

---

## Examples of AI Interaction

### Example 1: Understanding of NIfi

**My Prompt:**
```
I’m building a NiFi pipeline that consumes JSON messages from Kafka.
Each message has an event_type field, and I need to route each event
type to a different Kafka topic. What processors should I use and how
should I structure the flow?
```

**AI Response Summary:**
- AI suggested using ComsumeKafkaRecord_2_0 to read messages from Kafka
- It recommended RouteOnAttribute to route FlowFiles based on event_type

**What I Did With It:**
- We implemented a process flow that would include all of the processors including ConsumeKafka all the way to PublishKafkaRecord.

**Outcome:**
✅ **Partially successful** GENAI forgot to include data enrichment and there had to be hands-on debugging to ensure the overall flow design was correct. We corrected the structure by placing processsors at the correct level and verified behavior using NiFi provenance. 


### Example 2: [Title]

**My prompt:**
```
I have aggregated temporal data with columns day_of_week, hour_of_day,
unique_patients, and event_count. I want to predict event_count.
What type of ML model makes sense here, and how should I evaluate it?
```

**AI response summary:**
- AI sugested using a regression model rather than classification.
- The first recommended tree-based model was a random forest to capture non-linear relationships and to have something that exceed basic ML
- It also suggested metrics such as the RMSE and MAE for evaluation metrics for count prediction.

**What we did with it:**
- We implemented a RandomForestRegressor with 100 trees and performed an 80/20 train-test split.
- We evaluated predictions using both RMSE and MAE to then store predictions and evaluation metrics back into our postgres table.

**Outcome:**
✅ **Successful** The model produced reasonable predictions and meaningful error metrics. We learned that even simple feature sets such as temporal patterns could benefit from non-linear models and that evaluating with multiple metrics would provide better insight into model performance.
