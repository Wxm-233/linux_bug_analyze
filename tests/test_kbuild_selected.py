import tempfile
import unittest
from pathlib import Path

from linux_bug_analyze.kernel_facts import BUNDLE_SCHEMA, kbuild_selected, query


def tree(files):
    root = Path(tempfile.mkdtemp())
    for rel, text in files.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(text)
    return root


FILES = {
    "drivers/Makefile": "obj-y\t+= base/ \\\n\tfirmware/\n",
    "drivers/base/Makefile": "obj-y := core.o \\\n\t topology.o\nobj-$(CONFIG_GENERIC_ARCH_TOPOLOGY) += arch_topology.o\n",
    "drivers/firmware/Makefile": "obj-y += efi/\nifeq ($(CONFIG_SYSFS),y)\nobj-y += sysfb.o\nendif\n",
    "drivers/firmware/efi/Makefile": "subdir-$(CONFIG_EFI_STUB) += libstub\n",
    "drivers/firmware/efi/libstub/Makefile": "lib-y := helper.o\nlib-$(CONFIG_EFI_GENERIC_STUB) += efi-stub.o string.o\n",
    "mm/Makefile": "mmu-$(CONFIG_MMU) := memory.o\nobj-y := filemap.o shmem.o\nfoo-y := part.o\nobj-$(CONFIG_FOO) += foo.o\n",
}


class KbuildSelectedTest(unittest.TestCase):
    def setUp(self):
        self.src = tree(FILES)

    def test_selection(self):
        s = lambda p, cfg: kbuild_selected(self.src, p, cfg)["value"]
        self.assertTrue(s("drivers/base/topology.c", {}))
        self.assertTrue(s("mm/shmem.c", {}))
        self.assertFalse(s("drivers/base/arch_topology.c", {}))
        self.assertTrue(s("drivers/base/arch_topology.c", {"CONFIG_GENERIC_ARCH_TOPOLOGY": True}))
        lib = "drivers/firmware/efi/libstub/string.c"
        self.assertTrue(s(lib, {"CONFIG_EFI_STUB": True, "CONFIG_EFI_GENERIC_STUB": True}))
        self.assertFalse(s(lib, {"CONFIG_EFI_STUB": True}))                       # x86-like: no generic stub
        self.assertFalse(s(lib, {"CONFIG_EFI_GENERIC_STUB": True}))               # directory not selected
        self.assertIsNone(s("drivers/firmware/sysfb.c", {"CONFIG_SYSFS": True}))  # only inside ifeq: unknown
        self.assertIsNone(s("mm/unknown.c", {}))
        self.assertTrue(s("mm/part.c", {"CONFIG_FOO": "m"}))                     # composite object part
        self.assertFalse(s("mm/part.c", {}))

    def test_query(self):
        b = {"schema": BUNDLE_SCHEMA, "revision": "r", "config": {}, "files": {
            "a.c": {"kbuild_selected": {"value": False, "trail": []}}, "b.c": {"kbuild_selected": {"value": None, "trail": []}}}}
        self.assertEqual(query(b, {"kind": "kbuild_selected", "file": "a.c"}), (True, False))
        self.assertEqual(query(b, {"kind": "kbuild_selected", "file": "b.c"}), (False, "kbuild_unknown"))
        self.assertFalse(query(b, {"kind": "kbuild_selected", "file": "c.c"})[0])


if __name__ == "__main__":
    unittest.main()
