"""Independent expected source uses for the hand-written fixture."""
import gzip
import json
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import enumerate as enum


def main():
    source = HERE / "src"
    work = Path(os.environ["KBUILD"]) / "enumeration/selftest"
    work.mkdir(parents=True, exist_ok=True)
    generated = work / "arch/test/include/generated/asm/generated_api.h"
    generated.parent.mkdir(parents=True, exist_ok=True)
    generated.write_bytes((HERE / "generated_api.h").read_bytes())
    files = ["kernel/user.c", "kernel/second.c", "arch/test/implementation.c", "arch/test/from_asm.S"]
    rows = []
    for file in files:
        output = str(Path(file).with_suffix(".o"))
        (work / output).parent.mkdir(parents=True, exist_ok=True)
        argv = ["clang", "--target=x86_64-linux-gnu", "-I" + str(source / "include"),
                "-I" + str(source / "arch/test/include"),
                "-I" + str(work / "arch/test/include/generated"),
                "-fno-pie", "-c", "-o", output, str(source / file)]
        enum.command(argv, cwd=work)
        rows.append({"directory": str(work), "file": str(source / file), "arguments": argv})
    enum.save_json(work / "compile_commands.json", rows)
    objects = [str(Path(file).with_suffix(".o")) for file in files]
    enum.command(["llvm-ar", "crsT", "vmlinux.a", *objects], cwd=work)
    enum.command(["ld.lld", "-e", "user", "-o", "vmlinux", "--whole-archive", "vmlinux.a"], cwd=work)
    cache = work / enum.sha256(HERE.parent / "enumerate.py")
    build = enum.Build("test", source, work, enum.load_entries(work / "compile_commands.json"), cache, {})
    enum.scan(build, jobs=1, limit=100)
    result = enum.merge(build, work)
    assert result["parse_failed_units"] == 0, result
    symbols = enum.load_json(work / "symbols_test.json")
    with gzip.open(work / "boundary_test.jsonl.gz", "rt") as stream:
        points = [json.loads(line) for line in stream]
    actual = {
        (p["use"]["file"], p["use"]["line"], p["use"]["column"],
         symbols[p["symbol_id"]]["name"], p["action"])
        for p in points
    }
    expected = set()
    def expect(file, line, token, name, action):
        text = (source / file).read_text().splitlines()[line - 1]
        assert text.count(token) == 1, (file, line, token)
        expected.add((file, line, text.index(token) + 1, name, action))
    for line, token, name, action in [
        (11, "arch_item", "arch_item", "type"), (11, "arch_value", "arch_value", "type"),
        (13, "arch_word", "arch_word", "type"), (13, "ARCH_LIMIT", "ARCH_LIMIT", "read"),
        (14, "arch_data", "arch_data", "write"), (15, "arch_data", "arch_data", "read_write"),
        (16, "arch_data", "arch_data", "address"), (17, "arch_call", "arch_call", "address"),
        (18, "value +", "arch_item", "type"), (18, "i +", "arch_value", "type"),
        (18, "arch_data", "arch_data", "read"), (19, "arch_call", "arch_call", "call"),
        (19, "fallback", "fallback", "call"), (19, "hook", "hook", "call"),
        (19, "GENERATED_CONSTANT", "GENERATED_CONSTANT", "macro_expand"),
        (20, "ARCH_INCREMENT", "ARCH_INCREMENT", "macro_expand"),
    ]:
        expect("kernel/user.c", line, token, name, action)
    expect("include/shared_inline.h", 4, "arch_call", "arch_call", "call")
    expect("arch/test/implementation.c", 5, "shared_call", "shared_call", "call")
    expect("arch/test/implementation.c", 5, "shared_data", "shared_data", "read")
    assert actual == expected, {"missing": sorted(expected - actual), "extra": sorted(actual - expected)}
    shared = [p for p in points if p["use"]["file"] == "include/shared_inline.h"]
    assert len(shared) == 1 and shared[0]["units"] == [0, 1], shared
    nm = enum.load_json(work / "object_evidence_test.json.gz")
    assert set(nm["weak_overrides"]) == {"hook"}, nm
    assert [(p["symbol"], p["direction"]) for p in nm["asm_boundaries"]] == [
        ("shared_call", "arch_to_public")], nm
    assert not nm["asm_unresolved"], nm
    assert next(s for s in symbols if s["name"] == "hook")["definition"]["file"] == "arch/test/implementation.c"
    enum.save_json(HERE / "result.json", {"status": "passed", "points": len(points),
                    "symbols": len(symbols), "enumerate_sha256": enum.sha256(HERE.parent / "enumerate.py")})
    print("SELFTEST PASSED", len(points), "points")


if __name__ == "__main__":
    main()
