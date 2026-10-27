# N2.15：die既有输入与最小适配建议

本轮只读旧构建/运行材料，并从保留片段重算有限计数和身份关系；未调用模型、编译、启动内核、获取Git源码或修改旧核心。以下是已读第二机制的迁移开发材料，不构成新缺陷或独立泛化样本。

## 静态六格：真实schema

`die_arch_contract_20261013/results.json`为6项list，单格另存`profiles/<profile>/result.json`。profile为old/fixed × `x86_smp/s390_smp/x86_up`；固定父版`555a0ce4558d87d5b97c4321f34b19e051c7b0c1`、修复版`2c4dcd7fd57b20a21b65da04d89c38a7217d79cf`。

可直接引用的字段：

```text
profile, revision, arch, source_arch, requested_smp, build_directory, kernel_boot=false
configuration {CONFIG_SMP,CONFIG_SYSFS,CONFIG_X86_64,CONFIG_S390,...}
preprocessing:
  include_sources[]
  macro_definitions[name][] {file,source_line,preprocessed_line,definition}
  arrays[name] {text,die_references[]}
  declarations[name]:bool
  functions_or_calls[name]:bool
  attribute_reference_count
object {path,elf_header,die_symbols[]}
target_identity {configuration_key,configuration_value,elf_fields,...}
```

原片段单独在`profiles/<profile>/preprocessed_evidence.json`；同目录有真实`kernel.config/autoconf.h/symbols.stdout.log/elf.stdout.log`。`old_source_map.json/fixed_source_map.json`保存9个选定源文件的Git blob及旧采集时的归档匹配结果。现有result未保存完整`topology.i`文件SHA，不能把有限片段SHA冒称完整预处理文件SHA；若不补读既有大文件，就明确限定为旧归档片段重放。

### 这次可以从原片段重算什么

1. 从`kernel.config`重读实际SMP、SYSFS、架构选择与NR_CPUS；`# CONFIG_* is not set`可解释为n，完全缺失的键仍未知。
2. 从两个`arrays[].text`完整数组片段重算三个die表项是否被引用及计数。此次重算与旧摘要相同：x86 SMP旧/修复3/3、s390 SMP 3/0、x86 UP 3/0。
3. 从`symbols.stdout.log`最后一列精确符号名重算三个die符号是否存在；此次六格符号计数与数组计数逐格一致。ELF架构/端序可从`elf.stdout.log`原头和实际config重算。
4. 从宏定义的实际`file/definition/preprocessed_line`重核来源。当前两个目标宏在每格各有唯一记录：x86 SMP两者均来自`arch/x86/include/asm/topology.h`；s390 SMP两者均来自公共`include/linux/topology.h`；x86 UP仅ID来自架构，mask来自公共fallback。来源规则应标为经审核的适配规则，不是通用能力推断。

`declarations`只有已抽取bool，没有独立保留声明原句；`functions_or_calls`也只是文本存在性bool，不能单凭这些证明注册调用已执行。`expected_attributes/expected_native_sources/preprocess_matches_expectation/object_matches_expectation/status`是旧试验的期望或验收输出，不能充当本轮事实输入。尤其`expected_native_sources`在旧脚本中按profile构造；应改用实际定义来源，不复用其答案。

### 为什么不能看final define

六格最后都能取得`topology_die_id`和`topology_die_cpumask`，因为公共头会补fallback。它们“存在”不等于架构原生提供。必须保存来源及定义时机：修复x86 SMP的两个架构定义先出现，公共`TOPOLOGY_DIE_SYSFS`随后出现；s390及x86 UP没有该opt-in记录。不能把TOPOLOGY_DIE_SYSFS缺失反推“两个接口都不存在”，也不能将旧版本没有该新门控误当原生提供者不存在。

`include_sources`是进入头文件的顺序，不等同于宏最终生效的时序；应使用`preprocessed_line`与源位置。当前有限packet记录define而非完整undef历史；若出现多定义、来源不明或需要判断未保留的undef，应不足，不选取一个有利定义。架构来源也不等于物理硬件拓扑已经认证。

## 四格运行：schema与可重算项

`runtime/build_results.json`、`boot_results.json`均为4项list；单格保留于`runtime/profiles/<profile>/build.json/boot.json`，profile为`old/fixed_s390`和`old/fixed_x86_64`，不是静态profile的同名索引。

```text
build: profile,revision,arch,source_c_modified=false,source_identity[],
       effective_configuration,image_sha256,release,init_*_sha256,config_sha256,status
boot: profile,revision,arch,release,image_sha256,init_*_sha256,qemu_argv,
      analysis_runner_sha256,qemu_receipt,observations
observations: events[],parse_errors[],raw_cpu_sets,foundation,cpus[],status
file_read event: path,cpu,status,errno,raw,raw_byte_length,read_limit_bytes,truncated,encoding
```

此次从四份`qemu_boot.stdout.log`重新提取JSON事件，均无解析错误，事件列表与对应`boot.json/observations/events`完全一致；各CPU的三个die读取各出现一次。四份实际config摘要均匹配build记录，boot与build的image SHA逐格相等。

可重新计算：读取成功/ENOENT/其他错误的区别；原始ID整数、bitmap与CPU-list集合是否一致；选定CPU是否包含于导出集合；x86旧/修复原始值是否保持；online/present/possible集合及控制属性是否满足观察有效性。应同时要求`status=ok/errno=0/truncated=false`，不能把空字符串、读失败或截断当合法值。缺文件只在`open_error/errno=2`且普通控制属性/目录仍正常时才支持“该属性缺失”。其他errno不等于门控正确。

