# Modeling & Simulation - Example Workflows

This document provides realistic, end-to-end workflows for the M&S persona. Each workflow starts with synthetic data generation (so you can try immediately) and progresses through a complete analysis.

**How to use**: Select the M&S persona in Settings, then try these prompts sequentially in a new notebook.

---

## Workflow 1: Single Ascending Dose (SAD) Study - First-in-Human PK

**Scenario**: You're analyzing a Phase 1 SAD study for a novel oncology drug. Three dose levels (50, 150, 500 mg) were tested in healthy volunteers. You need to characterize PK, assess dose-proportionality, and recommend Phase 2 doses.

### Prompt 1: Generate Synthetic SAD Data
```
Create a synthetic PK dataset for a Single Ascending Dose study:
- 3 dose levels: 50, 150, 500 mg (IV bolus)
- 8 subjects per dose level (24 total)
- Sampling times: 0.25, 0.5, 1, 2, 4, 8, 12, 24 hours post-dose
- True PK parameters: CL = 5 L/h (CV 30%), Vd = 50 L (CV 25%)
- Add 15% residual variability
- Include subject demographics (ID, dose, age, weight, sex)
- Save as 'sad_pk_data.csv'
```

**Expected Output**: DataFrame with ~192 rows (24 subjects × 8 timepoints), concentration-time data

---

### Prompt 2: Non-Compartmental Analysis (NCA)
```
Perform NCA on the SAD data for each dose level:
- Calculate AUC_0-24, Cmax, Tmax, t1/2, CL, Vd for each subject
- Create a summary table with median and range by dose level
- Test for dose-proportionality (plot AUC and Cmax vs dose on log-log scale)
```

**Expected Output**:
- Table of NCA parameters by dose level
- Log-log plots showing dose-proportionality
- Statistical assessment (slope = 1 for proportional)

---

### Prompt 3: Visualize Individual PK Profiles
```
Create a spaghetti plot showing individual concentration-time profiles:
- Semi-log plot (concentration on log scale)
- Color-code by dose level (50 mg = blue, 150 mg = orange, 500 mg = red)
- Include median profile per dose level as thick line
- Add reference lines for potential therapeutic window (Cmin = 100 ng/mL, Cmax = 5000 ng/mL)
```

**Expected Output**: Publication-quality spaghetti plot showing dose-dependent PK

---

### Prompt 4: Fit One-Compartment Model
```
Fit a one-compartment IV bolus model to the pooled SAD data:
- Use lmfit for parameter estimation with bounds (CL > 0, Vd > 0)
- Estimate population CL and Vd with 95% confidence intervals
- Report %CV for each parameter
- Create goodness-of-fit plots (observed vs predicted, residuals vs time)
- Calculate AIC and R²
```

**Expected Output**:
- Parameter estimates: CL = 5.1 L/h (95% CI: 4.7-5.5), Vd = 48.3 L (95% CI: 45.2-51.4)
- GOF diagnostics showing good fit

---

### Prompt 5: Predict Phase 2 Dose Range
```
Using the fitted PK model, simulate exposures for Phase 2 candidate doses:
- Doses to test: 200, 300, 400, 600 mg
- Calculate predicted median AUC_0-24 and Cmax for each dose
- Include inter-individual variability (30% CV on CL, 25% CV on Vd)
- Identify which doses achieve target exposure (AUC_0-24 between 2000-8000 ng·h/mL)
- Create a table with dose recommendations
```

**Expected Output**:
- Table showing predicted exposures for Phase 2 doses
- Recommended dose range based on target exposure

---

## Workflow 2: Dose-Response Study - Efficacy Endpoint

**Scenario**: You have preclinical dose-response data for tumor growth inhibition. You need to characterize the dose-response relationship, determine ED50/ED90, and simulate clinical trial outcomes.

### Prompt 1: Generate Dose-Response Data
```
Create synthetic dose-response data for a tumor growth inhibition study:
- 7 dose levels: 0, 1, 3, 10, 30, 100, 300 mg/kg
- 12 animals per dose (84 total)
- Response: % tumor growth inhibition (TGI)
- True Emax model: E0 = 5%, Emax = 95%, ED50 = 25 mg/kg, Hill coefficient = 1.5
- Add 12% residual variability
- Include some non-responders at low doses and ceiling effects at high doses
```

**Expected Output**: DataFrame with dose and %TGI for 84 animals

---

### Prompt 2: Fit Sigmoid Emax Model
```
Fit a sigmoid Emax (Hill) model to the dose-response data:
- Parameters: E0 (baseline), Emax (maximum effect), ED50, gamma (Hill coefficient)
- Use lmfit with constraints (E0 >= 0, Emax <= 100, ED50 > 0, 0.5 <= gamma <= 5)
- Report parameter estimates with 95% confidence intervals
- Calculate and display AIC, BIC, R²
```

