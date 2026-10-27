"""Independent synthetic boundary probes; reads a hash-bound extractor snapshot.

No kernel source, device, model, or old CLI execution. Run with python -B.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE.parent.parent
sys.path.insert(0, str(BASE))
MODULE = HERE / "extractor_final_snapshot.py"
spec = importlib.util.spec_from_file_location("audit_extractor_snapshot", MODULE)
e = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = e
spec.loader.exec_module(e)


def source(text, revision="synthetic", path="synthetic.c"):
    raw = text.encode("utf-8")
    blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
    return e.Source(path, revision, path, blob, raw)


def run_case(name, kind, sources, callback, intended_boundary):
    try:
        output = callback(*[source(text, rev, path) for text, rev, path in sources])
        error = None
    except Exception as exc:
        output = None
        error = {"type": type(exc).__name__, "message": str(exc)}
    return {"name": name, "kind": kind,
            "sources": [{"text": text, "revision": rev, "path": path} for text, rev, path in sources],
            "intended_boundary": intended_boundary, "actual_output": output, "exception": error}


def main():
    cases = []

    def reads(name, expr, prefix="", head="", target="__le32", expected=""):
        text = head + f"\nstruct disk {{ {target} flags; }};\nvoid f(struct disk *p) {{ {prefix} if ({expr}) {{}} }}"
        cases.append(run_case(name, "scalar_reads", [(text, "synthetic", "scalar.c")],
                     lambda s: e.scalar_reads(s, s, "f", "p", "disk", "flags"), expected))

    reads("duplicate_occurrences_split_atoms", "le32_to_cpu(p->flags) == 1 && (p->flags & MASK)", expected="normal then candidate; separate exact occurrences")
    reads("duplicate_occurrences_same_atom", "le32_to_cpu(p->flags) | p->flags", expected="both insufficient")
    text = "typedef struct host opaque_t; struct disk { __le32 flags; }; struct host { u32 flags; };\nvoid f(struct disk *p) { { opaque_t *p; if (p->flags & MASK) {} } }"
    cases.append(run_case("opaque_pointer_shadow", "scalar_reads", [(text, "synthetic", "shadow.c")], lambda s: e.scalar_reads(s, s, "f", "p", "disk", "flags"), "refuse opaque pointer shadow"))
    text = "typedef struct host opaque_t; struct disk { __le32 flags; }; struct host { u32 flags; };\nvoid f(struct disk *p) { { opaque_t p[2]; if (p->flags & MASK) {} } }"
    cases.append(run_case("opaque_array_shadow", "scalar_reads", [(text, "synthetic", "shadow.c")], lambda s: e.scalar_reads(s, s, "f", "p", "disk", "flags"), "refuse array-typedef shadow; inner p resolves to host.flags"))
    reads("inactive_conversion_macro", "le32_to_cpu(p->flags) & MASK", head="#define le32_to_cpu(x) (x)", expected="normal must be explicitly shape-only or macro override refused")
    text = "struct disk { __le32 flags; };\nvoid f(struct disk *p) { (void)sizeof(({ if (p->flags == 0) {} 1; })); }"
    cases.append(run_case("unevaluated_if_inside_sizeof", "scalar_reads", [(text, "synthetic", "sizeof_statement.c")], lambda s: e.scalar_reads(s, s, "f", "p", "disk", "flags"), "GNU statement-expression sizeof enclosing if is not a value read"))

    fixed = "struct disk { __le32 flags; };\nvoid f(struct disk *p) { if (n < sizeof(p->flags)) {} }"
    cases.append(run_case("fixed_scalar_sizeof", "sizeof", [(fixed, "synthetic", "sizeof.c")], lambda s: e.sizeof_references(s, s, "f", "p", "disk", "flags"), "not_value_read"))
    vla = "struct disk { u32 flags[n]; };\nvoid f(struct disk *p) { if (n < sizeof(p->flags)) {} }"
    cases.append(run_case("vla_member_not_fixed_scalar", "sizeof", [(vla, "synthetic", "vla.c")], lambda s: e.sizeof_references(s, s, "f", "p", "disk", "flags"), "refuse unsupported field, rather than certify non-evaluation"))

    def init(name, before="", after="", rhs="reg", expected=""):
        text = "struct msg { __le32 reg; };\nstatic int f(u32 reg) { " + before + " struct msg msg = { .reg = " + rhs + " }; " + after + " return 0; }\nvoid caller(void) { f(0); }"
        cases.append(run_case(name, "initializer_write", [(text, "synthetic", "initializer.c")], lambda s: {"initializer": e.initializer_write(s, "f", "msg", "msg", "reg", "reg"), "domain": e.visible_call_domain(s, "f", 0)}, expected))

    init("source_parameter_assignment", before="reg = 1;", expected="initializer insufficient; zero caller cannot certify stored value")
    init("source_parameter_parenthesized_assignment", before="(reg) = 1;", expected="initializer insufficient; alternate lhs spelling still writes source")
    init("source_parameter_parenthesized_increment", before="++(reg);", expected="initializer insufficient; alternate increment spelling still writes source")
    init("target_member_reassignment", after="msg.reg = 1; handoff(&msg);", rhs="cpu_to_le32(reg)", expected="initializer may be local shape normal; must not certify actual handoff")
    init("opaque_source_shadow", before="{ opaque_t reg = raw;", after="}", expected="refuse opaque typedef source shadow")

    def domain(name, head):
        text = head + "\nstatic int getter(u32 v) { return v; }\nvoid caller(void) { getter(REG); }"
        cases.append(run_case(name, "visible_call_domain", [(text, "synthetic", "domain.c")], lambda s: e.visible_call_domain(s, "getter", 0), "insufficient: conditional macro scope unknown"))
    domain("ifdef_domain", "#ifdef CONFIG_A\n#define REG 0\n#endif")
    domain("ifndef_domain", "#ifndef CONFIG_A\n#define REG 0\n#endif")

    enum = "enum utf16_endian { UTF16_HOST_ENDIAN, UTF16_LITTLE_ENDIAN, UTF16_BIG_ENDIAN };\n"
    helper = enum + "void put_utf16(u16 *s, u16 c, enum utf16_endian endian) { switch (endian) { case UTF16_LITTLE_ENDIAN: *s = __cpu_to_le16(c); break; } }"

    def api(name, text, helper_text=helper, source_rev="synthetic", helper_rev="synthetic", expected=""):
        cases.append(run_case(name, "api_format", [(enum + text, source_rev, "api.c"), (helper_text, helper_rev, "helper.c")], lambda s, h: e.api_format(s, h, "f"), expected))

    api("api_selector_baseline", "void f(void) { utf8s_to_utf16s(s, n, UTF16_LITTLE_ENDIAN, out, cap); }", expected="local API selector shape normal")
    api("api_selector_parameter_shadow", "void f(enum utf16_endian UTF16_LITTLE_ENDIAN) { utf8s_to_utf16s(s, n, UTF16_LITTLE_ENDIAN, out, cap); }", expected="insufficient: selector is parameter, not enumerator")
    api("api_selector_local_shadow", "void f(void) { enum utf16_endian UTF16_LITTLE_ENDIAN = UTF16_BIG_ENDIAN; utf8s_to_utf16s(s, n, UTF16_LITTLE_ENDIAN, out, cap); }", expected="insufficient: selector is BE-valued local variable")
    api("api_selector_macro_override", "#define UTF16_LITTLE_ENDIAN UTF16_BIG_ENDIAN\nvoid f(void) { utf8s_to_utf16s(s, n, UTF16_LITTLE_ENDIAN, out, cap); }", expected="insufficient: selector macro overrides spelling")
    api("api_helper_overwrite", "void f(void) { utf8s_to_utf16s(s, n, UTF16_LITTLE_ENDIAN, out, cap); }", helper_text=enum + "void put_utf16(u16 *s, u16 c, enum utf16_endian endian) { switch(endian) { case UTF16_LITTLE_ENDIAN: *s = __cpu_to_le16(c); *s = __cpu_to_be16(c); break; } }", expected="normal must mean pattern presence only; cannot prove helper output LE")
    api("api_helper_constant_switch", "void f(void) { utf8s_to_utf16s(s, n, UTF16_LITTLE_ENDIAN, out, cap); }", helper_text=enum + "void put_utf16(u16 *s, u16 c, enum utf16_endian endian) { switch(UTF16_BIG_ENDIAN) { case UTF16_LITTLE_ENDIAN: *s = __cpu_to_le16(c); break; } }", expected="normal must mean pattern presence only; unreachable case is no format authority")
    api("api_helper_cross_revision", "void f(void) { utf8s_to_utf16s(s, n, UTF16_LITTLE_ENDIAN, out, cap); }", helper_rev="other", expected="refuse same-version constraint violation")

    def bitfield(name, declaration, segment, expected="", header=""):
        text = header + "\nstruct disk { " + declaration + " tl; };\nvoid f(struct disk *p) { u16 tag; " + segment + " }"
        mode = "void modes(void) { if (flags & HAL_SRNG_FLAGS_DATA_TLV_SWAP) activate(); }"
        cases.append(run_case(name, "bitfield_read", [(text, "synthetic", "bits.c"), (mode, "synthetic", "mode.c")], lambda s, m: e.bitfield_read(s, s, "f", "p", "disk", "tl", m), expected))
    bitfield("bitfield_matching_helper", "__le64", "tag = le64_get_bits(p->tl, MASK); switch(tag) {}", "normal means local helper/type shape only; helper implementation and active swap unknown")
    bitfield("bitfield_unknown_contract", "u64", "tag = u64_get_bits(p->tl, MASK); switch(tag) {}", "insufficient external format")
    bitfield("bitfield_width_mismatch", "__le32", "tag = le64_get_bits(p->tl, MASK); switch(tag) {}", "insufficient: helper width 64 differs from declared field width 32")
    bitfield("bitfield_result_overwritten", "__le64", "tag = le64_get_bits(p->tl, MASK); tag = 0; switch(tag) {}", "switch spelling is present, but dataflow dispatch not established")
    bitfield("bitfield_macro_override", "__le64", "tag = le64_get_bits(p->tl, MASK); switch(tag) {}", "normal must be shape-only or macro override refused", "#define le64_get_bits(v,m) (v)")

    result = {"extractor_snapshot_sha256": hashlib.sha256(MODULE.read_bytes()).hexdigest(),
              "probe_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "cases": cases, "case_count": len(cases), "kernel_compilation": False,
              "model_calls": 0, "old_cli_run": False}
    destination = HERE / "probe_final_output.json"
    if destination.exists():
        raise SystemExit("Refusing to replace independent probe output")
    destination.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary = [{"name": c["name"], "status": ([x.get("status") for x in c["actual_output"]] if isinstance(c["actual_output"], list) else c["actual_output"].get("status", c["actual_output"].get("initializer", {}).get("status")) if isinstance(c["actual_output"], dict) else None), "error": c["exception"]} for c in cases]
    print(json.dumps({"case_count": len(cases), "snapshot": result["extractor_snapshot_sha256"], "observed": summary}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
