# N2.11计划与执行边界

`probe_compiler.py --plan`在既有Ubuntu WSL中只读核对协议、prior manifest、完整.i/.config、saved .cmd及已安装编译器，stdout返回计划；Windows调用方保存`command_plan.json`。规划不调用编译器。计划摘要为`fb174a23f1126e899099839d503af7148f62678e681a0e6b5ec4d9f8c07ce6af`，脚本摘要为`cc62b5b01b890164ebf1d7b84b4060dd5dba0b34ac97c853828bf8a8dbcf565e`。

saved命令只允许唯一core.o cmd、指定compiler basename和一个已知core.c源。shlex仅生成argv，不执行shell。变更是编译器绝对路径、精确core.i及`-x cpp-output`、`-c`改`-S`、绝对新assembly输出、去依赖文件写入、两个显式original/gimple dump；保留其他原target/semantic flag。首个只读计划因安全分类漏原`-pg`而拒绝，记录保留，后只允许原`-pg`继续保留，不是编译失败后的调flag重试。

`--execute --approved-plan-sha <hash> --profile old_s390|old_x86`先核批准plan原字节及重新生成身份不变。每个profile输出目录必须新建，attempt以x模式记录一次额度，不能覆盖或重试；old_x86还必须有同plan的s390 exit0、所有输出及唯一完整目标区段。执行身份重核允许primary目录已存在，不因此阻断第二profile；当前profile仍必须全新。

编译直接Popen argv，无shell、无assembler/link/boot。原build为cwd以保相对只读include语义，所有显式输出与TMPDIR/TMP/TEMP均为新stage raw/profile，干净PATH/locale环境不带用户密钥或依赖输出变量。raw解析后必须留在stage内，拒stage外符号链接。每次120秒，超时终止新进程组；失败保stdout/stderr/状态，不改flag重试。前后保护.i、.config、原.cmd、core.c及原o/依赖文件身份，原缺失依赖保持缺失，不创建旧文件。

完整GIMPLE文件保留在ignored raw；有限提取目标函数时按唯一声明及配对嵌套花括号，跳过字符串/注释内括号，记录原dump SHA、字节/行范围和完整函数摘要。分支/goto/字段名称只是文字库存，不是CFG、def-use、对象别名或契约证明。

**已知定位边界：**签名return-type模式中的`\s+`可能跨越上一行纯标识符，从而让自动start包含无关前行。该潜在问题在root启动首次固定计划编译时提出；脚本及计划未更改。实际dump需独立核对签名和起止行，若不能确定则保raw、标区段不足，不通过改定位器/重编追认成功。自动定位状态本身不代替这一复核。

4项离线命令与配对括号门禁测试通过，见`offline_gate_tests.json`。它们不调用WSL/编译器，不证明实际Linux区段起点，也不计内核分析成功。root负责首次实际调用及结果记录，本说明不预报结果。两个profile均为既有已读源码，不是新案例或独立泛化证据。
