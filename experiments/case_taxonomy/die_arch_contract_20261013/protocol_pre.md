# die原生能力/fallback：真实配置与构建配对协议

2026-10-13，执行前保存。已读案例的因果补证，不是盲测或新缺陷发现。

## 目的与版本

检验相同公共topology/sysfs导出代码，在实际架构配置下是否保留提供者来源区别。固定旧版`555a0ce4558d87d5b97c4321f34b19e051c7b0c1`和修复版`2c4dcd7fd57b20a21b65da04d89c38a7217d79cf`，只从本地Linux Git导出，不修改checkout。政策依据为本次修复确立的原生双宏opt-in，不倒推父版已违反明确ABI禁令。

## 固定矩阵与独立期望

| 真实配置 | 旧版die属性数 | 修复版die属性数 | 预期来源 |
| --- | ---: | ---: | --- |
| x86_64＋SMP＋SYSFS | 3 | 3 | ID及mask均架构原生 |
| s390＋SMP＋SYSFS | 3 | 0 | ID及mask由公共fallback补齐 |
| x86_64＋无SMP＋SYSFS | 3 | 0 | ID原生，mask由公共fallback补齐 |

两版本×三配置，共六个构建单元，不算六个独立缺陷。以该版defconfig为起点，scripts/config显式编辑SMP、SYSFS，olddefconfig后核对实际值。x86使用ARCH=x86_64，s390使用ARCH=s390及s390x-linux-gnu-；无SMP仅固定x86，不以手工-D制造s390配置。SYSFS关闭、注册失败或设备不可用是观察不适用条件，不能据此判断门控正确；本轮不增加SYSFS关闭网格。

## 操作与验收

1. 保存工具版本与Kconfig可达证据；源码归档及各输出目录放WSL专属缓存，源文件来自固定版本。
2. 各配置执行defconfig→编辑→olddefconfig→prepare，保存.config、autoconf及命令/失败日志。相关功能条件以最终Kconfig为准。
3. 用历史Kbuild生成整个`drivers/base/topology.c`的预处理结果（附`-dD -H`），而非替身头。记录真正选中的asm/topology.h、原生/默认宏定义位置、门控的存在性和定义时机。
4. 核对三个属性的声明和两个属性数组引用；原生双宏缺失但公共fallback最终补齐时，不能把最终宏存在当支持证明。以完整预处理源码中的表项验证预期，不复用修复if表达式作为唯一结果。
5. 尝试构建该历史`topology.o`，以目标ELF和符号补充类型/分支事实；不要求完整内核构建。现代工具链适配若必要，仅记录构建选项，不修改历史内核C/头；失败分清工具兼容、配置和实验脚本错误。
6. 保留六单元的完整结果，包括不可达/构建失败；一个独立角色只读复核来源、期望与结果。不得将失败格删除或追加网格来凑通过。

源码与大型预处理/对象留WSL缓存；仓库保存脚本、协议、必要配置头、摘要和有限摘录。历史实验保持原样，不额外建立封存目录。不调用外部模型、不访问密钥、不推送GitHub。

## 边界与停点

本轮只验收真实Kconfig、include/宏来源、公共导出表项和目标对象。没有启动历史内核、观察CPUHP/sysfs文件、读取真实硬件值或验证用户程序损失；预处理通过不能升级为运行复现或检测泛化。六格后停止扩展，保存完整结果及下一项：评估历史内核sysfs运行的工具/启动条件；跨架构检测对照归R5。s390 system emulator当前未安装，先记录可行性缺口，不自动安装大型依赖。

## 首轮后的兼容处理与验收补充

首轮s390两格完成，x86四格均在objtool主机工具构建阶段失败：GCC13的use-after-free和format-truncation警告被历史-Werror升级。保留首轮results/commands和四格prepare失败日志，只重试未完成x86格，加入`WERROR=0`（历史libsubcmd工具支持）及`HOSTCFLAGS=-Wno-error=use-after-free -Wno-error=format-truncation`（历史objtool从KBUILD_HOSTCFLAGS取得）。这些选项只处理主机工具警告，不改公共驱动或架构提供者源码；同一选项用于旧/修复及SMP/无SMP。

事前独立脚本审查补充：PASS须校验实际CONFIG_X86_64/CONFIG_S390和目标ELF64 machine/端序；s390已保存ELF头及实际配置直接补验，不重复成功构建。`functions_or_calls`是文本存在性记录，不能据此声称注册已经执行。
