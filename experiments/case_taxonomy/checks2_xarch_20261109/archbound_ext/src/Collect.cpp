#include "Facts.h"
#include "Support.h"

#include "clang/AST/ASTConsumer.h"
#include "clang/AST/ASTContext.h"
#include "clang/AST/ASTTypeTraits.h"
#include "clang/AST/Expr.h"
#include "clang/AST/ExprCXX.h"
#include "clang/AST/ParentMapContext.h"
#include "clang/AST/RecursiveASTVisitor.h"
#include "clang/AST/Stmt.h"
#include "clang/Basic/SourceManager.h"
#include "clang/Frontend/CompilerInstance.h"
#include "clang/Frontend/FrontendActions.h"
#include "clang/Index/USRGeneration.h"
#include "clang/Lex/Lexer.h"
#include "clang/Lex/PPCallbacks.h"
#include "clang/Lex/Preprocessor.h"
#include "clang/Tooling/CommonOptionsParser.h"
#include "clang/Tooling/JSONCompilationDatabase.h"
#include "clang/Tooling/Tooling.h"
#include "llvm/Support/CommandLine.h"
#include "llvm/Support/FileSystem.h"
#include "llvm/Support/Path.h"
#include "llvm/Support/ThreadPool.h"
#include "llvm/Support/Threading.h"
#include "llvm/Support/raw_ostream.h"

#include <mutex>
#include <set>
#include <string>
#include <vector>

using namespace clang;
using namespace clang::tooling;

static llvm::cl::OptionCategory ArchBoundCat("archbound-collect options");
static llvm::cl::opt<std::string> OptBuildPath("p", llvm::cl::desc("build dir or compile_commands.json"),
                                               llvm::cl::cat(ArchBoundCat));
static llvm::cl::list<std::string> OptSources(llvm::cl::Positional, llvm::cl::desc("[source files...]"),
                                              llvm::cl::ZeroOrMore, llvm::cl::cat(ArchBoundCat));
static llvm::cl::opt<std::string> OptRoot("root", llvm::cl::desc("kernel source root (absolute)"),
                                          llvm::cl::cat(ArchBoundCat));
static llvm::cl::opt<std::string> OptOut("out", llvm::cl::desc("output facts json"),
                                         llvm::cl::init("facts.json"),
                                         llvm::cl::cat(ArchBoundCat));
static llvm::cl::opt<std::string> OptArch("arch", llvm::cl::desc("architecture tag (auto-inferred if omitted)"),
                                          llvm::cl::init(""), llvm::cl::cat(ArchBoundCat));
static llvm::cl::opt<unsigned> OptJobs("j", llvm::cl::desc("parallel jobs (0 = single-threaded)"),
                                       llvm::cl::init(0), llvm::cl::cat(ArchBoundCat));

namespace {

// ---------------------------------------------------------------------------
// Per-TU accumulation + process-wide deduplicated store.
// ---------------------------------------------------------------------------

// A completed preprocessor branch range (for associating a call site with the
// enclosing #if/#ifdef/#elif/#else chain). Keyed by file ID + [startOff, endOff).
struct PPBranch {
  clang::FileID fid;
  unsigned startOff = 0, endOff = 0;
  std::string anchorLoc; // "file:line" of the original #if (stable across archs)
  std::string cond;      // branch condition text / macro name
};

struct TUState {
  ASTContext *Ctx = nullptr;
  std::string root;
  std::vector<arb::DefFact> defs;
  std::vector<arb::CallFact> calls;
  std::vector<arb::PPFact> pps;
  std::vector<arb::FlowFact> flows;
  std::vector<arb::GlobalDef> globals;
  std::vector<arb::MacroFact> macros;
  std::vector<arb::MacroRes> macroRes;
  std::vector<arb::GlobalFlow> globalFlows;
  std::vector<PPBranch> ppBranches;
};

struct SharedFacts {
  std::mutex M;
  std::string root;
  std::set<std::string> defKeys, callKeys, ppKeys, flowKeys, globalKeys, macroKeys,
      macroResKeys, globalFlowKeys;
  std::vector<arb::DefFact> defs;
  std::vector<arb::CallFact> calls;
  std::vector<arb::PPFact> pps;
  std::vector<arb::FlowFact> flows;
  std::vector<arb::GlobalDef> globals;
  std::vector<arb::MacroFact> macros;
  std::vector<arb::MacroRes> macroRes;
  std::vector<arb::GlobalFlow> globalFlows;
  std::vector<arb::UnitFact> units; // [ext]

