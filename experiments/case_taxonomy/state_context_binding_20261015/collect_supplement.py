"""Collect explicit same-revision source context; never read a credential or patch."""
from pathlib import Path
import subprocess,json,hashlib,argparse
HERE=Path(__file__).resolve().parent
REV="88b604263f3d6eedae0b1c2c3bbd602d1e2e8775"
WINDOWS=[("X_core_storage","kernel/sched/core.c",42,48),("X_lock_guard_open","kernel/sched/core.c",84,94),("X_lock_functions","kernel/sched/core.c",240,261),("X_lock_guard_close","kernel/sched/core.c",359,366),("X_starting_guard_open","kernel/sched/core.c",5340,5347),("X_core_stubs","kernel/sched/core.c",5838,5865),("X_rq_init","kernel/sched/core.c",9090,9140),("X_topology_include","include/linux/topology.h",28,40),("X_topology_mask","include/linux/topology.h",185,212),("X_x86_topology","arch/x86/include/asm/topology.h",110,132),("X_s390_topology","arch/s390/include/asm/topology.h",1,64),("X_rq_macro","kernel/sched/sched.h",1350,1360),("X_core_kconfig","kernel/Kconfig.preempt",103,121)]
def main():
 parser=argparse.ArgumentParser();parser.add_argument("--repo",required=True);args=parser.parse_args()
 if (HERE/"model_ledger.json").exists(): raise RuntimeError("Do not change inputs after ledger initialization")
 cache={};docs=[]
 for ident,path,lo,hi in WINDOWS:
  if path not in cache: cache[path]=subprocess.check_output(["git","-C",args.repo,"show",REV+":"+path])
  raw=cache[path];lines=raw.decode().splitlines()
  if hi>len(lines): raise ValueError(path+" source interval too long")
  docs.append({"id":ident,"kind":"source","path":path,"revision":REV,"start_line":lo,"end_line":hi,"full_original_file_sha256":hashlib.sha256(raw).hexdigest(),"source":"local_git_object_original_uninstrumented","text":"\n".join(str(n)+": "+lines[n-1] for n in range(lo,hi+1))})
 p=HERE/"source_packet.json";packet=json.loads(p.read_text(encoding="utf-8"))
 assert packet["revision"]==REV
 packet["supplemental_documents"]=docs
 packet["supplement_note"]="Explicit same-revision original source additions for branch/configuration and initialization review; no fix/runtime/reviewer answer included. Noncontiguous excerpts are not complete translation units."
 p.write_text(json.dumps(packet,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print(json.dumps({"supplemental_documents":len(docs),"supplemental_lines":sum(d["end_line"]-d["start_line"]+1 for d in docs),"packet_bytes":p.stat().st_size,"revision":REV}))
if __name__=="__main__":main()
