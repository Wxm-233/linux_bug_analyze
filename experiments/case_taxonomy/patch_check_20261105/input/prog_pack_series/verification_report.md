# Fresh final RISC-V series verification

- Status: **PASS**
- Checks: 10/10 PASS
- Sequential apply: 8/8

- PASS: `commit_count` — patches=8
- PASS: `provenance` — model generation and all feedback/hardening loops passed
- PASS: `hashes` — all frozen hashes match the index
- PASS: `architecture_isolation` — no foreign-architecture output path
- PASS: `sequential_apply` — applied=8/8
- PASS: `preemption_interval` — all page-loop exits restore preemption after unmapping
- PASS: `compile_feedback_api` — unavailable API removed while terminal release remains
- PASS: `pack_lifecycle` — pack failure, finalize, and delayed free lifecycle retained
- PASS: `rv32_bridge` — RV32 supplies the shared text copy/invalidate interface
- PASS: `runtime_rx_alias` — runtime executable alias is initialized before publication
