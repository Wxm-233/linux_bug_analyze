"""Offline command/extraction gates. Never invokes a compiler or WSL."""
import copy
import importlib.util
from pathlib import Path
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("n211_probe", HERE / "probe_compiler.py")
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


def original():
    return ["gcc", "-Wp,-MMD,kernel/sched/.core.o.d", "-O2", "-pg", "-c", "-o", "kernel/sched/core.o", probe.ORIGINAL_C]


class ProbeGates(unittest.TestCase):
    def test_single_saved_command_and_known_input_only(self):
        good = "cmd_kernel/sched/core.o := gcc -O2 -c -o kernel/sched/core.o " + probe.ORIGINAL_C
        self.assertEqual(probe.saved_argv(good.encode(), "/usr/bin/gcc")[1][-1], probe.ORIGINAL_C)
        for bad in [good + "\n" + good, good + "; echo changed", good + " extra.c", good.replace("gcc", "wrapper")]:
            with self.subTest(command=bad), self.assertRaises(ValueError): probe.saved_argv(bad.encode(), "/usr/bin/gcc")

    def test_derived_outputs_are_explicit_and_semantic_flags_preserved(self):
        argv = original(); prior = copy.deepcopy(argv)
        with tempfile.TemporaryDirectory() as folder:
            result, changes, outputs, old_outputs = probe.derive(argv, "/usr/bin/gcc", "/exact/core.i", Path(folder))
            self.assertEqual(argv, prior)
            self.assertIn("-pg", result)
            self.assertIn("-O2", result)
            self.assertNotIn("-c", result)
            self.assertNotIn("-Wp,-MMD,kernel/sched/.core.o.d", result)
            self.assertEqual(result[result.index("-x") + 1:result.index("-x") + 3], ["cpp-output", "/exact/core.i"])
            self.assertTrue(all(probe.under(path, folder) for path in outputs.values()))
            self.assertEqual(len([x for x in result if x.startswith("-fdump-tree-")]), 2)
            self.assertEqual(old_outputs, ["kernel/sched/.core.o.d", "kernel/sched/core.o"])
            self.assertTrue(changes)

    def test_extra_output_plugins_forwarding_response_and_unknown_bare_input_reject(self):
        with tempfile.TemporaryDirectory() as folder:
            for flag in ["-fplugin=/tmp/plugin.so", "-save-temps", "-fprofile-arcs", "-fdump-tree-all", "@args", "other.o", "-Wp,-MD,dep,extra", "-Wa,-a=old.lst"]:
                with self.subTest(flag=flag), self.assertRaises(ValueError):
                    probe.derive(original() + [flag], "/usr/bin/gcc", "/exact/core.i", Path(folder))

    def test_whole_function_braces_offsets_and_ambiguity_are_checked(self):
        raw = b'prefix\nvoid sched_core_cpu_starting (unsigned int cpu)\n[file.c:5:1] {\n if (cpu) { x = "}"; }\n}\nvoid later (void)\n{\n}\n'
        result = probe.extract_function(raw)
        self.assertEqual(result["status"], "unique_complete_target_section")
        self.assertEqual(raw[result["start_byte"]:result["end_byte_exclusive"]].decode(), result["text"])
        self.assertIn('x = "}";', result["text"])
        self.assertNotIn("later", result["text"])
        self.assertFalse(result["def_use_or_obligation_proved"])
        for bad in [raw + raw, raw.replace(b'}\nvoid later', b'\nvoid later'), b"no declaration"]:
            with self.subTest(raw=bad), self.assertRaises(ValueError): probe.extract_function(bad)


if __name__ == "__main__": unittest.main()
