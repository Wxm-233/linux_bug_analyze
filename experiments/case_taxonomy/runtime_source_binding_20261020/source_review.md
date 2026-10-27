# N2.16：归档运行配置内的die直接来源复核

2026-10-20，arch_check_review。独立助手的源码复核，不是人类专家金标准或自动契约推导。仅阅读本轮`cached_source_packet.json`、N2.15已读材料、原runtime runner及必要四份归档配置/回执；未调用WSL、外部模型或网络，未预处理、编译、启动及补取其他源码。

## 1. 身份与可支持的证据层级

短包含两版各四份完整直接源：公共topology头、x86/s390架构topology头及公共driver，共8份。复核按`text`的UTF-8字节重算SHA256与Git blob，8份均与包内身份一致；各run的4条source_keys又与该run既有`build.json.source_identity`的对应blob一致。这支持将**这些完整直接文件**绑定到四个已登记版本，不表示所有传递依赖或有效宏都已核对。

四run的当前缓存`.config`与归档SHA相同；实际均为`SMP=y、SYSFS=y、NR_CPUS=4`，x86为`NUMA=n`，s390为`SCHED_TOPOLOGY=n`。它们不能借用先前六格defconfig预处理的有效宏事实。autoconf当前缓存与归档字节一致，关键键与配置一致；原runner在`:142`复制config、`:150–151`记录镜像与release、`:174–175`记录config摘要并复制autoconf，但没有独立历史autoconf摘要。四份当前`.topology.o.cmd`也没有独立历史摘要，不能按本次新算的SHA反向认证它在历史启动时未变化。

当前命令记录的首选include路径指向对应版本的目标架构头，direct_dependency_mentions包含目标架构头、公共头和driver。命令中没有直接`-D/-U topology_die_*`或`TOPOLOGY_DIE_SYSFS`；但有`-include compiler-version.h/kconfig.h/compiler_types.h`，只核命令不能说明这些文件及其间接内容没有相关影响。它们是当前缓存的路径/参数旁证，不是原runtime翻译单元的展开记录。

## 2. 完整直接源的guard、顺序与局部覆盖

两版x86头相同blob：`arch/x86/include/asm/topology.h:25–26`为文件guard；`:103`先包含`asm-generic/topology.h`；`:111`直接定义`topology_die_id(cpu)`为`cpu_data(cpu).cpu_die_id`，位于NUMA分支结束`:101`之后，不受NUMA条件限制；`:116–118`在`CONFIG_SMP`下直接定义mask为`per_cpu(cpu_die_map,cpu)`。其后仍有`:169–170`的条件`asm/percpu.h`和`:199–200`的`SMP && X86_64`条件`asm/cpufeature.h`；后者在这两份x86配置下启用。直接头本身无相关`#undef`，没有后续直接重定义。

两版s390头同blob：`:2–3`为文件guard；`:5–6`包含cpumask/numa；`:11–62`是SCHED_TOPOLOGY分支，两分支均无die ID或mask直接定义；`:99`仍包含未展开的`asm-generic/topology.h`。因此可以确定**这份完整s390头没有直接die定义**，不能仅由这一点确定整个include闭包没有定义或实际getter必为公共回退。

公共头两版均在`:27–28`设文件guard，`:30–35`包含六个公共依赖，`:36`包含架构头。old`:186–188、204–206`分别在缺宏时提供`-1`与`cpumask_of(cpu)`；fixed`:190–192、208–210`同理。fixed额外在`:183–185`、回退之前检查两宏并设置`TOPOLOGY_DIE_SYSFS`。公共头在架构include返回后没有新的include，也没有相关undef或后续重定义；但这个局部事实不覆盖前述间接头和较早包含路径。

driver两版`:11–15`依次include mm/cpu/module/hardirq/topology；这些前置头可能已通过文件guard参与topology加载。old三项声明及表项无die门控；fixed在`:48、75、110、129`用`TOPOLOGY_DIE_SYSFS`保护声明/表项。driver本体在这些include之后没有新的include、相关undef或宏重定义。该局部连接支持公共消费用途，却不重建较早include顺序。

## 3. 四个run的直接来源候选

以下为**研究者根据直接源和实际配置提出的条件候选**，不是可直接写入runtime `native_id/native_mask`的已证布尔。共同前提为：目标头按正常guard被加载；未展开的强制/传递include没有改变相关宏、文件guard或配置；到公共消费处没有其他定义覆盖。

| run | 直接ID候选 | 直接mask候选 | 来源与guard依据 | 当前有效TU结论 |
| --- | --- | --- | --- | --- |
| old_x86_64 | x86架构定义 | x86架构定义 | 相应old blob，`:111`及SMP启用的`:118` | 两项unknown |
| fixed_x86_64 | x86架构定义 | x86架构定义 | 相应fixed blob，同两处定义；固定政策在公共fallback前 | 两项unknown |
| old_s390 | 公共fallback | 公共fallback | s390完整直接头无定义；若进入公共ifndef则`:187、205`补齐 | 两项unknown |
| fixed_s390 | 公共fallback | 公共fallback | 同上；公共ifndef在`:191、209`补齐，双宏政策检查在其前 | 两项unknown |

可升级的仅是：从“借另一配置猜测”推进到“本run版本/blob、实际SMP条件、完整直接定义及局部顺序相符的来源候选”。s390的SCHED_TOPOLOGY=n并不妨碍这个直接头缺定义的结论，但也不能把该开关直接等同于die能力开关。相同ISA的其他配置不补齐本run证据。

## 4. 是否足以解除unknown

**现有短包不足以解除runtime有效宏来源的unknown；建议按计划保留core不足并停止同例追源。** 已有材料未给出本runtime TU的有效定义序列，或覆盖所有可能相关入口的经审核闭包。具体缺口是：强制include及其传递内容；driver前置公共头及文件guard的实际首次加载；x86定义后的条件include；s390尾部asm-generic；以及当前cmd/autoconf没有独立历史摘要的归属强度。当前依赖命中和源码局部无undef降低歧义，但不等价于证明这些缺口为空。

不需要为本轮再扩大整树搜索或重新-E以凑四项满足。记录条件来源候选、共同前提与未证项即可；若以后主动选择更强取证，应另登记其范围和历史/当前重建差别。既有六格`.i`不是本runtime配置，既有文件读值也不能唯一反推出宏来源，所以二者均不能补上当前闭合。

即便以后来源闭合，也只说明编译选择：不证明getter实际被调用、数据已经初始化、物理die拓扑真值、读取全程稳定、CPU对象/生命周期全正确或首次消费期限。已核四次归档的open/read/ENOENT可继续保持自身运行事实，不能借它们把来源候选变成确定值。父版双原生政策关系仍是反事实情景，旧版ABI规范不足不变；修复版表项门控也不能代替实际发布证据。

本轮新增事实是有界来源身份与guard绑定；不是新缺陷、新运行、自动推导成功或独立泛化。两机制收束时宜明确分列：程序核验的档案/局部关系、研究者提供的义务和来源候选、仍未闭合的有效TU及运行全链。
