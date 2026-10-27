# 覆盖边界实验的方法独立审阅（执行前建议）

审阅者：独立方法审阅子任务。日期：2026-10-11。读取旧阶段 checkpoint/synthesis 与已保存 `03_kunit_config.py`、`02_kunit_kernel.py`；没有运行历史函数、Git、构建或 QEMU。旧阶段均保持只读。本记录写入新阶段 `audit_method/`，在新 protocol/runner/输入尚未出现时保存，不替代其预冻结。

## 可检验的命题

六项仅检验非空用户请求加入架构请求后的有效要求，及已保存真实 `is_subset_of` 对合成输出的满足性。`LinuxSourceTreeOperationsQemu.make_arch_config`（已保存 kernel 文件第115–118行）先解析架构字符串，再 `merge_in_entries(base_kunitconfig)`；`merge_in_entries`（已保存 config 文件第72–74行）按键赋值。因而同键用户值覆盖架构默认值。

对于父/提交两版，`user y → output y`、`user n → output n`、`user n → output y` 的有效 CPU 要求均依次为 y、n、n；预期 subset 均依次为 True、True、False。提交版两项 user n 相对原 arch y 存在同键值差异；父版没有显式 CPU 项，加入 user 请求不构成这项冲突。为让输出仅改变端序项，合成输出应保留其他架构请求。

## 必须保持的区分

1. 架构默认、用户请求、合并后的有效要求、合成输出、环境要求与覆盖合法性分别记录；环境要求/覆盖政策仍为未知。
2. `make_arch_config` 不调用 `conflicting_options`，不能把实验 wrapper 为审计显式调用的冲突列表描述成原流程的门禁。已保存 kernel 文件第189行的冲突检查仅属于多用户文件合并。
3. 合并与 subset 成功只能说明最终请求被满足；不能说明原架构默认仍被保留、配置请求完整、覆盖合法或实际运行正确。
4. 补丁新增 `CONFIG_CPU_BIG_ENDIAN=y` 不能成为强制环境要求的唯一依据。base 优先本身不构成缺陷，冲突数也不是缺陷数。
5. 合成输出不代表可生成的真实 `.config`，不证明 Kconfig 依赖可达、构建成功或运行后果。六项是同一已读实例的机制开发，不是独立迁移、盲测或真实正常内核。

## 执行前审查点

- 六项固定为两版本 × 三种请求/输出；不得根据结果追加、替换或重跑。
- provider 从保存源物提取字符串；runner 不导入历史 kernel/QEMU 主流程，只使用已保存 config 模块的真实解析、合并、subset（可选冲突观测）。
- 每项采用独立对象，先记录合并前 arch/user，再记录最终请求与输出，防止循环共享变异。
- 合成输出覆盖完整 arch 请求，仅 CPU 项依据协议替换；非 CPU 要求应有固定不变核对。
- runner/输入/源物哈希与独立预期在唯一一轮之前冻结，观察值与预期分文件，运行后比较不反写预期。
- 计数与结论保持：真实配置生成/构建/启动为0；新确认、独立阳性为0；原12条6/5/1与整体 D2/D3 口径不扩大。

等待新阶段 protocol/runner/输入后做只读预审；执行后只读复核原始输出、比较与 synthesis。
