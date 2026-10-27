# Independent read-only final audit, 2026-10-02

**Status: `pass_with_explicit_fixture_limits`; blockers: none.** All 16 formal rows agree with the independent source oracle sealed at `2026-10-02T03:50:24.839142+00:00`, before experimental harness/results were read. This is agreement with the predicted historical behavior, including the known parent s390x representation error, not a claim that all payloads satisfy the little endian contract.

The audit reads the latest frozen runner, generated C, source evidence, result JSON and captured raw process stdout. It independently compares source excerpts to previously exported complete Git blobs and reconstructs each raw row's expected values from the sealed oracle. It never imports or invokes the runner, recompiles C, replays executables, or edits an input. `final_audit.json` contains the seven final input hashes, 1,202 boolean checks and their detailed records, complete row comparisons, raw-stdout digests, limits, and an empty `blockers_found` list.

| Final input, relative to experiment stage | SHA256 |
|---|---|
| `run_request_copy.py` | `b5a10d26418562b017ec1c0dac7bd731c6724504c16f06e6de8d95515d9dd3f8` |
| `source_evidence.json` | `fb939ed34dcd41fc90a768a6b6dbdb4a6407a224d4f4c3f7f18f6ad51f477f9e` |
| `results.json` | `be12cadf72bf64e3ca7871bb0390632242bb58e5af073b5167e6c6c9aea34809` |
| `request_copy_parent.c` | `9599a9dcf626eaf07ffde175974c9b8de134b76590c3b4cf596e460cc3007a10` |
| `request_copy_fix.c` | `b0ffd66deace80b4c8b911aed3f0476d5d5218b0f4742b014a68346ee16492a3` |
| `protocol_pre.md` | `836977f9cc197ce19482ef161aee2077922ead37254346eaea77bfa406906d7a` |
| `source_review/expected_matrix_pre_harness.json` | `e40312ab39e2762907342293d81a8d1836355ee18265c5e60aae7b1e1b54fcb0` |

The runner's before/after bindings and the independently recomputed final file digests agree. The oracle receipt remains unchanged. Both versions' five complete original functions—`hci_init4_req`, `hci_req_add`, `hci_req_add_ev`, `hci_prepare_cmd`, and `skb_put_data`—are preserved verbatim. All relevant source evidence blobs, hashes and excerpt line numbers match the reviewer's independently saved originals. Historical default initializer values remain 27 and 328; their indentation is normalized in the generated fixture outside the preserved original functions.

`hci_req_add` is a real preserved C function, forwarding event zero to `hci_req_add_ev`; it is not an intercepting replacement macro. The original `hci_request` declaration is preserved, with `hdev`, `cmd_q` and stored `err`. Its `sk_buff_head` member type is a local reduced queue, so preserved request text does not mean a full kernel request layout was executed.

The target's add attempt is counted by the original add_ev debug call before its `req.err` guard. The allocator counter sits inside the allocation stub and independently establishes whether allocation actually occurs. `skb_put` counts bounded storage reservations. The preserved `skb_put_data` body then runs `memcpy(tmp, data, len)`; the original prepare debug call after that helper returns observes completed copy and snapshots the resulting SKB fixture storage. It does not substitute a producer parameter capture for the copy. The queue-tail stub later captures the same header, payload and complete command bytes after original request metadata assignments. Copy completion is observed after the helper returns, rather than by an instrumentation counter inside libc memcpy.

| Initial `req.err` | Allocation configured | Add attempt | Actual allocation | Completed four-byte copy | Queue-tail stub | Final `req.err` | init4 return |
|---|---|---:|---:|---:|---:|---:|---:|
| 0 | success | 1 | 1 | 1 | 1 | 0 | 0 |
| 0 | failure | 1 | 1 | 0 | 0 | -12 | 0 |
| -5 | success | 1 | 0 | 0 | 0 | -5 | 0 |
| -5 | failure | 1 | 0 | 0 | 0 | -5 | 0 |

Each condition occurs in parent/fix × x86_64/s390x, yielding 16 add attempts, 8 actual allocations, 4 completed copies, 4 queue-tail observations, and 12 byte-format rows normalized to **`not_evaluated`**. Allocation failure creates no header/payload and records one failure log; an existing `-EIO` bypasses allocation entirely and is preserved. All 16 real init4 returns are zero. `req_err_after` is separate stored request state; no `req_run` was executed and no top-level error propagation was demonstrated.

| Successful copy row | Header | Copied payload = queue payload | Little endian decoded payload |
|---|---|---|---|
| parent x86_64 | `242004` | `1b004801` | 27, 328 |
| parent s390x | `242004` | `001b0148` | 6912, 18433 |
| fix x86_64 | `242004` | `1b004801` | 27, 328 |
| fix s390x | `242004` | `1b004801` | 27, 328 |

These are seven command bytes without a transport packet-type prefix. The HCI header is always correct because its opcode conversion is independent of the parameter conversion. The sole copied payload mismatch is the predicted parent s390x case. The 12 absent-copy rows keep all copied/queued byte arrays and byte verdicts null with `byte_check_execution=not_executed`; zero queue metadata fields in their raw output are placeholders, not observed normal commands. The four raw executable stdout records are saved under `raw_stdout_final/` and checked against processed result base fields.

All four final compile command records include `-fno-strict-aliasing`. Supplementary post-read evidence confirms both original Makefiles include that option in `KBUILD_CFLAGS:459`; it is deliberately separate from the sealed oracle. The command header is packed, requiring alignment one, and its size/offsets are statically asserted. The fixture control buffer is explicitly aligned eight, which suffices for its reduced byte/16-bit struct on the selected ABI projections. Runtime pointer alignment is not independently instrumented. The storage/control arrays remain declared character arrays accessed through structure casts; adopting Linux's compiler aliasing assumption does not establish a general ISO C object-model proof or reproduce the real `bt_skb_cb` union and SKB layout.

The initial flags snapshot was read during review and then superseded after the storage/aliasing assumption was identified. Root preserved it under `development_previous_flags/` and reran the same fixed 16-row matrix with the added option. This final audit binds only the latest hashes above. The unchanged C and oracle, and the same source example/inputs, make this a development revalidation; neither run is an independent holdout or a new defect.

The claims remain limited to direct execution of original historical request-building functions in a bounded user-mode fixture. `HCI_PRIMARY`, LMP_LE and DLE are supplied context; the isolated init4 target branch itself checks DLE, and the outer normal-init gate is not executed. Allocation/reserve behavior, queue locks/workqueues, feature discovery, init3 responses, synchronous request execution, completion readers, controller transport and hardware acceptance are not exercised. QEMU provides a s390x user-mode process with observed big endian marker bytes. Queue-tail observations therefore establish arrival at a local queue mock, and the copied-byte checks establish the conditional representation difference, without supporting detector accuracy, hardware reachability or full-kernel correctness claims.