  void merge(TUState &S) {
    std::lock_guard<std::mutex> L(M);
    for (auto &d : S.defs) {
      std::string key = d.file + ":" + std::to_string(d.line);
      if (defKeys.insert(key).second)
        defs.push_back(std::move(d));
    }
    for (auto &c : S.calls) {
      std::string key = c.callerFile + ":" + std::to_string(c.callerLine) + "|" +
                        c.calleeName + "|" + c.file + ":" + std::to_string(c.line);
      if (callKeys.insert(key).second)
        calls.push_back(std::move(c));
    }
    for (auto &p : S.pps) {
      std::string key = p.file + ":" + std::to_string(p.line) + "|" + p.kind + "|" + p.cond;
      if (ppKeys.insert(key).second)
        pps.push_back(std::move(p));
    }
    for (auto &fl : S.flows) {
      std::string key = fl.file + ":" + std::to_string(fl.line) + "|" + fl.kind + "|" +
                        fl.lhs.spelling + "|" + fl.rhs.spelling;
      if (flowKeys.insert(key).second)
        flows.push_back(std::move(fl));
    }
    for (auto &g : S.globals) {
      std::string key = g.name + "|" + g.file;
      if (globalKeys.insert(key).second)
        globals.push_back(std::move(g));
    }
    for (auto &m : S.macros) {
      std::string key = m.kind + "|" + m.name;
      if (macroKeys.insert(key).second)
        macros.push_back(std::move(m));
    }
    for (auto &r : S.macroRes) {
      std::string key = r.macro + "|" + r.resource;
      if (macroResKeys.insert(key).second)
        macroRes.push_back(std::move(r));
    }
    for (auto &g : S.globalFlows) {
      std::string key = g.global + "|" + g.file + ":" + std::to_string(g.line);
      if (globalFlowKeys.insert(key).second)
        globalFlows.push_back(std::move(g));
    }
  }
};

static SharedFacts GShared;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

static std::string usrOf(const NamedDecl *D) {
  llvm::SmallString<256> Buf;
  if (D && clang::index::generateUSRForDecl(D, Buf))
    return Buf.str().str();
  return "";
}

static std::string makeRel(const std::string &abs, const std::string &root) {
  if (!root.empty() && abs.size() > root.size() && abs.compare(0, root.size(), root) == 0) {
    size_t off = root.size();
    while (off < abs.size() && abs[off] == '/')
      off++;
    return abs.substr(off);
  }
  return abs;
}

static std::string relFile(SourceManager &SM, SourceLocation Loc) {
  if (Loc.isInvalid())
    return "";
  FileID fid = SM.getFileID(Loc);
  std::string abs;
  if (const FileEntry *FE = SM.getFileEntryForID(fid)) {
    llvm::StringRef real = FE->tryGetRealPathName();
    abs = real.empty() ? FE->getName().str() : real.str();
  }
  if (abs.empty())
    abs = SM.getFilename(Loc).str();
  if (abs.empty())
    abs = SM.getBufferName(Loc).str();
  return makeRel(abs, GShared.root);
}

static void collectTypedefs(QualType T, std::set<std::string> &out) {
  T = T.getLocalUnqualifiedType();
  while (!T.isNull()) {
    if (auto *TT = T->getAs<TypedefType>()) {
      out.insert(TT->getDecl()->getName().str());
      T = TT->desugar();
    } else if (auto *ET = T->getAs<ElaboratedType>()) {
      T = ET->desugar();
    } else if (auto *ST = T->getAs<SubstTemplateTypeParmType>()) {
      T = ST->desugar();
    } else if (auto *AT = T->getAs<AttributedType>()) {
      T = AT->getModifiedType();
    } else if (auto *DT = T->getAs<DecayedType>()) {
      T = DT->getDecayedType();
    } else if (auto *AD = T->getAs<AdjustedType>()) {
      T = AD->getOriginalType();
    } else {
      break;
    }
  }
}

static arb::TypeInfo classify(QualType T, ASTContext &Ctx) {
  arb::TypeInfo ti;
  if (T.isNull())
    return ti;
  ti.spelling = T.getAsString();
  QualType C = T.getCanonicalType();
  if (C->isIntegerType() || C->isEnumeralType()) {
    ti.isInt = true;
    ti.sizeBits = (int)Ctx.getTypeSize(C);
    ti.isSigned = C->isSignedIntegerType();
  } else if (C->isPointerType() || C->isReferenceType()) {
    ti.sizeBits = (int)Ctx.getTypeSize(C); // pointer width is arch-dependent
  }
  std::set<std::string> names;
  collectTypedefs(T, names);
  names.insert(ti.spelling);
  for (const auto &n : names) {
    if (arb::isFixedWidthName(n))
      ti.fixed = true;
    if (arb::isArchWidthName(n))
      ti.archwidth = true;
  }
  return ti;
}

static void classifyReturn(ReturnStmt *R, std::string &kind, std::string &val) {
  if (!R->getRetValue()) {
    kind = "void";
    return;
  }
  Expr *E = R->getRetValue()->IgnoreParenCasts();
  bool neg = false;
  if (auto *U = dyn_cast<UnaryOperator>(E)) {
    if (U->getOpcode() == UO_Minus) {
      neg = true;
      E = U->getSubExpr()->IgnoreParenCasts();
    } else if (U->getOpcode() == UO_Plus) {
      E = U->getSubExpr()->IgnoreParenCasts();
    }
  }
  if (auto *I = dyn_cast<IntegerLiteral>(E)) {
    llvm::APSInt V(I->getValue(), /*isUnsigned=*/false);
    if (neg)
      V = -V;
    llvm::SmallString<32> Buf;
    V.toString(Buf, 10);
    kind = "const";
    val = Buf.str().str();
    return;
  }
  kind = "normal";
}

static void classifyBody(Stmt *B, std::string &kind, std::string &val) {
  kind = "normal";
  if (!B)
    return;
  if (auto *R = dyn_cast<ReturnStmt>(B)) {
    classifyReturn(R, kind, val);
    return;
  }
  auto *CS = dyn_cast<CompoundStmt>(B);
  if (!CS)
    return;
  if (CS->body_empty()) {
    kind = "empty";
    return;
  }
  if (CS->size() == 1) {
    if (auto *R = dyn_cast<ReturnStmt>(CS->body_front())) {
      classifyReturn(R, kind, val);
      return;
    }
  }
}

// "file:line" string for a source location (relative path).
static std::string locString(SourceManager &SM, SourceLocation Loc) {
  if (Loc.isInvalid())
    return "";
  // 宏展开位置先解析到真实调用点（否则拿到 "<invalid buffer>:N"，多个宏会撞号）。
  Loc = SM.getFileLoc(Loc);
  std::string f = relFile(SM, Loc);
  if (f.empty())
    return "";
  return f + ":" + std::to_string(SM.getSpellingLineNumber(Loc));
}

// Is the call result actually consumed at this call site? A bare "foo();"
// statement discards the result; an assignment / comparison / return / argument
// consumes it. This distinguishes "const-return stub the common code ignores"
// from "const-return stub the common code branches on".
static bool callResultUsed(CallExpr *CE, ASTContext &Ctx) {
  auto parents = Ctx.getParents(*CE);
  while (!parents.empty()) {
    const DynTypedNode &P = parents[0];
    if (const Expr *E = P.get<Expr>()) {
      // Transparent wrappers around the call's value.
      if (isa<ImplicitCastExpr>(E) || isa<ParenExpr>(E) ||
          isa<ExprWithCleanups>(E) || isa<MaterializeTemporaryExpr>(E) ||
          isa<CXXBindTemporaryExpr>(E) || isa<FullExpr>(E)) {
        parents = Ctx.getParents(P);
        continue;
      }
      return true; // any other expression context consumes the value
    }
    if (P.get<VarDecl>() || P.get<ReturnStmt>() || P.get<BinaryOperator>() ||
        P.get<CallExpr>() || P.get<UnaryOperator>() || P.get<ConditionalOperator>() ||
        P.get<IfStmt>() || P.get<SwitchStmt>() || P.get<WhileStmt>() ||
        P.get<DoStmt>() || P.get<ForStmt>() || P.get<ArraySubscriptExpr>())
      return true;
    return false; // e.g. a bare "foo();" inside a CompoundStmt
  }
  return false;
}

// Is the (possibly pointer-to-)record type ARCH-PRIVATE, i.e. defined under
// arch/<name>/? A field of such a type (e.g. pt_regs, thread_struct) is an
// architecture-internal representation; only the SHARED resource its value
// flows from/to matters for cross-arch comparison.
static bool isArchPrivateRecord(QualType T, SourceManager &SM) {
  T = T.getCanonicalType();
  if (T->isPointerType())
    T = T->getPointeeType();
  if (const RecordType *RT = T->getAs<RecordType>()) {
    const RecordDecl *RD = RT->getDecl()->getDefinition();
    if (!RD)
      return false;
    std::string f = relFile(SM, SM.getSpellingLoc(RD->getLocation()));
    return f.rfind("arch/", 0) == 0;
  }
  return false;
}

// Is a global/static variable arch-internal? True if EITHER its declaration or
// its definition lives under arch/ (covers "declared in common header, defined
// per-arch" globals such as __per_cpu_offset / loops_per_jiffy).
static bool isArchPrivateGlobal(const VarDecl *VD, SourceManager &SM) {
  auto inArch = [&](const VarDecl *V) {
    if (!V)
      return false;
    return relFile(SM, SM.getSpellingLoc(V->getLocation())).rfind("arch/", 0) == 0;
  };
  const VarDecl *Canon = VD->getCanonicalDecl();
  if (inArch(Canon))
    return true;
  if (const VarDecl *Def = Canon->getDefinition())
    if (inArch(Def))
      return true;
  return false;
}

// Returns the name of the NAMED struct that owns the field, walking up through
// anonymous structs (e.g. pgd inside struct mm_struct's anonymous member).
static std::string namedStructName(const ValueDecl *MD) {
  if (auto *FD = dyn_cast<FieldDecl>(MD)) {
    const RecordDecl *RD = FD->getParent();
    while (RD && RD->getName().empty())
      RD = dyn_cast<RecordDecl>(RD->getDeclContext());
    if (RD && !RD->getName().empty())
      return RD->getName().str();
  }
  return "";
}

// Raw resource key WITHOUT the arch-private filter. Used for macro attribution:
// we WANT to see which arch-private resources (cpu_data, pt_regs fields, ...) a
// macro touches, because that is exactly the arch-exclusive capability signal.
static std::string rawResourceKey(const Expr *E) {
  E = E->IgnoreParenImpCasts();
  if (!E)
    return "";
  if (auto *M = dyn_cast<MemberExpr>(E)) {
    std::string name;
    if (const ValueDecl *MD = M->getMemberDecl())
      name = MD->getName().str();
    else
      name = M->getMemberNameInfo().getName().getAsString();
    if (name.empty())
      return rawResourceKey(M->getBase()); // 匿名结构体成员：透明
    // 全局键：字段所属的具名结构体.字段（跨函数、跨架构可比）
    std::string tn = namedStructName(M->getMemberDecl());
    if (!tn.empty())
      return tn + "." + name;
    std::string base = rawResourceKey(M->getBase());
    if (base.empty())
      return "";
    return base + (M->isArrow() ? "->" : ".") + name;
  }
  if (auto *U = dyn_cast<UnaryOperator>(E)) {
    if (U->getOpcode() == UO_Deref) {
      std::string sub = rawResourceKey(U->getSubExpr());
      if (sub.empty())
        return "";
      return "*" + sub;
    }
  }
  if (auto *A = dyn_cast<ArraySubscriptExpr>(E)) {
    std::string base = rawResourceKey(A->getBase());
    if (base.empty())
      return "";
    return base + "[]";
  }
  if (auto *D = dyn_cast<DeclRefExpr>(E)) {
    if (auto *P = dyn_cast<ParmVarDecl>(D->getDecl()))
      return "p#" + std::to_string(P->getFunctionScopeIndex());
    if (auto *V = dyn_cast<VarDecl>(D->getDecl()))
      if (V->hasGlobalStorage())
        return "g:" + V->getName().str();
    return "";
  }
  return "";
}

// Render a resource access as a naming-independent key, but ONLY for SHARED
// resources (a field of a common struct, a shared global, a scalar param).
// Accesses to arch-private resources (registers, arch-specific struct fields)
// return "" — their shared origin is captured separately by the shared reads /
// writes that feed them (the data-flow projection).
static std::string resourceKey(const Expr *E, SourceManager &SM) {
  E = E->IgnoreParenImpCasts();
  if (!E)
    return "";
  if (auto *M = dyn_cast<MemberExpr>(E)) {
    // If the base object is an arch-private struct, skip the whole field access.
    if (isArchPrivateRecord(M->getBase()->getType(), SM))
      return "";
    std::string name;
    if (const ValueDecl *MD = M->getMemberDecl())
      name = MD->getName().str();
    else
      name = M->getMemberNameInfo().getName().getAsString();
    if (name.empty())
      return resourceKey(M->getBase(), SM); // 匿名结构体成员：透明
    // 全局键：字段所属的具名结构体.字段（跨函数、跨架构可比）
    std::string tn = namedStructName(M->getMemberDecl());
    if (!tn.empty())
      return tn + "." + name;
    std::string base = resourceKey(M->getBase(), SM);
    if (base.empty())
      return "";
    return base + (M->isArrow() ? "->" : ".") + name;
  }
  if (auto *U = dyn_cast<UnaryOperator>(E)) {
    if (U->getOpcode() == UO_Deref) {
      if (isArchPrivateRecord(U->getSubExpr()->getType(), SM))
        return "";
      std::string sub = resourceKey(U->getSubExpr(), SM);
      if (sub.empty())
        return "";
      return "*" + sub;
    }
  }
  if (auto *A = dyn_cast<ArraySubscriptExpr>(E)) {
    if (isArchPrivateRecord(A->getBase()->getType(), SM))
      return "";
    std::string base = resourceKey(A->getBase(), SM);
    if (base.empty())
      return "";
    return base + "[]";
  }
  if (auto *D = dyn_cast<DeclRefExpr>(E)) {
    if (auto *P = dyn_cast<ParmVarDecl>(D->getDecl())) {
      // scalar params are shared; pointer params are shared only if the pointee
      // record is not arch-private.
      if (isArchPrivateRecord(P->getType(), SM))
        return "";
      return "p#" + std::to_string(P->getFunctionScopeIndex());
    }
    if (auto *V = dyn_cast<VarDecl>(D->getDecl())) {
      if (!V->hasGlobalStorage())
        return ""; // local var is not a shared resource
      if (isArchPrivateGlobal(V, SM))
        return ""; // arch-internal global
      return "g:" + V->getName().str();
    }
    return "";
  }
  return "";
}

// Well-known memory-write routines: their destination (arg 0) is a write target.
static bool isMemWrite(llvm::StringRef name) {
  return name == "memcpy" || name == "memmove" || name == "memset" ||
         name == "strcpy" || name == "strncpy" || name == "strlcpy" ||
         name == "strscpy" || name == "copy_from_user" ||
         name == "strncpy_from_user";
}

// Returns the parameter index (>= 0) if E (through parens/casts/member-base/
// array-base) refers to a function parameter, otherwise -1.
static int paramIndexOf(const Expr *E) {
  E = E->IgnoreParenCasts();  // see through implicit AND explicit casts (e.g. "(u32)idx")
  if (!E)
    return -1;
  if (auto *D = dyn_cast<DeclRefExpr>(E)) {
    if (auto *P = dyn_cast<ParmVarDecl>(D->getDecl()))
      return (int)P->getFunctionScopeIndex();
    return -1;
  }
  if (auto *M = dyn_cast<MemberExpr>(E))
    return paramIndexOf(M->getBase());
  if (auto *A = dyn_cast<ArraySubscriptExpr>(E))
    return paramIndexOf(A->getBase());
  return -1;
}

// Variable name of E when it is a direct reference to a VarDecl, else "".
static std::string varNameOf(const Expr *E) {
  if (!E)
    return "";
  E = E->IgnoreParenImpCasts();
  if (auto *D = dyn_cast<DeclRefExpr>(E))
    if (auto *V = dyn_cast<VarDecl>(D->getDecl()))
      return V->getName().str();
  return "";
}

// For well-known memory/string routines, return the argument index that is the
// length/size (the "dangerous" position), else -1.
static int memLenArgIndex(llvm::StringRef name) {
  if (name == "memcpy" || name == "memmove" || name == "memset" ||
      name == "memcmp" || name == "strncpy" || name == "strncmp" ||
      name == "strncasecmp" || name == "strlcpy" || name == "strlcat" ||
      name == "strscpy" || name == "memchr" || name == "copy_from_user" ||
      name == "copy_to_user" || name == "strncpy_from_user" ||
      name == "strnlen_user")
    return 2;
  if (name == "strnlen" || name == "strnlen_user")
    return 1;
  return -1;
}

// ---------------------------------------------------------------------------
// AST visitor
// ---------------------------------------------------------------------------

class ArchVisitor : public RecursiveASTVisitor<ArchVisitor> {
public:
  explicit ArchVisitor(TUState &S) : S(S) {}

