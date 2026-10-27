# I3C配置谓词依据与局部模式对照：事前协议

2026-10-11。本例已读提交说明和父版C，属于知情开发，不是新样本盲测。
父版固定7ff730ca458e841dbcdc87f264d7afe3eaed525e。上一阶段38文件封存SHA=9e0e7c7ff9c69bb5f80de83c5992361b012bc4a39fdd81366d5b40592fdef6f2。

## 有限补证

只取同版include/linux/kconfig.h、arch/arm/mm/Kconfig两份原物，一次git cat-file --batch。一次git grep允许行首空白、精确BIG_ENDIAN/CPU_BIG_ENDIAN声明；仍只在Kconfig文本定义域内，不声称完整语言/生成来源已求解。总2Git命令，完整输出每命令上限2MiB，缺物/超额停机不换材料。旧八物料不重取，不读取修复patch。

## 支持后的局部对照

先核对IS_ENABLED原定义及ARM CPU属性，再锁源码投影、fixture配置、独立oracle与runner后编译/运行。
最多16格：两谓词（原CONFIG_BIG_ENDIAN与对照CONFIG_CPU_BIG_ENDIAN）×CPU端序注入BE/LE×数据模式bit初態0/1×写接受/拒绝。
仅使用原core.c第663–685行的模式片段及必要常量；原实现原样保存，对照仅替换配置引用。片段末尾追加局部返回0，不能解释为完整初始化成功。现有写后回读与-EOPNOTSUPP保留。
配置fixture中CONFIG_BIG_ENDIAN、CONFIG_BIG_ENDIAN_MODULE与CONFIG_CPU_BIG_ENDIAN_MODULE都未定义；BE定义CONFIG_CPU_BIG_ENDIAN=1，LE不定义。由同版kconfig.h解释，不手写IS_ENABLED替身。generated/autoconf.h是测试fixture，不是实际内核生成结果。
寄存器测试替身：只有数据端序bit控制是否匹配注入CPU属性；write接受时存新值，拒绝时保持原值。其余位带固定非零模式，应始终保持。该模型不是设备规范或设备行为证明。
先保存独立oracle的selector、最终bit、写读次数、局部返回值和成功契约；运行代码只报告观测值，不以自身行为生成预期。错误返回与未执行不能当配置正确通过。
本次编译运行限定WSL本机用户态，CPU端序是宏注入，不是ARM或大端目标二进制，不检测实际数据传输。最多4个编译变体、每变体一次4输入运行；编译失败保存结果，不无限重复，最多一次有明确原因的修复重试且保留首次材料。

## 验收与边界

核对新两物料/旧源码身份与引文、先锁后运行、16格与独立预期、无关位和失败路径。独立来源审阅及投影审阅，保存原始stdout/stderr/编译命令与结果。
新增确认和独立阳性0，固定12条6/5/1、C1–C4、D2整体、D3全部裁定、D4/NUMA不勾选。实际config/autoconf、外部-D、Kconfig全路径、控制寄存器规范、消费者和真实设备仍未知。
更新10/11唯一合并日志、两端待办与下一停点，不扩大标题池/模型筛选，不查余额，不改Word或推送GitHub。
