# Modeling & Simulation Persona - Code Examples

Practical PK/PD modeling examples for pharmaceutical scientists using Digital Article's M&S persona.

## Target Workflows

This persona supports:
- **NCA** (Non-Compartmental Analysis): AUC, Cmax, t1/2, clearance
- **Compartmental PK**: 1/2/3-comp models with parameter estimation
- **PK/PD**: Dose-response (Emax), indirect response, turnover models
- **QSP** (Quantitative Systems Pharmacology): SBML-based pathway models
- **Trial Simulation**: Virtual populations, dose optimization, PTA

## Key Libraries

- `scipy` - ODE solvers (solve_ivp), integration
- `lmfit` - Parameter estimation with bounds/CI (better than scipy.optimize.curve_fit)
- `tellurium` - QSP/SBML modeling with Antimony syntax
- `pandas`, `numpy`, `matplotlib` - Standard scientific stack

---

## 1. Non-Compartmental Analysis (NCA)

Calculate PK parameters (AUC, Cmax, t1/2, CL, Vd) without assuming a compartmental model.

```python
import numpy as np
import pandas as pd
from scipy.integrate import trapezoid
import matplotlib.pyplot as plt

# PK data: IV bolus
time = np.array([0, 0.5, 1, 2, 4, 8, 12, 24])  # hours
conc = np.array([100, 85, 72, 52, 28, 8, 2.3, 0.15])  # ng/mL
dose = 100  # mg

pk_data = pd.DataFrame({'Time (h)': time, 'Concentration (ng/mL)': conc})
display(pk_data, "Table 1: PK Data")

# Cmax, Tmax
cmax = np.max(conc)
tmax = time[np.argmax(conc)]
idx_max = np.argmax(conc)

# AUC: linear-trapezoidal (ascending), log-linear (descending)
auc_asc = trapezoid(conc[:idx_max+1], time[:idx_max+1]) if idx_max > 0 else 0
auc_desc = sum((conc[i] - conc[i+1]) / np.log(conc[i] / conc[i+1]) * (time[i+1] - time[i])
               for i in range(idx_max, len(conc)-1) if conc[i] > 0 and conc[i+1] > 0)
auc_0_t = auc_asc + auc_desc

# Terminal half-life (last 3 points)
slope = np.polyfit(time[-3:], np.log(conc[-3:]), 1)[0]
lambda_z = -slope
t_half = np.log(2) / lambda_z

# Derived parameters
cl = dose / auc_0_t  # Clearance
vd = cl / lambda_z   # Volume of distribution

# Results
nca_params = pd.DataFrame([{
    'Cmax (ng/mL)': cmax, 'Tmax (h)': tmax, 'AUC_0-t (ng·h/mL)': auc_0_t,
    't1/2 (h)': t_half, 'CL (L/h)': cl, 'Vd (L)': vd
}])
display(nca_params, "Table 2: NCA Parameters")

# Semi-log plot
fig, ax = plt.subplots(figsize=(8, 5))
ax.semilogy(time, conc, 'o-', markersize=8, linewidth=2, color='steelblue')
ax.set_xlabel('Time (h)', fontsize=12)
ax.set_ylabel('Concentration (ng/mL)', fontsize=12)
ax.set_title('PK Profile', fontsize=14, fontweight='bold')
ax.grid(True, alpha=0.3)
display(fig, "Figure 1: Concentration-Time Profile")
```

**Key Points**: Use mixed trapezoidal rule (linear ascending, log-linear descending) for accurate AUC. Terminal λz from last 3-4 points.

---

## 2. Compartmental PK Modeling

Fit structural models using lmfit for parameter estimation with bounds and confidence intervals.