  bool TraverseFunctionDecl(FunctionDecl *FD) {
    // Skip forward declarations: only process the actual definition. This avoids
    // double-traversing a function body (declaration in header + definition in
    // .c), which otherwise contaminates CurAccesses across function boundaries.
    if (!FD->isThisDeclarationADefinition())
      return true;
    FunctionDecl *Prev = CurFn;
    CurFn = FD;
    CurAccesses.clear();
    CurWrites.clear();
    CurSoft.clear();
    CurChecked.clear();
    CurDangerous.clear();
    CurWriteLocs.clear();
    CurDangerUses.clear();
    CurRetConsts.clear();
    CurRetNonConst = false;
    CondDepth = 0;
    bool r = RecursiveASTVisitor::TraverseFunctionDecl(FD);
    S.defs.push_back(buildDef(FD));
    CurFn = Prev;
    return r;
  }

  // Mark accesses inside conditional guards as "soft" (the common layer
  // tolerates their absence). Each override bumps CondDepth while traversing.
  // IfStmt/SwitchStmt additionally push a runtime-dispatch context so sibling
  // calls in the same if/else or switch can be grouped as one semantic slot.
  bool TraverseIfStmt(IfStmt *S) {
    CondDepth++;
    arb::DispatchCtx c;
    c.kind = "runtime-if";
    c.condLoc = locString(SM(), S->getIfLoc());
    c.cond = "if";
    RtStack.push_back(std::move(c));
    bool r = RecursiveASTVisitor::TraverseIfStmt(S);
    RtStack.pop_back();
    CondDepth--;
    return r;
  }
  bool TraverseWhileStmt(WhileStmt *S) {
    CondDepth++;
    bool r = RecursiveASTVisitor::TraverseWhileStmt(S);
    CondDepth--;
    return r;
  }
  bool TraverseDoStmt(DoStmt *S) {
    CondDepth++;
    bool r = RecursiveASTVisitor::TraverseDoStmt(S);
    CondDepth--;
    return r;
  }
  bool TraverseForStmt(ForStmt *S) {
    CondDepth++;
    bool r = RecursiveASTVisitor::TraverseForStmt(S);
    CondDepth--;
    return r;
  }
  bool TraverseSwitchStmt(SwitchStmt *S) {
    CondDepth++;
    arb::DispatchCtx c;
    c.kind = "switch";
    c.condLoc = locString(SM(), S->getSwitchLoc());
    c.cond = "switch";
    RtStack.push_back(std::move(c));
    bool r = RecursiveASTVisitor::TraverseSwitchStmt(S);
    RtStack.pop_back();
    CondDepth--;
    return r;
  }
  bool TraverseConditionalOperator(ConditionalOperator *CO) {
    CondDepth++;
    bool r = RecursiveASTVisitor::TraverseConditionalOperator(CO);
    CondDepth--;
    return r;
  }
  bool TraverseBinaryOperator(BinaryOperator *BO) {
    bool isCond = BO->getOpcode() == BO_LAnd || BO->getOpcode() == BO_LOr;
    if (isCond)
      CondDepth++;
    bool r = RecursiveASTVisitor::TraverseBinaryOperator(BO);
    if (isCond)
      CondDepth--;
    return r;
  }

