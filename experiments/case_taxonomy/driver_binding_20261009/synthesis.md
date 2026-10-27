# 历史驱动的声明与局部构建绑定

本轮完成三个事前固定路径的核查：私有 `include/linux/if_pppox.h` 路径在指定父修订缺失；局部Makefile和Kconfig存在。目标 `core/rtw_br_ext.o` 明确列入 `r8188eu-y`，由 `obj-$(CONFIG_R8188EU) := r8188eu.o` 挂接到驱动对象。局部配置是tristate，依赖WLAN、USB、CFG80211和m。**已取得局部源码/构建文字关系，尚未确认实际采用的声明、CONFIG或真实构建。**

唯一历史修订为3123109284176b1532874591f7c81f3837bbdc17。先以本地Git确认commit类型，后一次cat-file batch请求三个固定文件，共2条Git命令/3次文件对象请求；保存2个blob、1个missing响应，没有追加替代路径、跟随include、取新候选/补丁或重试。原stdin/stdout/stderr/退出码和实际Git blob oid保存，每个保存文件的SHA及Git式blob与原响应匹配。

|环节|本轮取得的证据|仍未知|
|---|---|---|
|源文件include|原C引用`../include/linux/if_pppox.h`；按C目录归一的首要私有路径missing|后续quote/-I搜索、公共包装头/生成头和实际声明|
|局部对象链|Makefile 2–53行聚合，36行目标对象，55行CONFIG挂接|父级构建入口、真实配置/命令、成功编译|
|局部搜索设置|完整55行Makefile未列局部-I/ccflags类设置|顶层Kbuild提供的搜索目录及顺序|
|配置约束|Kconfig2–5行tristate和依赖；正常配置语义下m约束不应当作built-in已可用|实际CONFIG取值、父级约束、目标架构/设备是否可达|

私有首要路径缺失不能认定编译失败。编译器可能按同一个quoted token在其他搜索目录查找；本轮未读取那些目录或实际旗标，也没有证明公共标准UAPI头被采用。不能用一个标准结构声明覆盖实际绑定证据，也不能以Makefile文字代替真实编译和运行。局部对象关系增强了代码构建入口的source支持，但不解除布局/typedef/CHAR_BIT/packed/转换、单位/完整长度和实际路径条件。

绑定卡是针对已读固定材料的人工审阅与明确文本校验，不是通用Kbuild解析器或未知缺陷检测。独立协议/代码核对在导出前完成，独立语义与Kbuild审阅核对了原物。根只读校验退出0：根卡6组、语义9组、Kbuild6组引用，共16组唯一引用；其中1组来自生成的export_manifest，明确其Git式哈希是本地指纹，非检索Git源码blob。所有引用、源字节/oid、两命令和3请求收据与冻结一致，核验没有再次调用Git或旧规则。

输入锁SHA-256=`5eacd6579dfb0ff4390129a06fefa6a4fc2e36144212552683cf46d36a94042f`，导出器=`01d4b11296c77cefede6db7e5ddaa4513737bf028b91f7decd9d1c707312e3cc`，导出清单=`f005c09c024ee0835cc4b8d4450b0c98f0e746eade39398e26f36edf9f142a07`，绑定卡=`33eee111bb03ad425c5d177f85cec6444fc6dbef7ef139cdc2c354a756fedfaf`。原WSL代理提示保存在stderr，未阻止两条命令完成；没有编译/内核/设备实验或项目外部模型调用。

本轮按边界停止。原12模板条件全部仍未证，固定12条6/5/1、新确认0、独立阳性0不变；C1–C4、D2整体、D3全部裁定和NUMA状态不变。下一项另立协议、仅核查同修订顶层 `Makefile` 与 `include/linux/if_pppox.h` 两个固定路径，检验可见搜索设置与公共包装头链能否支持候选声明来源；本轮不补取它们。没有完整命令/类型/配置证据时仍不能认证实际预处理绑定，不继续跟随其他头或重做同例网格。
