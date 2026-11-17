# 第二标注人盲判记录

我按用户要求独立判断 `review_top30.txt` 的 30 个调用点，内核源码固定为 `df2908090cda`。结论为：**可能 0，不可能 30，说不清 0**；每项依据见 `codex_top30.json`。“不可能”只否定该条报告所声称的契约缺失，不代表证明所在函数不存在其他问题。

我没有读取第一标注人的判断、实验 README、主文件夹的交接文档或进度日志，也没有计算标注一致性。除了允许的报告和判据、本目录文件，只通过 `git show`、`git grep` 读取固定提交的内核源码；WSL 脚本按项目要求先加载 `tools/wsl_env.sh`。没有构建、运行内核、联网、安装软件或调用其他模型。

## 事先固定的判据与输入

逐条核对完整源码前，我先写定本目录的 `criteria.md` 并计算 SHA256；没有因本批全部为阴性而修改判据。

| 文件 | SHA256 |
| --- | --- |
| `codex_blind/criteria.md` | `efbc8293371d8eba9bde2c7c8c095e8d45e9b6c38dba2be7d94ae208a169f135` |
| `review_top30.txt` | `bfbd9089a29fb784490ff197ebd13f639eabf617a6d4e0b14f12d2614e841af8` |
| `criteria.md` | `62ac6279d3343d92ab1aba1f353dafdb780cc435d80b1f726262ffbd628c11c7` |
| `criteria_amendment1.md` | `663c22933bb195cd323385b5332d6d5e11152608f9528ebc40460bdc91678f3e` |
| `criteria_amendment2.md` | `5cdc93b829960337f4bbbd29e5539983b2ced34e63f60359c4fcdcba6e370f37` |

上面后三个文件是实验已有判据，其内容由用户明确允许读取。结果中 `k` 和 `loc` 保留报告的原编号与位置，第 30 条的两项 K3 偏离合并判断。

## 需要读上下文才能排除的条目

- **第 1 条**：`early_page_owner_param` 把 `kstrtobool` 的错误返回给早期参数解析框架；`init/main.c:738` 会检查返回值并给出警告。`lib/kstrtox.c:351` 的实现仅在成功分支写出参；`lib/stackdepot.c:132` 的请求操作是设置初始化请求标志。不能只因本函数没有 `if (ret)` 就认定错误被忽略。
- **第 3～14 条**：其中第 3～10、14 条共 9 条是持锁返回的封装或加锁回调，其配对解锁属于调用者或另一回调；第 11～13 条共 3 条在辅助函数内解锁。尤其 `mm/hugetlb.c:149` 的 `spin_unlock_irqrestore` 在是否释放 subpool 的分支之前无条件执行，三处报告都未缺少解锁效果。
- **第 16 条**：`bd = *bdp = malloc(i)` 后立即检查 `!bd` 并返回内存不足。此条在报告窗口后几行就能排除，属于链式赋值没有被识别，而不是分配失败路径不清楚。
- **第 17 条**：`local_softirq_pending` 返回软中断位图。RT 路径在 `kernel/softirq.c:377` 比较传入的刷新前快照与当前值；非 RT 路径在 `include/linux/interrupt.h:601` 直接执行软中断，不依赖这个快照。
- **第 18、19、26、29 条**：判断或状态保证跨函数发生。`pagemap_page_category` 检查空项与 present 状态，`can_gather_numa_stats` 检查 present 及普通页；`mlock_pte_range` 在持锁情况下验证 PTE 后调用步进函数；`page_vma_mapped_walk` 返回匹配目标 folio 且持有页表锁的映射，读取值继续用于批量计算。
- **第 23～25、27 条**：对应布尔赋值中的判断、布尔中间变量、转换为 `softleaf_t` 后的判断，以及 `do-while` 条件；并非实际缺少检查。
- **第 30 条**：缓存刷新后不总要使用清空再安装映射的序列。这里沿用同一物理页，`mm/pgtable-generic.c:60` 明确说明 `ptep_set_access_flags` 用于更新访问位、脏位和放宽写权限，其通用实现在变化时写 PTE 并处理 TLB；`arch/x86/mm/pgtable.c:380` 和 arm64 的封装也提供对应架构操作。报告把其他用途常见的调用序列套到了原地放宽权限的场景。

## 对契约挖掘的看法

我认为多数用法可以帮助定位需要阅读的代码，但本批显示，“同一函数内有没有出现某个语法形式”还不能直接当成接口的语义契约。

K2 需要区分错误状态、普通数据和判断结果。真实例子是：`malloc` 的空指针需要处理，但 `node_distance` 的距离数据可直接参与权重计算，页表转储可直接显示 `ptep_get` 读出的内容。即使确实需要检查，还要追踪链式赋值、布尔派生值、表示转换、返回传播和被调函数中的判断；否则会把已有处理报成缺失。

K3 需要表达跨函数的锁所有权转移，并把辅助函数的解锁效果传回调用点。对页表操作，还需要区分替换物理映射与只修改访问权限：第 30 条的 `ptep_set_access_flags` 已完成本场景需要的更新，不能只按常见接口名字要求另一套序列。

本批 30 条包含 K2 17 条、K3 13 条，其中 12 条 K3 都来自同一个加锁/解锁契约。这些报告之间高度相关；本批未发现阳性，不能据此前 30 条推算全部候选的准确率，也没有覆盖 K1 的表现。我没有修改挖掘器、门槛或排序，后续与第一标注人比较应由拿到两份独立结果的人完成。

## 复核方式与限制

`read_kernel.sh` 仅提供固定提交的只读源码查询，例如：

```powershell
wsl -u root -- bash /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/contract_20261115/codex_blind/read_kernel.sh 'mm/hugetlb.c:129-157,183-194,249-282,6811-6830'
wsl -u root -- bash /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/contract_20261115/codex_blind/read_kernel.sh 'mm/memory.c:3883-3918' 'mm/pgtable-generic.c:60-80'
```

有一条早期源码查询因 Windows 到 WSL 的参数引用使正则中的竖线被解释为管道而失败；我拆开查询并成功重跑。首次格式校验还因 PowerShell 把 JSON 数组整体嵌入另一数组而误报条数，修正校验命令后，实际 30 项全部通过编号、位置、字段、枚举值和非空依据校验；报告与事先固定的盲判判据哈希均未变化。这些是命令问题，没有改变判据或判断结果。

所有结论是静态人工判断，动态验证结果为 `null`；未对各架构及配置逐一运行验证。