旧`matches_contract/status=PASS`含按架构/版本设置的期望，不能直接作为新协议发现结果。建议仅从原事件重算基础有效性与发布事实，再运行现有contract_protocol。旧分析器对重复路径取最后一项；新薄适配可要求die路径恰一次，避免重复日志被静默覆盖。

## 配置层必须分开

静态六格基于defconfig，x86 SMP NR_CPUS=64、s390 SMP=512、x86 UP=1；运行四格基于allnoconfig最小内核，均SMP、NR_CPUS=4。运行使用原历史内核，`source_c_modified=false`，与前一个s390生命周期案例的内核观测补丁不同，但仍不是静态那次构建。不得凭版本和架构相同将静态`.config/.i/.o`身份直接替代运行配置/镜像。

| 配置层 | config SHA |
|---|---|
| 静态old/fixed x86 SMP（两版字节相同） | `13b7a3381ab2b194cc99d7c7a6079ab9d2275a508e0a63cd58e0835be9dfb1b8` |
| 静态old/fixed s390 SMP（两版字节相同） | `8d996bbd4e992dff2a125c7802299f8c55553d4d1764345a7663f242694f24d2` |
| 静态old/fixed x86 UP（两版字节相同） | `891299cde2df459620b885f76e8ff779a2a4a2c8369b909d3925dff0b4706dac` |
| 运行old_s390 | `221cf5ca03ebcf9d754fbae113807eab84f571f22365acf66003818c1e3de2c8` |
| 运行fixed_s390 | `251f0ad043e8eca1d2eb2182c892af2ccfa2758a78214986e527fa3757e66a0c` |
| 运行old_x86_64 | `20901720da562ac9fbd2f037bf08adf9e30989e56882588233ce938d5695fe4c` |
| 运行fixed_x86_64 | `387539860dbd124adc3465e500191acd24ff60874c255e9d13acc8afa95f761d` |

本次原事件读回值为：两版x86每CPU均`ID=0/bitmap=3/list=0-1`且逐字节保持；旧s390 ID=-1、集合为各自单CPU；修复s390两CPU的三个属性均ENOENT。它们只是已读虚拟双CPU运行事实，不认证物理die拓扑、热插拔或用户损失。x86 UP没有对应运行格。

## 最小适配建议

分成6条`noninstrumented_static_excerpt`观察和4条`historical_runtime`观察，分别保留profile、revision、arch、完整config SHA、输入packet/log SHA及具体JSON pointer或日志行。不要把10条观察算10个案例。

静态层建议输入仅有“ID与mask是否各来自审核过的架构提供者”“三个表项/符号数量”“SYSFS与目标配置已建立”。接口政策另作为研究者审核输入：本次修复建立原生双宏opt-in，不能倒推父版违反当时已明确的ABI禁令。运行层建议先只输入“每CPU三属性的成功/ENOENT/未知、原值和控制有效性”。如要把静态来源结论用于运行层，需单独审核同版本源码与实际运行配置下的适用条件，不伪装成运行构建已经取得相同预处理材料。

已有contract_protocol可据这些有限bool/计数/集合做已登记政策检查；native origin规则和政策均保持人工审核输入。缺来源、缺基础控制、配置不符、读失败或重复均不足。无需新增解析核心、CFG或模型；效果只说明第二个已读机制能否复用协议，不能据此报告自动发现或独立准确率。

## 关键旧packet身份（本次读取时SHA）

以下均相对`experiments/case_taxonomy/die_arch_contract_20261013/`；不是新事前冻结或全树封存。

| 文件 | SHA-256 |
|---|---|
| results.json | `e43a736c127e11a05e2f47e91c2c11a6d53666b050059b573d2cd9adafbd072f` |
| certification.json | `ac7fc62ef77b2281fd62560b2e067e25228640fb2143e1d5bf872e003a027b22` |
| old_source_map.json | `12d72a699207991c1d7cff14d85772371379e58768a7f16d7606b4890dd11eda` |
| fixed_source_map.json | `e9a32cef5b852baa3ff0ea7e5147c2eecddb8bdd9cef161486349c0834d3d8ae` |
| runtime/build_results.json | `dea5bf0efdbfb0c360e64c33d3bdf44d8aaacf66e8b64ae33963b9632ba28bc2` |
| runtime/boot_results.json | `7edb999a02a54c728ed132ac8f85121d8d1f2c73db870d49792d953f45c81bdc` |
| runtime/configuration_pairs.json | `f3cd8df987c9ab4afa04475a5f8ea98c100ebee7ed7addf57b0e0584d40811be` |
| runtime/x86_preservation.json | `c22b20f401ad08e0a684417f927ff3ed768b8f13db04b54bac6a1396375c33bb` |

四份原boot日志SHA：old_s390 `86d2a8ad4dc5d580d37369f6656cf2c93cd0cc913bf4109c307bff8b08ac3542`；fixed_s390 `140b6511cb3fdfcb490264eafce65a888c148b1389e30b7b23e543f48ae38bf0`；old_x86_64 `3ad2822c22521dde1f1d611229021c750a02f36edd64d82c8741e8c44d634c91`；fixed_x86_64 `4d4cb6c613a5014075ef86f561c746d46fe308a7c71c50e88190b6fd45b71306`。
