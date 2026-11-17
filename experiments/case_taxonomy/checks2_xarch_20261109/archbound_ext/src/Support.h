#ifndef ARB_SUPPORT_H
#define ARB_SUPPORT_H

#include <string>
#include <set>
#include <vector>

namespace arb {

// ---------------------------------------------------------------------------
// File-path based layering: which part of the kernel does a file belong to?
// ---------------------------------------------------------------------------

// Returns the architecture directory name ("x86", "arm64", "riscv", ...) when
// the relative path lives under arch/<name>/, and "" otherwise.
inline std::string archOfFile(const std::string &rel) {
  const std::string prefix = "arch/";
  if (rel.compare(0, prefix.size(), prefix) != 0)
    return "";
  size_t p = rel.find('/', prefix.size());
  if (p == std::string::npos)
    return "";
  return rel.substr(prefix.size(), p - prefix.size());
}

inline bool isArchFile(const std::string &rel) { return !archOfFile(rel).empty(); }

// Common (architecture-independent) kernel layers per the paper.
inline bool isCommonFile(const std::string &rel) {
  static const std::vector<std::string> dirs = {
      "kernel/", "mm/",  "fs/",      "lib/",      "drivers/", "net/",
      "block/",  "crypto/", "security/", "init/", "ipc/",     "io_uring/",
      "sound/",  "virt/", "include/",  "samples/", "certs/"};
  for (const auto &d : dirs)
    if (rel.compare(0, d.size(), d) == 0)
      return true;
  return false;
}

// ---------------------------------------------------------------------------
// Type-spelling classification: fixed-width typedef vs architecture-width type.
// The classic cross-arch trap is u64 (always 64 bit) meeting unsigned long /
// size_t / uintptr_t (64 bit on x86_64 / arm64, 32 bit on i386 / arm).
// ---------------------------------------------------------------------------

inline bool isFixedWidthName(const std::string &s) {
  static const std::set<std::string> names = {
      "u8",        "u16",        "u32",        "u64",
      "s8",        "s16",        "s32",        "s64",
      "__u8",      "__u16",      "__u32",      "__u64",
      "__s8",      "__s16",      "__s32",      "__s64",
      "uint8_t",   "uint16_t",   "uint32_t",   "uint64_t",
      "int8_t",    "int16_t",    "int32_t",    "int64_t",
      "__le16",    "__le32",     "__le64",     "__be16",
      "__be32",    "__be64",     "__sum16",    "__wsum"};
  return names.count(s) != 0;
}

inline bool isArchWidthName(const std::string &s) {
  static const std::set<std::string> names = {
      "unsigned long",   "long",          "size_t",      "ssize_t",
      "uintptr_t",       "intptr_t",      "__kernel_ulong_t",
      "__kernel_long_t", "__kernel_size_t", "__kernel_ssize_t",
      "ulong",           "long unsigned int", "unsigned long int"};
  return names.count(s) != 0;
}

// Substrings that mark an #if / #elif condition as architecture-dependent.
inline bool hasArchToken(const std::string &cond) {
  static const std::vector<std::string> toks = {
      "X86", "ARM", "RISCV", "LOONGARCH", "POWERPC", "S390", "MIPS",
      "SPARC", "PARISC", "IA64", "CSKY", "XTENSA", "HEXAGON", "NIOS2",
      "OPENRISC", "MICROBLAZE", "M68K", "SUPERH"};
  for (const auto &t : toks)
    if (cond.find(t) != std::string::npos)
      return true;
  return false;
}

} // namespace arb

#endif
