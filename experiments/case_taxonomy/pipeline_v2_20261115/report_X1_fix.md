# 流水线报告：X1 修复后对照（静态同上；动态：X1 修复后内核）

静态候选 7 个：动态确认 0，动态检查通过 1，转人工 6；模板违反却无对应候选 0 项。动态检查的架构：arm64、arm64（开 MTE）、riscv、x86_64。

## 一、动态确认

（无）

## 二、动态检查通过（所有架构上性质都成立）

- `post_alloc_hook` 调用 `tag_clear_highpage`（mm/page_alloc.c:1828），规则 R1，由 Z2、Z3、Z4、Z7 检查

## 三、无法动态检查，转人工分析

- `kvm_get_dirty_log_protect` 调用 `kvm_arch_sync_dirty_log`（virt/kvm/kvm_main.c:2254）：资源 `kvm、memslot`，性质“已写入（清零或初始化）”。原因：资源在内核内部，需要 ACTOR 或调试内核
- `kvm_clear_dirty_log_protect` 调用 `kvm_arch_sync_dirty_log`（virt/kvm/kvm_main.c:2376）：资源 `kvm、memslot`，性质“已写入（清零或初始化）”。原因：资源在内核内部，需要 ACTOR 或调试内核
- `__irq_set_trigger` 调用 `mask_irq`（kernel/irq/manage.c:922）：资源 `desc`，性质“已写入（清零或初始化）”。原因：资源在内核内部，需要 ACTOR 或调试内核
- `ring_buffer_read_page` 调用 `local_set`（kernel/trace/ring_buffer.c:6702）：资源 `bpage`，性质“已写入（清零或初始化）”。原因：资源在内核内部，需要 ACTOR 或调试内核
- `move_ptes` 调用 `pte_none`（mm/mremap.c:263）：资源 `new_ptep`，性质“已写入（清零或初始化）、页表项已设置”。原因：资源在内核内部，需要 ACTOR 或调试内核
- `check_stack_read_fixed_off` 调用 `verbose`（kernel/bpf/verifier.c:5445）：资源 `env`，性质“已写入（清零或初始化）”。原因：资源在内核内部，需要 ACTOR 或调试内核

## 四、模板违反了，却没有对应的静态候选（静态可能漏报）

（无）
