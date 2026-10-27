# N2.11 命令计划独立审查（执行前，2026-10-18）

审查对象为 `command_plan.json` SHA-256 `fb174a23f1126e899099839d503af7148f62678e681a0e6b5ec4d9f8c07ce6af` 和 `probe_compiler.py` SHA-256 `cc62b5b01b890164ebf1d7b84b4060dd5dba0b34ac97c853828bf8a8dbcf565e`。重算脚本/协议摘要与计划相符，两份既有 manifest 的文件摘要与登记相符；两个 profile 的 `.i`、`.config`、revision 及编译器身份与协议逐项一致。审查时 `raw/` 尚不存在，计划记录 0 次编译器调用。本审查不执行编译。

实际原命令各只有一个已知 `kernel/sched/core.c` 输入及 `-c -o kernel/sched/core.o`。s390 的 99 个原 argv、x86 的 97 个原 argv 仅发生六组登记变更：将编译器名换为已安装绝对路径；删除 `-Wp,-MMD,kernel/sched/.core.o.d`；将 `-c` 改 `-S`；将旧 `.o` 输出改为各自 `raw/<profile>/core.s`；用精确 SHA 的旧 `.i` 代替原 `.c` 并在它前面放 `-x cpp-output`；追加显式落在同 profile raw 目录的 original/gimple dump 路径。其余原旗标包括 s390 的 `-pg`、`-O2`、目标 ABI/机器选项、`-std=gnu89`、include/宏定义及 x86 的对应选项均保持原 argv 顺序。未见响应文件、多命令、另一个源输入或其他显式输出选项。

计划按 WSL 参数数组调用目标 GCC，旧 `.i`、`.config`、`.cmd`、`.c`、旧 `.o`/依赖文件登记前后摘要；新汇编、dump、临时文件和标准输出均指定本阶段 `raw/<profile>`。脚本现已将 `raw` 实际路径约束在 stage 内，`execute` 重新核批准计划与输入，且只要求当前 profile 的新目录创建成功；这关闭了旧版脚本中 s390 完成后 x86 因目录存在而必失败的门禁问题。x86 只在 s390 退出 0、三个计划输出存在且目标 GIMPLE 函数唯一完整提取后才可启动。两 profile 各最多一次，失败/超时不改旗标重试。

结论：在**计划及脚本字节仍保持上述 SHA**、实际执行继续通过其输入/目录门禁的条件下，未见阻止一次 old_s390 探查的命令或输出隔离问题；old_x86 仅可按保存的 s390 门禁结果条件执行。这里的批准只限生成汇编和 dump 的可行性探查，不是 Linux 构建/运行或契约证明。GCC 的 original/gimple 表示可能降低/优化源码，函数抽取失败须保留为不足，不以片段、退出码 0 或两个架构编译成功推导语义机制。
