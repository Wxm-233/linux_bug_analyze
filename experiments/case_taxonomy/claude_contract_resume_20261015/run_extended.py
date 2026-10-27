"""Extended completion allowance after a confirmed length-limited final-empty response."""
from pathlib import Path
import importlib.util,sys
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location("frozen_focused_review",HERE/"run_focused.py")
focused=importlib.util.module_from_spec(spec);sys.dont_write_bytecode=True;spec.loader.exec_module(focused)
base=focused.base
base.LEDGER=HERE/"extended_model_ledger.json";base.LOCK=HERE/".extended_review.lock"
base.CARRY=282074;base.UNKNOWN=150612;base.NEW=717926
base.PRIOR=base.PRIOR+(("focused_model_ledger.json",7922,"235e9bc7197f792b2526f1e54a88eff244091dd01cae680f4c6b35ee5c201af7"),)
base.local=lambda relative:focused.old_local("extended_plan.json" if relative=="plan.json" else relative)
prior_prepare=base.prepare
def prepare():
 p=prior_prepare()
 p["bindings"]["files"][Path(__file__).name]=base.digest(Path(__file__).read_bytes())
 p["fingerprint"]=base.digest(base.encoded(p["bindings"]))
 return p
base.prepare=prepare
if __name__=="__main__":base.main()
