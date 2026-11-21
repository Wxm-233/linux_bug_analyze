# 任务：给一批 Linux 内核提交做分类标注（第二标注人，盲判）

目录 `D:\homework\software\linux_bug_analyze\linux_bug_analyze\experiments\case_taxonomy\linmap_20261119\packets\` 下每个 `NNN.txt` 是一个历史提交的材料：提交说明，以及相关文件的改动（diff）。

背景：内核里有些接口**只对线性映射地址有意义**，包括 `virt_to_phys`、`__pa`、`virt_to_page`、`virt_to_pfn`、`virt_to_folio`、`virt_to_head_page`，以及 `sg_init_one`、`sg_set_buf` 的缓冲区参数。线性映射是内核把物理内存整块映射出来的那段虚拟地址。下面这些地址**不在线性映射里**：
- 内核镜像里的符号：arm64 等架构上，内核代码、数据、链接符号（如 `__start_xxx`、`_text`）单独映射，应该用 `__pa_symbol`、`lm_alias`；
- vmalloc、vmap、ioremap、模块的地址：所有架构都是，应该用 `vmalloc_to_page` 等；
- kmap 返回的地址：在有高端内存的 32 位架构上是。

**对每个样本回答一个问题：**

> 这个提交是否修复了（或主要是为了消除）这样一个问题：上面那些“只认线性映射地址”的接口，被用在了**不在线性映射里**的地址上？

回答：
- `yes`：修复前确实把非线性映射地址交给了这类接口，这次提交改掉了它（换成 `__pa_symbol`、`vmalloc_to_page`、加 `is_vmalloc_addr`/`virt_addr_valid` 判断、改为拷贝到线性缓冲区等）；
- `no`：不符合。例如：
  - 纯重构、改名、格式调整，修复前的代码本来就是对的；
  - 新增功能（比如新开始支持 vmalloc 缓冲区，而修复前根本不会传入这类地址）；
  - 修的是别的错误；
- `unsure`：材料不足以判断。

要求：
- 只看 `packets/` 里的材料；需要时可以在 WSL 里用 `git -C /root/repos/linux show <提交号>` 看完整提交。
- **不要读**本目录下的 `claude_labels.json`、`mined.json`、`head*`、`dev*`、`*.log` 文件，也不要运行 `linmap.py`。这是盲判，不能看分析器结果和另一位标注人的结论。
- 结果写到本目录的 `codex_labels.json`，格式为列表，每项 `{"n": 样本编号(整数), "label": "yes|no|unsure", "addr": "被误用的地址属于哪类（镜像符号/vmalloc/vmap/kmap/ioremap/模块/其他/无）", "reason": "一两句理由"}`，覆盖全部 80 个样本。
- 结束时在 `experiments/codex_worklog.md` 末尾追加一段记录（做了什么、多少个样本、各标签数量）。
- 不要修改 `packets/` 和其他任何文件。
