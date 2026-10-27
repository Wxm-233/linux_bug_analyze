# 已保存首轮结果的只读后置复核

2026-10-11，审阅身份 `/root/override_result_audit`。结论：通过六项固定合成对照的首轮结果完整性与结论含义复核，无阻塞发现。

本次只读取保存的 JSON、原始字节、冻结源码与结果说明，以文件 SHA-256 和独立 JSON 字段比较核对；未运行历史函数、runner、比较脚本、Git、模型、make、QEMU 或内核。仅新增本目录的 `result_review.json/md`。全部事前文件，包括 `pre_review.json`，保持不变。

## 身份与首轮原流

`execution_pre.json` 的 SHA-256 为 `c2fd00c7962bdec3f1f23d89fbec1bc8dfca958561980bc61de8c6cea82ae711`，所列 17 项文件的实际 SHA-256 全部与冻结值相同；源物、原 oracle 与 adapter 均未发生变化。

保存收据 returncode=0、exception=null，stdout 为 6607 字节，stderr 为 0 字节；两原流的实际 SHA-256 均与收据一致。stdout 解析后的 JSON 与 `observations.json` 结构和值完全一致。收据记录一次离线 runner、零内核/QEMU 执行；首轮防重跑 guard 与冻结代码一致。本次文件审阅只支持这些保存材料记录的运行身份，未独立证明材料外不存在未记录进程。

## 独立预期与结果

六行 ID 和顺序与 inputs、原 oracle、adapter 一致。每行 8 个 adapter 预期字段及 5 个未知状态字段全部一致，共 78 项；另以保存观察映射回原 oracle 的 11 个语义字段，核对 66 项全部一致。原 oracle 的 SHA 与 adapter 引用和冻结清单一致；静态读取原函数也支持其合并方向、覆盖、冲突与子集规则。比较文件记录的 6/6、78、4/2/2 与此次只读核对一致。

| row ID | 原 arch CPU | user CPU | 最终 request CPU | 合成 output CPU | 请求满足 | 覆盖政策复核候选 |
| --- | --- | --- | --- | --- | --- | --- |
| parent_user_y_output_y | 未含此项 | y | y | y | true | false |
| parent_user_n_output_n | 未含此项 | n | n | n | true | false |
| parent_user_n_output_y | 未含此项 | n | n | y | false | false |
| revision_user_y_output_y | y | y | y | y | true | false |
| revision_user_n_output_n | y | n | n | n | true | true |
| revision_user_n_output_y | y | n | n | y | false | true |

全部最终 CPU 请求等于 user 值，合并请求和合成输出均保留其他四项 provider 请求为 y。父版三行只新增 CPU 请求；提交 user=y 行没有值改变；提交 user=n 两行将原 y 改为 n。后两行的合并前同名异值是诊断性冲突，仅形成“核实覆盖是否合法”的复核候选，不能据此确认两个缺陷。无冲突也不证明环境正确。

已保存 `02_kunit_kernel.py` 第 115–118 行只 parse arch、merge base、return，没有调用冲突检查或在该位置拒绝覆盖；第 300 行将合并请求写回，后由第 280–284 行按该请求做 subset。源码仅静态读取，没有执行。原 `03_kunit_config.py` 第 72–74 行解释 user 优先，第 52–61 行解释显式 CPU 输出须与最终请求同值；本轮没有测试缺省输出的 n 分支。

## 未知状态与说明复核

六行均保持 `environment_required_CPU_BIG_ENDIAN=null`、`override_legality=unknown`、`policy_violation=null`、`actual_generated_kernel_config=unknown`、`Kconfig_reachability_or_runtime_certified=false`。合成输出没有升级为真实 .config、实际端序或启动证据。

只读复核 `synthesis.md`、`mechanism_card.md/json` 与 `checkpoint.md` 后，表格、计数和边界说明均与保存结果一致。E/R/S 区分、默认/用户选择/硬性要求区分、验证位置与未知首个真实消费者区分均保留；P2/P4 交接说明没有增加第五类，也没有声称新完成 P3 时机或 P1 范围验证。六条记录仍是同例合成对照；原 12 条 6/5/1、新确认 0、独立阳性 0 及整体未完成口径未扩大。下一项 NUMA 材料核对只被列为待办。

可结束本次有限配置覆盖子任务。真实环境权威、覆盖政策、配置可达性、实际消费者与独立检出证据仍需另行取得；此审阅不替代这些裁定。详细文件摘要与逐行比较存于 [结构化复核](result_review.json)。
