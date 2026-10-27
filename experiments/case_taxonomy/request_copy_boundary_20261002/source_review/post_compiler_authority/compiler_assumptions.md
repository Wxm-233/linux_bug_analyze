# Post-read compiler and storage assumptions

This supplementary evidence was collected **after** reading the initial harness/result snapshot. It is not part of the independent pre-harness oracle. That oracle and its manifest remain sealed and unchanged.

Both specified revisions use the same top-level `Makefile` blob `779c9c9b9820f8750c6673a2daca1a5fc571f51b` (SHA256 `7b2a9704e609a52bddc7c38353aaa2eb329c228c835579464fa6c7c744d2a159`). `KBUILD_CFLAGS` begins at 458; line 459 includes **`-fno-strict-aliasing`**. Complete raw Makefiles and the export time/blob/hash record are saved alongside this note.

The reduced harness uses declared character arrays as its storage and control buffer, with casts to `struct hci_command_hdr *` and the `bt_cb` macro's `struct bt_skb_cb *`. The final harness run therefore needs the historical Linux `-fno-strict-aliasing` assumption in both target compilation commands. This suppresses compiler optimizations relying on incompatible-type aliasing; it does not turn the fixture into a kernel SKB or provide a general ISO C object-model proof.

The HCI header declaration is preserved with `__packed`, so its required alignment is one, and its size/offsets are checked in the C file. The fixture's control buffer is explicitly `__attribute__((aligned(8)))`; its reduced `bt_skb_cb` only contains byte and 16-bit fields, so that alignment suffices for the selected x86_64 and s390x ABI projections. These observations follow from declarations and compiler assumptions. They are not an instrumented check of every runtime pointer.

The real `bt_skb_cb` at `include/net/bluetooth/bluetooth.h:319-328` contains additional fields and a union. The harness preserves the original `bt_cb`/opcode/type macros but substitutes a small control-buffer struct. The real `bt_skb_alloc` at 335-343 calls `alloc_skb` with `BT_SKB_RESERVE`; the harness returns a bounded local SKB fixture. `struct hci_request` text is preserved exactly while its `sk_buff_head` member uses a reduced queue type. These are explicit model boundaries, regardless of aliasing flags.

Final audit binding must identify the completed run with the added option. The preceding flags/results snapshot is development history and must not be presented as the final pass artifact. No compile or replay is performed by this reviewer.
