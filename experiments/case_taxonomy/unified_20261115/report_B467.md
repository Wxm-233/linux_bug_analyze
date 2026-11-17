# 统一报告：B467（修复前、修复后内核）

## 实现一致性（效果依赖）

（本树没有这类检查的数据）

## 类型一致性

动态确认 4、动态检查通过 0、转人工 0、动态发现但静态归因不对或没有静态来源 6。

### 动态确认

- 用例 15743：`perf_event_open` t:0 s:self i:0 f:neg i:0（b467_pre 返回 EINVAL；b467_fix 返回 ENOENT；b467_ref_arm64 返回 ENOENT；b467_ref_x86_64 返回 ENOENT）
  - **实现一致性检查**：结构体字段 struct perf_event_attr|type，改为 0xffffffff（pm1）；比较位置 pmu_legacy_ctr_get_idx（drivers/perf/riscv_pmu_legacy.c:20，架构代码）、perf_event_modify_attr（kernel/events/core.c:3267）、perf_swevent_init（kernel/events/core.c:10282）、cpu_clock_event_init（kernel/events/core.c:11339）（第一候选）
- 用例 15959：`perf_event_open` t:0 s:self i:0 f:neg i:0（b467_pre 返回 EINVAL；b467_fix 返回 ENOENT；b467_ref_arm64 返回 ENOENT；b467_ref_x86_64 返回 ENOENT）
  - **实现一致性检查**：结构体字段 struct perf_event_attr|type，改为 0x93a4d8f（outside）；比较位置 pmu_legacy_ctr_get_idx（drivers/perf/riscv_pmu_legacy.c:20，架构代码）、perf_event_modify_attr（kernel/events/core.c:3267）、perf_swevent_init（kernel/events/core.c:10282）、cpu_clock_event_init（kernel/events/core.c:11339）（第一候选）
- 用例 16010：`perf_event_open` t:0 s:self i:0 f:neg i:0（b467_pre 返回 EINVAL；b467_fix 返回 ENOENT；b467_ref_arm64 返回 ENOENT；b467_ref_x86_64 返回 ENOENT）
  - **实现一致性检查**：结构体字段 struct perf_event_attr|type，改为 0xa6ed8551（outside）；比较位置 pmu_legacy_ctr_get_idx（drivers/perf/riscv_pmu_legacy.c:20，架构代码）、perf_event_modify_attr（kernel/events/core.c:3267）、perf_swevent_init（kernel/events/core.c:10282）、cpu_clock_event_init（kernel/events/core.c:11339）（第一候选）
- 用例 16112：`perf_event_open` t:0 s:self i:0 f:neg i:0（b467_pre 返回 EINVAL；b467_fix 返回 ENOENT；b467_ref_arm64 返回 ENOENT；b467_ref_x86_64 返回 ENOENT）
  - **实现一致性检查**：结构体字段 struct perf_event_attr|type，改为 0x3300fe12（outside）；比较位置 pmu_legacy_ctr_get_idx（drivers/perf/riscv_pmu_legacy.c:20，架构代码）、perf_event_modify_attr（kernel/events/core.c:3267）、perf_swevent_init（kernel/events/core.c:10282）、cpu_clock_event_init（kernel/events/core.c:11339）（第一候选）

### 动态检查通过

（已有数据没有逐条记录“检查了但没差异”的项）
（无）

### 转人工

（无）

### 动态发现但静态归因不对或没有静态来源

- 用例 3356：`perf_event_open` t:0 s:self i:0 f:neg i:0（b467_pre 返回 EINVAL；b467_fix 返回 ENOENT；b467_ref_arm64 返回 ENOENT；b467_ref_x86_64 返回 ENOENT）
  静态归因不对：第一候选 **不归类**：perf_event_alloc（kernel/events/core.c:12270），参数 [2] 的值与提示吻合；边界项 `cpu_to_node`，证据 1，得分 0.285；静态取值 riscv=None、arm64=None、x86_64=None
- 用例 5878：`perf_event_open` t:1 s:self i:0 f:neg i:0（b467_pre 返回 EINVAL；b467_fix 返回 ENOENT；b467_ref_arm64 返回 ENOENT；b467_ref_x86_64 返回 ENOENT）
  静态归因不对：第一候选 **不归类**：perf_event_alloc（kernel/events/core.c:12270），参数 [2] 的值与提示吻合；边界项 `cpu_to_node`，证据 1，得分 0.285；静态取值 riscv=None、arm64=None、x86_64=None
- 用例 6226：`perf_event_open` t:0 s:self i:0 f:neg i:0（b467_pre 返回 EINVAL；b467_fix 返回 ENOENT；b467_ref_arm64 返回 ENOENT；b467_ref_x86_64 返回 ENOENT）
  静态归因不对：第一候选 **不归类**：perf_event_alloc（kernel/events/core.c:12270），参数 [2] 的值与提示吻合；边界项 `cpu_to_node`，证据 1，得分 0.285；静态取值 riscv=None、arm64=None、x86_64=None
- 用例 8066：`perf_event_open` t:0 s:self i:0 f:neg i:0（b467_pre 返回 EINVAL；b467_fix 返回 ENOENT；b467_ref_arm64 返回 ENOENT；b467_ref_x86_64 返回 ENOENT）
  静态归因不对：第一候选 **不归类**：perf_event_alloc（kernel/events/core.c:12270），参数 [2] 的值与提示吻合；边界项 `cpu_to_node`，证据 1，得分 0.285；静态取值 riscv=None、arm64=None、x86_64=None
- 用例 10129：`perf_event_open` t:0 s:self i:0 f:neg i:0（b467_pre 返回 EINVAL；b467_fix 返回 ENOENT；b467_ref_arm64 返回 ENOENT；b467_ref_x86_64 返回 ENOENT）
  静态归因不对：第一候选 **不归类**：perf_event_alloc（kernel/events/core.c:12270），参数 [2] 的值与提示吻合；边界项 `cpu_to_node`，证据 1，得分 0.285；静态取值 riscv=None、arm64=None、x86_64=None
- 用例 10935：`perf_event_open` t:0 s:self i:0 f:neg i:0（b467_pre 返回 EINVAL；b467_fix 返回 ENOENT；b467_ref_arm64 返回 ENOENT；b467_ref_x86_64 返回 ENOENT）
  静态归因不对：第一候选 **不归类**：perf_event_alloc（kernel/events/core.c:12270），参数 [2] 的值与提示吻合；边界项 `cpu_to_node`，证据 1，得分 0.285；静态取值 riscv=None、arm64=None、x86_64=None

## 调用上下文

（本树没有这类检查的数据）