  bool VisitCallExpr(CallExpr *CE) {
    if (!CurFn)
      return true;
    FunctionDecl *Callee = CE->getDirectCallee();
    if (!Callee)
      return true;
    if (Callee->getBuiltinID() != 0)
      return true;
    if (!Callee->getIdentifier())
      return true;
    if (Callee->getName().startswith("__compiletime_assert"))
      return true;
    // dangerous: memcpy-family length/size argument coming straight from a param
    int lenIdx = memLenArgIndex(Callee->getName());
    if (lenIdx >= 0 && (int)CE->getNumArgs() > lenIdx) {
      int pidx = paramIndexOf(CE->getArg(lenIdx));
      if (pidx >= 0) {
        CurDangerous.insert("param#" + std::to_string(pidx) + ":len");
        recordDangerUse("param#" + std::to_string(pidx), "len",
                        Callee->getName().str(), CE->getBeginLoc());
      }
    }
    // write: destination (arg 0) of a memory-write function
    if (isMemWrite(Callee->getName()) && CE->getNumArgs() > 0) {
      std::string k = resourceKey(CE->getArg(0), SM());
      if (!k.empty())
        CurWrites.insert(k);
      recordWriteLoc(CE->getArg(0), "memwrite", CE->getBeginLoc());
    }
    arb::CallFact c;
    c.callerUsr = usrOf(CurFn);
    c.callerName = CurFn->getNameAsString();
    c.callerFile = relFile(SM(), CurFn->getLocation());
    c.callerLine = SM().getSpellingLineNumber(CurFn->getLocation());
    c.calleeUsr = usrOf(Callee);
    c.calleeName = Callee->getNameAsString();
    // 宏展开里的调用点：把位置解析到真实展开处，避免 "<invalid buffer>" 噪声。
    SourceLocation CELoc = SM().getFileLoc(CE->getBeginLoc());
    c.file = relFile(SM(), CELoc);
    if (c.file.empty())
      c.file = c.callerFile;
    c.line = SM().getSpellingLineNumber(CELoc);
    c.ctx = dispatchCtxFor(CE->getBeginLoc());
    c.usesRet = callResultUsed(CE, *S.Ctx);
    for (unsigned i = 0; i < CE->getNumArgs(); i++)
      // 剥掉隐式转换，记录公共侧真实传入的源类型（否则 u64->unsigned long 的
      // 隐式转换会把源 u64 抹掉，宽度截断就检测不到了）。
      c.args.push_back(classify(CE->getArg(i)->IgnoreParenImpCasts()->getType(), *S.Ctx));
    for (unsigned i = 0; i < CE->getNumArgs(); i++) // [ext] constant argument values
      c.argConsts.push_back(intConst(CE->getArg(i)));
    for (unsigned i = 0; i < Callee->getNumParams(); i++)
      c.params.push_back(classify(Callee->getParamDecl(i)->getOriginalType(), *S.Ctx));
    S.calls.push_back(std::move(c));
    return true;
  }

