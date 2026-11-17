#include "Facts.h"
#include "Support.h"

#include "llvm/ADT/SmallVector.h"
#include "llvm/Support/CommandLine.h"
#include "llvm/Support/FileSystem.h"
#include "llvm/Support/JSON.h"
#include "llvm/Support/MemoryBuffer.h"
#include "llvm/Support/raw_ostream.h"

#include <algorithm>
#include <functional>
#include <map>
#include <set>
#include <string>
#include <vector>

using namespace llvm;

static cl::OptionCategory ArchBoundAnalyzeCat("archbound-analyze options");
static cl::opt<std::string> OptFacts("facts", cl::desc("comma-separated facts json files"),
                                     cl::init(""), cl::cat(ArchBoundAnalyzeCat));
static cl::opt<std::string> OptReport("report", cl::desc("text report path (stdout if omitted)"),
                                      cl::init(""), cl::cat(ArchBoundAnalyzeCat));
static cl::opt<std::string> OptJSON("json", cl::desc("machine-readable json output path"),
                                    cl::init(""), cl::cat(ArchBoundAnalyzeCat));
static cl::opt<unsigned> OptLimit("limit", cl::desc("max items per section"),
                                  cl::init(200), cl::cat(ArchBoundAnalyzeCat));
static cl::opt<unsigned> OptMinSev("min-sev",
                                   cl::desc("min severity for type-flow output "
                                            "(1=all, 2=latent+narrowing, 3=narrowing only)"),
                                   cl::init(2), cl::cat(ArchBoundAnalyzeCat));
static cl::opt<std::string> OptPoints("points",
                                      cl::desc("output DGF test points as JSON"),
                                      cl::init(""), cl::cat(ArchBoundAnalyzeCat));

