"""Compile historical virtio_input layouts and two controlled partial edits.

The program checks cacheline overlap between the DMA event array and adjacent
CPU-owned fields. It does not perform DMA or run a virtio device.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path


FIX = "95c7b0ad6c69d1c0608ff0bbd358a546856beaf3"


def git_file(linux_dir: Path, revision: str, path: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(linux_dir), "show", f"{revision}:{path}"],
        text=True,
    )


def struct(source: str, name: str) -> str:
    start = source.index(f"struct {name} {{")
    end = source.index("};", start)
    return source[start : end + 2]


def macro(source: str, name: str) -> str:
    lines = source.splitlines()
    for pos, line in enumerate(lines):
        if line.startswith(f"#define {name}("):
            result = [line]
            while result[-1].rstrip().endswith("\\"):
                pos += 1
                result.append(lines[pos])
            return "\n".join(result)
    raise ValueError(f"macro not found: {name}")


SCAFFOLD = r"""
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
typedef uint8_t __u8;
typedef uint16_t __le16;
typedef uint32_t __le32;
typedef struct { unsigned int value; } spinlock_t;
struct virtio_device;
struct input_dev;
#define __aligned(x) __attribute__((aligned(x)))
#ifdef ARCH_DMA_MINALIGN
#define ARCH_HAS_DMA_MINALIGN
#endif
#ifdef ARCH_HAS_DMA_MINALIGN
#define ____dma_from_device_aligned __aligned(ARCH_DMA_MINALIGN)
#else
#define ____dma_from_device_aligned
#endif
"""


MAIN = r"""
int main(void)
{
    size_t event_start = offsetof(struct virtio_input, evts);
    size_t event_end = event_start + sizeof(((struct virtio_input *)0)->evts);
    size_t previous_end = offsetof(struct virtio_input, sts) +
                          sizeof(((struct virtio_input *)0)->sts);
    size_t next_start = offsetof(struct virtio_input, lock);
    size_t alignment = DMA_ALIGN;
    bool start_isolated = previous_end &&
        ((previous_end - 1) / alignment != event_start / alignment);
    bool end_isolated = event_end &&
        ((event_end - 1) / alignment != next_start / alignment);
    printf("%zu %zu %zu %zu %zu %d %d\n", previous_end, event_start,
           event_end, next_start, sizeof(struct virtio_input),
           start_isolated, end_isolated);
    return 0;
}
"""


def run(linux_dir: Path) -> dict:
    path = "drivers/virtio/virtio_input.c"
    old_source = git_file(linux_dir, FIX + "^", path)
    fixed_source = git_file(linux_dir, FIX, path)
    old = struct(old_source, "virtio_input")
    fixed = struct(fixed_source, "virtio_input")
    begin = "\t__dma_from_device_group_begin();\n"
    end = "\t__dma_from_device_group_end();\n"
    if begin not in fixed or end not in fixed:
        raise AssertionError("expected DMA boundary markers missing")
    if fixed.replace(begin, "").replace(end, "") != old:
        raise AssertionError("old/fixed struct differs beyond DMA markers")
    variants = {
        "old": old,
        "end_only_mutant": fixed.replace(begin, ""),
        "begin_only_mutant": fixed.replace(end, ""),
        "fixed": fixed,
    }
    event = struct(
        git_file(linux_dir, FIX, "include/uapi/linux/virtio_input.h"),
        "virtio_input_event",
    )
    cache = git_file(linux_dir, FIX, "include/linux/cache.h")
    dma = git_file(linux_dir, FIX, "include/linux/dma-mapping.h")
    macros = "\n".join(
        macro(source, name)
        for source, name in (
            (cache, "__cacheline_group_begin"),
            (cache, "__cacheline_group_end"),
            (dma, "__dma_from_device_group_begin"),
            (dma, "__dma_from_device_group_end"),
        )
    )
    cases = []
    with tempfile.TemporaryDirectory(prefix="virtio-dma-layout-") as tmp:
        root = Path(tmp)
        for event_count in (64, 63):
            for alignment in (64, 128):
                for name, layout in variants.items():
                    if event_count != 64:
                        layout = layout.replace("evts[64]", "evts[63]")
                    source = "\n".join((SCAFFOLD, macros, event, layout, MAIN))
                    program = root / f"{name}-{event_count}-{alignment}.c"
                    executable = root / f"{name}-{event_count}-{alignment}"
                    program.write_text(source)
                    subprocess.run(
                        [
                            "cc", "-std=gnu11", "-Wall", "-Wextra", "-Werror",
                            f"-DARCH_DMA_MINALIGN={alignment}",
                            f"-DDMA_ALIGN={alignment}", str(program),
                            "-o", str(executable),
                        ],
                        check=True,
                    )
                    fields = [int(v) for v in subprocess.check_output(
                        [str(executable)], text=True
                    ).split()]
                    previous_end, event_start, event_end, next_start, size, begin_safe, end_safe = fields
                    cases.append(
                        {
                            "variant": name,
                            "events": event_count,
                            "dma_cache_alignment": alignment,
                            "previous_cpu_field_end": previous_end,
                            "dma_array_start": event_start,
                            "dma_array_end": event_end,
                            "next_cpu_field_start": next_start,
                            "struct_size": size,
                            "start_isolated": bool(begin_safe),
                            "end_isolated": bool(end_safe),
                            "both_isolated": bool(begin_safe and end_safe),
                        }
                    )
    for item in cases:
        if item["variant"] == "fixed" and not item["both_isolated"]:
            raise AssertionError(f"fixed layout shares DMA cacheline: {item}")
        if item["variant"] == "old" and item["both_isolated"]:
            raise AssertionError(f"old layout unexpectedly isolated: {item}")
    return {
        "fix": FIX,
        "evidence_level": "historical struct/macro layout compiled with type doubles; no DMA execution",
        "old_source_sha256": hashlib.sha256(old.encode()).hexdigest(),
        "fixed_source_sha256": hashlib.sha256(fixed.encode()).hexdigest(),
        "cases_total": len(cases),
        "cases": cases,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--linux-dir", type=Path, default=Path("/root/repos/linux"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    encoded = json.dumps(run(args.linux_dir), ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(encoded)
    else:
        print(encoded, end="")