```python
import numpy as np
import pandas as pd
from lmfit import Model
import matplotlib.pyplot as plt

# Data: one-compartment IV bolus
time_data = np.array([0.5, 1, 2, 4, 6, 8, 12, 24])  # hours
conc_data = np.array([92, 75, 50, 25, 12.5, 6.25, 1.56, 0.006])  # ng/mL
dose = 100  # mg

# Model: C(t) = (Dose/Vd) * exp(-k*t), where k = CL/Vd
def one_comp_iv_bolus(t, cl, vd):
    """One-compartment IV bolus: C(t) = C0 * exp(-k*t)"""
    return (dose / vd) * np.exp(-(cl/vd) * t)

# Fit with lmfit (better than scipy.optimize - provides CI, bounds, AIC/BIC)
model = Model(one_comp_iv_bolus)
params = model.make_params(cl=5.0, vd=10.0)
params['cl'].set(min=0.1, max=50)   # Physical constraint: CL > 0
params['vd'].set(min=1.0, max=100)  # Physical constraint: Vd > 0
result = model.fit(conc_data, params, t=time_data)

# Parameter estimates with uncertainty
cl_est, vd_est = result.params['cl'].value, result.params['vd'].value
cl_se, vd_se = result.params['cl'].stderr, result.params['vd'].stderr
k_est, t_half_est = cl_est/vd_est, np.log(2)/(cl_est/vd_est)

param_table = pd.DataFrame({
    'Parameter': ['CL (L/h)', 'Vd (L)', 'k (1/h)', 't1/2 (h)'],
    'Estimate': [cl_est, vd_est, k_est, t_half_est],
    '%CV': [100*cl_se/cl_est, 100*vd_se/vd_est, np.nan, np.nan]
})
display(param_table, "Table 3: Parameter Estimates")
print(f"Model fit: AIC={result.aic:.1f}, BIC={result.bic:.1f}, R²={result.rsquared:.3f}")

# Diagnostics
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

# Fit plot
time_pred = np.linspace(0, 24, 100)
ax1.semilogy(time_data, conc_data, 'o', markersize=10, label='Observed', color='steelblue')
ax1.semilogy(time_pred, one_comp_iv_bolus(time_pred, cl_est, vd_est),
             '-', linewidth=2, label='Model', color='coral')
ax1.set_xlabel('Time (h)'); ax1.set_ylabel('Concentration (ng/mL)')
ax1.set_title('One-Compartment Fit'); ax1.legend(); ax1.grid(alpha=0.3)

# Residuals
residuals = conc_data - one_comp_iv_bolus(time_data, cl_est, vd_est)
ax2.scatter(time_data, residuals, s=100, color='steelblue')
ax2.axhline(0, color='red', linestyle='--', linewidth=2)
ax2.set_xlabel('Time (h)'); ax2.set_ylabel('Residuals (ng/mL)')
ax2.set_title('Residual Plot'); ax2.grid(alpha=0.3)

plt.tight_layout()
display(fig, "Figure 2: Model Diagnostics")
```

**Why lmfit over scipy.optimize**:
- Parameter bounds (CL > 0, Vd > 0)
- Automatic confidence intervals and %CV
- Model comparison (AIC/BIC)
- Better for regulatory work

---

## 3. PK/PD Modeling

Link drug exposure to pharmacological effect using dose-response models.

```python
import numpy as np
import pandas as pd
from lmfit import Model
import matplotlib.pyplot as plt

# Dose-response data
dose = np.array([0, 1, 3, 10, 30, 100, 300])  # mg
effect = np.array([5, 15, 35, 62, 78, 88, 92])  # % efficacy

# Sigmoid Emax: E = E0 + (Emax - E0) * D^γ / (ED50^γ + D^γ)
def sigmoid_emax(d, e0, emax, ed50, gamma):
    """Hill equation for dose-response"""
    return e0 + (emax - e0) * d**gamma / (ed50**gamma + d**gamma)

# Fit
model = Model(sigmoid_emax)
params = model.make_params(e0=5, emax=100, ed50=10, gamma=1)
params['e0'].set(min=0); params['emax'].set(min=0, max=120)
params['ed50'].set(min=0.1); params['gamma'].set(min=0.5, max=5)
result = model.fit(effect, params, d=dose)

# Parameters with 95% CI
param_table = pd.DataFrame({
    'Parameter': ['E0 (%)', 'Emax (%)', 'ED50 (mg)', 'γ'],
    'Estimate': [result.params[p].value for p in ['e0', 'emax', 'ed50', 'gamma']],
    '95% CI': [f"[{result.params[p].value - 1.96*result.params[p].stderr:.2f}, " +
               f"{result.params[p].value + 1.96*result.params[p].stderr:.2f}]"
               for p in ['e0', 'emax', 'ed50', 'gamma']]
})
display(param_table, "Table 4: Emax Model Parameters")

# Plot
fig, ax = plt.subplots(figsize=(8, 6))
dose_pred = np.logspace(-1, 3, 200)
ed50 = result.params['ed50'].value

ax.semilogx(dose, effect, 'o', markersize=12, label='Data', color='steelblue')
ax.semilogx(dose_pred, result.eval(d=dose_pred), '-', linewidth=2, label='Sigmoid Emax', color='coral')
ax.axvline(ed50, color='gray', linestyle='--', alpha=0.5, label=f'ED50 = {ed50:.2f} mg')
ax.set_xlabel('Dose (mg)'); ax.set_ylabel('Effect (%)')
ax.set_title('Dose-Response Curve'); ax.legend(); ax.grid(alpha=0.3)
display(fig, "Figure 3: Dose-Response")
```

