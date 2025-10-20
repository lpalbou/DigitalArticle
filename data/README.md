# Data Directory

This directory contains datasets available for analysis in the Digital Article.

## Available Datasets

### Biological Research Data

- `gene_expression.csv` - Gene expression data with 20 genes across 6 samples
- `patient_data.csv` - Clinical patient data with treatment responses and biomarkers

## Usage in Digital Articles

These files are automatically available in the execution environment. Use these paths in your analysis:

- `data/gene_expression.csv`
- `data/patient_data.csv`

## File Structure

```
gene_expression.csv:
- Gene_ID: Unique gene identifier
- Sample_1, Sample_2, Sample_3: Treatment samples
- Control_1, Control_2, Control_3: Control samples

patient_data.csv:
- Patient_ID: Unique patient identifier  
- Age: Patient age
- Gender: Male/Female
- Condition: Medical condition
- Treatment_Response: Complete_Response/Partial_Response/No_Response
- Biomarker_Level: Numerical biomarker measurement
```
