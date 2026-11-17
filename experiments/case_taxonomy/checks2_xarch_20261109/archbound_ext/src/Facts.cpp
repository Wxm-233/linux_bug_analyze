#include "Facts.h"

namespace arb {

using llvm::json::Array;
using llvm::json::Object;
using llvm::json::Value;

llvm::json::Value toJSON(const TypeInfo &t) {
  Object o;
  o["spelling"] = t.spelling;
  o["size"] = t.sizeBits;
  o["int"] = t.isInt;
  o["signed"] = t.isSigned;
  o["fixed"] = t.fixed;
  o["archwidth"] = t.archwidth;
  return Value(std::move(o));
}

llvm::json::Value toJSON(const DispatchCtx &d) {
  Object o;
  o["kind"] = d.kind;
  o["condLoc"] = d.condLoc;
  o["cond"] = d.cond;
  return Value(std::move(o));
}

llvm::json::Value toJSON(const WriteLoc &w) {
  Object o;
  o["resource"] = w.resource;
  o["file"] = w.file;
  o["line"] = w.line;
  o["kind"] = w.kind;
  return Value(std::move(o));
}

llvm::json::Value toJSON(const DangerUse &d) {
  Object o;
  o["param"] = d.param;
  o["kind"] = d.kind;
  o["callee"] = d.callee;
  o["file"] = d.file;
  o["line"] = d.line;
  return Value(std::move(o));
}

llvm::json::Value toJSON(const DefFact &d) {
  Object o;
  o["usr"] = d.usr;
  o["name"] = d.name;
  o["file"] = d.file;
  o["line"] = d.line;
  o["static"] = d.isStatic;
  o["def"] = d.isDef;
  o["ret"] = toJSON(d.ret);
  Array params;
  for (const auto &p : d.params)
    params.push_back(toJSON(p));
  o["params"] = std::move(params);
  o["bodyKind"] = d.bodyKind;
  o["constVal"] = d.constVal;
  Array accesses, writes;
  for (const auto &a : d.accesses)
    accesses.push_back(a);
  for (const auto &w : d.writes)
    writes.push_back(w);
  o["accesses"] = std::move(accesses);
  o["writes"] = std::move(writes);
  Array soft;
  for (const auto &s : d.soft)
    soft.push_back(s);
  o["soft"] = std::move(soft);
  Array checked, dangerous;
  for (const auto &c : d.checked)
    checked.push_back(c);
  for (const auto &dg : d.dangerous)
    dangerous.push_back(dg);
  o["checked"] = std::move(checked);
  o["dangerous"] = std::move(dangerous);
  Array writeLocs, dangerUses;
  for (const auto &w : d.writeLocs)
    writeLocs.push_back(toJSON(w));
  for (const auto &u : d.dangerUses)
    dangerUses.push_back(toJSON(u));
  o["writeLocs"] = std::move(writeLocs);
  o["dangerUses"] = std::move(dangerUses);
  Array retConsts;
  for (const auto &r : d.retConsts)
    retConsts.push_back(r);
  o["retConsts"] = std::move(retConsts);
  o["retNonConst"] = d.retNonConst;
  return Value(std::move(o));
}

llvm::json::Value toJSON(const CallFact &c) {
  Object o;
  o["callerUsr"] = c.callerUsr;
  o["callerName"] = c.callerName;
  o["callerFile"] = c.callerFile;
  o["callerLine"] = c.callerLine;
  o["calleeUsr"] = c.calleeUsr;
  o["calleeName"] = c.calleeName;
  o["file"] = c.file;
  o["line"] = c.line;
  Array args, params;
  for (const auto &a : c.args)
    args.push_back(toJSON(a));
  for (const auto &p : c.params)
    params.push_back(toJSON(p));
  o["args"] = std::move(args);
  o["params"] = std::move(params);
  o["ctx"] = toJSON(c.ctx);
  o["usesRet"] = c.usesRet;
  Array argConsts;
  for (const auto &a : c.argConsts)
    argConsts.push_back(a);
  o["argConsts"] = std::move(argConsts);
  return Value(std::move(o));
}

llvm::json::Value toJSON(const PPFact &p) {
  Object o;
  o["file"] = p.file;
  o["line"] = p.line;
  o["kind"] = p.kind;
  o["cond"] = p.cond;
  return Value(std::move(o));
}

llvm::json::Value toJSON(const FlowFact &f) {
  Object o;
  o["kind"] = f.kind;
  o["func"] = f.func;
  o["file"] = f.file;
  o["line"] = f.line;
  o["lhs"] = toJSON(f.lhs);
  o["rhs"] = toJSON(f.rhs);
  o["lhsName"] = f.lhsName;
  o["rhsName"] = f.rhsName;
  return Value(std::move(o));
}

llvm::json::Value toJSON(const GlobalDef &g) {
  Object o;
  o["name"] = g.name;
  o["file"] = g.file;
  return Value(std::move(o));
}

llvm::json::Value toJSON(const MacroFact &m) {
  Object o;
  o["name"] = m.name;
  o["file"] = m.file;
  o["kind"] = m.kind;
  return Value(std::move(o));
}

llvm::json::Value toJSON(const MacroRes &r) {
  Object o;
  o["macro"] = r.macro;
  o["resource"] = r.resource;
  return Value(std::move(o));
}

llvm::json::Value toJSON(const GlobalFlow &g) {
  Object o;
  o["global"] = g.global;
  o["file"] = g.file;
  o["line"] = g.line;
  o["lhs"] = toJSON(g.lhs);
  o["rhs"] = toJSON(g.rhs);
  o["srcVar"] = g.srcVar;
  return Value(std::move(o));
}

llvm::json::Value toJSON(const Facts &f) {
  Object o;
  o["arch"] = f.arch;
  o["root"] = f.root;
  Array defs, calls, pps, flows, globals, macros, macroRes, globalFlows;
  for (const auto &d : f.defs)
    defs.push_back(toJSON(d));
  for (const auto &c : f.calls)
    calls.push_back(toJSON(c));
  for (const auto &p : f.pps)
    pps.push_back(toJSON(p));
  for (const auto &fl : f.flows)
    flows.push_back(toJSON(fl));
  for (const auto &g : f.globals)
    globals.push_back(toJSON(g));
  for (const auto &m : f.macros)
    macros.push_back(toJSON(m));
  for (const auto &r : f.macroRes)
    macroRes.push_back(toJSON(r));
  for (const auto &g : f.globalFlows)
    globalFlows.push_back(toJSON(g));
  o["defs"] = std::move(defs);
  o["calls"] = std::move(calls);
  o["pps"] = std::move(pps);
  o["flows"] = std::move(flows);
  o["globals"] = std::move(globals);
  o["macros"] = std::move(macros);
  o["macroRes"] = std::move(macroRes);
  o["globalFlows"] = std::move(globalFlows);
  Array units;
  for (const auto &u : f.units) {
    Object uo;
    uo["file"] = u.file;
    uo["status"] = u.status;
    units.push_back(Value(std::move(uo)));
  }
  o["units"] = std::move(units);
  return Value(std::move(o));
}

TypeInfo typeFromJSON(const Value &v) {
  TypeInfo t;
  const Object *o = v.getAsObject();
  if (!o)
    return t;
  if (auto s = o->getString("spelling"))
    t.spelling = s->str();
  if (auto i = o->getInteger("size"))
    t.sizeBits = (int)*i;
  if (auto b = o->getBoolean("int"))
    t.isInt = *b;
  if (auto b = o->getBoolean("signed"))
    t.isSigned = *b;
  if (auto b = o->getBoolean("fixed"))
    t.fixed = *b;
  if (auto b = o->getBoolean("archwidth"))
    t.archwidth = *b;
  return t;
}

DispatchCtx ctxFromJSON(const Value &v) {
  DispatchCtx d;
  const Object *o = v.getAsObject();
  if (!o)
    return d;
  if (auto s = o->getString("kind"))
    d.kind = s->str();
  if (auto s = o->getString("condLoc"))
    d.condLoc = s->str();
  if (auto s = o->getString("cond"))
    d.cond = s->str();
  return d;
}

WriteLoc writeLocFromJSON(const Value &v) {
  WriteLoc w;
  const Object *o = v.getAsObject();
  if (!o)
    return w;
  if (auto s = o->getString("resource"))
    w.resource = s->str();
  if (auto s = o->getString("file"))
    w.file = s->str();
  if (auto i = o->getInteger("line"))
    w.line = (int)*i;
  if (auto s = o->getString("kind"))
    w.kind = s->str();
  return w;
}

DangerUse dangerUseFromJSON(const Value &v) {
  DangerUse d;
  const Object *o = v.getAsObject();
  if (!o)
    return d;
  if (auto s = o->getString("param"))
    d.param = s->str();
  if (auto s = o->getString("kind"))
    d.kind = s->str();
  if (auto s = o->getString("callee"))
    d.callee = s->str();
  if (auto s = o->getString("file"))
    d.file = s->str();
  if (auto i = o->getInteger("line"))
    d.line = (int)*i;
  return d;
}

DefFact defFromJSON(const Value &v) {
  DefFact d;
  const Object *o = v.getAsObject();
  if (!o)
    return d;
  if (auto s = o->getString("usr"))
    d.usr = s->str();
  if (auto s = o->getString("name"))
    d.name = s->str();
  if (auto s = o->getString("file"))
    d.file = s->str();
  if (auto i = o->getInteger("line"))
    d.line = (int)*i;
  if (auto b = o->getBoolean("static"))
    d.isStatic = *b;
  if (auto b = o->getBoolean("def"))
    d.isDef = *b;
  if (auto r = o->get("ret"))
    d.ret = typeFromJSON(*r);
  if (auto a = o->getArray("params"))
    for (const auto &e : *a)
      d.params.push_back(typeFromJSON(e));
  if (auto s = o->getString("bodyKind"))
    d.bodyKind = s->str();
  if (auto s = o->getString("constVal"))
    d.constVal = s->str();
  if (auto a = o->getArray("accesses"))
    for (const auto &e : *a)
      if (auto s = e.getAsString())
        d.accesses.push_back(s->str());
  if (auto a = o->getArray("writes"))
    for (const auto &e : *a)
      if (auto s = e.getAsString())
        d.writes.push_back(s->str());
  if (auto a = o->getArray("soft"))
    for (const auto &e : *a)
      if (auto s = e.getAsString())
        d.soft.push_back(s->str());
  if (auto a = o->getArray("checked"))
    for (const auto &e : *a)
      if (auto s = e.getAsString())
        d.checked.push_back(s->str());
  if (auto a = o->getArray("dangerous"))
    for (const auto &e : *a)
      if (auto s = e.getAsString())
        d.dangerous.push_back(s->str());
  if (auto a = o->getArray("writeLocs"))
    for (const auto &e : *a)
      d.writeLocs.push_back(writeLocFromJSON(e));
  if (auto a = o->getArray("dangerUses"))
    for (const auto &e : *a)
      d.dangerUses.push_back(dangerUseFromJSON(e));
  return d;
}

CallFact callFromJSON(const Value &v) {
  CallFact c;
  const Object *o = v.getAsObject();
  if (!o)
    return c;
  if (auto s = o->getString("callerUsr"))
    c.callerUsr = s->str();
  if (auto s = o->getString("callerName"))
    c.callerName = s->str();
  if (auto s = o->getString("callerFile"))
    c.callerFile = s->str();
  if (auto i = o->getInteger("callerLine"))
    c.callerLine = (int)*i;
  if (auto s = o->getString("calleeUsr"))
    c.calleeUsr = s->str();
  if (auto s = o->getString("calleeName"))
    c.calleeName = s->str();
  if (auto s = o->getString("file"))
    c.file = s->str();
  if (auto i = o->getInteger("line"))
    c.line = (int)*i;
  if (auto a = o->getArray("args"))
    for (const auto &e : *a)
      c.args.push_back(typeFromJSON(e));
  if (auto a = o->getArray("params"))
    for (const auto &e : *a)
      c.params.push_back(typeFromJSON(e));
  if (auto t = o->get("ctx"))
    c.ctx = ctxFromJSON(*t);
  if (auto b = o->getBoolean("usesRet"))
    c.usesRet = *b;
  return c;
}

PPFact ppFromJSON(const Value &v) {
  PPFact p;
  const Object *o = v.getAsObject();
  if (!o)
    return p;
  if (auto s = o->getString("file"))
    p.file = s->str();
  if (auto i = o->getInteger("line"))
    p.line = (int)*i;
  if (auto s = o->getString("kind"))
    p.kind = s->str();
  if (auto s = o->getString("cond"))
    p.cond = s->str();
  return p;
}

FlowFact flowFromJSON(const Value &v) {
  FlowFact f;
  const Object *o = v.getAsObject();
  if (!o)
    return f;
  if (auto s = o->getString("kind"))
    f.kind = s->str();
  if (auto s = o->getString("func"))
    f.func = s->str();
  if (auto s = o->getString("file"))
    f.file = s->str();
  if (auto i = o->getInteger("line"))
    f.line = (int)*i;
  if (auto t = o->get("lhs"))
    f.lhs = typeFromJSON(*t);
  if (auto t = o->get("rhs"))
    f.rhs = typeFromJSON(*t);
  if (auto s = o->getString("lhsName"))
    f.lhsName = s->str();
  if (auto s = o->getString("rhsName"))
    f.rhsName = s->str();
  return f;
}

GlobalDef globalFromJSON(const Value &v) {
  GlobalDef g;
  const Object *o = v.getAsObject();
  if (!o)
    return g;
  if (auto s = o->getString("name"))
    g.name = s->str();
  if (auto s = o->getString("file"))
    g.file = s->str();
  return g;
}

MacroFact macroFromJSON(const Value &v) {
  MacroFact m;
  const Object *o = v.getAsObject();
  if (!o)
    return m;
  if (auto s = o->getString("name"))
    m.name = s->str();
  if (auto s = o->getString("file"))
    m.file = s->str();
  if (auto s = o->getString("kind"))
    m.kind = s->str();
  return m;
}

MacroRes macroResFromJSON(const Value &v) {
  MacroRes r;
  const Object *o = v.getAsObject();
  if (!o)
    return r;
  if (auto s = o->getString("macro"))
    r.macro = s->str();
  if (auto s = o->getString("resource"))
    r.resource = s->str();
  return r;
}

GlobalFlow globalFlowFromJSON(const Value &v) {
  GlobalFlow g;
  const Object *o = v.getAsObject();
  if (!o)
    return g;
  if (auto s = o->getString("global"))
    g.global = s->str();
  if (auto s = o->getString("file"))
    g.file = s->str();
  if (auto i = o->getInteger("line"))
    g.line = (int)*i;
  if (auto t = o->get("lhs"))
    g.lhs = typeFromJSON(*t);
  if (auto t = o->get("rhs"))
    g.rhs = typeFromJSON(*t);
  if (auto s = o->getString("srcVar"))
    g.srcVar = s->str();
  return g;
}

Facts factsFromJSON(const Value &v) {
  Facts f;
  const Object *o = v.getAsObject();
  if (!o)
    return f;
  if (auto s = o->getString("arch"))
    f.arch = s->str();
  if (auto s = o->getString("root"))
    f.root = s->str();
  if (auto a = o->getArray("defs"))
    for (const auto &e : *a)
      f.defs.push_back(defFromJSON(e));
  if (auto a = o->getArray("calls"))
    for (const auto &e : *a)
      f.calls.push_back(callFromJSON(e));
  if (auto a = o->getArray("pps"))
    for (const auto &e : *a)
      f.pps.push_back(ppFromJSON(e));
  if (auto a = o->getArray("flows"))
    for (const auto &e : *a)
      f.flows.push_back(flowFromJSON(e));
  if (auto a = o->getArray("globals"))
    for (const auto &e : *a)
      f.globals.push_back(globalFromJSON(e));
  if (auto a = o->getArray("macros"))
    for (const auto &e : *a)
      f.macros.push_back(macroFromJSON(e));
  if (auto a = o->getArray("macroRes"))
    for (const auto &e : *a)
      f.macroRes.push_back(macroResFromJSON(e));
  if (auto a = o->getArray("globalFlows"))
    for (const auto &e : *a)
      f.globalFlows.push_back(globalFlowFromJSON(e));
  return f;
}

} // namespace arb
