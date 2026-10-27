# 同版编码长度组成与单位：已读源码语义审阅

本审阅限定两份已保存父版源码和上一轮模板结果，未取新源、未执行 Git、模型、编译或旧规则。由与生成器作者分离的审阅者阅读，但对象已读，仍不计独立阳性、专家金标准或泛化验证。

## 能够从源码支持的局部关系

父 C 第32–36行给出 RTL_RELAY_TAG_LEN=(ETH_ALEN)、TAG_HDR_LEN=4、MAGIC_CODE_LEN=2。ETH_ALEN 的定义未在获准材料中，必须保留符号，不能替换为6。第446–453行将40个 unsigned char 的 tag_buf 转为 tag 指针，old_tag_len 初始为0，存在旧 tag 时通过 ntohs 取旧长度。第471行将 `MAGIC_CODE_LEN+RTL_RELAY_TAG_LEN+old_tag_len` 经 htons 写入 tag_len，未包含 TAG_HDR_LEN。第461–462行把旧 payload 写在 magic 和 relay 部分后；第474–476行在 tag_data 起点写 magic，再以 ETH_ALEN 复制地址部分；第479行将该对象传给消费函数。

因此，局部生产者意图可写为 payload=2+ETH_ALEN+old_len。第81行复制从 tag 对象起点开始，而非 tag_data 起点；标准 UAPI 声明第122–126行在 char payload 前有两项 __be16 并带 packed 拼写。配合第56–63行扫描器以 unsigned char 指针前进 TAG_HDR_LEN+decoded tagLen、和显式 TAG_HDR_LEN=4，可提出有条件的“复制整个 tag 需要 payload 加前缀”关系。这比单凭字段名或已有 +4 强，但仍不是实际布局测量或规范裁定。

char 缓冲、char payload、字节指针步进、复制长度及生产者填充提供相互印证的字节计数量纲。__be16 注解单独只支持编码域/位宽拼写，不证明字节单位，更不证明 payload/total。宏名 TAG_HDR_LEN 自身同样不能成为头长权威。

## 不能解除的适用条件

父 C 第10行是 `../include/linux/if_pppox.h` 私有相对 include。现存 `include/uapi/linux/if_pppox.h` 是同版声明见证，尚不能证明它真正绑定到该驱动；相关 typedef、宏定义及配置缺失。两个 __be16 等于4字节前缀要依赖真实类型、字节宽度、packing 和声明绑定；本轮未证明 sizeof/offsetof。第474–475行通过 unsigned short* 写 magic，也尚未证明它正好覆盖2字节，不得从 MAGIC_CODE_LEN=2 自动补出类型事实。

htons/ntohs 和 memcpy/skb_put/skb_tailroom 的真实绑定未证。生产者总长检查第454–459行仅位于 pOldTag 分支内，不能泛化为所有路径均检查40字节容量。旧长度真实范围、初始化连续覆盖、对齐、源目的对象大小、临时数组有效性、整数提升/窄化/溢出，以及 htons 的输入可表示性都未证。嵌套协议、method、sid、code 和 addPPPoETag 条件也只是可见源码上下文，不是到达或运行证据。

上一模板的字段单位、显式加项角色、局部组成三类阻断由“无局部证据”推进到“source-supported conditional”。12项条件仍全为 proven=false。完整长度、外部约定、真实 ABI、全入口及运行行为不能由这一条链认证。消费者第79行目的偏移和第80行总长更新仍超出既有自动检查范围，不因本次阅读而被自动覆盖。

## 对自动检查建议的含义

允许受限提取器记录：生产者编码 payload 的符号项、byte-array 到 typed-object 的词法链、payload 填充及 object-origin copy、声明前缀候选和来源原文。允许生成“若实际绑定/布局/单位成立，则规范化 payload 后按前缀组成整对象复制长度”的可审阅义务。不得根据名字、修复标签、一个数字4或既有布局模型，自动猜测缺失加项并认定新问题；也不得把数学关系直接写成 C 断言或内核补丁。

新增确认0、独立阳性0。当前推进的是解释检查的来源与明确未证边界。

## 原始字节与引用

父版 revision：`3123109284176b1532874591f7c81f3837bbdc17`。

- parent_c: `drivers/staging/r8188eu/core/rtw_br_ext.c`；18341字节/657行；SHA256 `0310bf04241d497049337252be03ce69746f47ad4f1c9713295c36d72e0233e6`；Git式原字节blob `d68611ef22f80f07d9f0a6dc18b4efcb927b6ac5`。
- parent_header: `include/uapi/linux/if_pppox.h`；4804字节/160行；SHA256 `aa3da6f6a3f1bc67b2507afde489106f895c07553723f04cda3dfbb10ec03b1e`；Git式原字节blob `e7a693c28f16560c7d646ca3f954d952428a408b`。

上一模板 results SHA256 `c8cff54502d114b83c9afa9b69fdbad72290e1308118d676a3eed2f28578274b`。详细逐字原文及起止行见 review.json；共11组引用，仅来自上述两份固定源。
