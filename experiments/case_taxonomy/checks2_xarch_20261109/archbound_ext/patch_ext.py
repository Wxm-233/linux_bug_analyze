# Claude 2026-11-09: the three additions to archbound collect required by criteria section 2 (checks2_xarch_20261109).
#   1. per-unit parse status in the facts ("units")
#   2. integer-constant value of every call argument ("argConsts", "" when not an integer constant expression)
#   3. integer constants of every return statement ("retConsts") and whether a non-constant return exists ("retNonConst")
from pathlib import Path
src = Path(__file__).resolve().parent / "src"
def rep(f, a, b):
    p = src / f; s = p.read_text(encoding="utf-8")
    assert s.count(a) == 1, (f, a[:60], s.count(a)); p.write_text(s.replace(a, b), encoding="utf-8")

# ---- Facts.h
rep("Facts.h", "  std::vector<DangerUse> dangerUses;\n};", "  std::vector<DangerUse> dangerUses;\n"
    "  std::vector<std::string> retConsts; // [ext] integer constants returned\n"
    "  bool retNonConst = false;           // [ext] some return is not an integer constant\n};")
rep("Facts.h", "  bool usesRet = false;    // call result is consumed (not a bare \"foo();\")\n};",
    "  bool usesRet = false;    // call result is consumed (not a bare \"foo();\")\n"
    "  std::vector<std::string> argConsts; // [ext] per argument: integer constant value or \"\"\n};")
rep("Facts.h", "// A single arch's collected facts (produced by one `collect` run).\nstruct Facts {",
    "// [ext] parse status of one compile unit\nstruct UnitFact {\n  std::string file;\n  int status = 0; // ClangTool::run result: 0 ok, 1 error, 2 skipped\n};\n\n"
    "// A single arch's collected facts (produced by one `collect` run).\nstruct Facts {")
rep("Facts.h", "  std::vector<GlobalFlow> globalFlows;\n};\n\nllvm::json::Value toJSON(const TypeInfo &t);",
    "  std::vector<GlobalFlow> globalFlows;\n  std::vector<UnitFact> units; // [ext]\n};\n\nllvm::json::Value toJSON(const TypeInfo &t);")

# ---- Facts.cpp
rep("Facts.cpp", "  o[\"dangerUses\"] = std::move(dangerUses);\n  return Value(std::move(o));",
    "  o[\"dangerUses\"] = std::move(dangerUses);\n  Array retConsts;\n  for (const auto &r : d.retConsts)\n    retConsts.push_back(r);\n"
    "  o[\"retConsts\"] = std::move(retConsts);\n  o[\"retNonConst\"] = d.retNonConst;\n  return Value(std::move(o));")
rep("Facts.cpp", "  o[\"usesRet\"] = c.usesRet;\n  return Value(std::move(o));",
    "  o[\"usesRet\"] = c.usesRet;\n  Array argConsts;\n  for (const auto &a : c.argConsts)\n    argConsts.push_back(a);\n"
    "  o[\"argConsts\"] = std::move(argConsts);\n  return Value(std::move(o));")
rep("Facts.cpp", "  o[\"globalFlows\"] = std::move(globalFlows);\n  return Value(std::move(o));",
    "  o[\"globalFlows\"] = std::move(globalFlows);\n  Array units;\n  for (const auto &u : f.units) {\n    Object uo;\n"
    "    uo[\"file\"] = u.file;\n    uo[\"status\"] = u.status;\n    units.push_back(Value(std::move(uo)));\n  }\n"
    "  o[\"units\"] = std::move(units);\n  return Value(std::move(o));")

