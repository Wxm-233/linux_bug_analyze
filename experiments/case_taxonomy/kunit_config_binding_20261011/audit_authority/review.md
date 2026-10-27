# KUnit配置提供—消费—输出核验链独立审阅

2026-10-11。只读09ea90e5同版4份保存源码和前阶段提供者事实，未Git取证、导入主流程或执行历史源码。四物料blob/SHA/字节、batch导出和收据通过。精确原文与行号保存在review.json的14段quotes。

## 同版链已静态补齐

qemu_config.py第12–20行将kconfig作为QemuArchParams字符串字段。kunit_kernel.py第103–118行存入Qemu操作对象、parse_from_string后merge基础请求；第214–239行实见配置模块载入和操作对象构造。第264–267行加载基础片段并加入命令行kconfig_add。

生成路径第295–307行将合并请求写入build_dir/.config，调用olddefconfig，再调用validate_config。第280–293行的核验并非未用helper：它实际parse_file该.config，并对self._kconfig调用is_subset_of；缺失或值不同则返回False。kunit_config.py第81–108行展示parse_file实际解析文本，第52–61行展示匹配按请求键/值进行，显式请求n而输出缺键时允许通过。

第323–337行已有配置复用仍检查请求子集及上次请求；否则重生成。第339–346行build_kernel在olddefconfig和make之后再次validate。kunit.py第269–281行run顺序是配置→构建→执行，前两阶段失败均提前返回。因此应区分“生成后配置核验”与“构建后复验”，不能说所有配置变化均在编译前被拦截。这里只读程序，不代表实际.config被本次解析或实际构建发生。

## 请求覆盖与合并边界

匹配只遍历请求已有键。父版提供者缺显式CPU_BIG_ENDIAN，仅说明提供者没有要求它；基础片段、命令行、默认值或解析过程仍可能得到BE，不能推导真实输出为LE。若合成LE/缺键能满足父版请求，反例是“请求遗漏不在匹配义务内”，不是生成器错误或历史运行故障证明。BE必要性还需独立环境/接口要求，不能由标题或修复加入该键反推。

合并还有已见限制：kunit_config.py第72–74行逐项覆盖；make_arch_config第117行将base覆盖进架构请求，未在该处先报冲突。基础片段可覆盖架构CPU=y。第182–194行多基础片段冲突检查是另一条路径，不能说全部合并都会拒绝冲突。若六组合成只使用提供者字符串，需明确未加入其他覆盖请求。

实际合并输入、真实最终.config、PowerPC依赖/默认、QEMU端序契约和内核运行仍unknown。新确认、独立阳性均0，首次发现unknown。