  bool VisitBinaryOperator(BinaryOperator *BO) {
    if (!CurFn)
      return true;
    if (BO->isAssignmentOp()) {
      recordWrite(BO->getLHS());
      bool isBitOp = BO->getOpcode() == BO_AndAssign || BO->getOpcode() == BO_OrAssign ||
                     BO->getOpcode() == BO_XorAssign || BO->getOpcode() == BO_ShlAssign ||
                     BO->getOpcode() == BO_ShrAssign;
      recordWriteLoc(BO->getLHS(), isBitOp ? "bitop" : "assign", BO->getOperatorLoc());
      if (BO->getOpcode() == BO_Assign) {
        recordFlow("assign", BO->getLHS()->getType(), BO->getRHS(), BO->getOperatorLoc(),
                   varNameOf(BO->getLHS()));
        recordGlobalFlow(BO->getLHS(), BO->getRHS(), BO->getOperatorLoc());
      }
      return true;
    }
    // dangerous: shift amount
    if (BO->getOpcode() == BO_Shl || BO->getOpcode() == BO_Shr) {
      int pidx = paramIndexOf(BO->getRHS());
      if (pidx >= 0) {
        CurDangerous.insert("param#" + std::to_string(pidx) + ":shift");
        recordDangerUse("param#" + std::to_string(pidx), "shift", "",
                        BO->getOperatorLoc());
      }
      return true;
    }
    // checked: comparison involving a param (a bounds/validity check)
    if (BO->isComparisonOp()) {
      int li = paramIndexOf(BO->getLHS());
      int ri = paramIndexOf(BO->getRHS());
      if (li >= 0)
        CurChecked.insert("param#" + std::to_string(li));
      if (ri >= 0)
        CurChecked.insert("param#" + std::to_string(ri));
    }
    return true;
  }

  bool VisitUnaryOperator(UnaryOperator *UO) {
    if (!CurFn)
      return true;
    if (UO->isIncrementDecrementOp()) {
      recordWrite(UO->getSubExpr());
      recordWriteLoc(UO->getSubExpr(), "assign", UO->getOperatorLoc());
      return true;
    }
    // dangerous + access: pointer dereference
    if (UO->getOpcode() == UO_Deref) {
      int pidx = paramIndexOf(UO->getSubExpr());
      if (pidx >= 0) {
        CurDangerous.insert("param#" + std::to_string(pidx) + ":deref");
        recordDangerUse("param#" + std::to_string(pidx), "deref", "",
                        UO->getOperatorLoc());
      }
      recordAccess(UO);
    }
    return true;
  }

  bool VisitArraySubscriptExpr(ArraySubscriptExpr *AE) {
    if (!CurFn)
      return true;
    // dangerous: array index coming from a param
    int pidx = paramIndexOf(AE->getIdx());
    if (pidx >= 0) {
      CurDangerous.insert("param#" + std::to_string(pidx) + ":index");
      recordDangerUse("param#" + std::to_string(pidx), "index", "",
                      AE->getExprLoc());
    }
    recordAccess(AE);
    return true;
  }

  bool VisitMemberExpr(MemberExpr *ME) {
    if (CurFn)
      recordAccess(ME);
    return true;
  }

  bool VisitDeclRefExpr(DeclRefExpr *DRE) {
    if (CurFn)
      recordAccess(DRE);
    return true;
  }

  bool VisitVarDecl(VarDecl *VD) {
    if (CurFn && VD->hasInit())
      recordFlow("init", VD->getType(), VD->getInit(), VD->getLocation(),
                 VD->getName().str());
    // global variable initialization (may be at file scope, CurFn == null)
    if (VD->hasInit() && VD->hasGlobalStorage())
      recordGlobalFlow(VD, VD->getInit(), VD->getLocation());
    // record global definitions (for cross-TU arch-private resolution)
    if (VD->hasGlobalStorage() && VD->isThisDeclarationADefinition()) {
      arb::GlobalDef g;
      g.name = VD->getName().str();
      g.file = relFile(SM(), VD->getLocation());
      if (!g.file.empty())
        S.globals.push_back(std::move(g));
    }
    return true;
  }

  bool VisitReturnStmt(ReturnStmt *RS) {
    if (CurFn && RS->getRetValue())
      recordFlow("return", CurFn->getReturnType(), RS->getRetValue(), RS->getBeginLoc(), "");
    if (CurFn && RS->getRetValue()) { // [ext] constant return values
      std::string v = intConst(RS->getRetValue());
      if (v.empty()) CurRetNonConst = true; else CurRetConsts.insert(v);
    }
    return true;
  }

private:
  SourceManager &SM() { return S.Ctx->getSourceManager(); }
  const LangOptions &LO() { return S.Ctx->getLangOpts(); }

  // Resolve the innermost dispatch context for a call site: the enclosing
  // preprocessor branch (preferred, it is the compile-time arch selector), else
  // the enclosing runtime if/switch.
  arb::DispatchCtx dispatchCtxFor(SourceLocation Loc) {
    arb::DispatchCtx ctx;
    clang::FileID fid = SM().getFileID(Loc);
    unsigned off = SM().getFileOffset(Loc);
    unsigned bestStart = 0;
    bool found = false;
    for (const auto &b : S.ppBranches) {
      if (b.fid != fid)
        continue;
      if (off >= b.startOff && off < b.endOff) {
        if (!found || b.startOff >= bestStart) {
          found = true;
          bestStart = b.startOff;
          ctx.kind = "pp-if";
          ctx.condLoc = b.anchorLoc;
          ctx.cond = b.cond;
        }
      }
    }
    if (found)
      return ctx;
    if (!RtStack.empty())
      return RtStack.back();
    return ctx;
  }

  void recordGlobalFlow(VarDecl *VD, Expr *RHS, SourceLocation Loc) {
    if (!VD || !VD->hasGlobalStorage())
      return;
    emitGlobalFlow(VD->getName().str(), VD->getType(), RHS, Loc);
  }

