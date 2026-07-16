#!/usr/bin/env bash
# Golden tests for the Phase-1 edge-coverage fix in check-presentation.py.
# Each case asserts the script's EXIT CODE against a crafted SVG.
#   0 = equivalent (OK)   1 = diverges (FAIL)   2 = usage/error   3 = incomplete
set -u
cd "$(dirname "$0")"
CHECK=../references/check-presentation.py
D2=fx_edges.d2
pass=0; fail=0

run() {  # <expected-code> <svg> <description>
  local want="$1" svg="$2" desc="$3" got
  python3 "$CHECK" "$D2" "$svg" >/tmp/_chk.out 2>&1
  got=$?
  if [ "$got" = "$want" ]; then
    echo "  ok   [$desc] exit=$got"
    pass=$((pass+1))
  else
    echo "  FAIL [$desc] want exit=$want got=$got"
    sed 's/^/         | /' /tmp/_chk.out
    fail=$((fail+1))
  fi
}

echo "check-presentation.py edge-coverage golden tests"
run 0 fx_edges.good.svg          "all edges incl. container-internal/parallel/bidir"
run 0 fx_edges.bidir_reversed.svg "bidir tagged b<->a still matches a<->b (sorted key)"
run 1 fx_edges.drop_bidir.svg    "dropped bidirectional edge is CAUGHT (old bug)"
run 1 fx_edges.drop_parallel.svg "dropped one parallel edge is CAUGHT (multiset)"
run 1 fx_edges.invented.svg      "invented edge not in D2 is CAUGHT"

echo
echo "decoder unit tests (test_decode.py)"
if python3 test_decode.py; then
  pass=$((pass+1))
else
  echo "  FAIL decoder unit tests"
  fail=$((fail+1))
fi

echo "----"
echo "pass=$pass fail=$fail"
[ "$fail" = 0 ]
