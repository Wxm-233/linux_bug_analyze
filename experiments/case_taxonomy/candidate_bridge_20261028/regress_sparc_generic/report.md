# Unified check report

| case | family / mechanism | tier | adapter | inputs | status | decisions | expected match |
| --- | --- | --- | --- | ---: | --- | --- | --- |
| sparc_width_generic | cpu_identity_range / compiled width branch (generic facts) | compiled_object | kernel_source_facts | 4 | {'judged': 4} | {'satisfied': 4} | 4/4 |

Deadline and whole-path results are reported per relation in the JSON; a sample never establishes the deadline.
`unsupported` inputs had no registered adapter and were not judged.