  void recordGlobalFlow(Expr *LHS, Expr *RHS, SourceLocation Loc) {
    LHS = LHS->IgnoreParenImpCasts();
    const VarDecl *VD = nullptr;
    if (auto *D = dyn_cast<DeclRefExpr>(LHS))
      VD = dyn_cast<VarDecl>(D->getDecl());
    if (!VD || !VD->hasGlobalStorage())
      return;
    emitGlobalFlow(VD->getName().str(), LHS->getType(), RHS, Loc);
  }

  void emitGlobalFlow(const std::string &name, QualType lhsTy, Expr *RHS,
                      SourceLocation Loc) {
    Expr *R = RHS->IgnoreParenImpCasts();
    arb::GlobalFlow g;
    g.global = name;
    g.file = relFile(SM(), Loc);
    g.line = SM().getSpellingLineNumber(Loc);
    g.lhs = classify(lhsTy, *S.Ctx);
    g.rhs = classify(R->getType(), *S.Ctx);
    if (auto *D = dyn_cast<DeclRefExpr>(R))
      if (auto *V = dyn_cast<VarDecl>(D->getDecl()))
        g.srcVar = V->getName().str();
    S.globalFlows.push_back(std::move(g));
  }

  // Record a resource as ACCESSED (read or write) — naming-independent key.
  void recordAccess(const Expr *E) {
    std::string k = resourceKey(E, SM());
    if (!k.empty()) {
      CurAccesses.insert(k);
      if (CondDepth > 0)
        CurSoft.insert(k);
      attributeMacro(E);
    }
  }

  // Record a resource as WRITTEN.
  void recordWrite(Expr *E) {
    std::string k = resourceKey(E, SM());
    if (!k.empty()) {
      CurWrites.insert(k);
      CurAccesses.insert(k); // a write is also an access
      if (CondDepth > 0)
        CurSoft.insert(k);
      attributeMacro(E);
    }
  }

  // Record the LOCATION of a write (assignment / bit op / memory-write fn),
  // for the call-context "write asymmetry" target point.
  void recordWriteLoc(Expr *E, const std::string &kind, SourceLocation Loc) {
    std::string k = resourceKey(E, SM());
    if (k.empty())
      return;
    SourceLocation FL = SM().getFileLoc(Loc);
    arb::WriteLoc w;
    w.resource = k;
    w.file = relFile(SM(), FL);
    w.line = SM().getSpellingLineNumber(FL);
    w.kind = kind;
    CurWriteLocs.push_back(std::move(w));
  }

  // Record the LOCATION of a dangerous parameter use, for the call-context
  // "param-check asymmetry" target point.
  void recordDangerUse(const std::string &param, const std::string &kind,
                       const std::string &callee, SourceLocation Loc) {
    SourceLocation FL = SM().getFileLoc(Loc);
    arb::DangerUse u;
    u.param = param;
    u.kind = kind;
    u.callee = callee;
    u.file = relFile(SM(), FL);
    u.line = SM().getSpellingLineNumber(FL);
    CurDangerUses.push_back(std::move(u));
  }

  // Attribute a resource access to the macro whose expansion produced it.
  // Uses the RAW key (no arch-private filter) so arch-exclusive resources
  // (cpu_data, ...) are captured as the capability signal.
  void attributeMacro(const Expr *E) {
    SourceLocation Loc = E->getBeginLoc();
    if (!Loc.isMacroID())
      return; // getImmediateMacroName asserts on non-macro locations (clang-15)
    llvm::StringRef mac = Lexer::getImmediateMacroName(Loc, SM(), LO());
    if (mac.empty() || !isValidMacroName(mac))
      return;
    std::string r = rawResourceKey(E);
    if (r.empty())
      return;
    arb::MacroRes mr;
    mr.macro = mac.str();
    mr.resource = r;
    S.macroRes.push_back(std::move(mr));
  }

  static bool isValidMacroName(llvm::StringRef s) {
    if (s.empty() || !(isalpha((unsigned char)s[0]) || s[0] == '_'))
      return false;
    for (char c : s)
      if (!(isalnum((unsigned char)c) || c == '_'))
        return false;
    return true;
  }

  // Record a value-flow edge only when it is a fixed-width <-> arch-width (or
  // width/sign) mismatch, to keep the facts small and precise. The source type
  // is taken AFTER stripping implicit casts, so that a silent narrowing
  // (e.g. "unsigned long x = u64_val;") is captured with its real source width.
  void recordFlow(llvm::StringRef kind, QualType Dest, Expr *Src, SourceLocation Loc,
                  const std::string &lhsName) {
    QualType SrcTy = Src->IgnoreParenImpCasts()->getType();
    QualType CL = Dest.getCanonicalType(), CR = SrcTy.getCanonicalType();
    bool bothInt = (CL->isIntegerType() || CL->isEnumeralType()) &&
                   (CR->isIntegerType() || CR->isEnumeralType());
    if (!bothInt)
      return;
    arb::TypeInfo lhs = classify(Dest, *S.Ctx);
    arb::TypeInfo rhs = classify(SrcTy, *S.Ctx);
    bool interesting = (lhs.fixed && rhs.archwidth) || (lhs.archwidth && rhs.fixed);
    if (lhs.sizeBits >= 0 && rhs.sizeBits >= 0 && lhs.sizeBits != rhs.sizeBits)
      interesting = true;
    if (lhs.isInt && rhs.isInt && lhs.isSigned != rhs.isSigned)
      interesting = true;
    if (!interesting)
      return;
    arb::FlowFact f;
    f.kind = kind.str();
    f.func = CurFn->getNameAsString();
    f.file = relFile(SM(), Loc);
    if (f.file.empty())
      f.file = relFile(SM(), CurFn->getLocation());
    f.line = SM().getSpellingLineNumber(Loc);
    f.lhs = std::move(lhs);
    f.rhs = std::move(rhs);
    f.lhsName = lhsName;
    f.rhsName = varNameOf(Src);
    S.flows.push_back(std::move(f));
  }

  arb::DefFact buildDef(FunctionDecl *FD) {
    arb::DefFact d;
    d.usr = usrOf(FD);
    d.name = FD->getNameAsString();
    d.file = relFile(SM(), FD->getLocation());
    d.line = SM().getSpellingLineNumber(FD->getLocation());
    d.isStatic = FD->getFormalLinkage() == clang::Linkage::Internal;
    d.isDef = true;
    d.ret = classify(FD->getReturnType(), *S.Ctx);
    for (auto *P : FD->parameters())
      d.params.push_back(classify(P->getOriginalType(), *S.Ctx));
    classifyBody(FD->getBody(), d.bodyKind, d.constVal);
    d.accesses.assign(CurAccesses.begin(), CurAccesses.end());
    d.writes.assign(CurWrites.begin(), CurWrites.end());
    d.soft.assign(CurSoft.begin(), CurSoft.end());
    d.checked.assign(CurChecked.begin(), CurChecked.end());
    d.dangerous.assign(CurDangerous.begin(), CurDangerous.end());
    d.writeLocs = CurWriteLocs;
    d.dangerUses = CurDangerUses;
    d.retConsts.assign(CurRetConsts.begin(), CurRetConsts.end());
    d.retNonConst = CurRetNonConst;
    return d;
  }

