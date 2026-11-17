#ifndef ARB_FACTS_H
#define ARB_FACTS_H

#include "llvm/Support/JSON.h"
#include <string>
#include <vector>

namespace arb {

// Type description captured at a boundary: enough to reason about width /
// signedness / fixed-vs-architecture-width without re-parsing.
struct TypeInfo {
  std::string spelling;    // e.g. "u64", "unsigned long", "size_t", "int"
  int sizeBits = -1;       // canonical size in bits; -1 if unknown
  bool isInt = false;
  bool isSigned = false;
  bool fixed = false;      // fixed-width typedef (u8..u64, s8..s64, uintN_t ...)
  bool archwidth = false;  // arch-dependent width (unsigned long, size_t, ...)
};

// Dispatch context enclosing a call site: the innermost architecture-selecting
// conditional (preprocessor #if/#ifdef or a runtime if/switch). Used to group
// the alternative implementations of the same semantic slot across archs.
struct DispatchCtx {
  std::string kind;    // "" (none) | "pp-if" | "runtime-if" | "switch"
  std::string condLoc; // "file:line" of the condition (stable cross-arch anchor)
  std::string cond;    // condition text or macro name
};

// A single WRITE to a resource, with its source location and mechanism.
// Used by the call-context "resource write asymmetry" check: the write location
// is the target point.
struct WriteLoc {
  std::string resource; // resource key ("p#0[]", "g:foo", "struct.field")
  std::string file;     // relative path where the write happens
  int line = 0;
  std::string kind;     // "assign" | "bitop" | "memwrite"
};

// A single DANGEROUS use of a parameter (subscript / memcpy-length / shift /
// deref), with the source location of the use and, for length kinds, the
// callee that received the length. The unchecked-use call site is the point.
struct DangerUse {
  std::string param;  // "param#N"
  std::string kind;   // "index" | "len" | "shift" | "deref"
  std::string callee; // for "len": the memory/string routine (e.g. "memcpy")
  std::string file;   // relative path where the use happens
  int line = 0;
};

// One function definition (or, for inline helpers, one per arch context).
struct DefFact {
  std::string usr;         // clang USR (may be empty); arch-independent for extern fns
  std::string name;
  std::string file;        // path relative to kernel root
  int line = 0;
  bool isStatic = false;
  bool isDef = true;
  TypeInfo ret;
  std::vector<TypeInfo> params;
  std::string bodyKind = "normal"; // normal | empty | const | void
  std::string constVal;            // integer literal when bodyKind == "const"
  // Resource access model (parameter-index / global based, naming-independent):
  //   accesses -> resource keys touched (read OR write): "p#1->state", "*p#0", "g:foo"
  //   writes   -> subset of accesses that are WRITTEN (assignment LHS, ++/--,
  //               memory-write function destination)
  std::vector<std::string> accesses;
  std::vector<std::string> writes;
  // accesses that happen under a conditional guard (if/while/for/?:/&&/||).
  // Unconditional reads = accesses - writes - soft  (the "hard" contract);
  // conditional reads   = soft - writes            (the "soft" contract).
  std::vector<std::string> soft;
  // call-context / precondition data:
  //   checked   -> "param#N" params that appear in a comparison (bounds check)
  //   dangerous -> "param#N:index|len|shift|deref" params used in a risky position
  std::vector<std::string> checked;
  std::vector<std::string> dangerous;
  // Location-bearing versions of writes / dangerous uses (for the point).
  std::vector<WriteLoc> writeLocs;
  std::vector<DangerUse> dangerUses;
  std::vector<std::string> retConsts; // [ext] integer constants returned
  bool retNonConst = false;           // [ext] some return is not an integer constant
};

// One call site.
struct CallFact {
  std::string callerUsr;
  std::string callerName;
  std::string callerFile;  // definition file of the enclosing function
  int callerLine = 0;      // definition line of the enclosing function
  std::string calleeUsr;
  std::string calleeName;
  std::string file;        // call-site file
  int line = 0;            // call-site line
  std::vector<TypeInfo> args;
  std::vector<TypeInfo> params;
  DispatchCtx ctx;         // enclosing arch-dispatch conditional (if any)
  bool usesRet = false;    // call result is consumed (not a bare "foo();")
  std::vector<std::string> argConsts; // [ext] per argument: integer constant value or ""
};

// One preprocessor observation (arch-conditional / __HAVE_ARCH capability).
struct PPFact {
  std::string file;
  int line = 0;
  std::string kind;   // ifdef | ifndef | if | elif | define
  std::string cond;   // macro name or condition text
};

// One value-flow edge at assignment / initialization / return: a value of type
// `rhs` is stored into / returned as type `lhs`. This is where a fixed-width
// value (u64) can be silently narrowed into an arch-width type (unsigned long).
struct FlowFact {
  std::string kind;   // init | assign | return
  std::string func;   // enclosing function
  std::string file;
  int line = 0;
  TypeInfo lhs;       // destination type (variable / return type)
  TypeInfo rhs;       // source type (stored / returned expression)
  std::string lhsName; // destination variable name (for data-flow trace-back)
  std::string rhsName; // source variable name when a direct DeclRefExpr, else ""
};

// A global/static variable definition, for cross-TU "arch-private vs shared"
// resolution: if a global is DEFINED under arch/ (e.g. __per_cpu_offset defined
// in arch/x86/kernel/setup_percpu.c), it is arch-internal state even though it
// is declared in a common header.
struct GlobalDef {
  std::string name;
  std::string file;   // defining file (relative to root)
};

// A macro observation for capability detection:
//   arch-def   -> the macro is #define'd in an arch/ header
//   common-use -> the macro is expanded (used) in common (non-arch) code
struct MacroFact {
  std::string name;
  std::string file;
  std::string kind;   // "arch-def" | "common-use"
};

// A resource access attributed to the macro whose expansion produced it:
//   macro M, when expanded, reads/writes `resource`. Compared across archs to
//   detect (1) inconsistent macro definitions, (2) arch-exclusive resources.
struct MacroRes {
  std::string macro;    // macro name
  std::string resource; // resource key ("p#N->field", "g:name")
};

// An assignment to a global variable, for the type-consistency "global variable
// data-flow trace-back" check: a global of arch-width type is assigned a
// fixed-width value (or vice versa). The assignment statement is the target
// point; `srcVar` names the RHS variable when it is a direct decl ref.
struct GlobalFlow {
  std::string global;   // global variable name (no "g:" prefix)
  std::string file;     // assignment file (relative to root)
  int line = 0;         // assignment line
  TypeInfo lhs;         // global's declared type
  TypeInfo rhs;         // assigned value's type
  std::string srcVar;   // RHS variable name if it is a DeclRefExpr, else ""
};

// [ext] parse status of one compile unit
struct UnitFact {
  std::string file;
  int status = 0; // ClangTool::run result: 0 ok, 1 error, 2 skipped
};

// A single arch's collected facts (produced by one `collect` run).
struct Facts {
  std::string arch;   // which arch this DB was built for
  std::string root;   // absolute kernel root
  std::vector<DefFact> defs;
  std::vector<CallFact> calls;
  std::vector<PPFact> pps;
  std::vector<FlowFact> flows;
  std::vector<GlobalDef> globals;
  std::vector<MacroFact> macros;
  std::vector<MacroRes> macroRes;
  std::vector<GlobalFlow> globalFlows;
  std::vector<UnitFact> units; // [ext]
};

llvm::json::Value toJSON(const TypeInfo &t);
llvm::json::Value toJSON(const DispatchCtx &d);
llvm::json::Value toJSON(const WriteLoc &w);
llvm::json::Value toJSON(const DangerUse &d);
llvm::json::Value toJSON(const DefFact &d);
llvm::json::Value toJSON(const CallFact &c);
llvm::json::Value toJSON(const PPFact &p);
llvm::json::Value toJSON(const FlowFact &f);
llvm::json::Value toJSON(const GlobalDef &g);
llvm::json::Value toJSON(const MacroFact &m);
llvm::json::Value toJSON(const MacroRes &r);
llvm::json::Value toJSON(const GlobalFlow &g);
llvm::json::Value toJSON(const Facts &f);

TypeInfo typeFromJSON(const llvm::json::Value &v);
DispatchCtx ctxFromJSON(const llvm::json::Value &v);
WriteLoc writeLocFromJSON(const llvm::json::Value &v);
DangerUse dangerUseFromJSON(const llvm::json::Value &v);
DefFact defFromJSON(const llvm::json::Value &v);
CallFact callFromJSON(const llvm::json::Value &v);
PPFact ppFromJSON(const llvm::json::Value &v);
FlowFact flowFromJSON(const llvm::json::Value &v);
GlobalDef globalFromJSON(const llvm::json::Value &v);
MacroFact macroFromJSON(const llvm::json::Value &v);
MacroRes macroResFromJSON(const llvm::json::Value &v);
GlobalFlow globalFlowFromJSON(const llvm::json::Value &v);
Facts factsFromJSON(const llvm::json::Value &v);

} // namespace arb

#endif
