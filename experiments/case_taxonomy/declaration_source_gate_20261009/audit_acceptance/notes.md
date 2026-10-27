# 声明来源门禁：独立验收边界建议

审阅范围：只读 `include_route_20261009/route_card.json`、相应四份保存源码，以及 `encoded_length_check_development_20261008/runs/initial/results.json` 的父版候选。不执行任何旧检测器、Git、网络、编译或外部模型；不修改旧阶段文件。以下为开发验收建议，尚不是实现验证结果。

## 真实候选与同版本来源的连接

- 历史版本统一为 `3123109284176b1532874591f7c81f3837bbdc17`。
- 取旧结果 `development[0].result.assignments[0]`，变量 `data_len`，实际赋值 `tag->tag_len + TAG_HDR_LEN`，父版 C 第 73 行；第 74 行是首个可见词法消费 `skb_tailroom`。词法首项不是控制流或实际执行证明。
- 候选字段身份为 `struct pppoe_tag` / `tag_len` / `__be16`；C 第 68 行函数参数给出对象与结构关系，同版本 UAPI 第 124 行给出字段声明。
- C 第 10 行完整引用 token 是 `../include/linux/if_pppox.h`；本地私有路径的 missing 记录只适用于此前固定路径查询。
- 顶层 Makefile 第 512–519 行的源码相对搜索根 `include` 与完整 token 作 POSIX 规范化，得到 `include/linux/if_pppox.h`。包装头第 19 行包含 `<uapi/linux/if_pppox.h>`，同源码根候选是 `include/uapi/linux/if_pppox.h`。
- 不能只比较 basename，也不能把缺失私有头解释为最终编译失败；不得静默替换最新系统头。

独立逐项核验路线卡 12 条引文的当前保存字节、SHA-256、Git blob hash、行号原文，均匹配。这里的 hash 只保证材料一致，不证明语义或编译生效。

| 保存源 | 字节数 | SHA-256 | Git blob SHA-1 |
|---|---:|---|---|
| 父版 C | 18341 | `0310bf04241d497049337252be03ce69746f47ad4f1c9713295c36d72e0233e6` | `d68611ef22f80f07d9f0a6dc18b4efcb927b6ac5` |
| 顶层 Makefile | 65156 | `af431943735adabb0c15bf16942fc39cf4982dde2f6efc401a31998e865e6903` | `8c7de9a72ea26f88316c70279164056897631541` |
| 公共包装头 | 2913 | `104ef0516444f02ccd2779e31310f9b5e033a98fbc9f9dfc79eedd4a6aabe71f` | `69e813bcb947ef59c1fc23e541a938d5c179d197` |
| 同版本 UAPI | 4804 | `aa3da6f6a3f1bc67b2507afde489106f895c07553723f04cda3dfbb10ec03b1e` | `e7a693c28f16560c7d646ca3f954d952428a408b` |

## 至多八项开发输入边界

1. **正常条件性路线。** 上述真实父版候选连接四份同版本来源。只能得到“保存源码支持条件性声明路线”，保留有效命令、搜索先后、guard、实际声明绑定、布局、长度契约等未证条件；不设为实际编译或缺陷确认。
2. **必要来源缺失。** 缺 C、Makefile、包装头、UAPI 或连接中必需的证据，输出 insufficient／blocked，并列明缺口。不能因为声明字段看起来熟悉而补用其他来源。
3. **混版本。** 源码、声明、路线或候选引文中有不同 revision，不能因为文件字节相同便默许适用性。必须阻断本阶段同版本路线。
4. **真实 token 不匹配。** 候选引用的 token 与保存 C 引文不符，或完整 token 与指定根规范化后不接所称包装头，阻断；不按 basename 接线。
5. **显式竞争根。** 输入新增另一路完整 token 命中，或已知同名声明可能由更早 root 提供，输出 ambiguous。不能把一条可到达路线等同实际优先选择；未检查其他 root 的正常样本仍仅条件性。
6. **声明身份不匹配。** 所称结构、字段或编码类型与真实声明文本不一致，阻断。检验包括候选对象参数身份与声明身份的连接；不能依据仅同名 tag_len 接线。
7. **保存证据失真。** SHA、blob hash、byte_count、行号或引文与保存字节不一致，输出 evidence_invalid。只改一处元数据构成开发扰动，不是新 Linux 案例。
8. **自报认证绕过。** 对缺失、混版本、竞争路线等扰动附加 `status=normal`、`certified=true`、`proven=true`，不能解除阻断。正常输入中的认证字段也不能把条件性路线提升到 actual。

预期应冻结在运行前，结果状态与阻断原因一起验收，不能只对“pass”字符串。开发扰动和一个已读真实候选分开计数，新增确认及独立正例保持 0。
