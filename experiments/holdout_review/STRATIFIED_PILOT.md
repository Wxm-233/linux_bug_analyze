# Bounded stratified pilot

The 2026-09-21 pilot freezes 500 public candidate commits before model calls.
Five chronological scan-rank bands are crossed with five priority groups based
on subject keywords: representation, lifecycle, geometry, capability, other.
Each cell contributes 20 unique items using seed 20260921. Bands are not calendar
years. Priority assignment is a sampling heuristic, not a relevance judgment.
The manifest stores population sizes and candidate-audit SHA256. Selection
excludes full-hash artifact filenames and existing hashes/selected_hashes lists;
317 distinct hashes were excluded in this run. This does not certify that no
sample has ever been mentioned outside those indexed artifacts.

The recorded pilot used screen-v4 and an external settings file. The script
imports the installed screening module and fingerprints its version and source;
the current checkout has advanced beyond screen-v4. Do not resume the old output
with changed sources: retain its frozen results and use a new directory for a new
experiment. For new throughput trials prefer `screen_fast.py` at the repository
root. No key is written to an artifact. Scope is short judgments only; no full
reports or experiments are triggered from classifications.

Hard local controls: 500 selected items, at most 600 requests and 4,000,000 charged
tokens across restarts of this output directory, with at most 1,200 output tokens
per request. Tokens with unknown usage retain their reservation. This is not a
currency-denominated billing cap. Changing output directories creates a new
budget and is not authorized by the original pilot budget.

A process lock prevents simultaneous execution. Existing successful results
are reused only under the runner's evidence/model/prompt fingerprint. The pilot
also freezes model, endpoint, context digest and core Python module hashes.
Restart restores the cumulative usage ledger rather than granting a fresh
budget. Offline tests verify exhausted requests and in-flight reservations
cannot be refunded by this restoration.

Two validation failures on an individual commit place it in failed_review.json;
it enters the review list without a fabricated valid model result. No further
paid retry of that exhausted sample is made on resume. Three consecutive
validation-failed samples stop the batch; service/authentication/budget stops
continue to use the original runner behavior. The first sample exposed this
distinction: 8,967 tokens were consumed before the initial all-stop behavior was
replaced with isolated format-failure handling. Those costs remain charged.

```bash
# First freeze the manifest without model calls.
python experiments/holdout_review/stratified_pilot.py \
  --outdir analysis_out/stratified-pilot --settings /path/to/settings.toml
# Paid run within the fixed cumulative caps; same path for resume.
python experiments/holdout_review/stratified_pilot.py \
  --outdir analysis_out/stratified-pilot --settings /path/to/settings.toml --run
python experiments/holdout_review/summarize_pilot.py --outdir analysis_out/stratified-pilot
```

The report separates model labels, program labels, format failures and pending
samples. Nonproportional cell quotas and missing independent expert labels mean
neither raw retained fraction nor model agreement estimates overall precision,
recall, or the prevalence of cross-architecture defects. Raw responses and
individual evidence should be reviewed before selecting new experiment cases.

Recorded completion: 500 attempted, 479 valid (60 related, 93 uncertain,
326 unrelated), and 21 format failures. The aggregate uncertain count of 114
includes those 21 failures; it is not 114 valid model judgments. There were
575 requests, 2,790,268 reported tokens, and 2,810,286 budget-charged tokens.
This nonproportional, model-labeled sample does not estimate population accuracy.
