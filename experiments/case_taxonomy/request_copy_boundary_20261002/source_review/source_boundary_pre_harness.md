# Independent source boundary, 2026-10-02

This note and `expected_matrix_pre_harness.json` were prepared from the two Git source revisions before reading the experimental runner, C harness, result JSON, or stdout. The oracle was sealed at **2026-10-02T03:50:24.839142+00:00**; its SHA256 is `e40312ab39e2762907342293d81a8d1836355ee18265c5e60aae7b1e1b54fcb0`. The receipt records this digest separately. Original exported source and blob identities are in `raw/` and `source_manifest_pre_harness.json`.

The commits are parent `cef456cd354ef485f12d57000c455e83e416a2b6` and fixed `727ea61a5028f8ac96f75ab34cb1b56e63fd9227`. Both use `net/bluetooth/hci_request.c` blob `7f6a581b5b7e14fa7b72db8449afc85a8d9327e2`. The change is confined to the two assignments at `net/bluetooth/hci_core.c:845-846`: the parent directly assigns native `__u16` values; the fix applies `cpu_to_le16`.

With all other init4 branches disabled, the DLE condition at `hci_core.c:842` enables exactly one `0x2024` add call at line 847. The fields are constructed before this call, regardless of `req.err`. `HCI_PRIMARY` is a normal initialization orchestration gate (`hci_core.c:879-890`), and `LMP_LE` is fixed context; the direct init4 target branch itself checks DLE. This isolated experiment must not claim it replayed the full initialization sequence.

`hci_req_add` is an actual C function (`hci_request.c:342-346`), forwarding to `hci_req_add_ev` with event zero. In `add_ev`, the existing error check at 323-324 precedes the call to `hci_prepare_cmd` at 326. A pre-existing `-EIO` therefore prevents a real allocator call even when failure is configured. It preserves `req.err=-5` and performs no payload copy or queue observation. With an initially clean request, allocation failure returns NULL from prepare (292-294) and stores `req.err=-ENOMEM` in add_ev (330), again with no payload copy or queue observation.

After allocation succeeds, prepare creates the three-byte header at 296-298, converting the opcode independently to little endian. It calls `skb_put_data` at 301. The original `include/linux/skbuff.h:2212-2220` appends storage and executes `memcpy(tmp, data, len)` at 2217. That is the parameter-byte copy boundary; it preserves the already constructed bytes without endian conversion. Only then does add_ev check the queue, mark START if empty, set event, and call `skb_queue_tail` (334-339).

For source values 27 and 328, the intended four-byte payload is `1b 00 48 01`. Parent x86_64 and both fixed architectures produce it. Parent s390x produces `00 1b 01 48`, which a little endian consumer decodes as 6912 and 18433. Every successful path has command header `24 20 04`. These are copied SKB command bytes; a queue stub may observe them, but does not establish controller transport or controller acceptance.

| Initial `req.err` | Allocation configured | Actual allocation | Payload copy | Queue-tail observation | Final `req.err` | init4 return |
|---|---|---:|---:|---:|---:|---:|
| 0 | success | 1 | 1, four bytes | 1 | 0 | 0 |
| 0 | failure | 1 | 0 | 0 | -12 | 0 |
| -5 | success | 0 | 0 | 0 | -5 | 0 |
| -5 | failure | 0 | 0 | 0 | -5 | 0 |

Every row has one target add attempt. Where no payload copy exists, copied-byte format is **not_evaluated**. Local stack parameter bytes may have a source-predicted value, but are not a copied command. `hci_init4_req` returns zero at 861 in every row. Stored errors are not top-level return values; without invoking `hci_req_run`, the experiment does not exercise subsequent error propagation.

The allocation, storage, and queue implementations in an eventual reduced harness require a separate audit. Appropriate claims depend on retaining the original `hci_prepare_cmd`, `hci_req_add_ev`, `hci_req_add`, and `skb_put_data` bodies, observing the copy into SKB storage, and identifying queue callbacks as stubs.
