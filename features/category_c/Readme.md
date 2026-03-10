## Category C – Visualizations

Category C provides a set of curated visualizations that sit **on top of the Phase 2 and Phase 3 database tables**.  

Implemented
- `epidemic_visualizations.ipynb` (Main visualization notebook) 

The notebook is deployed and run **inside the shared Jupyter pod** in our OpenShift project.

**Goal:** To give a quick, visual way to inspect trends, anomalies, and model quality.

##
### Visualizations Included

The notebook implements 7 visualizations, at least one of which is interactive (Plotly).
- **Visualization 1 – Rolling time series with anomalies overlay**
  - Converts `last_updated` to `datetime`.
  - Aggregates total events into 5-minute buckets.
  - Computes a *rolling 30-minute mean* of total events.
  - Overlays anomaly times (from `anomalies`) as red “X” markers above the line.
  - *Purpose:* Show how detected anomalies line up with overall symptom activity over time.

- **Visualization 2 – Top regions bar chart**
  - Aggregates total event counts per `region` from `symptom_df`.
  - Plots the top 10 regions as a bar chart.
  - *Purpose:* Identify which regions contribute the highest symptom load.

- **Visualization 3 – Severity vs hour heatmap**
  - Builds a pivot table: rows = `severity`, columns = `hour_of_day`, values = `event_count`.
  - Renders a heatmap (`plt.imshow`) with a colorbar.
  - *Purpose:* Show when (by hour) different severity levels are most active.
  - ![Category C](https://github.com/BU-CDS-DS551-2025-Fall/epidemic-engine-team-7/blob/main/docs/Output%20Screenshots/Visualisation%203%20.png)

- **Visualization 4 – Bubble chart by day-of-week & hour-of-day** (Plotly, interactive)
  - Uses Plotly Express `px.scatter` on `temp_df`.
  - Axes: `hour_of_day` (x) vs `day_of_week` (y).
  - Bubble size and color represent `event_count`.
  - Hover shows `unique_patients` and `last_updated`.
  - *Purpose:* Interactive view of temporal patterns – which days/hours are busiest.
  - ![Category C](https://github.com/BU-CDS-DS551-2025-Fall/epidemic-engine-team-7/blob/main/docs/Output%20Screenshots/Visualisation%204.png)

- **Visualization 5 – Interactive Plotly line chart by region**
  - Sorts `symptom_df` by `last_updated`.
  - Uses px.line with: x = `last_updated`, y = `event_count`, color = `region`, hover = `symptoms`
  - *Purpose:* Interactive time series of symptom counts, split by region, with hoverable symptom details.

- **Visualization 6 – True vs predicted events** (model quality)
  - Uses `pred_df` from `outbreak_predictions`.
  - Scatter plot of `event_count_true` vs `event_count_pred`.
  - Adds a red dashed 45° line (“perfect prediction”).
  - *Purpose:* Visual check of the Category B outbreak prediction model performance.
  - ![Category C](https://github.com/BU-CDS-DS551-2025-Fall/epidemic-engine-team-7/blob/main/docs/Output%20Screenshots/Visualisation%206.png)

- **Visualization 7 – Interactive error-by-hour plot**
  - (In notebook) uses Plotly to visualize model error across `hour_of_day` or other time dimensions.
  - Lets the user inspect where the model over- or under-predicts.
  - *Purpose:* Diagnose when the model struggles (e.g., specific hours or days).
  - ![Category C](https://github.com/BU-CDS-DS551-2025-Fall/epidemic-engine-team-7/blob/main/docs/Output%20Screenshots/Visualisation%207.png)

##
### How It Runs in OpenShift

**Pod:** jupyter

**Notebook location inside pod:** `/tmp/notebooks/epidemic_visualizations.ipynb`

The notebook file is copied into the pod with a command like:
```bash
oc cp features/category_c/epidemic_visualizations.ipynb \
    jupyter-779f7bc4cd-zv88w:/tmp/notebooks/epidemic_visualizations.ipynb
```

Then, using the Jupyter route:

- Run:
  ```bash
  oc get routes
  ```
  and open the URL for the jupyter route in your browser.
- Log in using the token from:
  ```bash
  oc logs deployment/jupyter | grep -i token
  ```
- In JupyterLab, navigate to `/tmp/notebooks` and open `epidemic_visualizations.ipynb`.
- Run Kernel → Restart Kernel and Run All Cells.

Because the notebook uses `DB_HOST=postgres` and the same credentials as the other components, it directly reads live data from the in-cluster Postgres.
