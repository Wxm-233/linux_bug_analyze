cd /root/repos/linux
for f in "$@"; do echo "################ $f"; git show --stat --format='%h %cs %s%n%n%b' $f | grep -v "^\(Signed-off-by\|Cc\|Reviewed-by\|Acked-by\|Tested-by\|Link\|Reported-by\|Suggested-by\|Co-developed-by\):" | head -45; git show --format= -U3 $f -- . ':!Documentation' | head -90; done
