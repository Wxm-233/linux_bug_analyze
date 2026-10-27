"""Compile historical bpos/bkey declarations for little/big-endian layout checks.

This uses the exact three struct definitions from the selected Linux revision;
only kernel scalar types and attribute macros are stubbed. It is a layout
probe, not a historical kernel build or a filesystem I/O test.
"""

import argparse
import json
import re
import subprocess
import tempfile
from pathlib import Path


FIX = "3f3ae1250e739fb446639efad0ba916ba0a012f0"
HEADER = "fs/bcachefs/bcachefs_format.h"


def git_show(repo: Path, revision: str, path: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(repo), "show", f"{revision}:{path}"], text=True
    )


def structure(source: str, name: str) -> str:
    match = re.search(rf"(?m)^struct {re.escape(name)} \{{", source)
    if not match:
        raise ValueError(f"missing struct {name}")
    opened = source.index("{", match.start())
    depth = 0
    for index in range(opened, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                end = source.index(";", index) + 1
                return source[match.start():end]
    raise ValueError(f"unclosed struct {name}")


def c_source(header: str) -> str:
    structs = "\n\n".join(structure(header, name) for name in
                           ("bpos", "bversion", "bkey"))
    return """#include <stddef.h>
#include <stdio.h>
typedef unsigned char __u8;
typedef unsigned int __u32;
typedef unsigned long long __u64;
#define __packed __attribute__((packed))
#define __aligned(n) __attribute__((aligned(n)))
#if __BYTE_ORDER__ == __ORDER_LITTLE_ENDIAN__
#define __LITTLE_ENDIAN_BITFIELD 1
#elif __BYTE_ORDER__ == __ORDER_BIG_ENDIAN__
#define __BIG_ENDIAN_BITFIELD 1
#else
#error unsupported byte order
#endif
""" + structs + """

int main(void)
{
    size_t declared = _Alignof(struct bpos);
    size_t embedded = offsetof(struct bkey, p);
    printf("{\\"bpos_size\\":%zu,\\"bpos_declared_align\\":%zu,"
           "\\"bkey_size\\":%zu,\\"bkey_align\\":%zu,"
           "\\"embedded_bpos_offset\\":%zu,"
           "\\"embedded_offset_meets_declared_align\\":%s}\\n",
           sizeof(struct bpos), declared, sizeof(struct bkey),
           _Alignof(struct bkey), embedded,
           embedded % declared == 0 ? "true" : "false");
    return 0;
}
"""


def measure(source: str, compiler: str, runner: list[str]) -> dict:
    with tempfile.TemporaryDirectory(prefix="bcachefs-bpos-") as tmp:
        root = Path(tmp)
        c_file = root / "layout.c"
        binary = root / "layout"
        c_file.write_text(source, encoding="utf-8")
        build = subprocess.run(
            [compiler, "-std=gnu11", "-O0", "-Wall", "-Wextra", str(c_file),
             "-o", str(binary)], text=True, capture_output=True, check=True
        )
        output = subprocess.check_output([*runner, str(binary)], text=True)
        return {"layout": json.loads(output), "compiler_stderr": build.stderr}


def run(linux_dir: Path) -> dict:
    result = {"fix": FIX, "source_path": HEADER,
              "method": "extract historical bpos/bversion/bkey declarations; compile as C with only scalar/attribute stubs; execute x86_64 natively and s390x via qemu user mode",
              "invariant": "offsetof(struct bkey, p) is a multiple of declared alignof(struct bpos)",
              "profiles": {}}
    for label, revision in (("old", FIX + "^"), ("fixed", FIX)):
        header = git_show(linux_dir, revision, HEADER)
        source = c_source(header)
        for profile, compiler, runner in (
            ("x86_64_little", "gcc", []),
            ("s390x_big", "s390x-linux-gnu-gcc", ["qemu-s390x", "-L", "/usr/s390x-linux-gnu"]),
        ):
            result["profiles"].setdefault(profile, {})[label] = measure(source, compiler, runner)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--linux-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    outcome = run(args.linux_dir)
    args.output.write_text(json.dumps(outcome, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")
    print(json.dumps({profile: {revision: data["layout"]["embedded_offset_meets_declared_align"]
                                for revision, data in versions.items()}
                      for profile, versions in outcome["profiles"].items()}))


if __name__ == "__main__":
    main()
