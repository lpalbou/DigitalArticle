This workflow focuses on **Survival Analysis (Time-to-Event)**, a cornerstone of "serious" clinical data science (common in Oncology and Cardiology).

This scenario involves **censored data** (patients leaving the study before the event occurs), which requires more sophisticated visualization than simple bar charts. We will use **interactive plotting** libraries (like `Plotly`) to make the data come alive for students.

### **The Scenario: Oncology Trial (ImmunoX vs. Chemo)**

* **Objective:** Determine if "ImmunoX" extends "Progression-Free Survival" (PFS) compared to Standard Chemotherapy.
* **Outcome:** Time (in months) until disease progression or death.
* **Key Complexity:** Censoring (some patients are still healthy at the end of the study).

---

### **Prompt 1: Synthetic Survival Data Generation**

*Goal: Generate complex "Time-to-Event" data with a programmed Hazard Ratio.*

> **Prompt:**
> "I need a Python script to generate a synthetic dataset for an Oncology clinical trial (N=400). We are comparing 'ImmunoX' (Treatment) vs. 'Chemotherapy' (Control).
> Please generate a DataFrame with these columns:
> 1. `PatientID`
> 2. `Group`: 'ImmunoX' or 'Chemo'.
> 3. `Age`: Normal dist (Mean=60, SD=10).
> 4. `ECOG_Score`: Ordinal scale 0-2 (integers).
> 5. `Time_to_Event`: Generate this using an exponential distribution.
> * **Control Group:** Risk rate  (Median survival  7 months).
> * **Treatment Group:** Risk rate  (Median survival  14 months). This implies a Hazard Ratio of 0.5 (strong benefit).
> 
> 
> 6. `Event_Observed`: Binary (1 = Progression/Death, 0 = Censored). Randomly censor about 20% of patients in both groups (set their event status to 0).
> 
> 
> Save this as a pandas DataFrame."

---

### **Prompt 2: Visualizing "Censoring" (Swimmer Plot)**

*Goal: Before statistical testing, students must understand that not every patient "failed." A Swimmer Plot visually explains censoring.*

> **Prompt:**
> "To explain the concept of 'censoring' to the class, I want to visualize individual patient timelines.
> Please use **Plotly Express** to create an **interactive Swimmer Plot** (Gantt-style bar chart) for a random sample of 20 patients from the dataset.
> * **X-axis:** Time in months.
> * **Y-axis:** Patient IDs.
> * **Color:** By `Group`.
> * **Markers:** Add a specific marker shape at the end of the bar to distinguish between an 'Event' (e.g., an X) and 'Censored' (e.g., a circle).
> 
> 
> The plot should allow zooming and hovering to see individual patient details."

---

### **Prompt 3: The Kaplan-Meier Curve (Interactive)**

*Goal: The most famous figure in clinical trials. We want an interactive version to see survival probabilities at specific times.*

> **Prompt:**
> "Now, perform the primary visualization. We need to plot the **Kaplan-Meier Survival Curves** for both groups.
> Please write Python code to:
> 1. Fit the Kaplan-Meier fitter (using the `lifelines` library) for both the 'ImmunoX' and 'Chemo' groups.
> 2. Extract the survival table (time vs. survival probability).
> 3. Use **Plotly** to plot the two curves on the same interactive line chart.
> 4. Add a dashed horizontal line at Y=0.5 to visually identify the **Median Survival Time** for each group.
> 5. Ensure the tooltip shows the exact survival probability when hovering over the curve."
> 
> 

---

### **Prompt 4: The Hazard Ratio (Forest Plot)**

*Goal: Instead of a text table for the Cox Regression results, we visualize the risk reduction.*

> **Prompt:**
> "We need to quantify the risk reduction using a **Cox Proportional Hazards model**.
> Please write code to:
> 1. Fit a CoxPH model using `lifelines` (`Duration` = Time_to_Event, `Event` = Event_Observed, `Covariates` = Group + Age + ECOG_Score).
> 2. Instead of printing the summary table, generate a **Forest Plot** using `matplotlib` or `lifelines` built-in plotting.
> 3. The plot should show the **Hazard Ratio (point estimate)** and the **95% Confidence Intervals** for each variable.
> 4. Draw a vertical line at HR=1 (the line of no effect). Variables to the left of this line indicate a beneficial effect."
> 
> 

---

### **Prompt 5: Checking Assumptions (Visualizing Residuals)**

*Goal: A "serious" analysis checks if the model is valid. The "Proportional Hazards" assumption means the curves shouldn't cross.*

> **Prompt:**
> "A critical step in survival analysis is checking the 'Proportional Hazards Assumption' (i.e., does the treatment effect remain constant over time?).
> Please write code to:
> 1. Calculate the **Schoenfeld Residuals** for the model fitted in the previous step.
> 2. Create a scatter plot of these residuals against Time.
> 3. Add a smoothed trend line (LOESS).
> 4. **Interpretation:** Explain that a flat trend line means the assumption holds. If the line slopes significantly, the assumption is violated."
> 
> 

---

### **Prompt 6: The "At-Risk" Table Visualization**

*Goal: Advanced clinical figures always include a table aligned below the X-axis showing how many patients are left.*

> **Prompt:**
> "For the final publication-ready figure, we need to combine the survival curve with a 'Number at Risk' table, which is standard in medical journals like NEJM or The Lancet.
> Please use the `lifelines` library's `KMPlot` class or `matplotlib` to generate a static, high-quality figure that includes:
> 1. The Kaplan-Meier curves on top.
> 2. A **aligned table below the X-axis** showing the count of patients still 'at risk' (alive and not censored) at time points 0, 5, 10, 15, and 20 months.
> 3. Style it professionally (white background, clear fonts, distinct colors for treatment vs control)."
> 
> 

---

### **What this teaches the students:**

1. **Complexity:** Moving from simple means (T-tests) to Rates and Risks.
2. **Censoring:** Understanding that missing data isn't always "bad" data; it carries information.
3. **Visual Verification:** Using Swimmer plots and Residual plots to "debug" the biology, not just the code.

**Would you like me to generate the code for Prompt 2 (The Interactive Swimmer Plot) so you can see how the visualization looks?**