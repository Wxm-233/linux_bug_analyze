# Local holdout pilot

Inputs were frozen as the latest two non-merge commits touching each of four
paths (mempolicy, perf parse-events, s390 topology, Btrfs disk-io) in 2023–2025.
This is a targeted, temporally clustered eight-commit set, not a representative
random sample. Titles were visible during selection; source labels were assigned
after the manifest. Audit excludes hashes in previous result filenames, which
does not prove they were never mentioned elsewhere.

The first external-model request was rejected before execution. After the user
explicitly approved these samples, the frozen eight inputs were submitted to
the configured ISRC API using DeepSeek-V4.1-Flash. All eight completed in nine
requests with 78,505 reported tokens, including one evidence-ID validation retry.
The original local review and source experiment predate those model results.

The one contract-related reference was labeled related. All six provisional
controls were labeled unrelated by the model, but c3d17464f026 was retained as
uncertain by the truncation safeguard. The scope-uncertain tool CPU-map example
was excluded by the model; that is a review disagreement, not a confirmed miss.
Final queue: one related, one uncertain, six excluded. No prompt/guard tuning
was performed. This tiny nonrepresentative sample is not an overall accuracy
estimate or expert-reviewed benchmark. Runtime model comparison is saved as
model-comparison.json alongside the original local-only audit snapshot.

```bash
python experiments/holdout_review/run.py --linux-dir /root/repos/linux \
  --outdir analysis_out/contract-holdout-20260915
```

If no manifest exists in the output directory, the runner copies the checked-in
samples.json containing the eight fixed public commit IDs. Existing manifests
are preserved. Human-readable reference
notes are encoded in run.py for the specific eight commits: six provisional
controls, one scope-uncertain example and one contract-related example. Review
covers commit descriptions and focused hunks; broader source changes were
inspected for the contract-related scheduler example. Controls are not proofs
that every cross-file transformation is behaviorally equivalent.

The unchanged local lead rule matches only 661f951e371c via topology_lifecycle.
This is a lead detector result, not a complete classifier verdict. The proposed
state-at-consumption contract transfers to that case: execute the real old/new
sd_numa_mask over synthetic two-level/two-node mask tables, vary requested level,
cached global level and CPU. Old: 4/8 mismatch, new: 0/8. This is manual contract
instantiation after review, not automatic synthesis or a booted scheduler test.
No reproduction of the upstream warning or physical NUMA topology is claimed.

Manifest, frozen contract snapshot, original patches, local review, generated C,
function sources, binaries, per-input outcomes and hashes remain ignored runtime
artifacts. This small set supports further validation, not statistical claims.
