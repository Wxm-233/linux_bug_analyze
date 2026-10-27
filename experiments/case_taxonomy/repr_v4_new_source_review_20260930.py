"""Read-only evidence collection after frozen parent reports were saved."""
import json
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = "/root/repos/linux"
MPT = "cd5897eda27dc155146f25ddf4b0dd9967b3e2bb"
BT = "7c6ca1201e5e87513b27196138f06df9cbd09a7a"


def git(*args):
    return subprocess.check_output(["git", "-C", REPO, *args], text=True)


def section(rev, path, ranges):
    lines = git("show", f"{rev}:{path}").splitlines()
    return {"revision": rev, "file": path, "lines": [
        {"line": i + 1, "text": text}
        for i, text in enumerate(lines)
        if any(start <= i + 1 <= end for start, end in ranges)
    ]}


def grep(rev, pattern, *paths):
    result = subprocess.run(["git", "-C", REPO, "grep", "-n", "-F", pattern, rev, "--", *paths], text=True, capture_output=True)
    return {"revision": rev, "pattern": pattern, "matches": result.stdout, "exit_code": result.returncode}


data = {"purpose": "independent manual source review, after frozen parent-only result manifest", "sections": [
    section(MPT, "drivers/scsi/mpt3sas/mpt3sas_base.c", [(1434, 1590), (1611, 1710), (1730, 1788)]),
    section(MPT, "drivers/scsi/mpt3sas/Kconfig", [(43, 51)]),
    section(BT, "drivers/bluetooth/hci_ll.c", [(620, 733)]),
    section(BT, "drivers/bluetooth/Kconfig", [(77, 100), (145, 156)]),
    section(MPT, "include/scsi/scsi_cmnd.h", [(179, 195)]),
    section(MPT, "drivers/scsi/mpt3sas/mpt3sas_base.c", [(1788, 1814)]),
    section(BT, "net/bluetooth/hci_request.c", [(111, 150), (177, 212), (275, 360)]),
    section("c30b93eade2ad1d77695669f25ddeb3833588d3b", "drivers/bluetooth/hci_ll.c", [(670, 671), (709, 720)]),
    section(BT, "include/linux/skbuff.h", [(2046, 2054)]),
    section(MPT, "drivers/scsi/mpt3sas/mpt3sas_base.h", [(1301, 1309)]),
    section(MPT, "drivers/scsi/mpt3sas/mpt3sas_base.c", [(3767, 3773), (4293, 4299), (5814, 5821)]),
    section("494f401bcd07d6b39f49f114e4eaa788842f16fe", "drivers/scsi/mpt3sas/mpt3sas_base.c", [(1439, 1442), (1739, 1752)]),
], "searches": [
    grep(MPT, "scsi_bufflen", "include/scsi/scsi_cmnd.h"),
    grep(MPT, "NVMe_Command", "drivers/scsi/mpt3sas/mpi"),
    grep(BT, "__hci_cmd_sync(", "net/bluetooth"),
    grep(BT, "hci_prepare_cmd(", "net/bluetooth"),
    grep(BT, "HCI_VS_UPDATE_UART_HCI_BAUDRATE", "drivers/bluetooth"),
    grep(BT, "skb_put_data(", "include/linux/skbuff.h"),
    grep(MPT, "NVME_PRP_PAGE_SIZE", "drivers/scsi/mpt3sas"),
]}
out = HERE / "repr_v4_20260930" / "new_source_review_evidence.json"
out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(out)
