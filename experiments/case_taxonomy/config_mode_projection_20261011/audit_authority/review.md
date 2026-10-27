# 同版配置宏与ARM端序属性补证独立审阅

2026-10-11。仅审阅本阶段保存的2原物、声明检索和收据，以及上一阶段同父版core.c/ARM/ARM64 Kconfig；只写audit_authority。没有Git取证、patch读取或C执行。提交说明已知，仍为开发验证。

## 身份与协议

新2原物的字节、SHA-256、Git blob SHA-1通过；batch响应导出逐对象一致。2份收据的stdout/stderr摘要与字节通过，请求摘要通过。复用的core.c、ARM根、ARM64文件仍与旧清单一致，同为7ff730ca458e841dbcdc87f264d7afe3eaed525e。事前协议与取证脚本摘要仍吻合冻结记录。新增允许行首空白的查询输出与旧查询逐字节一致。

## 这次补齐了什么

include/linux/kconfig.h第13–26、41–43、50–57、68–73行提供实际IS_ENABLED宏链：IS_BUILTIN使用__is_defined，IS_MODULE检查对应_MODULE选项，再由__or组合。因此在已声明fixture中，旧CONFIG_BIG_ENDIAN和其_MODULE均未定义时，旧谓词为0；CPU宏=1且CPU_MODULE未定义时，候选谓词为1；CPU宏和CPU_MODULE均未定义时，候选谓词为0。这是由同版宏展开可以推出的条件结论，尚不是运行观测，不覆盖任意外部宏值。

第5行仍include generated/autoconf.h；真实历史生成文件未取。本轮fixture中的生成头是试验输入，不能据此声称真实内核构建一定如此。第7–11行还按CPU宏是否存在选择__BIG_ENDIAN/__LITTLE_ENDIAN，为CPU属性提供同版关联证据，但ifdef存在性与IS_ENABLED在任意错误取值下不应混淆。

ARM子Kconfig第740–748行实见CPU_BIG_ENDIAN bool，依赖ARCH_SUPPORTS_BIG_ENDIAN和!LD_IS_LLD，help明确大端内核需板级与芯片/处理器相关准备。第1113–1117行定义ARCH_SUPPORTS_BIG_ENDIAN能力；第750–762行进一步区分BE8/BE32。本轮可将先前“根文件source子文件+grep定位”补成实际子文件声明与局部条件证据，但没有生成或验证一个可构建的ARM配置。ARM64旧物choice仍提供CPU数据访问端序定义，也不能当作实际已选配置。

## 仍然不能升级的结论

允许前导空白的精确Kconfig声明查询有15项CPU_BIG_ENDIAN、无BIG_ENDIAN匹配，排除了上轮查询的缩进漏匹配限制，但仍是限定文件模式/名称/文本语法的检索，不是完整Kconfig语言求值。旧直接宏定义查询也不代替生成配置或编译-D来源检查。

真实autoconf、实际driver构建可达及宏绑定、寄存器规范、模式位可写条件和PIO/DMA消费者未补齐。不能因此笼统称“旧实现实际运行恒走else”，也不能说新谓词已对真实硬件证明正确。

## 源码片段可投影的条件

旧core.c第663–685行可在明确模型下作局部控制逻辑对照：保留原始读写、回读和-EOPNOTSUPP；候选只替换配置引用。附加return0仅表示片段完成，不表示整个i3c_hci_init成功。

配置fixture必须逐项确定旧宏、旧_MODULE、CPU_MODULE均undef；CPU=1或undef由同版helper解释。不能手写IS_ENABLED替身。寄存器write接受/拒绝、控制bit与注入CPU属性的对应关系属于预先声明的试验假设。冻结片段、fixture、独立oracle、runner后再运行，并记录实际进入分支、读写次数、错误返回及无关位保持。未执行和拒绝设置不能当成功匹配。

本机用户态二进制只是以宏注入CPU属性，不是ARM执行或大端目标二进制，不测试payload实际字节传输。即使局部模型的旧/候选结果不同，也只验证该模型下控制逻辑与配置来源机制，不增加独立未知缺陷检出或真实内核/设备复现。

## 分类状态

子系统I3C/MIPI HCI可确认。P2配置来源/数据模式是有来源的机制候选；架构属性到公共驱动模式的纵向关系为暂定解释。触发架构、横纵统计值及错误引入侧仍unknown；首次发现和引入时间仍unknown。局部试验不使用作者日期替代首次发现，不计算两个时间间隔。新增确认、独立阳性均维持0。
