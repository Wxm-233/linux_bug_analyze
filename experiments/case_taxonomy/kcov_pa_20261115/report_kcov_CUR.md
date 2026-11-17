# 流水线报告（实测覆盖）：当前版本（本轮内核）

静态候选 6 个：动态确认 0，测过没事 0，部分架构测到 0，转人工 6；模板违反却无对应候选 0 项。

## 一、动态确认

（无）

## 二、测过没事（所有架构都有模板实际执行到，性质都成立）

（无）

## 三、只在部分架构上测到

（无）

## 四、转人工

- `__irq_set_trigger` 调用 `mask_irq`（kernel/irq/manage.c:944），规则 无；资源在内核内部，需要 ACTOR 或调试内核
- `ring_buffer_read_page` 调用 `local_set`（kernel/trace/ring_buffer.c:7304），规则 无；资源在内核内部，需要 ACTOR 或调试内核
- `move_ptes` 调用 `pte_none`（mm/mremap.c:267），规则 无；资源在内核内部，需要 ACTOR 或调试内核（另：被模板 Z9 执行到过，但规则不对应）
- `print_instance` 调用 `verbose`（kernel/bpf/liveness.c:507），规则 无；资源在内核内部，需要 ACTOR 或调试内核
- `arg_track_log` 调用 `verbose`（kernel/bpf/liveness.c:1042），规则 无；资源在内核内部，需要 ACTOR 或调试内核
- `propagate_precision` 调用 `verbose`（kernel/bpf/states.c:1038），规则 无；资源在内核内部，需要 ACTOR 或调试内核

## 五、模板违反却没有对应的静态候选

（无）
