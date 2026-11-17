# 统一报告：当前版本 7.3-rc2

## 实现一致性（效果依赖）

动态确认 0、动态检查通过 0、转人工 6、动态发现但静态归因不对或没有静态来源 0。

### 动态确认

（无）

### 动态检查通过

（无）

### 转人工

- `__irq_set_trigger` 调用 `mask_irq`（kernel/irq/manage.c:944）：资源 `desc`，性质“已写入（清零或初始化）”；资源在内核内部，需要 ACTOR 或调试内核
- `ring_buffer_read_page` 调用 `local_set`（kernel/trace/ring_buffer.c:7304）：资源 `dpage`，性质“已写入（清零或初始化）”；资源在内核内部，需要 ACTOR 或调试内核
- `move_ptes` 调用 `pte_none`（mm/mremap.c:267）：资源 `new_ptep`，性质“已写入（清零或初始化）、页表项已设置”；资源在内核内部，需要 ACTOR 或调试内核
- `print_instance` 调用 `verbose`（kernel/bpf/liveness.c:507）：资源 `env`，性质“已写入（清零或初始化）”；资源在内核内部，需要 ACTOR 或调试内核
- `arg_track_log` 调用 `verbose`（kernel/bpf/liveness.c:1042）：资源 `env、idx`，性质“已写入（清零或初始化）”；资源在内核内部，需要 ACTOR 或调试内核
- `propagate_precision` 调用 `verbose`（kernel/bpf/states.c:1038）：资源 `env、fr、i`，性质“已写入（清零或初始化）”；资源在内核内部，需要 ACTOR 或调试内核

### 动态发现但静态归因不对或没有静态来源

（无）

## 类型一致性

动态确认 0、动态检查通过 0、转人工 42、动态发现但静态归因不对或没有静态来源 0。

### 动态确认

（无）

### 动态检查通过

（已有数据没有逐条记录“检查了但没差异”的项）
（无）

### 转人工

- arm64 与众不同：listmount|EFAULT|E2BIG（5 个用例，例 12087）；候选 **实现一致性检查**：__do_sys_listmount（fs/namespace.c:6149），参数 [1] 的值与提示吻合；边界项 `access_ok`，证据 2，得分 0.4227；静态取值 riscv=None、arm64=None、x86_64=None；需人工判断（以往各轮判断这类差异多为环境或能力差异）
- arm64 与众不同：mincore|EFAULT|ENOMEM（1 个用例，例 12355）；候选 **实现一致性检查**：__do_sys_mincore（mm/mincore.c:313），参数 [2] 的值与提示吻合；边界项 `access_ok`，证据 2，得分 0.4227；静态取值 riscv=None、arm64=None、x86_64=None；需人工判断（以往各轮判断这类差异多为环境或能力差异）
- arm64 与众不同：mincore|EFAULT|arg1（3 个用例，例 12906）；候选 **实现一致性检查**：__do_sys_mincore（mm/mincore.c:313），参数 [2] 的值与提示吻合；边界项 `access_ok`，证据 2，得分 0.4227；静态取值 riscv=None、arm64=None、x86_64=None；需人工判断（以往各轮判断这类差异多为环境或能力差异）
- arm64 与众不同：mincore|EINVAL|EINVAL（9 个用例，例 11963）；候选 **实现一致性检查**：__do_sys_mincore（mm/mincore.c:306），参数 [1] 的值与提示吻合；边界项 `access_ok`，证据 2，得分 0.4227；静态取值 riscv=None、arm64=None、x86_64=None；需人工判断（以往各轮判断这类差异多为环境或能力差异）
- arm64 与众不同：mincore|ENOMEM|EFAULT（2 个用例，例 10830）；候选 **实现一致性检查**：__do_sys_mincore（mm/mincore.c:306），参数 [0, 1] 的值与提示吻合；边界项 `access_ok`，证据 2，得分 0.4227；静态取值 riscv=None、arm64=None、x86_64=None；需人工判断（以往各轮判断这类差异多为环境或能力差异）
- arm64 与众不同：mincore|ENOMEM|ENOMEM（6 个用例，例 11403）；候选 **实现一致性检查**：__do_sys_mincore（mm/mincore.c:306），参数 [1] 的值与提示吻合；边界项 `access_ok`，证据 2，得分 0.4227；静态取值 riscv=None、arm64=None、x86_64=None；需人工判断（以往各轮判断这类差异多为环境或能力差异）
- arm64 与众不同：mincore|ENOMEM|arg1（2 个用例，例 13118）；候选 **实现一致性检查**：__do_sys_mincore（mm/mincore.c:306），参数 [0] 的值与提示吻合；边界项 `access_ok`，证据 2，得分 0.4227；静态取值 riscv=None、arm64=None、x86_64=None；需人工判断（以往各轮判断这类差异多为环境或能力差异）
- arm64 与众不同：mlock2|arg2|ENOMEM（1 个用例，例 11207）；候选 **实现一致性检查**：follow_huge_pud（mm/gup.c:671），参数 [0] 的值与提示吻合；边界项 `pud_pfn`，证据 2，得分 0.3869；静态取值 riscv=nonconst、arm64=undefined、x86_64=nonconst；需人工判断（以往各轮判断这类差异多为环境或能力差异）
- ……另有 34 条，见 unified.json

### 动态发现但静态归因不对或没有静态来源

（无）

## 调用上下文

动态确认 0、动态检查通过 0、转人工 1、动态发现但静态归因不对或没有静态来源 0。

### 动态确认

（无）

### 动态检查通过

（已有数据没有逐条记录“检查了但没差异”的项）
（无）

### 转人工

- 当前版本执行上下文静态标记 30584 条（S 10760、I 9736、R 10088）。动态：三个调试内核跑完 8107 个用例各 3 次，用例阶段告警 0 条，没有触发任何标记；启动阶段只有 dbg_arm64 的一条与跨架构无关的跟踪事件格式告警。原来那一轮从中抽 40 条人工核对：疑似真问题 0、不是 38、判断不了 2

### 动态发现但静态归因不对或没有静态来源

（无）

