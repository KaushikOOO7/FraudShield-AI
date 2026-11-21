# Dataset register

Full acquisition record: `docs/datasets/uci_sms_web_export.manifest.json` and
`backend/app/ml/models/sms_manifest.json`.

| Field | Actual SMS corpus |
| --- | --- |
| Name | UCI SMS Spam Collection, web-exported mirror copy |
| Original source | https://archive.ics.uci.edu/dataset/228/sms+spam+collection |
| Original download | https://archive.ics.uci.edu/static/public/228/sms+spam+collection.zip |
| Citation | Almeida, T. and Hidalgo, J. (2011), https://doi.org/10.24432/C5CC84 |
| Version | 2011 collection, donated 2012; export identified by SHA-256 |
| Acquisition | 2026-11-21; prepared acquisition timestamp 04:22:50 UTC |
| License | CC BY 4.0, verified on the original UCI page |
| Mirror | https://github.com/veermshah/cs6350-sms-spam-dataset |
| Method | Connected web tool text export; original ZIP download was blocked |
| Source accounting | All 5,579 displayed lines: 5,574 labeled records and five continuations |
| Labels | ham = non-spam; spam = spam, not confirmed financial fraud |
| Raw classes | 4,827 ham; 747 spam |
| Prepared file | data/datasets/uci_sms_web_export.jsonl |
| Prepared SHA-256 | `5a493718c50cb7e0043ff6aafd814a73ddc4c499cee9ec45cd3be5eb5c70365c` |
| Mirror's original-file SHA-256 | `7d039a24a6083ed9ef0f806ebad56bbb976e3aeb8de05669173bfdc4996c239d` |

This is a transformed real corpus. No records or labels were invented. Web
acquisition decodes HTML entities once, rejoins continuations, preserves source
indices and writes UTF-8 JSONL. Whitespace/controls may differ from the original;
this is not a byte-identical ZIP download. The mutable mirror URL is a limitation;
the complete export is frozen locally with checksums.

Training: NFKC/casefold/whitespace normalization; remove conflicting normalized
labels and duplicates before splitting. Actual removals: zero conflicting-label
records, 415 normalized duplicates. Usable corpus: 5,159 records, 4,517 ham and
642 spam. URL/number templates share a stratified split group. TF-IDF fits only
the training records. See [MODEL_EVALUATION.md](MODEL_EVALUATION.md) for methodology,
all split counts, measured validation/test metrics and limitations.

Historical sources include UK spam reports and NUS messages from Singapore.
Indian financial-fraud, multilingual and current-campaign performance remain
unevaluated. Corpus URLs have no assumed current threat status. Tests use them
as corpus fixtures, not current fraud incidents.

| Other source/capability | Actual status |
| --- | --- |
| UCI PhiUSIIL Phishing URL (Website) | Original source/license/labels verified 2026-11-21; downloader and URL-text pipeline prepared; download failed with ConnectError, no corpus or trained models available. |
| UCI Phishing Websites | Not acquired; https://archive.ics.uci.edu/dataset/327/phishing+websites ; license pending acquisition verification. Its precomputed features cannot all be derived from a URL alone. |
| LegitPhish | Original release/version/license not yet verified; not acquired/trained. |
| Indian financial-fraud SMS | No approved corpus or claimed evaluation. |
| APK/caller/QR fraud | No approved labeled corpus or fabricated ML baseline. |
| ASVspoof/voice | Future research; not acquired/trained. |

The original-source downloader writes actual hashes/dates only after success.
The web-export preparer requires the original acquisition record and verifies
all source indices, label counts and prepared bytes.

PhiUSIIL's [original UCI page](https://archive.ics.uci.edu/dataset/967/phiusiil+phishing+url+dataset)
identifies the 2024 release under CC BY 4.0, DOI 10.1016/j.cose.2023.103545.
The publisher reports 235,795 rows: 134,850 legitimate (label 1) and 100,945
phishing (label 0). These are source-reported counts, not acquired local records.
Download date, local checksum, preprocessing removals, splits and evaluation
remain unavailable until original acquisition succeeds. The trainer reverses
labels internally so phishing is positive, drops invalid/conflicting/duplicate
normalized URLs, groups related hostnames and selects RF/XGBoost by validation
F1 before evaluating the untouched test partition. Only URL-text features are
used; historical page/content/corpus-derived features are not online evidence.
The dataset is not a live malicious URL feed or validated Indian fraud corpus.

## Identified raw-URL source — not acquired

UCI PhiUSIIL Phishing URL (Website), Prasad and Chandra (2024): https://archive.ics.uci.edu/dataset/967/phiusiil+phishing+url+dataset . Original license CC BY 4.0 was verified on 2026-11-21. Published source size is 235,795 records: 134,850 legitimate (label 1), 100,945 phishing (label 0). These are source documentation counts, not locally downloaded records. DOI/citation: 10.1016/j.cose.2023.103545.

The original-source acquisition command failed with ConnectError; no local corpus, download date/checksum, trained model or evaluation is invented. The downloader will record actual bytes/counts/labels/time only after success. The training code ignores page/content-derived and corpus-wide published features, extracting URL-text features only, with conservative domain groups and separate validation/test partitions. See URL_ML_PIPELINE.md.