**Expected Output**:
- E0 = 5.2% (95% CI: 3.1-7.3)
- Emax = 94.1% (95% CI: 91.5-96.7)
- ED50 = 26.3 mg/kg (95% CI: 22.8-29.8)
- γ = 1.48 (95% CI: 1.21-1.75)

---

### Prompt 3: Determine Key Efficacy Doses
```
Using the fitted Emax model, calculate:
- ED50 (dose achieving 50% of maximum effect)
- ED80 (dose achieving 80% of maximum effect)
- ED90 (dose achieving 90% of maximum effect)
- Create a dose-response curve with these doses marked
- Add 95% confidence bands for the model predictions
```

**Expected Output**:
- Key doses identified (ED50 = 26 mg/kg, ED80 = 89 mg/kg, ED90 = 163 mg/kg)
- Dose-response curve with CI bands

---

### Prompt 4: Simulate Clinical Trial Outcomes
```
Simulate a Phase 2 clinical trial using the Emax model:
- Test 4 dose levels: 30, 60, 100, 150 mg/kg
- 50 virtual patients per arm (200 total)
- Primary endpoint: % achieving ≥70% TGI
- Include inter-patient variability (ED50 varies with CV = 40%)
- Calculate success rate for each dose
- Determine minimum efficacious dose (MED)
```

**Expected Output**:
- Table showing % responders per dose
- Bar chart comparing arms
- Recommendation: MED = 60 mg/kg (85% achieve ≥70% TGI)

---

### Prompt 5: Dose Optimization Dashboard
```
Create an interactive visualization comparing dose levels:
- X-axis: Dose (log scale)
- Y-axis dual: (1) Mean %TGI, (2) % achieving ≥70% TGI
- Include error bars (95% CI)
- Highlight recommended dose range (60-100 mg/kg)
- Add therapeutic index consideration if you have safety data
```

**Expected Output**: Dashboard showing dose-efficacy relationship with optimal range highlighted

---

## Workflow 3: Drug-Drug Interaction (DDI) Study

**Scenario**: Your drug is metabolized by CYP3A4. You need to assess DDI potential when co-administered with a strong CYP3A4 inhibitor (e.g., ketoconazole). Predict the magnitude of interaction and provide dosing recommendations.

### Prompt 1: Generate PK Data Without and With Inhibitor
```
Create synthetic PK data for a DDI study (crossover design):
- Period 1: Drug alone (200 mg single dose, IV bolus)
- Period 2: Drug + CYP3A4 inhibitor (same drug dose)
- 16 subjects (crossover, each subject in both periods)
- Sampling: 0.25, 0.5, 1, 2, 4, 8, 12, 24, 48 hours
- True parameters:
  - Alone: CL = 20 L/h (CV 35%), Vd = 80 L (CV 30%)
  - With inhibitor: CL reduced to 8 L/h (60% inhibition), Vd unchanged
- Add 18% residual variability
```

**Expected Output**: DataFrame with concentrations for both periods (16 subjects × 9 timepoints × 2 periods)

---

### Prompt 2: Compare Exposures (NCA)
```
Perform NCA separately for each period:
- Calculate AUC_0-inf, Cmax, t1/2, CL for each subject in each period
- Calculate geometric mean ratios (GMR) with 90% confidence intervals:
  - GMR for AUC (With inhibitor / Alone)
  - GMR for Cmax (With inhibitor / Alone)
- Test if 90% CI falls outside 0.80-1.25 (FDA DDI threshold)
- Create paired plots showing individual changes
```

**Expected Output**:
- AUC GMR = 2.45 (90% CI: 2.18-2.76) → Significant interaction
- Cmax GMR = 1.12 (90% CI: 0.98-1.28) → Minimal effect

---

### Prompt 3: Visualize PK Profile Changes
```
Create a figure comparing median PK profiles:
- Semi-log plot of concentration vs time
- Blue line: Drug alone
- Red line: Drug + inhibitor
- Include individual data points with transparency
- Shade area between curves to highlight exposure increase
- Add legend showing fold-change in AUC
```

**Expected Output**: Clear visualization of DDI magnitude over time

---

### Prompt 4: Model the DDI Effect
```
Fit one-compartment models to both periods separately:
- Period 1 (alone): Estimate CL and Vd
- Period 2 (with inhibitor): Estimate CL_inhibited and Vd
- Calculate:
  - Fraction of CL remaining: fm = CL_inhibited / CL_alone
  - % CL inhibition: (1 - fm) × 100%
- Report with 95% confidence intervals
```

