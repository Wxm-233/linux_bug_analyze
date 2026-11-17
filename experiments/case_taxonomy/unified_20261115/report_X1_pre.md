# 统一报告：X1 修复前

## 实现一致性（效果依赖）

动态确认 1、动态检查通过 0、转人工 6、动态发现但静态归因不对或没有静态来源 0。

### 动态确认

- `post_alloc_hook` 调用 `tag_clear_highpage`（mm/page_alloc.c:1828），规则 R1；依赖性质：`page` 使用前必须已写入（清零或初始化）；违反：riscv（Z3）、x86_64（Z3）；成立：arm64、arm64（开 MTE）

### 动态检查通过

（无）

### 转人工

- `kvm_get_dirty_log_protect` 调用 `kvm_arch_sync_dirty_log`（virt/kvm/kvm_main.c:2254）：资源 `kvm、memslot`，性质“已写入（清零或初始化）”；资源在内核内部，需要 ACTOR 或调试内核
- `kvm_clear_dirty_log_protect` 调用 `kvm_arch_sync_dirty_log`（virt/kvm/kvm_main.c:2376）：资源 `kvm、memslot`，性质“已写入（清零或初始化）”；资源在内核内部，需要 ACTOR 或调试内核
- `__irq_set_trigger` 调用 `mask_irq`（kernel/irq/manage.c:922）：资源 `desc`，性质“已写入（清零或初始化）”；资源在内核内部，需要 ACTOR 或调试内核
- `ring_buffer_read_page` 调用 `local_set`（kernel/trace/ring_buffer.c:6702）：资源 `bpage`，性质“已写入（清零或初始化）”；资源在内核内部，需要 ACTOR 或调试内核
- `move_ptes` 调用 `pte_none`（mm/mremap.c:263）：资源 `new_ptep`，性质“已写入（清零或初始化）、页表项已设置”；资源在内核内部，需要 ACTOR 或调试内核
- `check_stack_read_fixed_off` 调用 `verbose`（kernel/bpf/verifier.c:5445）：资源 `env`，性质“已写入（清零或初始化）”；资源在内核内部，需要 ACTOR 或调试内核

### 动态发现但静态归因不对或没有静态来源

（无）

## 类型一致性

（本树没有这类检查的数据）

## 调用上下文

（本树没有这类检查的数据）

