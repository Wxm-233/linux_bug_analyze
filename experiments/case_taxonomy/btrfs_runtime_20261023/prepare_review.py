"""Prepare one source-grounded review of an already-read Btrfs case.

This script makes no network request and reads no credentials.
"""
from pathlib import Path
import hashlib
import json
import re

STAGE = Path(__file__).resolve().parent
ROOT = STAGE.parents[2]
OUTER = ROOT.parent
OUTPUT = OUTER / "模型调用测试/2026-10-23/btrfs_complete_chain_once"
PARENT = "0d977e0eba234e01a60bdde27314dc21374201b3"
FIX = "6f93e834fa7c5faa0372e46828b4b2a966ac61d7"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    if (OUTPUT / "receipt.json").exists():
        raise RuntimeError("A recorded task must not be overwritten or repeated")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    records, sections = [], []

    def excerpt(path, label, ranges, expected=None, text=None):
        data = path.read_bytes() if text is None else text.encode("utf-8")
        if expected:
            assert sha(data) == expected, label
        lines = data.decode("utf-8-sig").splitlines()
        pieces = []
        for a, b in ranges:
            assert 1 <= a <= b <= len(lines), (label, a, b)
            pieces.append("\n".join(f"{i}: {lines[i-1]}" for i in range(a, b + 1)))
        sections.append(f"## {label}\nFull source SHA256: {sha(data)}\n"
                        "Only the following original numbered ranges are supplied; gaps are omitted.\n\n"
                        + "\n\n[omitted intervening source]\n\n".join(pieces))
        records.append({"label": label, "saved_source": str(path.relative_to(ROOT)),
                        "full_source_sha256": sha(data), "ranges": ranges})

    oldbase = ROOT / "analysis_out/boundary-contracts-20260915-v2/btrfs/before"
    newbase = ROOT / "analysis_out/boundary-contracts-20260915-v2/btrfs/after"
    excerpt(oldbase / "fs_btrfs_disk-io.c", "PARENT fs/btrfs/disk-io.c",
            [(2551, 2635), (2905, 2930), (2968, 2990), (3192, 3400)],
            "55e2c1ca63518484f94e4a461d156292d23fbff4582c4f9c961c55fca3814fc7")
    excerpt(newbase / "fs_btrfs_disk-io.c", "FIX fs/btrfs/disk-io.c",
            [(3280, 3395)],
            "4c5be7ab508f0aec3af738ac9640a79d3ae6d4ee37f0d6ce6055abd401dfbf7e")
    excerpt(oldbase / "fs_btrfs_super.c", "BOTH fs/btrfs/super.c",
            [(450, 485), (775, 800), (1015, 1042), (1329, 1382),
             (1435, 1460), (1540, 1559), (1610, 1780), (1890, 1925),
             (2055, 2075), (2480, 2505)],
            "866f42dbd643afc4ac292a8dbb0157033644ea1e5ee524b0ae2633bffdd9c47a")
    excerpt(STAGE / "source_review/parent_fs__super.c", "BOTH fs/super.c",
            [(577, 635)], "36553386ca3beda8e64eea80c51a1f2a3833e353bce72261683eb47385184d1c")
    excerpt(STAGE / "source_review/parent_fs__btrfs__inode.c", "BOTH fs/btrfs/inode.c",
            [(236, 435), (652, 730), (1058, 1142)],
            "8d421890025ee2af2cb731957ea4e1191034f4c28dea207557d03b5da85ee5b2")
    excerpt(ROOT / "experiments/case_taxonomy/btrfs_geometry_authority_20261012/source/before_ctree.h",
            "BOTH fs/btrfs/ctree.h", [(234, 255), (680, 696), (972, 993),
            (1031, 1040), (1355, 1380), (1616, 1635), (2393, 2406)],
            "9e36c935aaf39fc2811b0ccd8c50c5dfbeb04daa214f5e7dfd832c7c97c258d4")
    archive = ROOT / "experiments/case_taxonomy/cross_arch_btrfs_source_20261013.json"
    old = json.loads(archive.read_text(encoding="utf-8-sig"))
    wanted = {"arch/arm64/Kconfig": [(840, 899), (937, 975)],
              "arch/arm64/include/asm/page-def.h": [(1, 18)],
              "arch/x86/include/asm/page_types.h": [(1, 39)],
              "fs/btrfs/Kconfig": [(1, 43)]}
    for item in old["new_sources"]:
        if item["git_path"] in wanted:
            assert item["representation"] == "full_source"
            excerpt(archive, "BOTH " + item["git_path"] + " (blob " + item["git_blob"] + ")",
                    wanted[item["git_path"]], text=item["text"])

    patch = (STAGE / "source_review/fix_commit.patch").read_text(encoding="utf-8")
    prompt = f"""请用中文分析一个已知的Linux历史Btrfs正确性案例，并审查后续本地QEMU实验方案。目标是研究架构/合法页大小配置对公共文件系统接口隐含要求的影响，不是发现或利用新问题。你没有工具，请只依据下面原始源码与已明确的环境事实分析；不知道的条件标为未知，不声称运行了命令。

固定版本：parent={PARENT}，fix={FIX}，Linux 5.14-rc7。本案例已经参与方法开发，给出了修复diff，因此所有结论属于已读案例机制复核，不能算独立检测、新缺陷或泛化评价。代码节选保持原始词语与行号，未覆盖的调用/配置不要补成已证明事实。

请交付一个连贯、足够深入但不过度铺陈的分析（建议约4000—6500中文字，可用表格）：
1. 建立架构或页配置约束→真实磁盘几何→fs_info准备→挂载选项裁剪→公开参数→实际文件消费的因果链。逐项引用路径、版本和行号。准确区分superblock已读取/校验与缓存是否更新；辨别临时4K恰好正确、请求遮蔽以及确实不满足要求的情形。不要将页大小配置直接等同于CPU ISA。
2. 结合通用sget和Btrfs setter/挂载分支，分析同一个fs_info如何交给消费者。区分新挂载、已有superblock复用、remount以及失败路径。只说明材料支持的对象联系，不把词法顺序称为完整控制流证明。
3. 从真实文件消费者检查max_inline允许某长度是否足以保证内联。审查起点、文件范围、扇区、元数据容量、是否压缩、subpage入口限制和插入失败。选择一种普通文件输入使旧/修复的差异在合法条件下可区分；明确哪些观察只证明生效参数，哪些才证明extent布局。还原范围未覆盖就标缺口。
4. 修正下面预设矩阵，形成可执行的最小历史内核对照方案：父/修复×ARM64原生4K/64K；磁盘sectorsize为4K的共同用途正常参照，64K只进入合法64K页配置；nodesize64K、单设备、无压缩；每次新建挂载状态。候选请求为默认/2048和8192，可增加少量确有必要的正常输入。不要把拒绝不合法镜像视为正常。列表区分源码预测、实测判定、不可适用及环境失败，避免无必要的矩阵膨胀。
5. 给出可由大模型提出、程序核实的有限契约与检查位置：配置/版本条件、原始来源、缓存写入、对象身份、消费条件、判定依据以及未知时拒判。指出怎样保留合法差异，怎样用未用于开发的同机制问题与同用途正常样本评价；不要宣称这个已知案例的断言就是可靠自动检测。
6. 最后列真正阻碍当前真实运行的少量具体事项，给出推进顺序；不要把再补若干声明、重新执行手工数值模板当作接口验证完成。

当前环境事实（不是你的执行结果）：本地Git有这两个版本；WSL有qemu-system-aarch64 8.2.2、aarch64交叉GCC13.3、cpio和aarch64静态libc。尚未安装btrfs-progs/mkfs.btrfs或busybox。已有另案6.10-rc6的ARM64/64K Image，BTRFS未启用，不能复用为本案5.14-rc7。可复用其静态initramfs打包经验，或编译普通静态C PID1。在WSL缓存中创建可丢弃普通镜像，仅在QEMU guest挂载，不碰宿主块设备。目前本Btrfs案例没有任何真实挂载、内核启动或extent布局实验；已有局部数值/字段投影不是这些实验的替代品。

待审假设，仅是源码预测：请求8192时，64K页+64K盘父版可能裁为4096，修复为8192；4K盘可能前后均4096。请自行查核适用条件、证据缺口和反例，不要因为这些预测已写出就默认全部成立。普通文件是否真的inline尚待实际布局证据。需要区分正常、遮蔽、不进路径与未知。

## 已知修复（原文）
{patch}

## 原始源码材料
""" + "\n\n".join(sections)
    assert not re.search(r"\bsk-[A-Za-z0-9_-]{12,}", prompt)
    (OUTPUT / "prompt.md").write_text(prompt, encoding="utf-8")
    manifest = {"parent": PARENT, "fix": FIX, "case_status": "previously_read_development_case",
                "source_records": records, "prompt_sha256": sha(prompt.encode()),
                "prompt_utf8_bytes": len(prompt.encode()),
                "output_directory": str(OUTPUT.relative_to(OUTER)),
                "authorization": "2026-10-23 user: one final Btrfs analysis attempt",
                "scope": "original task and source wording; no replay of refused OCFS2 task",
                "runner_calls_planned": 1, "runner_retries": 0,
                "round_ceiling": 1000000, "reservation": 200000,
                "internal_cli_recovery": "not fully observable; do not claim one upstream inference",
                "on_refusal_or_incomplete": "save receipt; no reformulation, no retry, no use of refused partial analysis",
                "runtime_tests_in_this_preparation": 0}
    (STAGE / "review_materials.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "prepared_no_network", "prompt_bytes": len(prompt.encode()),
                      "source_records": len(records), "output": str(OUTPUT)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