namespace {

// ---------------------------------------------------------------------------
// Loaded facts with their source architecture tagged on every element.
// ---------------------------------------------------------------------------

struct Def {
  arb::DefFact d;
  std::string srcArch; // which compile DB produced it
  std::string key;     // srcArch@file:line
  std::string fileArch;
};

struct Call {
  arb::CallFact c;
  std::string srcArch;
  std::string callerKey; // srcArch@callerFile:callerLine
  std::string fileArch;
};

struct PP {
  arb::PPFact p;
  std::string srcArch;
  std::string fileArch;
};

struct Flow {
  arb::FlowFact f;
  std::string srcArch;
};

struct Index {
  std::vector<std::string> archs;
  std::vector<Def> defs;
  std::vector<Call> calls;
  std::vector<PP> pps;
  std::vector<Flow> flows;
  std::map<std::string, std::vector<int>> byName;   // name -> def idx
  std::map<std::string, std::vector<int>> byUsr;    // usr  -> def idx
  std::map<std::string, std::vector<int>> byKey;    // key  -> def idx
  std::map<std::string, std::vector<int>> callsByCaller; // callerKey -> call idx
  std::map<std::string, std::vector<int>> callsByCallee; // calleeName -> call idx
  std::map<std::string, std::vector<int>> callsByCtx;    // ctx.condLoc -> call idx
  // cross-TU global definitions: name -> set of defining files (for arch-private)
  std::map<std::string, std::set<std::string>> globalDefFiles;
  // macro capability: arch -> macros defined under arch/, plus macros used in common code
  std::map<std::string, std::set<std::string>> archDefMacros;
  std::set<std::string> commonUsedMacros;
  // macro -> arch -> resources accessed by that macro's expansion
  std::map<std::string, std::map<std::string, std::set<std::string>>> macroResByArch;
};

static std::string defKey(const std::string &arch, const std::string &file, int line) {
  return arch + "@" + file + ":" + std::to_string(line);
}

// Is a "g:name" resource key arch-private, i.e. the global is DEFINED under arch/
// (cross-TU resolution via the global definition index)?
static bool isArchGlobalKey(const std::string &key, const Index &ix) {
  if (key.rfind("g:", 0) != 0)
    return false;
  std::string name = key.substr(2);
  auto it = ix.globalDefFiles.find(name);
  if (it == ix.globalDefFiles.end())
    return false;
  for (const auto &f : it->second)
    if (f.rfind("arch/", 0) == 0)
      return true;
  return false;
}

// Is a path a runtime kernel source file (not a host tool / generated build
// file / unresolved location)? Filters dtc, kconfig, usr/, and <invalid buffer>
// macro-expansion locations out of the boundary analysis.
static bool isRuntimeKernelFile(const std::string &f) {
  if (f.empty() || f.rfind("<invalid buffer>", 0) == 0)
    return false;
  if (f[0] == '/') // absolute path = outside source root (build dir, generated)
    return false;
  static const char *skip[] = {"scripts/", "tools/", "usr/"};
  for (const char *s : skip)
    if (f.rfind(s, 0) == 0)
      return false;
  return true;
}

// Resolve a callee to the set of definition indices.
static void resolveCallee(const Index &ix, const arb::CallFact &c, std::vector<int> &out) {
  out.clear();
  if (!c.calleeUsr.empty()) {
    auto it = ix.byUsr.find(c.calleeUsr);
    if (it != ix.byUsr.end()) {
      out = it->second;
      return;
    }
  }
  auto it = ix.byName.find(c.calleeName);
  if (it != ix.byName.end())
    out = it->second;
}

// Distinct arch/ dirs among a set of defs.
static std::set<std::string> defArchs(const Index &ix, const std::vector<int> &ids) {
  std::set<std::string> s;
  for (int i : ids)
    if (!ix.defs[i].fileArch.empty())
      s.insert(ix.defs[i].fileArch);
  return s;
}

static bool anyArchDef(const Index &ix, const std::vector<int> &ids) {
  for (int i : ids)
    if (!ix.defs[i].fileArch.empty())
      return true;
  return false;
}

// ---------------------------------------------------------------------------
// Analysis
// ---------------------------------------------------------------------------

struct Finding {
  std::string section;
  std::string detail;
};

static void runAnalysis(Index &ix, std::vector<Finding> &findings,
                        std::string &report) {
  // ---------------- Section 1: boundary calls (common -> arch) ----------------
  {
    struct BC {
      std::string callee;
      std::set<std::string> archs;
      std::vector<std::string> sites;
    };
    std::map<std::string, BC> byCallee;
    int boundarySites = 0;

    for (const auto &call : ix.calls) {
      if (!call.fileArch.empty())
        continue; // caller itself is in arch layer; focus on common callers
      std::vector<int> ids;
      resolveCallee(ix, call.c, ids);
      if (!anyArchDef(ix, ids))
        continue;
      std::set<std::string> as = defArchs(ix, ids);
      if (as.empty())
        continue;
      boundarySites++;
      std::string key = call.c.calleeName;
      auto &b = byCallee[key];
      b.callee = call.c.calleeName;
      b.archs.insert(as.begin(), as.end());
      b.sites.push_back(call.c.file + ":" + std::to_string(call.c.line));
    }

    std::vector<BC> bcs;
    for (auto &kv : byCallee)
      bcs.push_back(kv.second);
    std::sort(bcs.begin(), bcs.end(), [](const BC &x, const BC &y) {
      return x.archs.size() > y.archs.size();
    });

    raw_string_ostream R(report);
    R << "[1] BOUNDARY CALLS (common layer -> arch layer)\n";
    R << "    " << byCallee.size() << " unique callees, " << boundarySites
      << " call sites\n";
    unsigned shown = 0;
    for (auto &b : bcs) {
      if (shown++ >= OptLimit)
        break;
      R << "    " << b.callee << "  archs=[" << [&] { std::string s; for (auto &x : b.archs) s += x + ","; if(!s.empty())s.pop_back(); return s; }()
        << "]  sites=" << b.sites.size()
        << "  e.g. " << b.sites.front() << "\n";
    }
    R << "\n";
    R.flush();
  }

  // ---------------- Section 2: per-arch families ----------------
  {
    std::vector<std::pair<std::string, std::vector<int>>> families;
    for (auto &kv : ix.byName) {
      std::set<std::string> as = defArchs(ix, kv.second);
      if (as.size() >= 2)
        families.push_back(kv);
    }
    std::sort(families.begin(), families.end(),
              [&](auto &x, auto &y) { return defArchs(ix, x.second).size() > defArchs(ix, y.second).size(); });

    raw_string_ostream R(report);
    R << "[2] PER-ARCH FAMILIES (same function name defined in >=2 arch/ dirs): "
      << families.size() << "\n";
    unsigned shown = 0;
    for (auto &f : families) {
      if (shown++ >= OptLimit)
        break;
      R << "    " << f.first << "  -> ";
      for (int i : f.second)
        R << ix.defs[i].fileArch << "(" << ix.defs[i].d.file << ":" << ix.defs[i].d.line
          << " " << ix.defs[i].d.bodyKind << ") ";
      R << "\n";
    }
    R << "\n";
    R.flush();

    // ---------------- Check 2 + 3 run over families ----------------
    for (auto &f : families) {
      const std::vector<int> &ids = f.second;
      // bodyKind completeness: some arch empty/const, others normal
      bool anyNormal = false, anyStub = false;
      for (int i : ids) {
        const auto &d = ix.defs[i].d;
        if (d.bodyKind == "normal")
          anyNormal = true;
        else if (d.bodyKind == "empty" || d.bodyKind == "const")
          anyStub = true;
      }
      if (anyNormal && anyStub) {
        std::string detail = f.first + " : implementation completeness mismatch — ";
        for (int i : ids)
          detail += ix.defs[i].fileArch + "=" + ix.defs[i].d.bodyKind +
                    (ix.defs[i].d.bodyKind == "const" ? "(" + ix.defs[i].d.constVal + ")" : "") + " ";
        findings.push_back({"implementation-completeness", detail});
      }
      // Check 3a: output-write asymmetry across arch members
      // Check 3a: resource-access asymmetry across arch members.
      //   write asymmetry: a resource written on some archs but not others.
      //   access asymmetry: a resource read OR written on some archs but not others.
      std::map<std::string, std::set<std::string>> archWrites, archAccesses;
      for (int i : ids) {
        const auto &d = ix.defs[i];
        if (d.fileArch.empty())
          continue;
        for (auto &w : d.d.writes)
          archWrites[d.fileArch].insert(w);
        for (auto &a : d.d.accesses)
          archAccesses[d.fileArch].insert(a);
      }
      auto asym = [&](const std::map<std::string, std::set<std::string>> &M,
                      const char *section, const char *verb) {
        std::set<std::string> allKeys;
        for (auto &kv : M)
          for (auto &w : kv.second)
            allKeys.insert(w);
        for (auto &k : allKeys) {
          if (isArchGlobalKey(k, ix))
            continue; // arch-defined global: not a shared resource
          std::set<std::string> has;
          for (auto &kv : M)
            if (kv.second.count(k))
              has.insert(kv.first);
          if (has.size() < M.size()) {
            std::string missing;
            for (auto &kv : M)
              if (!kv.second.count(k))
                missing += kv.first + ",";
            if (!missing.empty())
              missing.pop_back();
            findings.push_back({section,
                                f.first + " " + verb + " '" + k +
                                    "' on some archs but NOT on [" + missing + "]"});
          }
        }
      };
      asym(archWrites, "output-write-asymmetry", "writes");
      asym(archAccesses, "resource-access-asymmetry", "accesses");
      // Check 3b: common-function call asymmetry across arch members
      std::map<std::string, std::set<std::string>> archCommonCalls;
      for (int i : ids) {
        const auto &d = ix.defs[i];
        if (d.fileArch.empty())
          continue;
        auto it = ix.callsByCaller.find(d.key);
        if (it == ix.callsByCaller.end())
          continue;
        for (int ci : it->second) {
          const auto &c = ix.calls[ci].c;
          std::vector<int> cids;
          resolveCallee(ix, c, cids);
          bool isCommon = !cids.empty() && !anyArchDef(ix, cids);
          if (isCommon)
            archCommonCalls[d.fileArch].insert(c.calleeName);
        }
      }
      std::set<std::string> allCalls;
      for (auto &kv : archCommonCalls)
        for (auto &w : kv.second)
          allCalls.insert(w);
      for (auto &k : allCalls) {
        std::set<std::string> has;
        for (auto &kv : archCommonCalls)
          if (kv.second.count(k))
            has.insert(kv.first);
        if (has.size() < archCommonCalls.size()) {
          std::string missing;
          for (auto &kv : archCommonCalls)
            if (!kv.second.count(k))
              missing += kv.first + ",";
          if (!missing.empty())
            missing.pop_back();
          findings.push_back({"common-call-asymmetry",
                              f.first + " calls common fn '" + k + "' on some archs but NOT on [" + missing + "]"});
        }
      }
      // Check 3c: param-precondition asymmetry (check before dangerous use).
      // A param used in a risky position (array index / memcpy length / shift /
      // deref) should be bounds-checked. If one arch checks it and another uses
      // it without checking, the unchecked arch is a candidate.
      std::map<std::string, std::set<std::string>> archDangerous, archChecked;
      for (int i : ids) {
        const auto &d = ix.defs[i];
        if (d.fileArch.empty())
          continue;
        for (auto &dg : d.d.dangerous)
          archDangerous[d.fileArch].insert(dg);
        for (auto &c : d.d.checked)
          archChecked[d.fileArch].insert(c);
      }
      std::set<std::string> allDangerous;
      for (auto &kv : archDangerous)
        for (auto &dg : kv.second)
          allDangerous.insert(dg);
      for (auto &dg : allDangerous) {
        auto pos = dg.find(':');
        std::string param = dg.substr(0, pos);        // "param#N"
        std::string kind = dg.substr(pos + 1);        // index|len|shift|deref
        std::set<std::string> checks, noCheck;
        for (auto &kv : archDangerous) {
          if (!kv.second.count(dg))
            continue; // this arch does not use the param in this way
          (archChecked[kv.first].count(param) ? checks : noCheck).insert(kv.first);
        }
        if (checks.empty() || noCheck.empty())
          continue; // all agree, or no one checks
        std::string c, nc;
        for (auto &x : checks)
          c += x + ",";
        for (auto &x : noCheck)
          nc += x + ",";
        if (!c.empty())
          c.pop_back();
        if (!nc.empty())
          nc.pop_back();
        findings.push_back({"param-precondition-asymmetry",
                            f.first + " uses " + param + " as " + kind +
                                " with a check on [" + c + "] but WITHOUT a check on [" + nc + "]"});
      }
    }
  }

  // ---------------- Section 3: __HAVE_ARCH capability map ----------------
  {
    std::map<std::string, std::set<std::string>> defines;   // macro -> archs that #define it
    std::map<std::string, std::vector<std::string>> guards; // macro -> header fallback sites
    for (auto &pp : ix.pps) {
      if (pp.p.kind == "define" && StringRef(pp.p.cond).startswith("__HAVE_ARCH"))
        defines[pp.p.cond].insert(pp.srcArch);
      else if (pp.p.kind == "ifndef" && StringRef(pp.p.cond).startswith("__HAVE_ARCH"))
        guards[pp.p.cond].push_back(pp.p.file + ":" + std::to_string(pp.p.line));
    }
    raw_string_ostream R(report);
    R << "[3] __HAVE_ARCH_* CAPABILITY (arch-provided overrides)\n";
    unsigned shown = 0;
    for (auto &kv : guards) {
      if (shown++ >= OptLimit)
        break;
      auto dit = defines.find(kv.first);
      std::string provided;
      if (dit != defines.end())
        for (auto &a : dit->second)
          provided += a + ",";
      if (!provided.empty())
        provided.pop_back();
      if (provided.empty())
        provided = "(none)";
      R << "    " << kv.first << "  provided-by=[" << provided << "]  fallback@" << kv.second.front()
        << "\n";
    }
    R << "\n";
    R.flush();
  }

  // ---------------- Section 3b: arch-macro capability ----------------
  // Macros #define'd in arch/ headers but USED in common code. If a macro is
  // used by common code but only SOME architectures define it (e.g.
  // topology_die_id), the common code silently falls back / misbehaves on the
  // archs that don't provide it.
  {
    std::map<std::string, std::set<std::string>> byMacro; // macro -> archs that define it
    for (auto &kv : ix.archDefMacros)
      for (auto &m : kv.second)
        byMacro[m].insert(kv.first);
    raw_string_ostream R(report);
    R << "[3b] ARCH-MACRO CAPABILITY (arch-defined macro used in common code, only some archs provide it)\n";
    unsigned shown = 0;
    for (auto &name : ix.commonUsedMacros) {
      auto it = byMacro.find(name);
      if (it == byMacro.end())
        continue;
      if (it->second.size() >= ix.archs.size())
        continue; // all archs define it: no mismatch
      if (shown++ >= OptLimit)
        break;
      std::string provided;
      for (auto &a : it->second)
        provided += a + ",";
      if (!provided.empty())
        provided.pop_back();
      std::string missing;
      for (auto &a : ix.archs)
        if (!it->second.count(a))
          missing += a + ",";
      if (!missing.empty())
        missing.pop_back();
      R << "    " << name << "  provided-by=[" << provided << "]  MISSING-on=[" << missing << "]\n";
      findings.push_back({"arch-macro-capability",
                          name + " used in common code but only defined on [" + provided +
                              "], missing on [" + missing + "]"});
    }
    R << "\n";
    R.flush();
  }

  // ---------------- Section 3c: macro resource access comparison ----------------
  // Attribute resource accesses to the macro whose expansion produced them, then
  // compare across archs:
  //   - unconditional use (macro on all archs): its body reads/writes different
  //     resources on different archs -> inconsistent definition.
  //   - conditional use (macro only on some archs): it touches resources other
  //     archs never touch -> arch-exclusive capability.
  {
    raw_string_ostream R(report);
    R << "[3c] MACRO RESOURCE ACCESS (does a macro's expansion touch different resources across archs?)\n";
    unsigned shown = 0;
    for (auto &kv : ix.macroResByArch) {
      const std::string &m = kv.first;
      const auto &resByArch = kv.second;
      if (resByArch.size() < 2)
        continue; // need at least 2 archs to compare
      // union of resources touched by this macro
      std::set<std::string> allRes;
      for (auto &a : resByArch)
        for (auto &r : a.second)
          allRes.insert(r);
      // for each resource, which archs' version of M touches it?
      bool anyDiff = false;
      std::string diffDetail;
      for (auto &r : allRes) {
        std::set<std::string> has;
        for (auto &a : resByArch)
          if (a.second.count(r))
            has.insert(a.first);
        if (has.size() < ix.archs.size() && has.size() < resByArch.size()) {
          // some archs touch r via M, others don't
          anyDiff = true;
          std::string miss;
          for (auto &a : ix.archs)
            if (resByArch.count(a) && !resByArch.at(a).count(r))
              miss += a + ",";
          if (!miss.empty())
            miss.pop_back();
          diffDetail += "  resource '" + r + "' touched on [";
          for (auto &a : has) diffDetail += a + ",";
          diffDetail.pop_back();
          diffDetail += "] but NOT on [" + miss + "]\n";
        }
      }
      if (!anyDiff)
        continue;
      if (shown++ >= OptLimit)
        break;
      R << "    " << m << "\n" << diffDetail;
      findings.push_back({"macro-resource-asymmetry",
                          m + " touches resources inconsistently across archs:\n" + diffDetail});
    }
    R << "\n";
    R.flush();
  }

  // ---------------- Section 4: type-flow mismatch (fixed-width <-> arch-width) --------
  {
    struct Flow {
      std::string callee;
      int argIdx = 0;
      std::string argSpelling, paramSpelling;
      int argSize = -1, paramSize = -1;
      bool argFixed = false, argArch = false, paramFixed = false, paramArch = false;
      bool isFlow = false; // true for assign/init/return flows (callee = "func [kind]")
      std::set<std::string> narrowingArchs;
      std::string example;
      int sites = 0;
    };
    std::map<std::string, Flow> flows;
    for (const auto &call : ix.calls) {
      unsigned n = std::min(call.c.args.size(), call.c.params.size());
      for (unsigned i = 0; i < n; i++) {
        const auto &a = call.c.args[i];
        const auto &p = call.c.params[i];
        bool fixedArch = (a.fixed && p.archwidth) || (a.archwidth && p.fixed);
        bool widthDiff = a.sizeBits >= 0 && p.sizeBits >= 0 && a.sizeBits != p.sizeBits;
        bool signDiff = a.isInt && p.isInt && a.isSigned != p.isSigned;
        if (!fixedArch && !widthDiff && !signDiff)
          continue;
        std::string key = call.c.calleeName + "|" + std::to_string(i) + "|" + a.spelling + "|" + p.spelling;
        auto &f = flows[key];
        f.callee = call.c.calleeName;
        f.argIdx = (int)i;
        f.argSpelling = a.spelling;
        f.paramSpelling = p.spelling;
        f.argSize = a.sizeBits;
        f.paramSize = p.sizeBits;
        f.argFixed = a.fixed;
        f.argArch = a.archwidth;
        f.paramFixed = p.fixed;
        f.paramArch = p.archwidth;
        f.sites++;
        if (f.example.empty())
          f.example = call.c.file + ":" + std::to_string(call.c.line);
        if ((a.fixed && p.archwidth && a.sizeBits > p.sizeBits) ||
            (a.archwidth && p.fixed && a.sizeBits < p.sizeBits))
          f.narrowingArchs.insert(call.srcArch);
      }
    }
    // value flows at assignment / initialization / return (rhs = source, lhs = dest)
    for (const auto &fl : ix.flows) {
      const auto &lhs = fl.f.lhs; // destination (variable / return type)
      const auto &rhs = fl.f.rhs; // source (stored / returned value)
      bool fixedArch = (lhs.fixed && rhs.archwidth) || (lhs.archwidth && rhs.fixed);
      bool widthDiff = lhs.sizeBits >= 0 && rhs.sizeBits >= 0 && lhs.sizeBits != rhs.sizeBits;
      bool signDiff = lhs.isInt && rhs.isInt && lhs.isSigned != rhs.isSigned;
      if (!fixedArch && !widthDiff && !signDiff)
        continue;
      std::string key = "F|" + fl.f.func + "|" + fl.f.kind + "|" + rhs.spelling + "|" + lhs.spelling;
      auto &f = flows[key];
      f.callee = fl.f.func + " [" + fl.f.kind + "]";
      f.argIdx = -1;
      f.argSpelling = rhs.spelling;
      f.paramSpelling = lhs.spelling;
      f.argSize = rhs.sizeBits;
      f.paramSize = lhs.sizeBits;
      f.argFixed = rhs.fixed;
      f.argArch = rhs.archwidth;
      f.paramFixed = lhs.fixed;
      f.paramArch = lhs.archwidth;
      f.isFlow = true;
      f.sites++;
      if (f.example.empty())
        f.example = fl.f.file + ":" + std::to_string(fl.f.line);
      if ((rhs.fixed && lhs.archwidth && rhs.sizeBits > lhs.sizeBits) ||
          (rhs.archwidth && lhs.fixed && rhs.sizeBits < lhs.sizeBits))
        f.narrowingArchs.insert(fl.srcArch);
    }

    struct Out { int sev; std::string line; std::string detail; };
    std::vector<Out> outs;
    for (auto &kv : flows) {
      const auto &f = kv.second;
      bool fixedArch = (f.argFixed && f.paramArch) || (f.argArch && f.paramFixed);
      std::string reason;
      int sev = 0;
      if (!f.narrowingArchs.empty()) {
        reason = "narrowing (width drop observed)";
        sev = 3;
      } else if (fixedArch) {
        reason = "fixed-width <-> arch-width (latent)";
        sev = 2;
      } else if (f.argSize >= 0 && f.paramSize >= 0 && f.argSize != f.paramSize) {
        reason = "width mismatch";
        sev = 1;
      } else {
        reason = "signedness mismatch";
        sev = 1;
      }
      std::string where = f.isFlow ? "" : (" arg#" + std::to_string(f.argIdx));
      std::string line = f.callee + where + ": " + f.argSpelling + " -> " + f.paramSpelling;
      std::string detail = f.callee + where + ": " +
                           f.argSpelling + "(" + std::to_string(f.argSize) + ") -> " +
                           f.paramSpelling + "(" + std::to_string(f.paramSize) + ") [" + reason +
                           "] sites=" + std::to_string(f.sites) + " e.g. " + f.example;
      if (!f.narrowingArchs.empty()) {
        detail += " narrowing-on=[";
        for (auto &x : f.narrowingArchs)
          detail += x + ",";
        detail.pop_back();
        detail += "]";
      }
      if (sev < (int)OptMinSev.getValue())
        continue;
      outs.push_back({sev, line, detail});
      findings.push_back({"type-flow-mismatch", detail});
    }
    std::sort(outs.begin(), outs.end(),
              [](const Out &x, const Out &y) { return x.sev > y.sev; });
    raw_string_ostream R(report);
    R << "[4] TYPE-FLOW MISMATCH (fixed-width <-> arch-width at call sites / value flows): "
      << outs.size() << "\n";
    unsigned shown = 0;
    for (auto &o : outs) {
      if (shown++ >= OptLimit)
        break;
      R << "    [sev" << o.sev << "] " << o.line << "\n";
    }
    R << "\n";
    R.flush();
  }

  // ---------------- Section 5: cross-build type-width asymmetry ----------------
  // The same function (same file:line) compiled for different builds may have
  // different widths for architecture-dependent types (unsigned long, size_t,
  // uintptr_t, ...). This is the classic "u64 vs unsigned long" truncation trap:
  // it is invisible within a single 64-bit build but becomes a real 64->32
  // truncation on 32-bit builds.
  {
    std::map<std::string, std::vector<int>> byLoc;
    for (int i = 0; i < (int)ix.defs.size(); i++)
      if (!ix.defs[i].d.file.empty())
        byLoc[ix.defs[i].d.file + ":" + std::to_string(ix.defs[i].d.line)].push_back(i);

    struct TW {
      std::string name, file;
      int line;
      std::vector<std::string> details;
    };
    std::vector<TW> tws;

    for (auto &kv : byLoc) {
      if (kv.second.size() < 2)
        continue;
      std::set<std::string> archs;
      for (int i : kv.second)
        archs.insert(ix.defs[i].srcArch);
      if (archs.size() < 2)
        continue;
      const Def &d0 = ix.defs[kv.second[0]];
      std::vector<std::string> details;

      auto checkType = [&](const char *what, const std::function<const arb::TypeInfo *(const Def &)> &get) {
        std::map<std::string, int> archSize;
        bool anyArchWidth = false;
        for (int i : kv.second) {
          const arb::TypeInfo *t = get(ix.defs[i]);
          if (!t)
            continue;
          if (t->archwidth)
            anyArchWidth = true;
          if (t->sizeBits >= 0)
            archSize[ix.defs[i].srcArch] = t->sizeBits;
        }
        if (!anyArchWidth || archSize.size() < 2)
          return;
        std::set<int> sizes;
        for (auto &as : archSize)
          sizes.insert(as.second);
        if (sizes.size() >= 2) {
          std::string d = std::string(what) + " width varies: ";
          for (auto &as : archSize)
            d += as.first + "=" + std::to_string(as.second) + "bit ";
          details.push_back(d);
        }
      };

      size_t np = 0;
      for (int i : kv.second)
        np = std::max(np, ix.defs[i].d.params.size());
      for (size_t p = 0; p < np; p++) {
        checkType(("param#" + std::to_string(p)).c_str(),
                  [&](const Def &d) -> const arb::TypeInfo * {
                    return p < d.d.params.size() ? &d.d.params[p] : nullptr;
                  });
      }
      checkType("return", [&](const Def &d) -> const arb::TypeInfo * {
        return &d.d.ret;
      });

      if (!details.empty()) {
        TW tw;
        tw.name = d0.d.name;
        tw.file = d0.d.file;
        tw.line = d0.d.line;
        tw.details = details;
        tws.push_back(std::move(tw));
        for (auto &dt : details)
          findings.push_back({"type-width-asymmetry",
                              d0.d.name + " @" + d0.d.file + ":" + std::to_string(d0.d.line) + " — " + dt});
      }
    }

    raw_string_ostream R(report);
    R << "[5] CROSS-BUILD TYPE-WIDTH ASYMMETRY (arch-width type differs across builds): "
      << tws.size() << "\n";
    unsigned shown = 0;
    for (auto &t : tws) {
      if (shown++ >= OptLimit)
        break;
      R << "    " << t.name << " @" << t.file << ":" << t.line << "\n";
      for (auto &d : t.details)
        R << "        " << d << "\n";
    }
    R << "\n";
    R.flush();
  }
}

// ---------------------------------------------------------------------------
// DGF test-point extraction (slot grouping + semantic-hypothesis labelling +
// reachability back-trace).
// ---------------------------------------------------------------------------

// Strip compiler suffixes (".isra.0", ".constprop.0") from a function name.
static std::string baseName(const std::string &n) {
  size_t p = n.find('.');
  return p == std::string::npos ? n : n.substr(0, p);
}

// If `name` is a syscall entry (__x64_sys_*, __do_sys_*, __riscv_sys_*, sys_*,
// ksys_*), return the syscall name; otherwise "".
static std::string syscallOf(const std::string &name) {
  std::string b = baseName(name);
  // __<role|arch>_sys_<name>
  size_t p = b.find("_sys_");
  if (p != std::string::npos && p >= 2 && b[0] == '_' && b[1] == '_')
    return baseName(b.substr(p + 5));
  if (b.rfind("ksys_", 0) == 0)
    return baseName(b.substr(5));
  if (b.rfind("sys_", 0) == 0)
    return baseName(b.substr(4));
  return "";
}

// Reverse BFS over the (merged) call graph: which syscalls can reach `func`?
// Results are memoized in `cache` keyed by function name (boundary functions
// repeat across many slots, so this avoids quadratic re-traversal).
static const std::set<std::string> &reachableSyscalls(
    const Index &ix, const std::string &func, int maxDepth,
    std::map<std::string, std::set<std::string>> &cache) {
  auto it = cache.find(func);
  if (it != cache.end())
    return it->second;
  std::set<std::string> &result = cache[func];
  std::set<std::string> visited;
  std::vector<std::pair<std::string, int>> q;
  q.push_back({func, 0});
  visited.insert(func);
  size_t head = 0;
  while (head < q.size()) {
    std::string fn = q[head].first;
    int d = q[head].second;
    head++;
    if (d > maxDepth)
      continue;
    auto cit = ix.callsByCallee.find(fn);
    if (cit == ix.callsByCallee.end())
      continue;
    for (int ci : cit->second) {
      const std::string &caller = ix.calls[ci].c.callerName;
      std::string sys = syscallOf(caller);
      if (!sys.empty()) {
        result.insert(sys);
        continue;
      }
      if (visited.insert(caller).second)
        q.push_back({caller, d + 1});
    }
  }
  return result;
}

static bool typeMismatch(const arb::TypeInfo &a, const arb::TypeInfo &b) {
  bool fixedArch = (a.fixed && b.archwidth) || (a.archwidth && b.fixed);
  bool widthDiff = a.sizeBits >= 0 && b.sizeBits >= 0 && a.sizeBits != b.sizeBits;
  bool signDiff = a.isInt && b.isInt && a.isSigned != b.isSigned;
  return fixedArch || widthDiff || signDiff;
}

// A single categorized point. Each point belongs to exactly ONE category; the
// fields irrelevant to that category stay empty and are omitted from JSON.
struct Point {
  std::string category;   // "width" | "empty-impl" | "const-ret" | "call-context"
  std::string subtype;    // "param" | "global" | "resource-missing" | "param-check"
  std::vector<std::string> archs;
  std::vector<std::string> loc;      // "arch:file:line" (arch-layer) or "file:line"
  // width-param:
  std::string param;                 // "arg#N"
  std::string commonType;            // common-side type description
  std::string archType;              // arch-side type description
  // width-global:
  std::string global;
  std::string globalType;
  std::string valueType;
  std::string tracedFrom;
  // empty-impl / const-ret:
  std::string func;
  std::vector<std::string> defs;     // "arch:file:line"
  // resource-missing:
  std::string resource;
  std::string commonCall;            // common-side call "file:line"
  std::vector<std::string> writes;   // "arch:file:line(kind)" or "arch:(无)"
  // param-check:
  std::string useKind;               // index | len | shift | deref
  std::vector<std::string> checked;  // archs that check the param
  std::vector<std::string> unchecked;// archs that don't
  // call-missing:
  std::string missingCall;           // common function not called on some archs
  std::vector<std::string> called;   // archs that call missingCall
  std::vector<std::string> notCalled;// archs that don't call it
};

// "u64 (fixed,64-bit)" style description of a type.
static std::string fmtType(const arb::TypeInfo &t) {
  std::string s = t.spelling;
  if (t.fixed)
    s += " (fixed," + std::to_string(t.sizeBits) + "-bit)";
  else if (t.archwidth)
    s += " (arch-width)";
  else if (t.sizeBits >= 0)
    s += " (" + std::to_string(t.sizeBits) + "-bit)";
  return s;
}

// Resolve a function name to def indices (prefer exact USR, then name).
static void defsOf(const Index &ix, const std::string &name, std::vector<int> &out) {
  out.clear();
  auto it = ix.byName.find(name);
  if (it != ix.byName.end())
    out = it->second;
}

// arch -> "file:line" of a function's definition (first def per arch).
static std::map<std::string, std::string> defLocByArch(const Index &ix,
                                                       const std::string &name) {
  std::map<std::string, std::string> m;
  std::vector<int> ids;
  defsOf(ix, name, ids);
  for (int i : ids) {
    const Def &D = ix.defs[i];
    if (!m.count(D.srcArch))
      m[D.srcArch] = D.d.file + ":" + std::to_string(D.d.line);
  }
  return m;
}

static void emitPoint(std::vector<Point> &points, std::map<std::string, int> &counts,
                      Point &&p) {
  std::string key = p.category;
  if (!p.subtype.empty())
    key += "/" + p.subtype;
  counts[key]++;
  points.push_back(std::move(p));
}

// Common-side call site "file:line" of a function (first caller outside arch/).
static std::string commonCallLoc(const Index &ix, const std::string &name) {
  auto it = ix.callsByCallee.find(name);
  if (it == ix.callsByCallee.end())
    return "";
  for (int ci : it->second) {
    const Call &C = ix.calls[ci];
    if (arb::archOfFile(C.c.callerFile).empty())
      return C.c.file + ":" + std::to_string(C.c.line);
  }
  return "";
}

// Category 1 (width, param subtype): a caller passes a value to an arch-defined
// function whose parameter has a mismatched type/width. Point = the arch-side
// function, all analyzed arches listed in loc.
static void runWidthParamPoints(Index &ix, std::vector<Point> &points,
                                std::map<std::string, int> &counts) {
  std::set<std::string> seen;
  for (const Call &C : ix.calls) {
    std::vector<int> cids;
    defsOf(ix, C.c.calleeName, cids);
    bool calleeArch = false;
    for (int i : cids)
      if (!ix.defs[i].fileArch.empty()) { calleeArch = true; break; }
    if (!calleeArch)
      continue;
    size_t n = std::min(C.c.args.size(), C.c.params.size());
    for (size_t i = 0; i < n; i++) {
      if (!typeMismatch(C.c.args[i], C.c.params[i]))
        continue;
      std::string key = C.c.calleeName + "|" + std::to_string(i);
      if (!seen.insert(key).second)
        continue;
      Point P;
      P.category = "width";
      P.subtype = "param";
      P.param = "arg#" + std::to_string(i);
      P.commonType = fmtType(C.c.args[i]);
      P.archType = fmtType(C.c.params[i]);
      P.func = C.c.calleeName;
      P.commonCall = C.c.file + ":" + std::to_string(C.c.line);
      auto locs = defLocByArch(ix, C.c.calleeName);
      for (auto &kv : locs) {
        P.archs.push_back(kv.first);
        P.loc.push_back(kv.first + ":" + kv.second);
      }
      emitPoint(points, counts, std::move(P));
    }
  }
}

// Categories 2 & 3, both based on the SAME function name defined under arch/
// in >=2 arches: empty/default return, resource write missing, param check
// differing.
static void runArchFamilyPoints(Index &ix, std::vector<Point> &points,
                                std::map<std::string, int> &counts) {
  for (auto &kv : ix.byName) {
    const std::string &name = kv.first;
    const std::vector<int> &ids = kv.second;
    std::map<std::string, const Def *> byArch;
    bool anyArch = false;
    for (int i : ids) {
      const Def &D = ix.defs[i];
      if (!byArch.count(D.srcArch))
        byArch[D.srcArch] = &D;
      if (!D.fileArch.empty())
        anyArch = true;
    }
    if (byArch.size() < 2 || !anyArch)
      continue;

    // ---- Category 2: empty impl / const return ----
    {
      bool anyNormal = false, anyEmpty = false, anyConst = false;
      for (auto &a : byArch) {
        if (a.second->d.bodyKind == "normal") anyNormal = true;
        else if (a.second->d.bodyKind == "empty") anyEmpty = true;
        else if (a.second->d.bodyKind == "const") anyConst = true;
      }
      auto emitImpl = [&](const std::string &cat) {
        Point P;
        P.category = cat;
        P.func = name;
        std::string cl = commonCallLoc(ix, name);
        if (!cl.empty())
          P.loc.push_back(cl);
        for (auto &a : byArch) {
          P.archs.push_back(a.first);
          P.defs.push_back(a.first + ":" + a.second->d.file + ":" +
                           std::to_string(a.second->d.line));
        }
        emitPoint(points, counts, std::move(P));
      };
      if (anyNormal && anyConst)
        emitImpl("const-ret");
      if (anyNormal && anyEmpty)
        emitImpl("empty-impl");
    }

    // ---- Category 3-1: resource write missing ----
    {
      std::set<std::string> allRes;
      for (auto &a : byArch)
        for (auto &w : a.second->d.writeLocs)
          allRes.insert(w.resource);
      for (const auto &res : allRes) {
        if (isArchGlobalKey(res, ix))
          continue;
        std::set<std::string> writers;
        for (auto &a : byArch)
          for (auto &w : a.second->d.writeLocs)
            if (w.resource == res) { writers.insert(a.first); break; }
        if (writers.empty() || writers.size() >= byArch.size())
          continue;
        Point P;
        P.category = "call-context";
        P.subtype = "resource-missing";
        P.func = name;
        P.resource = res;
        std::string cl = commonCallLoc(ix, name);
        if (!cl.empty())
          P.commonCall = cl;
        for (auto &a : byArch) {
          P.archs.push_back(a.first);
          if (writers.count(a.first)) {
            for (auto &w : a.second->d.writeLocs)
              if (w.resource == res) {
                P.writes.push_back(a.first + ":" + w.file + ":" +
                                   std::to_string(w.line) + "(" + w.kind + ")");
                P.loc.push_back(a.first + ":" + w.file + ":" + std::to_string(w.line));
              }
          } else {
            P.writes.push_back(a.first + ":(无)");
            P.loc.push_back(a.first + ":(无写入)");
          }
        }
        emitPoint(points, counts, std::move(P));
      }
    }

    // ---- Category 3-2: param check differing ----
    {
      std::map<std::string, std::set<std::string>> useByArch, checkedByArch;
      for (auto &a : byArch) {
        const Def &D = *a.second;
        std::set<std::string> chk(D.d.checked.begin(), D.d.checked.end());
        for (auto &u : D.d.dangerUses) {
          std::string key = u.param + ":" + u.kind;
          useByArch[key].insert(a.first);
          if (chk.count(u.param))
            checkedByArch[key].insert(a.first);
        }
      }
      for (auto &u : useByArch) {
        const std::string &key = u.first;
        if (u.second.size() < 2)
          continue;
        std::set<std::string> checkers = checkedByArch[key];
        if (checkers.empty() || checkers.size() >= u.second.size())
          continue; // no asymmetry (all or none check)
        std::string param = key.substr(0, key.find(':'));
        std::string kind = key.substr(key.find(':') + 1);
        Point P;
        P.category = "call-context";
        P.subtype = "param-check";
        P.func = name;
        P.param = param;
        P.useKind = kind;
        for (auto &a : byArch) {
          P.archs.push_back(a.first);
          (checkers.count(a.first) ? P.checked : P.unchecked).push_back(a.first);
          bool found = false;
          for (auto &du : a.second->d.dangerUses)
            if (du.param == param && du.kind == kind) {
              P.loc.push_back(a.first + ":" + du.file + ":" + std::to_string(du.line));
              found = true;
              break;
            }
          if (!found)
            P.loc.push_back(a.first + ":(无)");
        }
        emitPoint(points, counts, std::move(P));
      }
    }

    // ---- Category 3-3: common-function call missing (call-missing) ----
    {
      std::map<std::string, std::set<std::string>> archCommonCalls;
      for (auto &a : byArch) {
        const Def &D = *a.second;
        auto it = ix.callsByCaller.find(D.key);
        if (it == ix.callsByCaller.end())
          continue;
        for (int ci : it->second) {
          const Call &C = ix.calls[ci];
          // 只保留「纯公共」被调函数（有定义、且没有任何 arch/ 下的定义）
          std::vector<int> cids;
          defsOf(ix, C.c.calleeName, cids);
          if (cids.empty())
            continue;
          bool anyArch = false;
          for (int i : cids)
            if (!ix.defs[i].fileArch.empty()) { anyArch = true; break; }
          if (anyArch)
            continue;
          archCommonCalls[a.first].insert(C.c.calleeName);
        }
      }
      std::set<std::string> allCommon;
      for (auto &kv : archCommonCalls)
        allCommon.insert(kv.second.begin(), kv.second.end());
      for (const auto &callee : allCommon) {
        std::set<std::string> callers;
        for (auto &kv : archCommonCalls)
          if (kv.second.count(callee))
            callers.insert(kv.first);
        if (callers.empty() || callers.size() >= byArch.size())
          continue; // 全调或全不调，无失配
        // call-missing 噪声控制（策略）：
        //   首选：只报「被漏调的公共函数会写共享资源」的——missingCall 的任一
        //   def 有 writeLocs 才保留，过滤掉 _printk/ilog2/snprintf 这类无写
        //   副作用的日志/工具函数。实测 1308 -> 158。
        //   兜底：若该策略失效（残留仍多且无意义），改用黑名单过滤（_printk、
        //   printk、pr_*、dev_*、snprintf、sprintf、__ilog2_*、is_power_of_2 等）。
        {
          std::vector<int> cids;
          defsOf(ix, callee, cids);
          bool writesRes = false;
          for (int i : cids)
            if (!ix.defs[i].d.writeLocs.empty()) { writesRes = true; break; }
          if (!writesRes)
            continue;
        }
        Point P;
        P.category = "call-context";
        P.subtype = "call-missing";
        P.func = name;
        P.missingCall = callee;
        for (auto &a : byArch) {
          P.archs.push_back(a.first);
          (callers.count(a.first) ? P.called : P.notCalled).push_back(a.first);
          P.loc.push_back(a.first + ":" + a.second->d.file + ":" +
                          std::to_string(a.second->d.line));
        }
        emitPoint(points, counts, std::move(P));
      }
    }
  }
}

// Emit type-consistency points for global-variable narrowings (the data-flow
// form of the type check): a global of arch-width type is assigned a fixed-width
// value (or vice versa). The assignment statement is the target point; the
// RHS source variable is recorded in `tracedFrom` for later data-flow tracing.
static void runGlobalFlowPoints(
    const std::vector<std::pair<std::string, arb::GlobalFlow>> &globalFlows,
    std::vector<Point> &points, std::map<std::string, int> &counts) {
  std::set<std::string> emitted;
  for (const auto &[arch, g] : globalFlows) {
    if (!typeMismatch(g.lhs, g.rhs))
      continue;
    std::string key = g.file + ":" + std::to_string(g.line) + "|" + g.global;
    if (!emitted.insert(key).second)
      continue;
    Point P;
    P.category = "width";
    P.subtype = "global";
    P.global = g.global;
    P.globalType = fmtType(g.lhs);
    P.valueType = fmtType(g.rhs);
    P.archs.push_back(arch);
    P.loc.push_back(g.file + ":" + std::to_string(g.line));
    if (!g.srcVar.empty())
      P.tracedFrom = g.srcVar;
    emitPoint(points, counts, std::move(P));
  }
}

static llvm::json::Value pointToJSON(const Point &p) {
  using llvm::json::Array;
  using llvm::json::Object;
  using llvm::json::Value;
  auto arr = [](const std::vector<std::string> &v) {
    Array a;
    for (const auto &x : v)
      a.push_back(x);
    return a;
  };
  Object o;
  o["category"] = p.category;
  if (!p.subtype.empty())
    o["subtype"] = p.subtype;
  o["loc"] = arr(p.loc);
  if (!p.archs.empty())
    o["archs"] = arr(p.archs);
  if (!p.param.empty())
    o["param"] = p.param;
  if (!p.func.empty())
    o["func"] = p.func;
  if (!p.commonType.empty())
    o["commonType"] = p.commonType;
  if (!p.archType.empty())
    o["archType"] = p.archType;
  if (!p.global.empty())
    o["global"] = p.global;
  if (!p.globalType.empty())
    o["globalType"] = p.globalType;
  if (!p.valueType.empty())
    o["valueType"] = p.valueType;
  if (!p.tracedFrom.empty())
    o["tracedFrom"] = p.tracedFrom;
  if (!p.func.empty())
    o["func"] = p.func;
  if (!p.defs.empty())
    o["defs"] = arr(p.defs);
  if (!p.resource.empty())
    o["resource"] = p.resource;
  if (!p.commonCall.empty())
    o["commonCall"] = p.commonCall;
  if (!p.writes.empty())
    o["writes"] = arr(p.writes);
  if (!p.useKind.empty())
    o["useKind"] = p.useKind;
  if (!p.checked.empty())
    o["checked"] = arr(p.checked);
  if (!p.unchecked.empty())
    o["unchecked"] = arr(p.unchecked);
  if (!p.missingCall.empty())
    o["missingCall"] = p.missingCall;
  if (!p.called.empty())
    o["called"] = arr(p.called);
  if (!p.notCalled.empty())
    o["notCalled"] = arr(p.notCalled);
  return Value(std::move(o));
}

} // namespace

