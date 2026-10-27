# 导出前协议与静态代码核对

2026-10-09，独立只读审阅者 `/root/driver_binding_protocol`。未执行 Git、导出脚本、旧检查器、模型或编译。本审阅批准的是事前固定的有限检索步骤，不是实际声明绑定、构建可行性或新案例确认。

导出脚本 SHA256 为 `01d4b11296c77cefede6db7e5ddaa4513737bf028b91f7decd9d1c707312e3cc`；输入锁为 `5eacd6579dfb0ff4390129a06fefa6a4fc2e36144212552683cf46d36a94042f`。协议、输入 JSON 和本地读取指纹一致，`ready_for_export=true`，没有要求修改的问题。

旧保存 C 第10行是 `#include "../include/linux/if_pppox.h"`，从 `drivers/staging/r8188eu/core/rtw_br_ext.c` 的目录规范化，得到事前固定的私有头路径。该路径、同目录 Makefile、Kconfig 共三个独立事实项，全部限定在同一父修订 `3123109284176b1532874591f7c81f3837bbdc17`。引用的是已完成的 composition 阶段闭合清单，不把未完成 components 准备目录当作完成阶段。

静态检查确认：导出前重新校验冻结文件及旧阶段清单；第一次 Git 只确认修订类型，失败不请求文件；第二次 Git 通过一次 `cat-file --batch` 发送三项固定 spec。每项响应按字节长度取 blob，校验末尾换行、总流边界与 Git blob SHA1；missing 必须与原 spec 的完整返回一致。原始 stdin/stdout/stderr、退出码和指纹保存。一个路径 missing 不触发替代路径，也不取消事前已固定的其余两项；本批结束即停止。异常保留原始收据与失败记录，不自动重试。

必须保留解释边界：首要相对路径 missing 只证明该 revision:path 不存在，不证明编译找不到该 quoted token。其他 quote/-I 搜索目录、生成头、符号链接及实际编译命令尚未知。Makefile 中列举对象或选项只是局部 Kbuild 源码关系；Kconfig 中的局部依赖也不证明全树支持。均不能认证真实构建、运行到达或以标准 UAPI 无声替代私有声明。完整长度、ABI、typedef、CHAR_BIT、packed 和实际路径等条件仍保持未证。

本轮核对是来源、范围和解析可靠性的检查，不是独立阳性检测；新增确认和独立阳性仍为0。输出语义还应在检索后结合原始响应另作审阅。
