"""Registered fact adapters for the unified entry.

An adapter turns one stored raw input into facts (symbol -> value) plus an observation summary.
It never decides a relation. Each adapter is migrated from the experiment script named in its
module docstring and keeps that script's projection rules.
"""

from __future__ import annotations

from typing import Any, Callable, Mapping

from . import acpi_env, kernel_source, layout_arith, smmu_qtest, sparc_projection, virtio_trace

Adapter = Callable[[Mapping[str, Any]], dict[str, Any]]

REGISTRY: dict[str, tuple[str, Adapter]] = {
    "smmu_qtest": (smmu_qtest.VERSION, smmu_qtest.adapt),
    "virtio_split_trace": (virtio_trace.VERSION, virtio_trace.adapt),
    "virtio_layout": (layout_arith.VERSION, layout_arith.adapt_virtio_layout),
    "btrfs_min": (layout_arith.VERSION, layout_arith.adapt_btrfs_min),
    "acpi_env_console": (acpi_env.VERSION, acpi_env.adapt),
    "sparc_projection": (sparc_projection.VERSION, sparc_projection.adapt),
    "kernel_source_facts": (kernel_source.VERSION, kernel_source.adapt),
}
