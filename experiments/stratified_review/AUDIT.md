# 旧候选规则命中贡献审计

冻结审计扫描 404,475 条、保留 118,997 条（29.42%）。
四条默认正则在 subject/body/files 中命中任意一条即保留；下表中的“独中”只说明
其他三条规则未命中，**不表示提交与研究目标无关**。路径正则原来也会搜索 body。

| 旧规则 | 命中条数（可重叠） | 仅此规则命中 |
|---|---:|---:|
| architecture_path_pattern | 54,345 | 229 |
| architecture_name | 91,405 | 29,346 |
| cross_arch_wording | 1,685 | 299 |
| generic_boundary_word | 49,867 | 26,942 |

仅规则命中的字段分布：

| 旧规则 | 字段组合 | 条数 |
|---|---|---:|
| architecture_path_pattern | files | 223 |
| architecture_path_pattern | body,files | 4 |
| architecture_path_pattern | body | 2 |
| architecture_name | body | 17,418 |
| architecture_name | files,subject | 4,109 |
| architecture_name | files | 2,933 |
| architecture_name | body,files,subject | 2,401 |
| architecture_name | body,files | 1,264 |
| architecture_name | body,subject | 895 |
| architecture_name | subject | 326 |
| cross_arch_wording | body | 270 |
| cross_arch_wording | body,subject | 16 |
| cross_arch_wording | subject | 12 |
| cross_arch_wording | files | 1 |
| generic_boundary_word | body | 13,104 |
| generic_boundary_word | body,subject | 4,136 |
| generic_boundary_word | body,files,subject | 2,793 |
| generic_boundary_word | files | 2,710 |
| generic_boundary_word | files,subject | 2,173 |
| generic_boundary_word | subject | 1,033 |
| generic_boundary_word | body,files | 993 |

这是条件收紧前的命中结构审计，不能从只有入选项的审计文件直接计算漏检率。
后续以组合信号分层和低层/原未入选对照抽样检查，不把单一信号自动作为排除依据。
