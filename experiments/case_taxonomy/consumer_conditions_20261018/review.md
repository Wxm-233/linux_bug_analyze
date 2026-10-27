# N2.9 冻结挑战独立复核（2026-10-18）

本轮是**真实的输入覆盖失败**。冻结方法baseline SHA-256 为`1690945662b2052266867144c8d2010c88ab610c596fb8e8d7b839d06db90387`，独立oracle manifest为`5e9d612c02c9896eed199937fd5ced196c4d4e4d91f614689736649a3a0a1b17`；两份manifest所列文件及九份C源现值均与登记摘要匹配。`run_challenge.py`对原始字节调用`analyze_consumer`，没有做源改写。九份源均以`/* ... */`注释开头；冻结模块直接把raw text交给`pycparser.CParser().parse`，其九次首因均为第1行“Comments are not supported”。

结果表九源全部`insufficient`，包括预登记的七份拟支持源；2754条独立C/Python参考记录全部因源未抽取而跳过，实际`evaluate_consumer`次数为0。native C与独立Python的返回值一致只验证了参考侧；`return_matches=0`且`return_mismatches=0`的比较分母也是0，不能解释为提取器正确、零错误或量词机制得到验证。U1可变边界和U2非规范`while`虽都返回不足，但同样止于注释解析，预定的两项语义拒判门槛没有被触发。

即便将注释障碍单列，源码与冻结模板仍有**尚未执行验证的静态适用性缺口**：C0–C3/A3/V3/P3的循环内`int member = members[pos];`与当前`classify`只接受搜索体前置标量赋值/continue的形状不符；其更新循环累计`mismatch`、循环后统一`if(mismatch) return`，而当前模板要求循环内末尾`if (...) return`及尾return。P3还在同一轮先检查再更新，不能被称为“更新后检查”。这些只是按已读源码和冻结代码的静态判断，未绕过注释重新执行，不能伪装成第二轮挑战成绩。U1/U2在该前置障碍之后是否正确走到各自专门拒判亦未实测。

旧Linux D05/D10原配置材料保持原字节，因GNU表达式/asm解析不足，量词为空；人工看到的存在/逐成员线索仍不是机器从Linux自动抽取。下一独立方法版本可事前定义保坐标的普通C注释处理和更明确的可支持循环形状，或缩小承诺范围，并另设冻结挑战；本轮源、方法、结果不修改，也不删注释重跑追分。没有新内核案例、API调用或可声称的系统层自动检查收益。
