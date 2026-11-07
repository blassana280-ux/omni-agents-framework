#!/usr/bin/env bash
# OMNI WARSHIPS T-013.9 — tests du verificateur strict. Fixtures 100%
# FACTICES (archive factice, aucun secret, aucune valeur reelle, rien
# n est imprime). Chaque mode d echec doit etre REFUSE par
# verify-gameci-cli.sh ; l archive correcte + empreinte ancree
# concordante doit etre ACCEPTEE. Attendu : 9 reussites.
set -u

here="$(cd "$(dirname "$0")" && pwd)"
verify="$here/verify-gameci-cli.sh"
asset="gameci-cli-secure-linux-x64.tar.gz"
pass=0
fail=0

ok() { pass=$((pass + 1)); }
ko() { echo "::error::T-013.9 test : $1"; fail=$((fail + 1)); }

expect_refuse() {
  label="$1"
  shift
  if "$@" >/dev/null 2>&1; then ko "$label — le verificateur aurait du REFUSER"; else ok; fi
}

make_tree() {
  # <dir> : arborescence factice d un artefact VALIDE (binaire + dist personal).
  d="$1"
  mkdir -p "$d/dist/platforms/ubuntu/steps"
  printf '#!/bin/sh\nexit 0\n' > "$d/game-ci"
  printf 'echo personal --include-personal\n' > "$d/dist/platforms/ubuntu/steps/activate.sh"
  printf 'trap return_license_once EXIT\n' > "$d/dist/platforms/ubuntu/steps/runsteps.sh"
  printf 'echo Returning personal license seat\n' > "$d/dist/platforms/ubuntu/steps/return_license.sh"
  printf '/steps/runsteps.sh\n' > "$d/dist/platforms/ubuntu/entrypoint.sh"
}

pack() {
  # <dir> : archive + checksums.txt CORRECTS depuis <dir>/tree.
  d="$1"
  tar -czf "$d/$asset" -C "$d/tree" .
  ( cd "$d" && sha256sum "$asset" > checksums.txt )
}

root="$(mktemp -d)"

# 1) archive correcte + empreinte ancree concordante : ACCEPTEE.
f1="$root/ok"
mkdir -p "$f1/tree"
make_tree "$f1/tree"
pack "$f1"
cp "$f1/checksums.txt" "$f1/anchored.txt"
if bash "$verify" "$f1" "$asset" "$root/dest-ok" "$f1/anchored.txt" >/dev/null 2>&1; then
  ok
else
  ko "archive correcte + empreinte ancree — le verificateur aurait du ACCEPTER"
fi

# 2) checksums.txt inaccessible : REFUSE.
f2="$root/no-checksums"
mkdir -p "$f2/tree"
make_tree "$f2/tree"
pack "$f2"
rm "$f2/checksums.txt"
expect_refuse "checksums.txt inaccessible" bash "$verify" "$f2" "$asset" "$root/dest-2"

# 3) empreinte absente de checksums.txt : REFUSE.
f3="$root/no-fingerprint"
mkdir -p "$f3/tree"
make_tree "$f3/tree"
pack "$f3"
printf '0000000000000000000000000000000000000000000000000000000000000000  autre-chose.tar.gz\n' > "$f3/checksums.txt"
expect_refuse "empreinte absente de checksums.txt" bash "$verify" "$f3" "$asset" "$root/dest-3"

# 4) checksum incorrect : REFUSE.
f4="$root/bad-sum"
mkdir -p "$f4/tree"
make_tree "$f4/tree"
pack "$f4"
printf 'deadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef  %s\n' "$asset" > "$f4/checksums.txt"
expect_refuse "checksum incorrect" bash "$verify" "$f4" "$asset" "$root/dest-4"

# 5) empreinte absente du fichier ancree dans git : REFUSE.
f5="$root/no-anchored"
mkdir -p "$f5/tree"
make_tree "$f5/tree"
pack "$f5"
printf 'irrelevant\n' > "$f5/anchored.txt"
expect_refuse "empreinte absente du fichier ancree" bash "$verify" "$f5" "$asset" "$root/dest-5" "$f5/anchored.txt"

# 6) divergence checksums.txt / empreinte ancree : REFUSE.
f6="$root/diverge"
mkdir -p "$f6/tree"
make_tree "$f6/tree"
pack "$f6"
printf '1111111111111111111111111111111111111111111111111111111111111111  %s\n' "$asset" > "$f6/anchored.txt"
expect_refuse "divergence checksums.txt / empreinte ancree" bash "$verify" "$f6" "$asset" "$root/dest-6" "$f6/anchored.txt"

# 7) binaire absent de l archive verifiee : REFUSE.
f7="$root/no-binary"
mkdir -p "$f7/tree/dist/platforms/ubuntu/steps"
printf 'echo personal --include-personal\n' > "$f7/tree/dist/platforms/ubuntu/steps/activate.sh"
printf 'trap return_license_once EXIT\n' > "$f7/tree/dist/platforms/ubuntu/steps/runsteps.sh"
printf 'echo Returning personal license seat\n' > "$f7/tree/dist/platforms/ubuntu/steps/return_license.sh"
printf '/steps/runsteps.sh\n' > "$f7/tree/dist/platforms/ubuntu/entrypoint.sh"
pack "$f7"
expect_refuse "binaire absent de l archive" bash "$verify" "$f7" "$asset" "$root/dest-7"

# 8) scripts personal absents de l artefact : REFUSE.
f8="$root/no-personal"
mkdir -p "$f8/tree/dist/platforms/ubuntu/steps"
printf '#!/bin/sh\nexit 0\n' > "$f8/tree/game-ci"
printf 'echo sans chemin personal\n' > "$f8/tree/dist/platforms/ubuntu/steps/activate.sh"
printf 'trap return_license_once EXIT\n' > "$f8/tree/dist/platforms/ubuntu/steps/runsteps.sh"
printf 'echo Returning personal license seat\n' > "$f8/tree/dist/platforms/ubuntu/steps/return_license.sh"
printf '/steps/runsteps.sh\n' > "$f8/tree/dist/platforms/ubuntu/entrypoint.sh"
pack "$f8"
expect_refuse "scripts personal absents" bash "$verify" "$f8" "$asset" "$root/dest-8"

# 9) archive elle-meme INACCESSIBLE (checksums.txt present) : REFUSE.
f9="$root/no-archive"
mkdir -p "$f9/tree"
make_tree "$f9/tree"
pack "$f9"
rm "$f9/$asset"
expect_refuse "archive inaccessible (checksums.txt present)" bash "$verify" "$f9" "$asset" "$root/dest-9"


echo "verificateur strict T-013.9 : $pass reussite(s), $fail echec(s) — attendu 9 reussites (1 acceptation + 8 refus)."
rm -rf "$root"
[ "$fail" -eq 0 ] && [ "$pass" -eq 9 ]
