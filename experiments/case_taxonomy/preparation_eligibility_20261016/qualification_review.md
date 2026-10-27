# N1.4c.2：准备资格与同对象取证复核

2026-10-16。只读核对本目录 `source_material.json`、`iteration_references.json` 及 `../consumer_preprocessing_20261016/` 既有材料。未访问 API、密钥或 WSL，未编译、运行循环、调用检测器或新增解析器。本角色此前整理过原文包；本次独立于主智能体的程序实现做源码复核，不称独立原文采集、专家金标准或盲测。

两版：旧 `88b604263f3d6eedae0b1c2c3bbd602d1e2e8775`；修复 `a052096bdd6809eeab809202726634d1ac975aa1`。下文行号均为相应 revision 的原文件行号，非 JSON 物理行号。

## 1. Mapper 的有条件分支

`old_s390_map`／`fixed_s390_map` 均为 `arch/s390/kernel/topology.c:96–114` 完整函数。两版共同在101行调用 `cpumask_clear(&mask)`，113行调用 `cpumask_copy(dst, &mask)`。

| 源码条件 | 旧版 | 修复版 | 可核对的调用结构 |
| --- | --- | --- | --- |
| 资格不满足 | 102–103：`!cpu_online(cpu)` → `goto out` | 102–103：`!cpumask_test_cpu(cpu, &cpu_setup_mask)` → `goto out` | clear后跳到112–113的copy，没有经过104行set |
| 资格满足且非HW模式 | 104行set；105–106跳out | 同左 | clear → set → copy；不能说所有资格满足路径都先遇到循环 |
| 资格满足且HW模式 | 107改写局部cpu；108起循环；109按present筛兄弟；111与online集合取交 | 107改写局部cpu；108起循环；109按setup筛兄弟 | 可确认进入循环及其源文；有界前向路径方法若不支持循环，应停在循环前沿，不能假定完成循环后自然获得copy的效果 |

这里的clear/set/copy首先是调用事件。helper源码可辅助人工审查，不能据函数名把程序尚未建模的集合效果自动认定为已证明。

## 2. Updater、遍历资格与字段实参

`old_s390_update`／`fixed_s390_update` 分别来自两版Git对象，均为 `arch/s390/kernel/topology.c:251–287`，本材料内正文相同：

```text
254  声明 updater 自己的局部 cpu
256  for_each_possible_cpu(cpu)
257  topo = &cpu_topology[cpu]
258  cpu_thread_map(&topo->thread_mask, cpu)
272  for_each_online_cpu(cpu)
```

第一遍的调用将该次迭代索引对应的 `cpu_topology[cpu].thread_mask` 地址传给mapper的dst。第二遍online循环读取相关掩码并维护booted_cores等信息，不能将其online资格误当第一遍thread_mask写入入口。

`iteration_references.json` 保存两版 `include/linux/cpumask.h`：95行将 `cpu_possible_mask` 定义为 `&__cpu_possible_mask` 的常量指针视图；788行将 `for_each_possible_cpu(cpu)` 写为 `for_each_cpu((cpu), cpu_possible_mask)`。`for_each_cpu`有两个原定义：

- 119行 `#if NR_CPUS == 1` 分支，178–179行固定遍历cpu=0，使用`(void)mask`，没有检查mask内容。
- 186行else分支，240–243行通过`cpumask_next(cpu, mask)`与`nr_cpu_ids`推进，292行结束条件块。

因此，不能把未选择条件的宏原文一概说成“按possible位图枚举”。既有consumer四格记录NR_CPUS=4和实际配置；这支持所查配置语境，不等于本轮已经对updater的实际循环执行、目标位或外部迭代器实现完成取证。

## 3. 四种证据必须分开

1. **同名变量**：启动函数、updater、mapper、getter各自的cpu不是同一局部声明；updater无CPU形参。mapper107行还会将自己的cpu改为组基值，dst仍是调用时传入的地址，不能用改写后的同名cpu重建原目标身份。
2. **有条件的源码对象映射**：当第一遍迭代索引为目标T时，257–258行把`&cpu_topology[T].thread_mask`传入dst；113行使用该dst。consumer的两版s390配置展开getter也返回`&cpu_topology[cpu].thread_mask`。这是连接写端字段和读端字段的依据，但仍需绑定同一目标、revision/config和外部声明实体；不是通用别名／链接／并发证明。
3. **实际覆盖目标**：要断言该次更新准备了启动目标T，还需要当前调用实际到达、T确实被所选循环枚举、此前迭代没有阻断／改变条件等证据。source中的完整循环和目标变量拼写不能替代这些运行或已审前提。本次未执行循环。
4. **helper效果**：两版头文件原文相同。342–345行test调用`test_bit(cpumask_check(cpu), cpumask_bits(...))`；388–391行clear调用`bitmap_zero(..., nr_cpumask_bits)`；574–578行copy调用`bitmap_copy(..., nr_cpumask_bits)`。这些是委托关系原文，不是对全部位图原语、有效索引、覆盖范围与稳定性的实现证明。cpu_online也保留893–896行NR_CPUS>1分支和925–928行else，不能按名字无条件当online位图测试。

## 4. 通知边界与公共消费者能确认什么

`old_s390_start`在`arch/s390/kernel/smp.c:905`通知，910行online，911行更新；`fixed_s390_start`在906行set setup、907行更新、908行通知，913行online。可以确认源码调用顺序，不能单凭更新调用已在前面就声称目标集合已经正确。

`common_notify`的`kernel/cpu.c:1265`进入回调范围。`common_starting`的`kernel/sched/core.c:8836`调用core启动入口。`common_lock`在242行取得getter结果，245行保存IRQ状态，246–247行遍历集合并使用对应runqueue锁。

consumer既有四格材料明确保留了实际展开getter、锁循环及外部`cpumask_next`声明：s390 getter指向`cpu_topology[cpu].thread_mask`，x86是包含`cpu_sibling_map`与per-CPU偏移的表达式；其不同原始存储不能直接要求字节或布局相同。`cpumask_next`在这些所选翻译单元只有声明，不能把其他条件分支的inline实现移来冒充当前实现。

共同getter取得指针与后续循环读取内容是两个位置。该目录记录`control_flow_proved=false`、`runtime_content_proved=false`，精确消费内容和区间稳定仍未知；本次没有读取或借用runtime结果补成证明。

## 5. 复核结论

材料支持两版资格守卫、调用顺序、字段实参与配置展开读端之间的**有条件源码联系**，未见这些记录之间的阻断性矛盾。不能升级为实际循环必达、helper效果已建模、首次使用时集合必正确或全路径契约满足。应继续保留条件前提、未支持循环和未知输出；本次新增确认缺陷、独立检出、模型请求与运行均为0。
