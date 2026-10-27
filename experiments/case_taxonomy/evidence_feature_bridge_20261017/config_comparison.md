# N2.3 s390 配置的有限对比

只比较已登记的 `old_s390`、`fixed_s390` 两份非观测构建配置与各自的归档运行构建配置。四个文件的实际 SHA-256 均与对应 `artifact_binding.json`、`provider_consumer_binding` 的已选 artifact 或运行 `build.json` 声明相符；两侧的 revision/arch 元数据也对应。逐文件路径、摘要、所用元数据摘要和逐项统计见 `config_comparison.json`。未读取运行事件或结果。

每个非观测配置含 2,742 个显式 `CONFIG_` 记录，运行配置含 733 个；每对仅 731 个键共有，其中 184 个值不同，另有 2,011 个仅见于非观测配置、2 个仅见于运行配置。两种构建在 `CONFIG_64BIT`、`CONFIG_S390`、`CONFIG_SMP`、`CONFIG_SCHED_TOPOLOGY`、`CONFIG_SCHED_SMT`、`CONFIG_SCHED_CORE`、`CONFIG_HOTPLUG_CPU`、`CONFIG_SYSFS` 均为 `y`，`CONFIG_NR_CPUS` 均为 `4`，但 `CONFIG_LOCALVERSION` 随归档观测构建改变。在各自构建类别内部，旧版与修复版只在 `CONFIG_LOCALVERSION` 上不同。

这只能为相同 revision 下少数必要配置项的一致性提供证据。完整配置并不相同；原有 `.i/.o` 属非观测构建，归档运行配置的 `build.json` 明确标记 `source_instrumented=true`。不能因为这些共同开关相同，就自动把非观测构建中的提供者语义、编译产物身份、插桩影响或运行时准备状态转移给归档运行配置。缺失的配置键也没有被当作 `n`。
