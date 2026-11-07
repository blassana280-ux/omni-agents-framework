#!/usr/bin/env bash
# OMNI WARSHIPS T-013.9 — verification STRICTE + installation du CLI
# game-ci CORRIGE (heritage ENV des identifiants, secrets hors argv).
#
# Usage :
#   verify-gameci-cli.sh <base> <asset> <dest> [expected_file]
#
#   <base>          URL de release
#                   (https://github.com/<owner>/<repo>/releases/download/<tag>)
#                   OU dossier local contenant checksums.txt + <asset>
#                   (mode tests, fixtures factices).
#   <asset>         nom de l archive a verifier
#                   (ex. gameci-cli-secure-linux-x64.tar.gz).
#   <dest>          dossier d installation : le binaire game-ci et dist/
#                   y sont extraits.
#   [expected_file] fichier d empreinte attendue ANCRE DANS GIT
#                   (gameci-cli-secure/artifact-checksum.txt, commite par
#                   le bot CI) : requis par le workflow de build — la
#                   divergence entre checksums.txt et l empreinte ancree
#                   est FATALE.
#
# ECHEC STRICT (aucun soft-skip — l installateur officiel du CLI, lui,
# poursuit l installation apres un ECHEC de checksum : interdit ici) :
#   - checksums.txt inaccessible ;
#   - empreinte attendue absente de checksums.txt ;
#   - empreinte absente du fichier ancre dans git ;
#   - divergence checksums.txt / empreinte ancree ;
#   - divergence sha256 archive / empreinte attendue ;
#   - binaire absent de l archive verifiee ;
#   - binaire INSTALLE different du binaire de l archive verifiee ;
#   - scripts personal absents de l artefact (activate.sh --include-personal,
#     runsteps.sh trap EXIT, return_license.sh branche personal,
#     entrypoint.sh /steps/runsteps.sh).
set -euo pipefail

base="${1:?T-013.9 : base (URL de release ou dossier local) requis}"
asset="${2:?T-013.9 : nom de l archive requis}"
dest="${3:?T-013.9 : dossier d installation requis}"
expected_file="${4:-}"

fail() {
  echo "::error::T-013.9 : $1"
  exit 1
}

fetch() {
  # <out> <nom> : https -> curl, sinon copie locale (mode tests).
  out="$1"
  name="$2"
  if [ "${base#https://}" != "$base" ]; then
    curl -fsSL --retry 3 -o "$out" "$base/$name"
  else
    [ -f "$base/$name" ] || return 1
    cp "$base/$name" "$out"
  fi
}

tmp="$(mktemp -d)"
ref="$(mktemp -d)"

fetch "$tmp/checksums.txt" checksums.txt \
  || fail "checksums.txt INACCESSIBLE ($base/checksums.txt) — installation non verifiee REFUSEE"

want="$(awk -v a="$asset" '$NF == a { print $1; exit }' "$tmp/checksums.txt")"
[ -n "$want" ] || fail "empreinte attendue de $asset ABSENTE de checksums.txt"

if [ -n "$expected_file" ]; then
  [ -f "$expected_file" ] || fail "$expected_file introuvable (empreinte ancree dans git requise)"
  pinned="$(awk -v a="$asset" '$NF == a { print $1; exit }' "$expected_file")"
  [ -n "$pinned" ] || fail "empreinte de $asset absente du fichier ancree $expected_file"
  [ "$pinned" = "$want" ] || fail "divergence checksums.txt ($want) vs empreinte ancree git ($pinned)"
fi

fetch "$tmp/$asset" "$asset" || fail "archive $asset INACCESSIBLE ($base/$asset)"
got="$(sha256sum "$tmp/$asset" | awk '{ print $1 }')"
[ "$got" = "$want" ] || fail "checksum MISMATCH — attendu $want, obtenu $got (installation REFUSEE)"

tar -xzf "$tmp/$asset" -C "$ref"
mkdir -p "$dest"
tar -xzf "$tmp/$asset" -C "$dest"
[ -f "$ref/game-ci" ] || fail "binaire game-ci absent de l archive verifiee"
[ -f "$dest/game-ci" ] || fail "binaire game-ci non installe dans $dest"
chmod 755 "$dest/game-ci"

a="$(sha256sum "$dest/game-ci" | awk '{ print $1 }')"
b="$(sha256sum "$ref/game-ci" | awk '{ print $1 }')"
[ "$a" = "$b" ] || fail "le binaire INSTALLE ne correspond PAS au binaire de l archive verifiee ($a vs $b)"

steps="$dest/dist/platforms/ubuntu/steps"
[ -f "$steps/activate.sh" ] || fail "dist/platforms/ubuntu/steps/activate.sh absent de l artefact"
grep -q -- '--include-personal' "$steps/activate.sh" \
  || fail "activate.sh sans chemin personal (--include-personal absent) dans l artefact"
grep -qF 'trap return_license_once EXIT' "$steps/runsteps.sh" \
  || fail "runsteps.sh sans trap EXIT de restitution dans l artefact"
grep -qF 'Returning personal license seat' "$steps/return_license.sh" \
  || fail "return_license.sh sans branche personal dans l artefact"
grep -qF '/steps/runsteps.sh' "$dest/dist/platforms/ubuntu/entrypoint.sh" \
  || fail "entrypoint.sh sans orchestration /steps/runsteps.sh dans l artefact"

rm -rf "$tmp" "$ref"
echo "T-013.9 : CLI corrige VERIFIE (strict) et INSTALLE — archive $asset, sha256 $a, scripts personal + trap EXIT prouves dans l artefact."
