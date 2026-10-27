# 事前复核

citation_audit确认两request/source字节不变，prompt只加最终协议限制，无语义答案，允许空候选和insufficient。动态覆写HERE、prepare、parse和三旧账92647实际生效；新budget907353、8192输出、300秒、零重试保持，绑定base依赖SHA，不读oracle。

独立复核发现base默认容许Markdown围栏，与新prompt不符；root在首调用前增加原始JSON解码校验。两项离线边界验证：裸JSON空候选接受、带围栏拒绝。WSL dry-run已按修正代码重新生成指纹，无密钥或API调用。
