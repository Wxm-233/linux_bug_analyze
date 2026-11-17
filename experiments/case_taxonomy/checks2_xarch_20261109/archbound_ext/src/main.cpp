#include "llvm/Support/CommandLine.h"
#include "llvm/Support/raw_ostream.h"
#include <string>

namespace arb {
int collectMain(int argc, const char **argv);
int analyzeMain(int argc, const char **argv);
} // namespace arb

static void usage() {
  llvm::errs() << "usage:\n"
               << "  archbound collect -p <compile_commands.json> --root <kernel> "
                  "[--arch x86] --out facts.x86.json\n"
               << "  archbound analyze --facts facts.x86.json,facts.arm64.json "
                  "[--report report.txt]\n";
}

int main(int argc, const char **argv) {
  if (argc < 2) {
    usage();
    return 1;
  }
  std::string cmd = argv[1];
  if (cmd == "collect")
    return arb::collectMain(argc - 1, argv + 1);
  if (cmd == "analyze")
    return arb::analyzeMain(argc - 1, argv + 1);
  usage();
  return 1;
}
