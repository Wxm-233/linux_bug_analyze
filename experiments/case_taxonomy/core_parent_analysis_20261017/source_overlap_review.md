# D 父版与已读 3fcb 源码的重叠核查

2026-10-17。只读核对本轮已登记的 D 父版 `parent_sources/D/drivers/base/arch_topology.c`、`parent_files.json`，以及此前保存的 `../cross_arch_arch_topology_source_20261012.json` 中 `drivers/base/arch_topology.c` 的两个 `complete_git_blob_text` 源副本；既有 `../case_reviews.md` 和 `../cross_arch_causal_cards.md` 表明 3fcb 案例早已进行源码复核。定位只用 `rg --files`；未打开 D 的子提交说明/补丁、旧模型回答或标签，未扩查 Git 新源码，也未对 D 赋正例或正常标签。

| 材料 | 绑定版本 | 完整文件 SHA-256 | Git blob | `cpu_clustergroup_mask` |
|---|---|---|---|---|
| 本轮 D 父版 | `26a2b73a7b15a51ec1409648c9b43882f66fbacf` | `824432e45a79acec53b0a31c63a1ea6f40b3287c0455ea92926b6021a3af7af9` | `e384afb6cac71dfe6b7bdc968d2fda5f6fa029cb` | 第 687–690 行，直接返回 `&cpu_topology[cpu].cluster_sibling` |
| 旧 3fcb 直接父版的已读完整源 | `0c80f9e165f8f9cca743d7b6cbdb54362da297e0` | `f557107cebbb82b5169fbe8b2ac6e3d6c07730b7379fdfd0a02c429c5630305d` | `441e14ac33a4959208b2ab1ff68b17ba4f03e1e3` | 第 719–730 行，先对 `cpu_coregroup_mask` 与 cluster sibling 作 `cpumask_subset` 判断，可能返回 `get_cpu_mask(cpu)`，否则返回 cluster sibling |
| 旧 3fcb 修复版的已读完整源 | `3fcbf1c77d089fcf0331fd8f3cbbe6c436a3edbd` | `19c5f3d80388facf419bb81702927dcc8ac717634091d92d6f6635bece4f3c2f` | `0424b59b695ef0fe2d717405efbfbc7dfac2dc3a` | 同为第 719–730 行，与上述旧直接父版的此函数逐字相同 |

这些 SHA-256 由保存的完整文本计算；两份旧文本的 Git blob 重算值与旧 `source` 记录一致，D 的完整文件 SHA-256 与本轮 `parent_files.json` 一致。D 与两份旧完整文件的 SHA-256、Git blob 均不同，D 的函数体也不与旧函数体逐字相同（D 函数 SHA-256 为 `8b22639fd67f4d06eaf10d2ee1f0abb7e931f289a7f1d7c3be24ca87e117a66a`；旧两版为 `f8abd30cb24ddc3caed6edad3762be15aef385cb1a6cb89c8aa885271b45eeb7`）。但**同名函数、同一 cluster sibling 返回目标及该源码区间已经出现在旧案例完整已读源中**；文件散列不同不能推论 D 的源码位置对方法开发者未曝光。

**资格影响。** 将 D 标为 `known_prior_source_location_exposure`；不能把它当作“此前未读过的源码位置”的独立留出样本。上述重叠也不能直接证明 D 与 3fcb 是同一故障、同一修复家族，或 D 有应添加的检查：本核查没有读取 D 修复材料、公共消费者执行链及运行结果。若继续分析 D，应单独注明这是已接触位置上的迁移/再分析，独立性和机制真值仍待别的证据裁定。
