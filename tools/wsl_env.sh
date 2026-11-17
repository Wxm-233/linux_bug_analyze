# 在 WSL 中运行本项目命令前 source 本文件：
#   wsl -u root -- bash /mnt/d/.../某脚本.sh   （脚本第一行写 source 本文件）
# 作用：
# 1. PATH 只保留 Linux 目录，并把不带 -18 后缀的 LLVM 工具（llvm-ar 等）放在最前。
#    WSL 默认把 Windows 的 PATH 接在后面，其中含空格和括号（如 "Program Files (x86)"），
#    展开时没加引号就会出现 bash 语法错误。
# 2. 给出常用目录变量。
export PATH=/usr/lib/llvm-18/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export REPO=/mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze   # 本项目仓库（Windows D: 盘）
export WORKSPACE=/mnt/d/homework/software/linux_bug_analyze                # 外层主文件夹
export KSRC=/root/repos/linux                                              # 内核源码，只读，不要改工作树
export KBUILD=/root/work/boundary_build                                    # 构建矩阵输出（O= 目录）