  TUState &S;
  FunctionDecl *CurFn = nullptr;
  std::set<std::string> CurAccesses;
  std::set<std::string> CurWrites;
  std::set<std::string> CurSoft;   // conditional-guarded accesses (soft contract)
  std::set<std::string> CurChecked;
  std::set<std::string> CurDangerous;
  std::vector<arb::WriteLoc> CurWriteLocs;
  std::vector<arb::DangerUse> CurDangerUses;
  std::set<std::string> CurRetConsts; // [ext]
  bool CurRetNonConst = false;        // [ext]
  // [ext] integer constant value of E, or "" when E is not an integer constant expression
  std::string intConst(Expr *E) {
    if (!E || E->isValueDependent() || E->isTypeDependent())
      return "";
    Expr::EvalResult R;
    if (!E->EvaluateAsInt(R, *S.Ctx))
      return "";
    llvm::SmallString<32> Buf;
    R.Val.getInt().toString(Buf, 10);
    return Buf.str().str();
  }
  int CondDepth = 0;               // >0 inside if/while/for/do/switch/?:/&&/||
  std::vector<arb::DispatchCtx> RtStack; // runtime if/switch dispatch stack
};

// ---------------------------------------------------------------------------
// Preprocessor callbacks: __HAVE_ARCH_* capability + arch-conditional #if
// ---------------------------------------------------------------------------

class ArchPPCallbacks : public PPCallbacks {
public:
  ArchPPCallbacks(TUState &S, SourceManager &SM, const LangOptions &LO)
      : S(S), SM(SM), LO(LO) {}

  void If(SourceLocation Loc, SourceRange Cond, PPCallbacks::ConditionValueKind) override {
    pushFrame(Loc, condText(Cond, ""));
    record("if", Loc, Cond, "");
  }
  void Elif(SourceLocation Loc, SourceRange Cond, PPCallbacks::ConditionValueKind,
            SourceLocation) override {
    closeFrame(Loc);
    if (!Stack.empty()) {
      Stack.back().cond = condText(Cond, "");
      Stack.back().bodyStart = SM.getFileOffset(Loc);
    }
    record("elif", Loc, Cond, "");
  }
  void Ifdef(SourceLocation Loc, const Token &MacroNameTok, const MacroDefinition &) override {
    pushFrame(Loc, MacroNameTok.getIdentifierInfo()->getName().str());
    record("ifdef", Loc, SourceRange(), MacroNameTok.getIdentifierInfo()->getName().str());
  }
  void Ifndef(SourceLocation Loc, const Token &MacroNameTok, const MacroDefinition &) override {
    pushFrame(Loc, MacroNameTok.getIdentifierInfo()->getName().str());
    record("ifndef", Loc, SourceRange(), MacroNameTok.getIdentifierInfo()->getName().str());
  }
  void Else(SourceLocation Loc, SourceLocation) override {
    closeFrame(Loc);
    if (!Stack.empty()) {
      Stack.back().cond = "else";
      Stack.back().bodyStart = SM.getFileOffset(Loc);
    }
  }
  void Endif(SourceLocation Loc, SourceLocation) override {
    closeFrame(Loc);
    Stack.pop_back();
  }
  void MacroDefined(const Token &MacroNameTok, const MacroDirective *) override {
    llvm::StringRef n = MacroNameTok.getIdentifierInfo()->getName();
    if (n.startswith("__HAVE_ARCH")) {
      arb::PPFact p;
      p.file = relFile(SM, MacroNameTok.getLocation());
      p.line = SM.getSpellingLineNumber(MacroNameTok.getLocation());
      p.kind = "define";
      p.cond = n.str();
      S.pps.push_back(std::move(p));
    }
    // capability: record macros #define'd in arch/ headers
    std::string f = relFile(SM, MacroNameTok.getLocation());
    if (!f.empty() && f.rfind("arch/", 0) == 0) {
      ArchDefinedMacros.insert(n.str());
      arb::MacroFact m;
      m.name = n.str();
      m.file = f;
      m.kind = "arch-def";
      S.macros.push_back(std::move(m));
    }
  }

  void MacroExpands(const Token &MacroNameTok, const MacroDefinition &, SourceRange Range,
                    const MacroArgs *) override {
    llvm::StringRef n = MacroNameTok.getIdentifierInfo()->getName();
    if (!ArchDefinedMacros.count(n.str()))
      return; // not an arch-defined macro: skip (cheap, no file lookup)
    std::string f = relFile(SM, Range.getBegin());
    if (f.empty() || f.rfind("arch/", 0) == 0)
      return; // used in arch code, not common
    arb::MacroFact m;
    m.name = n.str();
    m.file = f;
    m.kind = "common-use";
    S.macros.push_back(std::move(m));
  }

private:
  struct PPFrame {
    clang::FileID fid;
    std::string anchorLoc; // "file:line" of the original #if/#ifdef/#ifndef
    std::string cond;
    unsigned bodyStart;    // file offset where this branch's body begins
  };

  std::string condText(SourceRange Cond, const std::string &macroName) {
    if (!macroName.empty())
      return macroName;
    if (Cond.isInvalid())
      return "";
    CharSourceRange R = CharSourceRange::getTokenRange(Cond);
    return Lexer::getSourceText(R, SM, LO).str();
  }

  void pushFrame(SourceLocation Loc, const std::string &cond) {
    PPFrame f;
    f.fid = SM.getFileID(Loc);
    f.anchorLoc = locString(SM, Loc);
    f.cond = cond;
    f.bodyStart = SM.getFileOffset(Loc);
    Stack.push_back(std::move(f));
  }

  // Close the current branch (its body spans [bodyStart, Loc)) and emit a range.
  void closeFrame(SourceLocation Loc) {
    if (Stack.empty())
      return;
    PPBranch b;
    b.fid = Stack.back().fid;
    b.startOff = Stack.back().bodyStart;
    b.endOff = SM.getFileOffset(Loc);
    b.anchorLoc = Stack.back().anchorLoc;
    b.cond = Stack.back().cond;
    S.ppBranches.push_back(std::move(b));
  }

