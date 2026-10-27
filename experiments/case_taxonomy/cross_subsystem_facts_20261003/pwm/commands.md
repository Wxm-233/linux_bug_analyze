# PWM 本地命令入口

工作区 `D:\homework\software\linux_bug_analyze`。所有写入限于新 `linux_bug_analyze/experiments/case_taxonomy/cross_subsystem_facts_20261003/pwm/`。Windows 编排使用既有 bundled Python；本地固定历史源码读取使用 `wsl -d Ubuntu -- git -C /root/repos/linux ...`。执行的精确底层 argv、时间、returncode、stdout/stderr 路径及 SHA 在相应 `commands_*.json`，原字节均保留。

```powershell
& 'C:\Users\dell\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -X utf8 'D:\homework\software\linux_bug_analyze\linux_bug_analyze\experiments\case_taxonomy\cross_subsystem_facts_20261003\pwm\run_pwm.py' --phase prepare
& 'C:\Users\dell\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -X utf8 'D:\homework\software\linux_bug_analyze\linux_bug_analyze\experiments\case_taxonomy\cross_subsystem_facts_20261003\pwm\run_pwm.py' --phase replay
& 'C:\Users\dell\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -X utf8 'D:\homework\software\linux_bug_analyze\linux_bug_analyze\experiments\case_taxonomy\cross_subsystem_facts_20261003\pwm\export_source_extension.py'
& 'C:\Users\dell\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -X utf8 'D:\homework\software\linux_bug_analyze\linux_bug_analyze\experiments\case_taxonomy\cross_subsystem_facts_20261003\pwm\export_type_contract.py'
& 'C:\Users\dell\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -X utf8 'D:\homework\software\linux_bug_analyze\linux_bug_analyze\experiments\case_taxonomy\cross_subsystem_facts_20261003\pwm\build_facts.py'
& 'C:\Users\dell\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -X utf8 'D:\homework\software\linux_bug_analyze\linux_bug_analyze\experiments\case_taxonomy\cross_subsystem_facts_20261003\pwm\seal_pwm.py'
```

正式回放的两条原 CLI 命令：

```text
wsl -d Ubuntu -- python3 -B /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/endian_producer_single_revision.py --linux-dir /root/repos/linux --revision d7b4408374b69dbc246c59c29e3077920b9f03eb --source drivers/pwm/pwm-raspberrypi-poe.c --output /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/cross_subsystem_facts_20261003/pwm/raw/parent.json
wsl -d Ubuntu -- python3 -B /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/endian_producer_single_revision.py --linux-dir /root/repos/linux --revision 09f688f0718f57f9cf68ee1aa94490f641e759ba --source drivers/pwm/pwm-raspberrypi-poe.c --output /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/experiments/case_taxonomy/cross_subsystem_facts_20261003/pwm/raw/fixed.json
```

两条 CLI 的 returncode 均为0，stdout 为空，stderr 保留 WSL 启动告警原字节。结果通过 `--output` 写入原 JSON，非从混合控制台输出解析。准备阶段 71 条本地 Git 命令，source_extension 16 条、type_contract 32 条；正式回放2条 CLI。facts 与 seal 只读取已保存字节做人工事实组装/完整性核对，不调用 Git、编译器或实验输入。
