#!/usr/bin/env bash
# Homer: fetch the 6502 acceptance programs (spec section 9 item 1) into build/dormann/. Nothing is committed.
# 6502_functional_test: Klaus Dormann, (c) 2012-2020, GNU GPL v3 or later (header of the listing). The prebuilt binary and its listing
#   come from the same repo; the listing shows it was built with decimal tests on (disable_decimal = 0), self-modifying code on,
#   64 KiB RAM, loaded directly at 0000h, start at 0400h; the success trap is 'jmp *' at 3469h (listing line 13377).
# 6502_decimal_test.a65: Bruce Clark's decimal mode test as published in the same repo, public domain (header). It is source only;
#   it has to be built (cputype = 0, vld_bcd = 0, chk_a/n/v/z/c = 1, as spec section 9 says), which is a separate step.
# Pinned by commit and sha256; a mismatch stops the run. From the repo root: ./sw/dormann/fetch.sh
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
REPO=Klaus2m5/6502_65C02_functional_tests
COMMIT=7954e2dbb49c469ea286070bf46cdd71aeb29e4b
OUT=build/dormann; mkdir -p "$OUT"
fetch() {   # path-in-repo sha256
  local f; f=$(basename "$1")
  curl -fsS --max-time 60 -o "$OUT/$f" "https://raw.githubusercontent.com/$REPO/$COMMIT/$1"
  echo "$2  $OUT/$f" | sha256sum -c --quiet - || { echo "sha256 mismatch for $f: refusing to use it" >&2; rm -f "$OUT/$f"; exit 1; }
}
fetch bin_files/6502_functional_test.bin fa12bfc761e6f9057e4cc01a665a7b800ff01ae91f598af1e39a1201d01953fd
fetch bin_files/6502_functional_test.lst a85bf71692a7087182f3a574830e74d420d166032f37d385e34940e7bb8d49e3
fetch 6502_decimal_test.a65 dfbe4b907c5821d47d9f7f74eeb51197cf4b9f5260375bc1c6c48c008220e1a0
grep -q 'GNU General Public License' "$OUT/6502_functional_test.lst" && grep -q 'Klaus Dormann' "$OUT/6502_functional_test.lst" \
  || { echo "functional test header is not what spec section 9 recorded: ask Sai" >&2; exit 1; }
grep -q 'public domain' "$OUT/6502_decimal_test.a65" || { echo "decimal test header is not public domain any more: ask Sai" >&2; exit 1; }
sed -n 13377p "$OUT/6502_functional_test.lst" | grep -q '^3469 : 4c6934' || { echo "success trap is not at 3469h in this listing" >&2; exit 1; }
echo "fetched the 6502 functional test (bin, listing) and the decimal test source from $REPO@${COMMIT:0:7}, hashes match"
