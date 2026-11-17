# 流水线报告：当前版本 7.3-rc2

静态候选 6 个：动态确认 0，动态检查通过 0，转人工 6；模板违反却无对应候选 0 项。动态检查的架构：arm64、riscv、x86_64。

## 一、动态确认

（无）

## 二、动态检查通过（所有架构上性质都成立）

（无）

## 三、无法动态检查，转人工分析

- `__irq_set_trigger` 调用 `mask_irq`（kernel/irq/manage.c:944）：资源 `desc`，性质“已写入（清零或初始化）”。原因：资源在内核内部，需要 ACTOR 或调试内核
- `ring_buffer_read_page` 调用 `local_set`（kernel/trace/ring_buffer.c:7304）：资源 `dpage`，性质“已写入（清零或初始化）”。原因：资源在内核内部，需要 ACTOR 或调试内核
- `move_ptes` 调用 `pte_none`（mm/mremap.c:267）：资源 `new_ptep`，性质“已写入（清零或初始化）、页表项已设置”。原因：资源在内核内部，需要 ACTOR 或调试内核
- `print_instance` 调用 `verbose`（kernel/bpf/liveness.c:507）：资源 `env`，性质“已写入（清零或初始化）”。原因：资源在内核内部，需要 ACTOR 或调试内核
- `arg_track_log` 调用 `verbose`（kernel/bpf/liveness.c:1042）：资源 `env、idx`，性质“已写入（清零或初始化）”。原因：资源在内核内部，需要 ACTOR 或调试内核
- `propagate_precision` 调用 `verbose`（kernel/bpf/states.c:1038）：资源 `env、fr、i`，性质“已写入（清零或初始化）”。原因：资源在内核内部，需要 ACTOR 或调试内核

## 四、模板违反了，却没有对应的静态候选（静态可能漏报）

（无）