# ---- Collect.cpp
rep("Collect.cpp", "    CurDangerUses.clear();\n    CondDepth = 0;", "    CurDangerUses.clear();\n    CurRetConsts.clear();\n    CurRetNonConst = false;\n    CondDepth = 0;")
rep("Collect.cpp", "      recordFlow(\"return\", CurFn->getReturnType(), RS->getRetValue(), RS->getBeginLoc(), \"\");\n    return true;",
    "      recordFlow(\"return\", CurFn->getReturnType(), RS->getRetValue(), RS->getBeginLoc(), \"\");\n"
    "    if (CurFn && RS->getRetValue()) { // [ext] constant return values\n"
    "      std::string v = intConst(RS->getRetValue());\n"
    "      if (v.empty()) CurRetNonConst = true; else CurRetConsts.insert(v);\n    }\n    return true;")
rep("Collect.cpp", "      c.args.push_back(classify(CE->getArg(i)->IgnoreParenImpCasts()->getType(), *S.Ctx));",
    "      c.args.push_back(classify(CE->getArg(i)->IgnoreParenImpCasts()->getType(), *S.Ctx));\n"
    "    for (unsigned i = 0; i < CE->getNumArgs(); i++) // [ext] constant argument values\n"
    "      c.argConsts.push_back(intConst(CE->getArg(i)));")
rep("Collect.cpp", "    d.dangerUses = CurDangerUses;\n    return d;",
    "    d.dangerUses = CurDangerUses;\n    d.retConsts.assign(CurRetConsts.begin(), CurRetConsts.end());\n    d.retNonConst = CurRetNonConst;\n    return d;")
rep("Collect.cpp", "  int CondDepth = 0;               // >0 inside if/while/for/do/switch/?:/&&/||",
    "  std::set<std::string> CurRetConsts; // [ext]\n  bool CurRetNonConst = false;        // [ext]\n"
    "  // [ext] integer constant value of E, or \"\" when E is not an integer constant expression\n"
    "  std::string intConst(Expr *E) {\n    if (!E || E->isValueDependent() || E->isTypeDependent())\n      return \"\";\n"
    "    Expr::EvalResult R;\n    if (!E->EvaluateAsInt(R, *S.Ctx))\n      return \"\";\n"
    "    llvm::SmallString<32> Buf;\n    R.Val.getInt().toString(Buf, 10);\n    return Buf.str().str();\n  }\n"
    "  int CondDepth = 0;               // >0 inside if/while/for/do/switch/?:/&&/||")
# per-unit status (both sequential and parallel modes go through one ClangTool per file)
rep("Collect.cpp", "  if (OptJobs == 0) {\n    ClangTool Tool(*DB, SourcePaths);\n    Tool.run(newFrontendActionFactory<CollectAction>().get());\n  } else {",
    "  if (OptJobs == 0) {\n    for (const auto &Path : SourcePaths) { // [ext] one tool per file to record its status\n"
    "      ClangTool T(*DB, {Path});\n      int rc = T.run(newFrontendActionFactory<CollectAction>().get());\n"
    "      std::lock_guard<std::mutex> L(GShared.M);\n      GShared.units.push_back({Path, rc});\n    }\n  } else {")
rep("Collect.cpp", "            ClangTool T(*DB, {Path}, std::make_shared<PCHContainerOperations>(), FS);\n            T.run(newFrontendActionFactory<CollectAction>().get());",
    "            ClangTool T(*DB, {Path}, std::make_shared<PCHContainerOperations>(), FS);\n"
    "            int rc = T.run(newFrontendActionFactory<CollectAction>().get());\n"
    "            std::lock_guard<std::mutex> L(GShared.M); // [ext]\n            GShared.units.push_back({Path, rc});")
rep("Collect.cpp", "  std::vector<arb::GlobalFlow> globalFlows;\n\n  void merge(TUState &S) {",
    "  std::vector<arb::GlobalFlow> globalFlows;\n  std::vector<arb::UnitFact> units; // [ext]\n\n  void merge(TUState &S) {")
rep("Collect.cpp", "  F.globalFlows = GShared.globalFlows;", "  F.globalFlows = GShared.globalFlows;\n  F.units = GShared.units;")
print("patched")
