# Observational training and validation

The included operational model is a synthetic-data prototype. No real observations or surveyed infrastructure were supplied with this task. Do not present its metrics as field-validated accuracy.

## Collect and audit data

Use Field Operations > Observational data to download the CSV header and validate a file. Required columns include location/time, a traceable source, verification, measured predictors and a confirmed landslide/non-event label. Validation checks structure, ranges, rainfall consistency, unique location/time pairs, explicit time zones and verified flags. It cannot authenticate a claimed source.

NASA COOLR provides reported landslide inventories: https://gpm.nasa.gov/applications/landslides/coolr . Export guidance: https://gpm.nasa.gov/landslides/guides/COOLRGuide_Exporting.pdf . Preserve record identifiers, uncertainty and original attribution. A landslide catalogue alone lacks confirmed non-event observations and may lack the environmental predictors needed here. Do not generate negative labels merely because no report exists. Obtain audited station data and an explicit sampling protocol; align predictors to information available before the labelled event and document the forecast lead time.

## Train a separate candidate

From backend, with requirements installed:

```sh
python -m app.ml.observations /path/to/audited-observations.csv --output candidate-model
```

At least 100 rows are required and both the earlier 80% training window and later holdout need at least five cases of each class. Equal timestamps stay in the same partition. Scaling and calibration fit only the training partition. Output: candidate.joblib plus evaluation.json (precision, recall, F1, ROC-AUC, Brier score, confusion matrix, sample counts, temporal cutoff, sources and dataset SHA-256).

The candidate is deliberately not promoted automatically. Review false negatives/positives, calibration, representativeness and provenance with domain experts. This temporal evaluation does not establish generalisation to new districts: add a separate held-out-district study before making that claim. Field reports are unverified initially and never automatically become training labels.

After independent review, back up the current model; deploy the candidate using the same Python/scikit-learn environment that produced it and restart. Record the review and chosen operating thresholds. The Dockerfile currently trains the demonstration model during build: change that explicit build step only when intentionally deploying an approved candidate.
