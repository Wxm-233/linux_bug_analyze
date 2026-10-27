# KUnit配置绑定：独立结果范围审查

结论：**PASS_FOR_SIX_EMPTY_BASE_OFFLINE_REQUEST_MATCHES**。首锁文件身份未变，唯一记录runner退出0；保存stdout与observations一致，六格与事前oracle逐项一致，4项请求匹配、2项拒绝。本审查只读，没有再次加载或执行历史模块、runner、Git、C或内核。

父请求未提出CPU_BIG_ENDIAN条件，所以合成y、n或缺项都满足其它请求；这不说明旧真实内核采用LE，更不说明三种输出都符合QEMU环境。提交请求明确y，合成n和缺项被集合检查拒绝。结果支持“先检查需要的条件有没有进入请求，再检查输出满足请求”这一分工，不是端序正确性、真实.config或Kconfig可达性验证。六格是一个已读案例的合成版本对照，不是六条独立案例。

**合并边界：** make_arch_config先解析架构字符串，再merge用户base；merge同名项由base覆盖（kunit_kernel.py 115–118、kunit_config.py 72–74）。六格base均为空，尚未测试覆盖冲突。源码的覆盖行为也可能是允许用户定制，不能仅据此认定缺陷；必须先有版本/环境明确的要求，才判断是否覆盖了不允许改变的条件。

**入口边界：**正常run_tests按config→build→exec推进，前两失败会返回；build_handler也通过config_and_build_tests先配置再构建。build_kernel函数自身在olddefconfig和make之后validate，不能概括所有检查都在编译前。直接exec_handler调用exec_tests，随后run_kernel到_ops.start，未走normal run的config/build链。这是保存源码的静态顺序，本轮没有执行这些入口，也没有认定直接exec设计有错。

后续若测试非空base，应另冻结少量输入及预期，保持“环境义务—合并后请求覆盖—生成结果满足”分开；真实环境契约和运行路径仍unknown。不要回改已完成六格，也不把请求匹配通过称作构建或启动成功。
