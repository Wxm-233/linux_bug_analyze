# CPU导出：目标文件、镜像与发布观察连接

2026-10-27。承接 cpu_source_policy_20261027。新工作是四份孤立object编译、四个镜像载荷提取/完整比较及有限链接关系核对；历史运行只复核，没有新guest或完整内核构建。

主要结论见 [method_card.md](method_card.md)、publication_results.json、bridge_evidence_final/ 和 controls.json。linked_graphs_final/ 为含initcall/CPUHP连接的最终图；graph_initial/、linked_graphs/、graph_results.json 保留最初仅到注册callback的图，不计新内核实验。

## 结果

| 配置 | 冻结CPP复现原object | 镜像载荷匹配 | die表项 | 旧CPU0/1文件观察 |
| --- | --- | --- | ---: | --- |
| old_x86_64 | 完整字节相同，含objtool | 是 | 3 | 三项均可读 |
| fixed_x86_64 | 完整字节相同，含objtool | 是 | 3 | 三项均可读 |
| old_s390 | 完整字节相同 | 是 | 3 | ID=-1、各CPU单项mask/list |
| fixed_s390 | 完整字节相同 | 是 | 0 | 三项均ENOENT，普通拓扑项可读 |

每个启动镜像SHA与旧构建/启动收据一致。x86载荷为剥离符号/comment后的ELF，s390为按原规则移除comment/vmlinux.info后的原始binary；分别17557616、3867904字节。载荷从实际boot_image内gzip流提取，均与转换后的完整vmlinux字节相同。

链接核对涵盖完整属性组、两张表、属性名及回调、读取函数、sysfs注册回调、CPUHP设置、initcall项。73个函数实体和77个数据实体按四构建重复计数；命名目标/字符串重定位逐项验证，其余字节全部比较，不是只遮掉重定位字段。x86 PREL32 initcall为4字节，s390为8字节，按原object中的完整单项section取得，未假设两者相同。两级thin archive各含准确的topology.o成员，成员命令仅保存，未执行其中的删除或构建指令。

八个历史CPU样本的 `published_any => compiled_any && linked_any` 必要关系均满足，消费期限和whole_path仍不足。原s390两格另复核16项已有默认值/CPU列表读回；不是新增运行或新正常样本。未读取的package_cpus不补造观察。

13项构造错误全部拒判：9个在内存副本中改变的真实ELF字节（架构、端序、指令、回调、表项、组字段、名字、initcall、emitter重定位），2个身份错配、1个缺观察、1个“无发布但证据未知”审核控制。记录见controls；原历史文件未改。

## 自动化与边界

公共 contract_protocol.py 保持原SHA，新增发布关系的8次核心判定及1次不足控制，共9次核心调用。源码政策仍沿用上轮人工审核，未将新事实提升为历史文本来源，旧runtime/binding文件完全不改。初次桥接程序遇到Windows索引反斜杠未归一化的KeyError，在生成契约前停止，代码及失败原因保存在bridge_attempt1/；修正路径归一化后通过，不算Linux缺陷或编译失败。

同object/同镜像不足以唯一恢复历史源码写法；物理拓扑真值、首次内容消费、初始化保证及并发生命周期仍不足。二进制链接地址域不能当实际客体地址。initcall关系是静态工件证明，实际CPUHP执行顺序没有新探针。本轮0模型调用、0新内核构建/启动、0新Linux缺陷，独立正例/正常0/0。

限定来源/用途政策方法已形成 [method_card.md](method_card.md)；家族和独立评价未完成。横向比较见mechanism_comparison.json。下一项核CPU身份与启动范围的方法和实际运行补证成本，保留本案例开放缺口。

## 工件与环境

- objects/：4份新object、原object、原命令、编译/objtool日志与SHA收据。
- images/：启动镜像与vmlinux完整副本、实际/预期payload、gzip流、构建规则原文及收据。
- archive_membership/：两级thin archive列表及只读收集到的原构建命令。
- bridge_evidence_final/：来源、链接图、镜像身份与历史观察的分层连接。
- publication_inputs/results、controls、delivery_manifest：显式契约、结果及归档身份。

WSL缓存仍/root/.cache/linux-bug-analyze/die-contract-20261013/，源码Git仍/root/repos/linux；当前代码和新输出均位于Windows挂载工作区。原配置、autoconf、命令、object、vmlinux、镜像的采集前后SHA一致。脚本拒绝覆盖原件；重现须使用新轮次路径或新输出目录，保留已完成的原记录。
