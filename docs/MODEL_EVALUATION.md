# Model evaluation

Actual model: `sms-spam-tfidf-logistic-regression`.
Version: `sms-uci-tfidf-lr-v1-efcaf62d777d`.
Task: historical SMS spam/ham classification.

Artifact: `backend/app/ml/models/sms_pipeline.joblib`.
SHA-256: `b0f588b84eb01bd317bc7df8d3d49522baa39516922ab77cdd48da7ce96959d7`.
Complete timestamps, parameters, dependencies and provenance are in
`sms_manifest.json`; per-record splits are in `sms_splits.json`.

| Partition | Messages | Ham | Spam |
| --- | ---: | ---: | ---: |
| Acquired corpus | 5,574 | 4,827 | 747 |
| After deduplication | 5,159 | 4,517 | 642 |
| Training | 3,095 | 2,710 | 385 |
| Validation | 1,032 | 903 | 129 |
| Test holdout | 1,032 | 904 | 128 |

Fixed pipeline: NFKC/casefold/whitespace normalization, word TF-IDF with
unigrams/bigrams, `min_df=2`, sublinear TF, then Logistic Regression with `C=1`,
balanced class weights, liblinear, maximum 1,000 iterations and seed 42.
No test-based tuning or final fit on test records occurred.

Outer StratifiedGroupKFold: five folds, seed 42, predetermined first test fold.
Remaining data: four folds, seed 43, predetermined validation fold. Exact
templates after URL/digit replacement share a group. Automated checks verify
disjoint groups/texts and vocabulary derived exclusively from training records.
Near-duplicate campaigns and chronology are not fully controlled.

| Metric, spam is positive | Validation | Test holdout |
| --- | ---: | ---: |
| Accuracy | 0.975775 | 0.988372 |
| Precision | 0.926230 | 0.932836 |
| Recall | 0.875969 | 0.976563 |
| F1 | 0.900398 | 0.954198 |
| False-positive rate | 0.009967 | 0.009956 |
| False-negative rate | 0.124031 | 0.023438 |

Rows = actual, columns = predicted, order `[ham, spam]`:

```text
Validation: [[894, 9], [16, 113]]
Test:       [[895, 9], [ 3, 125]]
```

Lower validation recall shows split variance. These are genuine held-out spam
measurements, not Indian fraud accuracy or independent external validation.
Current financial fraud, multilingual messages, APK/caller/QR fraud and temporal
performance remain unevaluated. Training accuracy is not presented as test
performance.

Inference returns the actual class and an explicitly uncalibrated decision
margin. It is never displayed as probability, confidence or risk score.
Out-of-vocabulary input gives `insufficient_features`; missing/incompatible/
corrupt artifacts give explicit unavailable states with null predictions.
Risk confidence stays null. Automated inference cannot confirm fraud.

URL evaluation is **not completed**. No trained URL classifier or comparison
between Random Forest and XGBoost is claimed.

URL acquisition/training was attempted in this continuation: acquisition returned ConnectError and training stopped with DatasetValidationError before fitting. Raw-URL feature/provenance/inference guard tests pass, but RF/XGBoost training, selection and holdout evaluation have not run. No URL accuracy, F1 or predictions are claimed.
