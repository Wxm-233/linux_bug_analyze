# 审计脚本自身修正记录

2026-10-09。首次独立审计调用退出1，错误为在`prefix.decode('ascii')`解码整个Git header时出现`UnicodeDecodeError: 'ascii' codec can't decode byte 0xc3 in position 111`。它是审计器错误假定作者名字只含ASCII，不是保存材料损坏，不是Git/源码导出/检测器失败。未对该头部的作者或正文作语义解释。

修正为只在header原字节中匹配`parent`/`tree`的40位hex，捕获后才ASCII解码hex本身。另在静态检查时修正diff-tree argv后缀长度比较为完整预定argv精确比较。原失败没有发出任何Git、模型或规则请求；修正后重新运行的也仅是只读保存材料审计。

以上为工具失败的人工转录摘要，不伪装成原始native stdout/stderr。修正记录单独保存，旧阶段和父版取证不修改。
