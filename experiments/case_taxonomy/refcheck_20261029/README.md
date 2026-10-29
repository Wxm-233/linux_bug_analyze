# 新增参考文献[11]—[17]核对（2026-10-29）

按用户“先核对文献并提交”实施，对象为新Word稿中新增的7条参考文献。

## 方法与限制

- 会话内的网页搜索工具报模型配置错误，无法使用。改用curl直接查询：
  - **Crossref公开接口**（`api.crossref.org/works`，原始返回存于`crossref/`）；
  - **USENIX论文页面**（`usenix.org/conference/...`，读取标题与作者栏）。
- DBLP接口与USENIX的BibTeX导出都返回人机验证页面（Anubis / Cloudflare），**未绕过**。因此3篇USENIX论文没有取到页码，引用中不写页码。

## 结果

| 编号 | 核对结论 | 依据 |
| --- | --- | --- |
| [11] Engler et al., Bugs as Deviant Behavior | 作者、题目一致；SOSP 2001，第57—72页，doi 10.1145/502034.502041 | Crossref |
| [12] Yun et al., APISan | 作者（I. Yun, C. Min, X. Si, Y. Jang, T. Kim, M. Naik）与题目一致；USENIX Security 2016 | USENIX页面 |
| [13] Lu, Pakki, Wu, Crix | 作者与题目一致；USENIX Security 2019 | USENIX页面 |
| [14] Jang, Agrawal, Brumley, ReDeBug | 一致；IEEE S&P 2012，第48—62页，doi 10.1109/SP.2012.13 | Crossref |
| [15] Kim, Woo, Lee, Oh, VUDDY | 一致；IEEE S&P 2017，第595—614页，doi 10.1109/SP.2017.62 | Crossref |
| [16] Xiao et al., MVP | 11位作者与稿中一致（页面将Zimu Yuan、Feng Li、Binghong Liu合并在同一单位条目下，Wei Huo与Wei Zou亦然）；USENIX Security 2020 | USENIX页面 |
| [17] Padioleau, Lawall, Hansen, Muller | 一致；EuroSys 2008，第247—260页，doi 10.1145/1352592.1352618 | Crossref |

7条均未发现作者、题目或会议的错误，补入页码与DOI后去掉了“待核对”标记。

## 新稿

- `文章写作/Linux跨架构隐含契约失配_重组稿_20261029.docx`（SHA `2fcf67a1…`，10页）重新生成，`build_docx.py`的SHA为`7e6bc93f…`。
- 稿件说明改为“新增参考文献已于2026年10月29日按Crossref记录与USENIX论文页面逐条核对”。
- 在本机Word中导出后检查了参考文献页，排版正常。
- 原稿未改动。

## 统计

Kimi调用0次；构建0；新确认缺陷0；独立正例／正常0/0。