**Expected Output**:
- CL_alone = 19.8 L/h (95% CI: 18.2-21.4)
- CL_inhibited = 7.9 L/h (95% CI: 7.1-8.7)
- Inhibition = 60% (95% CI: 55-65%)

---

### Prompt 5: Clinical Dosing Recommendations
```
Based on the DDI magnitude, generate dosing recommendations:
- Calculate dose adjustment factor to maintain similar AUC
- Simulate exposures with:
  1. Standard dose (200 mg) alone
  2. Standard dose (200 mg) + inhibitor
  3. Reduced dose (80 mg) + inhibitor
- Compare predicted AUC for all three scenarios
- Create a table with clinical recommendations
```

**Expected Output**:
```
Scenario                    | AUC_0-inf (ng·h/mL) | Recommendation
----------------------------|---------------------|------------------
200 mg alone               | 10,000              | Standard dose
200 mg + inhibitor         | 24,500              | ⚠️ 2.5× increase
80 mg + inhibitor          | 9,800               | ✓ Adjusted dose
```

**Clinical Recommendation**: When co-administered with strong CYP3A4 inhibitors, reduce dose to 80 mg (60% reduction) to maintain target exposure.

---

### Prompt 6: Regulatory Summary Table
```
Create a table summarizing the DDI study for regulatory submission:
- Study design (crossover, n=16)
- Geometric mean ratios with 90% CI for AUC and Cmax
- FDA significance assessment (>1.25 or <0.80)
- Mechanism (CYP3A4 inhibition, 60% reduction in CL)
- Dose adjustment recommendation
- Labeling language (avoid co-administration OR reduce dose by 60%)
```

**Expected Output**: Regulatory-ready summary table following FDA DDI guidance format

---

## Quick Start Examples (Single Prompt)

If you want to try M&S capabilities quickly without a full workflow:

### Quick Example 1: NCA Analysis
```
Create synthetic PK data for 10 patients receiving 100 mg IV bolus (sampling at 0.5, 1, 2, 4, 8, 12, 24h).
Perform NCA to calculate AUC, Cmax, Tmax, t1/2, CL, and Vd. Display results table and semi-log PK profile.
```

### Quick Example 2: Compartmental Modeling
```
Generate concentration-time data for 15 patients (doses: 50, 100, 200 mg). Fit a one-compartment IV bolus model
using lmfit. Report CL and Vd with 95% CI and %CV. Show observed vs predicted plot and residuals.
```

### Quick Example 3: Dose-Response
```
Create dose-response data for 7 doses (0.1 to 1000 mg) with Emax response. Fit sigmoid Emax model, calculate
ED50 and ED90, and plot dose-response curve with 95% CI bands.
```

### Quick Example 4: Population Simulation
```
Simulate a virtual population of 100 patients receiving 300 mg Q12H dosing. Use log-normal distributions for
CL (mean=10 L/h, CV=40%) and Vd (mean=60 L, CV=30%). Calculate probability of achieving Cmin >5 ng/mL and Cmax <100 ng/mL.
Create spaghetti plot with therapeutic window.
```

### Quick Example 5: QSP Model
```
Create a simple receptor-ligand binding QSP model using Tellurium: 100 nM receptor, 50 nM ligand, kon=0.01, koff=0.1.
Simulate for 200 minutes and plot free receptor, free ligand, and bound complex over time. Calculate steady-state occupancy.
```

---

## Tips for Best Results

1. **Start with synthetic data**: Use "Create synthetic..." prompts to generate data you can immediately analyze

2. **Be specific about units**: Always specify (mg, L, h, ng/mL, etc.)

3. **Request visualizations**: Ask for "semi-log plot", "spaghetti plot", "dose-response curve"

4. **Ask for uncertainty**: Request "95% CI", "%CV", "confidence intervals"

5. **Sequential analysis**: Each prompt builds on previous results - run in order

6. **Regulatory context**: Mention "FDA guidelines", "regulatory submission" for appropriate methodology

7. **Iterate**: If results need refinement, ask "adjust the model to include...", "refit with constraints..."

8. **Save intermediate results**: Request "save as 'filename.csv'" to preserve data between cells

---

## Workflow Customization

You can customize these workflows by:

- **Changing therapeutic area**: Replace "tumor growth inhibition" with "blood pressure reduction", "viral load", etc.
- **Adding covariates**: "Include age, weight, renal function as covariates"
- **Different routes**: "oral absorption with lag time", "subcutaneous with depot"
- **Different endpoints**: "time-to-event", "biomarker response", "safety endpoints"
- **Special populations**: "pediatric", "renally impaired", "elderly"

---

**Document Version**: 1.0
**Last Updated**: 2025-12-06
**Companion to**: [`examples/persona/persona-ms-examples.md`](../persona/persona-ms-examples.md)
**Digital Article Project**: Modeling & Simulation Persona
