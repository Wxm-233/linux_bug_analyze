"""Focused continuation after a timed-out broad query; old ledger stays frozen."""
from pathlib import Path
import importlib.util,sys
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location("frozen_http_review",HERE/"run_review.py")
base=importlib.util.module_from_spec(spec)
sys.dont_write_bytecode=True;spec.loader.exec_module(base)
base.LEDGER=HERE/"focused_model_ledger.json";base.LOCK=HERE/".focused_review.lock"
base.CARRY=274152;base.UNKNOWN=150612;base.NEW=725848
base.PRIOR=base.PRIOR+(("model_ledger.json",52225,"88cd94decb6bb0cf5ba0b9ea84c769870b320ebd06cc45ae72c749d093f8c87e"),)
old_local=base.local
base.local=lambda relative:old_local("focused_plan.json" if relative=="plan.json" else relative)
old_prepare=base.prepare
def prepare():
 p=old_prepare()
 p["bindings"]["files"][Path(__file__).name]=base.digest(Path(__file__).read_bytes())
 p["fingerprint"]=base.digest(base.encoded(p["bindings"]))
 return p
base.prepare=prepare
if __name__=="__main__":base.main()