**Note**: γ (Hill coefficient) describes sigmoidicity. γ=1 is simple Emax, γ>1 gives steeper curve.

---

## 4. Quantitative Systems Pharmacology (QSP)

Model biological pathways using SBML with Tellurium's Antimony syntax.

```python
import tellurium as te
import pandas as pd
import matplotlib.pyplot as plt

# Define model using Antimony (human-readable SBML)
model_str = """
model receptor_ligand
  species R=100, L=50, RL=0;  # Receptor, Ligand, Complex (nM)
  kon=0.01; koff=0.1; kint=0.05; ksyn=5; kdeg=0.05;  # Rate constants

  J1: R + L -> RL; kon*R*L;    # Binding
  J2: RL -> R + L; koff*RL;    # Dissociation
  J3: RL ->; kint*RL;          # Internalization
  J4: -> R; ksyn; J5: R->; kdeg*R;  # Turnover
end
"""

r = te.loada(model_str)
result = r.simulate(0, 200, 500)
sim_df = pd.DataFrame(result, columns=['Time', 'R', 'L', 'RL'])

# Steady-state occupancy
occupancy_ss = 100 * sim_df['RL'].iloc[-1] / (sim_df['R'].iloc[-1] + sim_df['RL'].iloc[-1])
print(f"Steady-state receptor occupancy: {occupancy_ss:.1f}%")
display(sim_df.head(10), "Table 5: Simulation (first 10 time points)")

# Plot
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

# Time course
for species, color in [('R', 'steelblue'), ('L', 'coral'), ('RL', 'green')]:
    ax1.plot(sim_df['Time'], sim_df[species], label=species, linewidth=2, color=color)
ax1.set_xlabel('Time (min)'); ax1.set_ylabel('Concentration (nM)')
ax1.set_title('Pathway Dynamics'); ax1.legend(); ax1.grid(alpha=0.3)

# Target engagement
occupancy = 100 * sim_df['RL'] / (sim_df['R'] + sim_df['RL'])
ax2.plot(sim_df['Time'], occupancy, linewidth=2, color='purple')
ax2.set_xlabel('Time (min)'); ax2.set_ylabel('Receptor Occupancy (%)')
ax2.set_title('Target Engagement'); ax2.grid(alpha=0.3)

plt.tight_layout()
display(fig, "Figure 4: QSP Simulation")

# Sensitivity analysis
print("\nParameter Sensitivity (+50%):")
for param in ['kon', 'koff', 'kint']:
    r.reset(); r[param] *= 1.5
    res = r.simulate(0, 200, 100)
    occ = 100 * res[-1, 3] / (res[-1, 1] + res[-1, 3])
    print(f"  {param}: {(occ - occupancy_ss)/occupancy_ss * 100:+.1f}% change in occupancy")
```

**Note**: Antimony syntax is human-readable alternative to raw SBML XML. Tellurium includes libroadrunner ODE solver.

---

## 5. Trial Simulation

Compare dose regimens using virtual populations and probability of target attainment (PTA).

