"""Three checks in one report (unified criteria 一~四). Read-only aggregation of existing results.

    python unified.py     -> report_<tree>.md, summary.md, unified.json
"""
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parent
_s = importlib.util.spec_from_file_location("locate", CT / "locate_dev_20261111" / "locate.py")
LOC = importlib.util.module_from_spec(_s)
_s.loader.exec_module(LOC)          # read-only import: candidates(), HITS, text(), SC (difftest score module)
RD = CT / "fieldhint2_dev_20261111"
PV2 = CT / "pipeline_v2_20261115"
CAT = {1: "动态确认", 2: "动态检查通过", 3: "转人工", 4: "动态发现但静态归因不对或没有静态来源"}
NODATA = "（本树没有这类检查的数据）"


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


# ---------- effect dependency (pipeline_v2) ----------
def effdep(tree):
    p = PV2 / f"pipeline_{tree}.json"
    if not p.exists():
        return None
    d = load(p)
    items = {1: [], 2: [], 3: [], 4: []}
    for r in d["candidates"]:
        head = f"`{r['fn']}` 调用 `{r['interface']}`（{r['loc']}）"
        if r["class"] == "confirmed":
            bad = [a for a, h in r["per_arch"].items() if h]
            ok = [a for a, h in r["per_arch"].items() if not h]
            items[1].append(f"{head}，规则 {r['rule']}；依赖性质：`{'、'.join(r['resources'])}` 使用前必须{r['property']}；"
                            f"违反：{'、'.join(a + '（' + '、'.join(r['per_arch'][a]) + '）' for a in bad)}；成立：{'、'.join(ok) or '无'}")
        elif r["class"] == "passed":
            items[2].append(f"{head}，规则 {r['rule']}，由 {'、'.join(r['templates'])} 检查，所有架构成立")
        else:
            items[3].append(f"{head}：资源 `{'、'.join(r['resources'] or [])}`，性质“{r['property']}”；{r['why']}")
    for a, t in d["orphan_violations"]:
        items[4].append(f"{a} 上模板 {t} 违反，没有对应的静态候选")
    return items


# ---------- type consistency (fieldhint2 runs + locate) ----------
def type_sample(g):
    probes = load(CT / "rtprobe_dev_20261110" / "probes.json")
    idx = load(CT / "locate_dev_20261111" / "index" / f"{g}.json")
    cases = {str(c["id"]): c for c in load(RD / "run" / g / "cases.json")["cases"]}
    cmp_ = load(RD / "cmp" / g / "compare.json")
    kernels = list(cmp_["kernels"])
    conf = LOC.SC.read_json(RD / "confirm.json").get(g, {})
    det = sorted(LOC.SC.detecting(cmp_, f"{g.lower()}_pre", f"{g.lower()}_fix"), key=int)
    items = {1: [], 2: [], 3: [], 4: []}
    for i in det:
        if not conf.get(i, {}).get("ok"):
            continue
        cs = LOC.candidates(cases[i], idx, probes, kernels)
        hit = [c for c in cs if LOC.HITS[g](c)]
        v = cmp_["values"].get(i, {})
        phen = "；".join(f"{k} 返回 {json.loads(x)[0]}" for k, x in v.items())
        head = f"用例 {i}：`{cases[i]['sc']}` {' '.join(cases[i]['args'])}（{phen}）"
        if hit:
            items[1].append(f"{head}\n  {LOC.text(hit[0])}" + ("（第一候选）" if cs and cs[0] is hit[0] else "（非第一候选）"))
        elif cs:
            items[4].append(f"{head}\n  静态归因不对：第一候选 {LOC.text(cs[0])[2:]}")
        else:
            items[4].append(f"{head}\n  没有静态来源")
    return items


def type_current():
    probes = load(CT / "rtprobe_dev_20261110" / "probes.json")
    idx = load(CT / "locate_dev_20261111" / "index" / "CUR.json")
    cases = {str(c["id"]): c for c in load(RD / "run" / "CUR" / "cases.json")["cases"]}
    cmp_ = load(RD / "cmp" / "CUR" / "compare.json")
    kernels = list(cmp_["kernels"])
    items = {1: [], 2: [], 3: [], 4: []}
    for a, cl in cmp_["checked"]["cur_riscv"]["clusters"].items():
        for k, m in cl.items():
            cs = LOC.candidates(cases[m[0]], idx, probes, kernels)
            head = f"{a} 与众不同：{k}（{len(m)} 个用例，例 {m[0]}）"
            items[3].append(f"{head}；" + (f"候选 {LOC.text(cs[0])[2:]}" if cs else "没有静态来源") + "；需人工判断（以往各轮判断这类差异多为环境或能力差异）")
    return items