namespace arb {
int analyzeMain(int argc, const char **argv);
}

int arb::analyzeMain(int argc, const char **argv) {
  cl::HideUnrelatedOptions(ArchBoundAnalyzeCat);
  cl::ParseCommandLineOptions(argc, argv, "archbound analyze");

  if (OptFacts.empty()) {
    errs() << "archbound analyze: missing --facts <file,...>\n";
    return 1;
  }

  Index ix;
  std::vector<Finding> findings;
  std::string report;
  std::vector<std::pair<std::string, arb::GlobalFlow>> globalFlows;

  llvm::SmallVector<llvm::StringRef, 8> files;
  llvm::StringRef(OptFacts.getValue()).split(files, ',');
  for (auto f : files) {
    if (f.empty())
      continue;
    auto bufOr = llvm::MemoryBuffer::getFile(f);
    if (!bufOr) {
      errs() << "cannot read " << f << "\n";
      continue;
    }
    auto v = json::parse(bufOr.get()->getBuffer());
    if (!v) {
      errs() << "bad json " << f << "\n";
      continue;
    }
    arb::Facts facts = arb::factsFromJSON(*v);
    ix.archs.push_back(facts.arch);
    for (auto &d : facts.defs) {
      if (!isRuntimeKernelFile(d.file))
        continue;
      Def D;
      D.d = std::move(d);
      D.srcArch = facts.arch;
      D.fileArch = arb::archOfFile(D.d.file);
      D.key = defKey(D.srcArch, D.d.file, D.d.line);
      ix.byName[D.d.name].push_back((int)ix.defs.size());
      if (!D.d.usr.empty())
        ix.byUsr[D.d.usr].push_back((int)ix.defs.size());
      ix.byKey[D.key].push_back((int)ix.defs.size());
      ix.defs.push_back(std::move(D));
    }
    for (auto &c : facts.calls) {
      if (!isRuntimeKernelFile(c.callerFile))
        continue;
      Call C;
      C.c = std::move(c);
      C.srcArch = facts.arch;
      C.fileArch = arb::archOfFile(C.c.file);
      C.callerKey = defKey(C.srcArch, C.c.callerFile, C.c.callerLine);
      ix.callsByCaller[C.callerKey].push_back((int)ix.calls.size());
      ix.callsByCallee[C.c.calleeName].push_back((int)ix.calls.size());
      if (!C.c.ctx.condLoc.empty())
        ix.callsByCtx[C.c.ctx.condLoc].push_back((int)ix.calls.size());
      ix.calls.push_back(std::move(C));
    }
    for (auto &p : facts.pps) {
      PP P;
      P.p = std::move(p);
      P.srcArch = facts.arch;
      P.fileArch = arb::archOfFile(P.p.file);
      ix.pps.push_back(std::move(P));
    }
    for (auto &fl : facts.flows) {
      Flow F;
      F.f = std::move(fl);
      F.srcArch = facts.arch;
      ix.flows.push_back(std::move(F));
    }
    for (auto &g : facts.globals)
      ix.globalDefFiles[g.name].insert(g.file);
    for (auto &m : facts.macros) {
      if (m.kind == "arch-def")
        ix.archDefMacros[facts.arch].insert(m.name);
      else if (m.kind == "common-use")
        ix.commonUsedMacros.insert(m.name);
    }
    for (auto &r : facts.macroRes)
      ix.macroResByArch[r.macro][facts.arch].insert(r.resource);
    for (auto &g : facts.globalFlows)
      if (isRuntimeKernelFile(g.file))
        globalFlows.push_back({facts.arch, std::move(g)});
  }

  errs() << "[analyze] loaded defs=" << ix.defs.size() << " calls=" << ix.calls.size()
         << " flows=" << ix.flows.size() << "\n";

  runAnalysis(ix, findings, report);
  errs() << "[analyze] runAnalysis done\n";

  // Categorized test points.
  std::vector<Point> points;
  std::map<std::string, int> pointCount;
  runWidthParamPoints(ix, points, pointCount);
  errs() << "[analyze] runWidthParamPoints done points=" << points.size() << "\n";

  runGlobalFlowPoints(globalFlows, points, pointCount);
  errs() << "[analyze] runGlobalFlowPoints done total=" << points.size() << "\n";

  runArchFamilyPoints(ix, points, pointCount);
  errs() << "[analyze] runArchFamilyPoints done total=" << points.size() << "\n";

  // Filter: drop points with no category (shouldn't happen) and single-arch
  // points, EXCEPT width/global narrowings (a narrowing observed in a single
  // arch is still cross-arch relevant: the same line truncates on a 32-bit
  // arch but not on a 64-bit one).
  {
    size_t before = points.size();
    std::vector<Point> kept;
    kept.reserve(points.size());
    std::map<std::string, int> newCount;
    for (auto &p : points) {
      if (p.category.empty())
        continue;
      if (p.archs.size() < 2 && !(p.category == "width" && p.subtype == "global"))
        continue;
      std::string key = p.category;
      if (!p.subtype.empty())
        key += "/" + p.subtype;
      newCount[key]++;
      kept.push_back(std::move(p));
    }
    points = std::move(kept);
    pointCount = std::move(newCount);
    errs() << "[analyze] filtered points " << before << " -> " << points.size()
           << "\n";
  }

  // Header.
  std::string header;
  raw_string_ostream H(header);
  H << "ARCHBOUND CROSS-ARCH BOUNDARY REPORT\n";
  H << "=====================================\n";
  H << "archs: ";
  for (size_t i = 0; i < ix.archs.size(); i++)
    H << ix.archs[i] << (i + 1 < ix.archs.size() ? ", " : "");
  H << "\n";
  H << "defs=" << ix.defs.size() << " calls=" << ix.calls.size() << " pps=" << ix.pps.size()
    << "\n\n";
  H.flush();

  // Findings summary.
  std::map<std::string, int> counts;
  for (auto &f : findings)
    counts[f.section]++;
  raw_string_ostream S(report);
  S << "[6] FINDINGS SUMMARY\n";
  for (auto &kv : counts)
    S << "    " << kv.first << ": " << kv.second << "\n";
  S << "\n";
  for (auto &f : findings)
    S << "  [" << f.section << "] " << f.detail << "\n";
  S.flush();

  std::string full = header + report;

  if (OptReport.empty()) {
    outs() << full;
  } else {
    std::error_code EC;
    raw_fd_ostream OS(OptReport.getValue(), EC, sys::fs::OF_Text);
    if (EC) {
      errs() << "cannot open " << OptReport.getValue() << ": " << EC.message() << "\n";
      return 1;
    }
    OS << full;
    OS.close();
  }

  if (!OptJSON.empty()) {
    json::Object j;
    json::Array jarchs;
    for (auto &a : ix.archs)
      jarchs.push_back(a);
    j["archs"] = std::move(jarchs);
    j["defs"] = (int64_t)ix.defs.size();
    j["calls"] = (int64_t)ix.calls.size();
    j["pps"] = (int64_t)ix.pps.size();
    json::Array jf;
    for (auto &f : findings) {
      json::Object o;
      o["section"] = f.section;
      o["detail"] = f.detail;
      jf.push_back(std::move(o));
    }
    j["findings"] = std::move(jf);
    std::error_code EC;
    raw_fd_ostream JO(OptJSON.getValue(), EC, sys::fs::OF_Text);
    if (EC) {
      errs() << "cannot open " << OptJSON.getValue() << ": " << EC.message() << "\n";
      return 1;
    }
    JO << json::Value(std::move(j));
    JO.close();
  }

  if (!OptPoints.empty()) {
    json::Object j;
    json::Array jarchs;
    for (auto &a : ix.archs)
      jarchs.push_back(a);
    j["archs"] = std::move(jarchs);
    json::Array jp;
    for (auto &p : points)
      jp.push_back(pointToJSON(p));
    j["points"] = std::move(jp);
    json::Object jh;
    for (auto &kv : pointCount)
      jh[kv.first] = (int64_t)kv.second;
    j["count"] = std::move(jh);
    std::error_code EC;
    raw_fd_ostream PO(OptPoints.getValue(), EC, sys::fs::OF_Text);
    if (EC) {
      errs() << "cannot open " << OptPoints.getValue() << ": " << EC.message() << "\n";
      return 1;
    }
    PO << json::Value(std::move(j));
    PO.close();
    errs() << "[points] points=" << points.size();
    for (auto &kv : pointCount)
      errs() << " " << kv.first << "=" << kv.second;
    errs() << " -> " << OptPoints.getValue() << "\n";
  }

  return 0;
}