```python
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

np.random.seed(42)

# Virtual population (log-normal PK parameters)
n_patients = 50
cl_pop = np.random.lognormal(np.log(5.0) - 0.5*0.3**2, 0.3, n_patients)  # CL: 5 L/h, CV 30%
vd_pop = np.random.lognormal(np.log(50.0) - 0.5*0.25**2, 0.25, n_patients)  # Vd: 50 L, CV 25%

# Dose regimens
regimens = {'Q12H': (100, 12), 'Q24H': (200, 24)}  # (dose mg, tau h)
cmin_target, cmax_target = 5.0, 50.0  # Therapeutic window (ng/mL)

# Simulate steady-state for each regimen
results = {}
for name, (dose, tau) in regimens.items():
    cmax_list, cmin_list = [], []

    for cl, vd in zip(cl_pop, vd_pop):
        k = cl / vd
        R = 1 / (1 - np.exp(-k * tau))  # Accumulation factor
        cmax_ss = (dose / vd) * R
        cmin_ss = cmax_ss * np.exp(-k * tau)
        cmax_list.append(cmax_ss)
        cmin_list.append(cmin_ss)

    # Probability of target attainment
    in_range = [(cmin >= cmin_target) and (cmax <= cmax_target)
                for cmin, cmax in zip(cmin_list, cmax_list)]
    pta = 100 * sum(in_range) / n_patients

    results[name] = {'Cmax': cmax_list, 'Cmin': cmin_list, 'PTA': pta}

# PTA table
pta_df = pd.DataFrame({
    'Regimen': list(results.keys()),
    'Cmax Median': [np.median(results[r]['Cmax']) for r in results],
    'Cmin Median': [np.median(results[r]['Cmin']) for r in results],
    'PTA (%)': [results[r]['PTA'] for r in results]
})
display(pta_df, "Table 6: PTA Comparison")

# Spaghetti plots
fig, axes = plt.subplots(1, 2, figsize=(14, 5))

for ax, (name, (dose, tau)) in zip(axes, regimens.items()):
    # Plot first 10 patients
    for i in range(10):
        k = cl_pop[i] / vd_pop[i]
        R = 1 / (1 - np.exp(-k * tau))
        cmax_ss = (dose / vd_pop[i]) * R

        t = np.linspace(0, 3*tau, 300)
        c = cmax_ss * np.exp(-k * (t % tau))
        ax.plot(t, c, alpha=0.6, linewidth=1.5, color='steelblue')

    # Therapeutic window
    ax.axhline(cmin_target, color='red', linestyle='--', label='Cmin', linewidth=2)
    ax.axhline(cmax_target, color='orange', linestyle='--', label='Cmax', linewidth=2)

    ax.set_xlabel('Time (h)'); ax.set_ylabel('Concentration (ng/mL)')
    ax.set_title(f'{name}: {dose}mg q{tau}h (PTA={results[name]["PTA"]:.0f}%)')
    ax.set_ylim([0, 80]); ax.legend(); ax.grid(alpha=0.3)

plt.tight_layout()
display(fig, "Figure 5: Population PK (Spaghetti Plots)")

print(f"Optimal: {max(results, key=lambda x: results[x]['PTA'])} (highest PTA)")
```

**Key Concepts**: Log-normal distribution for PK parameters, steady-state equations, PTA as decision metric.

---

## Best Practices

### Code Generation
1. **Always specify units** (mg, L, h, ng/mL)
2. **Use lmfit for parameter estimation** (provides confidence intervals, model comparison)
3. **Include goodness-of-fit diagnostics** (residuals, AIC, BIC, R²)
4. **Semi-log plots for PK profiles** (concentration on log scale)
5. **Handle BLQ data** (below limit of quantification) appropriately

### Methodology Reporting
1. **Model equations** with parameter definitions
2. **Parameter estimates** with %CV or 95% CI
3. **Software versions** (scipy, lmfit, tellurium)
4. **Model selection rationale** (AIC/BIC comparison)
5. **Cite regulatory guidelines** (FDA/EMA)

---

## Regulatory References

### FDA Guidance
- [FDA PBPK Guidance (2018, 2020)](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/physiologically-based-pharmacokinetic-analyses-format-and-content-guidance-industry)
- FDA Population PK Guidance

### EMA Guidance
- [EMA PBPK Reporting Guideline](https://www.ema.europa.eu/en/reporting-physiologically-based-pharmacokinetic-pbpk-modelling-simulation-scientific-guideline)
- EMA Population PK Guideline

### Reporting Standards
- [Population PK Reporting Guidelines (PMC4432104)](https://pmc.ncbi.nlm.nih.gov/articles/PMC4432104/)
- ICH M4E(R2) for CTD Module 2.7

---

## Additional Resources

- [Tellurium Documentation](https://tellurium.readthedocs.io/)
- [lmfit Documentation](https://lmfit.github.io/lmfit-py/)
- [Open Systems Pharmacology](https://www.open-systems-pharmacology.org/)
- [Pharmpy - AMD Tool](https://ascpt.onlinelibrary.wiley.com/doi/full/10.1002/psp4.13213)

---

**Document Version**: 1.0
**Last Updated**: 2025-12-06
**Digital Article Project**: Modeling & Simulation Persona