  void record(llvm::StringRef kind, SourceLocation Loc, SourceRange Cond,
              const std::string &macroName) {
    std::string cond = macroName;
    if (!Cond.isInvalid()) {
      CharSourceRange R = CharSourceRange::getTokenRange(Cond);
      cond = Lexer::getSourceText(R, SM, LO).str();
    }
    if (cond.empty())
      return;
    bool interesting = false;
    if (kind == "ifdef" || kind == "ifndef")
      interesting = llvm::StringRef(cond).startswith("__HAVE_ARCH");
    else
      interesting = arb::hasArchToken(cond);
    if (!interesting)
      return;
    arb::PPFact p;
    p.file = relFile(SM, Loc);
    p.line = SM.getSpellingLineNumber(Loc);
    p.kind = kind.str();
    p.cond = cond;
    S.pps.push_back(std::move(p));
  }

  TUState &S;
  SourceManager &SM;
  const LangOptions &LO;
  std::set<std::string> ArchDefinedMacros; // macros seen defined in arch/ headers
  std::vector<PPFrame> Stack;             // open #if/#ifdef chain
};

// ---------------------------------------------------------------------------
// Frontend action + consumer
// ---------------------------------------------------------------------------

class CollectConsumer : public ASTConsumer {
public:
  CollectConsumer(std::unique_ptr<TUState> S) : State(std::move(S)) {}
  void HandleTranslationUnit(ASTContext &Ctx) override {
    State->Ctx = &Ctx;
    ArchVisitor V(*State);
    V.TraverseDecl(Ctx.getTranslationUnitDecl());
    GShared.merge(*State);
  }

private:
  std::unique_ptr<TUState> State;
};

class CollectAction : public ASTFrontendAction {
public:
  std::unique_ptr<ASTConsumer> CreateASTConsumer(CompilerInstance &CI,
                                                 StringRef) override {
    auto S = std::make_unique<TUState>();
    S->root = GShared.root;
    CI.getPreprocessor().addPPCallbacks(
        std::make_unique<ArchPPCallbacks>(*S, CI.getSourceManager(), CI.getLangOpts()));
    return std::make_unique<CollectConsumer>(std::move(S));
  }
};

static std::string inferArch(CompilationDatabase &DB) {
  for (auto &c : DB.getAllCompileCommands()) {
    for (auto &a : c.CommandLine) {
      if (a.rfind("--target=", 0) != 0)
        continue;
      std::string t = a.substr(9);
      if (t.find("aarch64") != std::string::npos) return "arm64";
      if (t.find("x86_64") != std::string::npos) return "x86";
      if (t.find("riscv") != std::string::npos)  return "riscv";
      if (t.find("powerpc") != std::string::npos) return "powerpc";
      if (t.find("s390") != std::string::npos)  return "s390";
      if (t.find("mips") != std::string::npos)  return "mips";
      if (t.find("loongarch") != std::string::npos) return "loongarch";
      if (t.find("i386") != std::string::npos || t.find("i486") != std::string::npos ||
          t.find("i586") != std::string::npos || t.find("i686") != std::string::npos)
        return "x86";
    }
  }
  return "unknown";
}

} // namespace

namespace arb {
int collectMain(int argc, const char **argv);
} // namespace arb

int arb::collectMain(int argc, const char **argv) {
  llvm::cl::HideUnrelatedOptions(ArchBoundCat);
  llvm::cl::ParseCommandLineOptions(argc, argv, "archbound collect");

  std::string Err;
  std::unique_ptr<CompilationDatabase> DB;
  if (!OptBuildPath.empty()) {
    if (llvm::sys::fs::is_directory(OptBuildPath.getValue()))
      DB = CompilationDatabase::autoDetectFromDirectory(OptBuildPath.getValue(), Err);
    else
      DB = JSONCompilationDatabase::loadFromFile(
          OptBuildPath.getValue(), Err, JSONCommandLineSyntax::AutoDetect);
  }
  if (!DB) {
    if (Err.empty())
      Err = "no compilation database (pass -p <build-dir-or-json>)";
    llvm::errs() << "cannot load compilation database: " << Err << "\n";
    return 1;
  }

  // Normalise root.
  llvm::SmallString<256> R(OptRoot.getValue());
  if (!R.empty()) {
    llvm::sys::fs::make_absolute(R);
    llvm::SmallString<256> Real;
    if (!llvm::sys::fs::real_path(R, Real, true))
      R = Real;
  }
  GShared.root = R.str().str();

  std::string arch = OptArch.getValue();
  if (arch.empty())
    arch = inferArch(*DB);

  std::vector<std::string> SourcePaths(OptSources.begin(), OptSources.end());
  if (SourcePaths.empty())
    for (const auto &Cmd : DB->getAllCompileCommands())
      SourcePaths.push_back(Cmd.Filename);

  if (OptJobs == 0) {
    for (const auto &Path : SourcePaths) { // [ext] one tool per file to record its status
      ClangTool T(*DB, {Path});
      int rc = T.run(newFrontendActionFactory<CollectAction>().get());
      std::lock_guard<std::mutex> L(GShared.M);
      GShared.units.push_back({Path, rc});
    }
  } else {
    // Parallel execution: GShared.merge() is mutex-protected; each TU runs its
    // own CollectAction + TUState, so the only shared mutable state is GShared.
    llvm::ThreadPool Pool(llvm::hardware_concurrency(OptJobs));
    for (const auto &Src : SourcePaths) {
      Pool.async(
          [&](const std::string &Path) {
            IntrusiveRefCntPtr<llvm::vfs::FileSystem> FS =
                llvm::vfs::createPhysicalFileSystem();
            ClangTool T(*DB, {Path}, std::make_shared<PCHContainerOperations>(), FS);
            int rc = T.run(newFrontendActionFactory<CollectAction>().get());
            std::lock_guard<std::mutex> L(GShared.M); // [ext]
            GShared.units.push_back({Path, rc});
          },
          Src);
    }
    // Pool dtor joins all threads.
  }

  arb::Facts F;
  F.arch = arch;
  F.root = GShared.root;
  F.defs = GShared.defs;
  F.calls = GShared.calls;
  F.pps = GShared.pps;
  F.flows = GShared.flows;
  F.globals = GShared.globals;
  F.macros = GShared.macros;
  F.macroRes = GShared.macroRes;
  F.globalFlows = GShared.globalFlows;
  F.units = GShared.units;

  std::error_code EC;
  llvm::raw_fd_ostream OS(OptOut.getValue(), EC, llvm::sys::fs::OF_Text);
  if (EC) {
    llvm::errs() << "cannot open output: " << EC.message() << "\n";
    return 1;
  }
  OS << arb::toJSON(F);
  OS.close();

  llvm::errs() << "[collect] arch=" << arch << " defs=" << F.defs.size()
               << " calls=" << F.calls.size() << " pps=" << F.pps.size()
               << " flows=" << F.flows.size()
               << " globals=" << F.globals.size() << " macros=" << F.macros.size()
               << " globalFlows=" << F.globalFlows.size()
               << " -> " << OptOut.getValue() << "\n";
  return 0;
}
