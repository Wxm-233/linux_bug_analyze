# Unified check report

| case | family / mechanism | tier | adapter | inputs | status | decisions | expected match |
| --- | --- | --- | --- | ---: | --- | --- | --- |
| acpi_env | firmware_platform / scoped policy provider | archived_runtime | acpi_env_console | 4 | {'judged': 4} | {'satisfied': 5, 'violated': 3} | 4/4 |
| btrfs_min | memory_geometry / clipping arithmetic (min) | archived_runtime | btrfs_min | 12 | {'judged': 12} | {'satisfied': 11, 'violated': 1} | 12/12 |
| smmu_qtest | iommu / ordered command submission | archived_runtime | smmu_qtest | 14 | {'judged': 14} | {'violated': 3, 'satisfied': 5, 'not_applicable': 2, 'insufficient': 4} | 14/14 |
| sparc_compiled_objects | cpu_identity_range / compiled width branch | compiled_object | sparc_objects | 1 | {'unsupported': 1} | {} | 0/0 |
| sparc_identity_chain | cpu_identity_range / identity/count/preparation | source_projection | sparc_projection | 24 | {'judged': 24} | {'satisfied': 89, 'not_applicable': 16, 'violated': 15} | 24/24 |
| virtio_layout | dma / maintenance-granule isolation (floor_to) | archived_runtime | virtio_layout | 4 | {'judged': 4} | {'violated': 2, 'satisfied': 2} | 4/4 |
| virtio_split_trace | dma / per-object publication/recycle order | archived_runtime | virtio_split_trace | 60 | {'judged': 60} | {'satisfied': 109, 'violated': 5, 'insufficient': 6} | 60/60 |

Deadline and whole-path results are reported per relation in the JSON; a sample never establishes the deadline.
`unsupported` inputs had no registered adapter and were not judged.
