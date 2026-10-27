# I3C端序配置来源：事前有限开发取证协议

日期：2026-10-10。已阅读修复提交说明，尚未读取本轮父版C/Kconfig，不称盲测。
目标固定为父版7ff730ca458e841dbcdc87f264d7afe3eaed525e，修复线索7a2bccd1a27f0c8fc87e4ed56abd6ea9fa7314a6。

## 范围与额度

只获取八份同父版原物：drivers/i3c/master/mipi-i3c-hci/core.c、Kconfig、arch/Kconfig、arch/arm/Kconfig、arch/arm64/Kconfig、drivers/i3c/Kconfig、drivers/i3c/master/Kconfig、drivers/i3c/master/mipi-i3c-hci/Makefile。
使用一次git cat-file --batch查询八对象，保存请求/完整响应并核对返回blob身份。缺物记录缺失，不补文件。
最多三次同父版git grep：全树Kconfig中BIG_ENDIAN/CPU_BIG_ENDIAN的config/menuconfig声明；全树CONFIG_BIG_ENDIAN引用；全树直接#define CONFIG_BIG_ENDIAN/CONFIG_CPU_BIG_ENDIAN。
每命令原始输出上限2 MiB，超额停止而不截断为证据。退出1的grep只表示定义域零匹配。实际配置、生成输出及仓库外构建未覆盖。
不解封修复patch，不取得新标题样本，不调用项目模型，不编译或执行内核/设备。

## 判准

1. 机器事实分别保存C中配置引用、直接条件文本及所在函数/邻近操作，附版本、blob、SHA和原文行号。只支持可定位的简单形式，复杂表达式/控制流保留不足。
2. 同版Kconfig声明是来源证据；arm与arm64是固定的属性定义例，不以两个架构代替全架构证明。单独符号存在不证明目标分支可达。
3. CPU端序为何与具体操作相关，由人核对控制逻辑及原文；没有硬件/运行证据时只写源码条件关系。来源缺失可以提出需核查候选，不能据此认定编译或运行错误。
4. 生成宏/构建定义检索与实际生成结果分开。全树搜索的阴性只在当前历史版本和被检索域有效，不排除外部-D或生成头。
5. 产出机器事实—人工属性契约—有条件检查/不足卡，保留版本/配置/实际路径等未证前提。不会自动替换成相似名字或自动应用补丁。
6. 本轮不增加确认案例、独立阳性或泛化准确率，原固定12条6/5/1、C1–C4、D2整体、D3和D4/NUMA未完成状态不变。首次发现和两个时间间隔不猜测。

## 验收与收束

保存原物及Git收据、有限可复核事实输出、独立只读审阅、综合和下一停点；更新今日唯一日志及两端待办。证据不足也作为有限任务完成，不临时扩大八文件范围。
支持后下一轮才规划局部配置/模式对照，本轮不将静态事实包装为运行复现。
