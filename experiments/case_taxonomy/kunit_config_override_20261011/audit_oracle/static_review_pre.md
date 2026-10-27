# 首次执行前静态预审与字段适配

审阅身份：`/root/merge_oracle`。仅静态读取本轮 `protocol_pre.md`、`inputs_pre.json`、`run_override.py`、`execute_once.py`，未执行它们或历史函数。

## 预锁顺序

`audit_oracle/oracle_pre.json` 与 `oracle_pre.md` 先由冻结源码独立推导并保存；随后才读取本轮输入及脚本。原 JSON SHA-256 为 `958c5ef1b7811c3f99596b51f48e1228228960db04815f4bbd364fb3be9bc3de`。原 oracle 未为匹配 runner 修改。另存 `oracle_runner_adapter_pre.json` 仅处理字段名、冲突列表形状与由既定合并规则推出的改变项记账；其字段可供比较程序直接核对。

## 输入核对

六个 row ID、父/提交角色与预定 user/output 组合完全一致。inputs_pre.json 第 9、21、33 行沿用父 provider 完整字符串，第 45、57、69 行沿用提交 provider 完整字符串；第 10、22、34、46、58、70 行的用户请求只含 CPU_BIG_ENDIAN。第 11、23、35、47、59、71 行显式合成 CPU 输出并保留四项其他 provider 请求为 y。n 使用标准 is-not-set，符合 parse 源码第 100–102 行。provider SHA-256 与独立读取的两份源文件相符。

## runner 顺序与边界

- run_override.py 第 16–25 行仅以 AST 获取 QEMU_ARCH 调用的 kconfig 字符串，没有导入 provider。第 37–51 行检查解析器源码的顶层结构及标准库导入后加载保存的 kunit_config.py。
- 第 57–59 行核对 provider hash 和字面量请求文本；第 60–62 行每组各 parse arch、base、合成输出。
- 第 66 行诊断性读取合并前冲突，第 67 行 arch.merge_in_entries(base)，第 73 行合并后 arch.is_subset_of(generated)，顺序与预定对象一致。conflicting_options 并非真实 make_arch_config 中的历史门禁，代码第 65 行及 protocol 第 17 行正确注明。
- 第 71–72 行记录改变或新增条目。父组三项均新增 CPU，提交 user=y 没有值改变，提交 user=n 两项将 y 改为 n。这一记账与原 oracle 的 user_changes_provider_cpu_value 相容。
- 第 84 行 review_override_legality_candidate 只是是否存在冲突；只在提交 user=n 两行 true。第 86–90 行将环境要求、覆盖合法性、政策违例、真实配置及可达性保留 unknown/null/false，未将合成结果升级为缺陷。
- 六组固定循环预计 18 次真实 parse、6 次 merge、6 次 subset 与6次诊断 conflict。第 33 行阻止已有观察后的重复执行，第 34–36 行核对 execution_pre 冻结文件身份。
- execute_once.py 第 9 行阻止已有首轮收据后的再次执行，第 11–12 行先核对冻结 hash；第 13–16 行仅启动离线 runner；第 22–28 行保存 stdout/stderr 原始字节与收据，第 29 行之后才判定返回码。

## 审阅结论

输入与脚本静态设计支持原 oracle 的六组比较，未发现影响预定 parse/merge/subset 语义的阻塞项。此结论不等于执行通过，也不验证 execution_pre 实际冻结内容（该文件尚未提供），更不证明真实配置可达或覆盖是否合法。首次结果必须先保存，后对照原 oracle/适配文件；原 oracle 继续保持不变。