# ---------- call context (ctxcheck2 A175, dbgassert current) ----------
def ctx_a175():
    j = load(CT / "ctxcheck2_dev_20261112" / "judge_A175.json")
    kinds = {}
    for line in (CT / "ctxcheck2_dev_20261112" / "cases" / "cases.txt").read_text().splitlines():
        if line.strip():
            n, k = line.split()[:2]
            kinds[n] = k
    flag = next(s for s in load(CT / "checks_v1_20261108" / "sample_hit_review.json")["samples"] if s["id"] == "A175")
    items = {1: [], 2: [], 3: [], 4: []}
    for n in j["strong"]:
        c = j["cases"][n]
        items[1].append(f"用例 {n}（{kinds.get(n)}）：修复前 riscv 告警、修复后不告警；告警签名：{c['signatures']['a175_pre'][0]}；"
                        f"对应的静态标记：{flag['flag'].split('（')[0]}")
    for n in j["weak"]:
        c = j["cases"][n]
        items[4].append(f"用例 {n}（{kinds.get(n)}）：弱检出——修复前 riscv 和 arm64 都告警（{c['pre_verdict'][0]}），修复后只剩 arm64；"
                        "arm64 自己的问题已由上游另行修复（31575e11ecf7、0ac7584c08ce）")
    for n in j.get("noise_fix", []):
        items[4].append(f"用例 {n}（{kinds.get(n)}）：修复后仍然告警")
    return items


def ctx_current():
    st = load(CT / "checks_v1_20261108" / "stats.json")["current"]
    w = load(CT / "dbgassert_dev_20261111" / "runs" / "cases" / "warnings.json")
    case_warn = sum(1 for v in w["runs"].values() for e in v["events"] if e["phase"] != "boot")
    boot_warn = sorted({r.split(".")[0] for r, v in w["runs"].items() for e in v["events"] if e["phase"] == "boot"})
    items = {1: [], 2: [], 3: [], 4: []}
    items[3].append(f"当前版本执行上下文静态标记 {st['flags']} 条（S {st['by_kind']['S']}、I {st['by_kind']['I']}、R {st['by_kind']['R']}）。"
                    f"动态：三个调试内核跑完 8107 个用例各 3 次，用例阶段告警 {case_warn} 条，没有触发任何标记；"
                    f"启动阶段只有 {('、'.join(boot_warn) or '无')} 的一条与跨架构无关的跟踪事件格式告警。"
                    "原来那一轮从中抽 40 条人工核对：疑似真问题 0、不是 38、判断不了 2")
    return items, case_warn


def render(title, sections):
    L = [f"# 统一报告：{title}", ""]
    for name, items in sections:
        L += [f"## {name}", ""]
        if items is None:
            L += [NODATA, ""]
            continue
        L.append("、".join(f"{CAT[k]} {len(items[k])}" for k in (1, 2, 3, 4)) + "。")
        L.append("")
        for k in (1, 2, 3, 4):
            L.append(f"### {CAT[k]}")
            L.append("")
            if k == 2 and not items[k] and name != "实现一致性（效果依赖）":
                L.append("（已有数据没有逐条记录“检查了但没差异”的项）")
            show = items[k][:8]
            L += [f"- {x}" for x in show] or ["（无）"]
            if len(items[k]) > len(show):
                L.append(f"- ……另有 {len(items[k]) - len(show)} 条，见 unified.json")
            L.append("")
    return "\n".join(L) + "\n"


def main():
    out, summary = {}, []
    E, T, C = "实现一致性（效果依赖）", "类型一致性", "调用上下文"
    for tree, title in (("X1_pre", "X1 修复前"), ("X1_fix", "X1 修复后（对照）")):
        e = effdep(tree)
        out[tree] = {E: e, T: None, C: None}
        (HERE / f"report_{tree}.md").write_text(render(title, [(E, e), (T, None), (C, None)]), encoding="utf-8")
    for g in LOC.SAMPLES:
        t = type_sample(g)
        out[g] = {E: None, T: t, C: None}
        (HERE / f"report_{g}.md").write_text(render(f"{g}（修复前、修复后内核）", [(E, None), (T, t), (C, None)]), encoding="utf-8")
    c = ctx_a175()
    out["A175"] = {E: None, T: None, C: c}
    (HERE / "report_A175.md").write_text(render("A175（修复前、修复后内核）", [(E, None), (T, None), (C, c)]), encoding="utf-8")
    e, t, (c, cw) = effdep("CUR"), type_current(), ctx_current()
    out["CUR"] = {E: e, T: t, C: c}
    (HERE / "report_CUR.md").write_text(render("当前版本 7.3-rc2", [(E, e), (T, t), (C, c)]), encoding="utf-8")
    (HERE / "unified.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    S = ["# 三类检查汇总", "", "| 报告 | 检查 | 动态确认 | 动态检查通过 | 转人工 | 静态归因不对或无来源 |", "|---|---|---|---|---|---|"]
    for tree, secs in out.items():
        for name, items in secs.items():
            if items is not None:
                S.append(f"| {tree} | {name} | {len(items[1])} | {len(items[2])} | {len(items[3])} | {len(items[4])} |")
    tot1 = sum(len(out[g][T][1]) for g in LOC.SAMPLES)
    tot = sum(len(out[g][T][1]) + len(out[g][T][4]) for g in LOC.SAMPLES)
    S += ["", f"类型一致性 5 个样本：已确认检出用例 {tot}，其中候选命中修复位置 {tot1}（动态确认）。调用上下文当前版本用例阶段告警 {cw} 条。"]
    (HERE / "summary.md").write_text("\n".join(S) + "\n", encoding="utf-8")
    print("\n".join(S))


if __name__ == "__main__":
    main()
