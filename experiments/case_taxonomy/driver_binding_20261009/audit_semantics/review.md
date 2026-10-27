# 私有包含与局部构建证据：独立语义审阅

审阅者 `/root/driver_binding_semantics` 未实现根导出器或绑定卡，只读已保存父版 C 与本批 Makefile/Kconfig；没有执行 Git、联网/模型、编译或旧规则。本审阅核对源码及局部构建含义，不是独立缺陷检测试验或专家金标准。

父 C 第10行 quoted token 是 `../include/linux/if_pppox.h`，从源文件 core/ 目录归一后的首要文件位置为 `drivers/staging/r8188eu/include/linux/if_pppox.h`。本批 Git 原始响应确认为该固定修订的这一精确路径 missing。它没有直接证明找不到头文件：常见预处理器还可能把同一个完整 token 与后续 quote/-I 搜索根相接；例如若搜索根为内核 include，归一后可能落到公共 include/linux/if_pppox.h。这里只列条件性风险，没有观察或宣称实际搜索根、包装头存在/内容及其到 UAPI 的声明链。不能以本批 missing 宣告不可编译，也不能以已保存标准 UAPI 类型替代实际绑定。

Makefile 的 r8188eu-y 从第2行开始、包含第36行 core/rtw_br_ext.o、在第53行结束；第55行将 r8188eu.o 放入 obj-$(CONFIG_R8188EU)。这是一条完整的局部聚合文字关系。完整55行没有 -I 或局部 include 旗标赋值；不等于编译没有全局/继承旗标。父级 Kbuild 入口、实际 CONFIG、实际编译命令、预处理结果、生成头与运行到达均未取证。

Kconfig 第2–5行声明 R8188EU tristate，依赖 WLAN、USB、CFG80211 以及 m；第6–10行 select 五项设施。在通常 Kconfig tristate 语义下，m 约束不允许选为 built-in；它既不是已启用证明，也不是对所有架构的支持/可达证明。第11–16行 help 的设备介绍和模块名称不应当替代构建或运行记录。

既有12项模板适用条件仍全部 proven=false。此次没有解除实际声明绑定、typedef/存储宽度、CHAR_BIT、unsigned short 写出宽度/对齐、packed 生效、完整长度、转换/API、范围及运行路径等阻断。完整长度的条件性组成关系和原候选表示判断仍是原来的证据层级，新增确认与独立阳性均0。

独立原物核对：batch 3项响应逐字匹配；两个 blob 的保存字节、长度、SHA256 与 Git式 blob SHA1 均匹配原始批量响应；唯一 missing 不生成源文件。两份新文件加一份既有 C 提供9组精确引用，详见同目录 review.json。原物与哈希一致只是溯源核验，不证明契约语义或运行正确。
