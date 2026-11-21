# Raw-URL pipeline — training/evaluation pending

Original source: UCI PhiUSIIL Phishing URL (Website), Prasad and Chandra, 2024.
https://archive.ics.uci.edu/dataset/967/phiusiil+phishing+url+dataset
CC BY 4.0 and labels were verified on the original page. Published source counts
are 235,795 URLs: 134,850 legitimate (1), 100,945 phishing (0). These are source
documentation counts, not acquired local records or live threat reports.

Acquisition command: `.venv/bin/python scripts/download_url_dataset.py`.
It downloads the original ZIP, validates member size, columns/classes/counts,
and records actual acquisition time/hashes only after success. This session's
attempt failed with ConnectError. No replacement dataset was generated.

Once actual source/package access is available:

```bash
.venv/bin/python -m pip install -r backend/requirements-url-training.txt
.venv/bin/python scripts/download_url_dataset.py
.venv/bin/python -m backend.app.ml.url.train
```

The training code validates provenance/checksum/labels, removes unsupported or
credential-bearing URLs, conflicting normalized labels and duplicates, then
uses conservative last-two-host-label groups and predetermined stratified group
folds (outer five-way seed 42, inner four-way seed 43). Groups stay disjoint.
Multi-label suffixes may overgroup unrelated registrations; this grouping is
not ownership evidence. Evaluation covers only the supported cleaned subset.

Sixteen features are derived from URL text alone: lengths, host labels, IP/HTTPS
structure, character counts, query fields, character entropy and lexical tokens.
No page content, redirects, unverifiable domain age or published corpus-wide
probability/similarity features are reused. Token presence is a model input, not
a hardcoded fraud prediction.

Fixed RF and CPU XGBoost candidates fit training only. Highest validation F1
selects the model; the chosen training fit is evaluated once on the held-out test
partition, without refitting/tuning on test data. Actual accuracy, precision,
recall, F1, confusion matrix, FPR/FNR and class sizes are saved only after fitting.
No training accuracy substitutes for test evaluation.

Intended artifacts: url_pipeline.joblib, url_manifest.json and url_splits.json.
They contain actual hashes/version/provenance/dependencies/partitions/results.
The inference interface validates trusted artifact integrity, feature/classifier
structure and compatibility. It is connected to URL, SMS-extracted URL and QR
services, with per-model prediction provenance in SQL storage.

Actual status: no corpus downloaded, no RF/XGBoost fitted, no comparison/holdout
evaluation completed. Feature, missing-source/artifact and negative integrity
guards are tested; genuine training and positive model inference remain pending.
The API returns model_not_trained with null label/score/confidence. No temporary
model or random/hardcoded prediction fills the gap. Future labels are legitimate
or phishing, with no calibrated probability. A phishing model label raises
caution and cannot confirm fraud.

CPU-only optional package release: https://pypi.org/project/xgboost-cpu/3.2.0/ .
It is not installed/tested in this environment. SMS's trained baseline is separate.
