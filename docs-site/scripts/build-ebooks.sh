#!/usr/bin/env bash
#
# build-ebooks.sh — produce PDF and ePub of the Wire Framework docs from the
# Docusaurus markdown sources, for Read the Docs.
#
# Read the Docs ignores the `formats:` key when a project overrides
# `build.commands` (as this one does, to run a Docusaurus build). With a custom
# build you are responsible for every artifact: RTD publishes whatever lands in
# $READTHEDOCS_OUTPUT/{html,pdf,epub}/. This script produces the pdf/ and epub/
# outputs; .readthedocs.yaml produces html/.
#
# NON-FATAL BY DESIGN. The HTML docs must never fail to publish because an
# ebook step hiccuped, so .readthedocs.yaml invokes this with `|| true` and the
# script itself never exits non-zero on a build failure — it logs and moves on.
# It also exits 0 (skips) when pandoc isn't installed.
#
# Local smoke test (no pandoc needed): assemble only and print the file order:
#   EBOOK_ASSEMBLE_ONLY=1 bash docs-site/scripts/build-ebooks.sh
#
# Requires (installed via .readthedocs.yaml build.apt_packages): pandoc, and a
# PDF engine — wkhtmltopdf here (light, HTML/CSS-based). Swap --pdf-engine to
# xelatex (apt: texlive-xetex) for higher-fidelity typesetting if wanted.

set -uo pipefail

# Resolve repo-relative paths so this works from the repo root (RTD runs
# build.commands from the checkout root).
DOCS_DIR="docs-site/docs"
STATIC_DIR="docs-site/static"
OUT="${READTHEDOCS_OUTPUT:-docs-site/_ebook_out}"
TITLE="Wire Framework Documentation"

# Section reading order; any section dir not listed here is appended after,
# sorted by name, so a newly-added section still gets included.
PREFERRED_SECTIONS="getting-started tutorials release-types advanced reference"

WORK="$(mktemp -d)"
COMBINED="$WORK/wire-framework.md"
trap 'rm -rf "$WORK"' EXIT

frontmatter_title() {
  # title: -> sidebar_label: -> humanised filename
  local f="$1" t
  t="$(grep -m1 '^title:' "$f" 2>/dev/null | sed -E 's/^title:[[:space:]]*//; s/^["'"'"']//; s/["'"'"']$//')"
  [ -z "$t" ] && t="$(grep -m1 '^sidebar_label:' "$f" 2>/dev/null | sed -E 's/^sidebar_label:[[:space:]]*//; s/^["'"'"']//; s/["'"'"']$//')"
  [ -z "$t" ] && t="$(basename "$f" | sed -E 's/\.(md|mdx)$//; s/[-_]/ /g')"
  printf '%s' "$t"
}

strip_frontmatter() {
  # Drop a leading --- ... --- YAML block; pass everything else through.
  awk 'BEGIN{fm=0}
       NR==1 && /^---[[:space:]]*$/ {fm=1; next}
       fm==1 && /^---[[:space:]]*$/ {fm=0; next}
       fm==0 {print}' "$1"
}

list_section_files() {
  # Files in a section dir, sorted by sidebar_position (numeric, default 999)
  # then filename.
  local dir="$1" f pos
  for f in "$dir"/*.md "$dir"/*.mdx; do
    [ -f "$f" ] || continue
    pos="$(grep -m1 '^sidebar_position:' "$f" 2>/dev/null | sed 's/[^0-9]//g')"
    printf '%s\t%s\n' "${pos:-999}" "$f"
  done | sort -n -k1,1 -k2 | cut -f2
}

ordered_files() {
  # intro first
  [ -f "$DOCS_DIR/intro.md" ] && echo "$DOCS_DIR/intro.md"
  # preferred sections in order
  local seen=" "
  local s
  for s in $PREFERRED_SECTIONS; do
    [ -d "$DOCS_DIR/$s" ] || continue
    seen="$seen$s "
    list_section_files "$DOCS_DIR/$s"
  done
  # any remaining section dirs, alphabetically
  local d name
  for d in "$DOCS_DIR"/*/; do
    [ -d "$d" ] || continue
    name="$(basename "$d")"
    case "$seen" in *" $name "*) continue;; esac
    list_section_files "$d"
  done
  # any other top-level md (besides intro)
  for f in "$DOCS_DIR"/*.md "$DOCS_DIR"/*.mdx; do
    [ -f "$f" ] || continue
    [ "$f" = "$DOCS_DIR/intro.md" ] && continue
    echo "$f"
  done
}

if [ ! -d "$DOCS_DIR" ]; then
  echo "build-ebooks: $DOCS_DIR not found — run from the repo root. Skipping."
  exit 0
fi

# Assemble each doc as a chapter. Docusaurus docs usually carry their own `# Title`
# H1 (matching the frontmatter title); use it as the chapter heading. Only when a
# doc has no leading H1 (its title lives in frontmatter) do we inject one — so we
# never emit a duplicate heading, and never rewrite the body (which could touch a
# `#` line inside a code fence).
: > "$COMBINED"
count=0
while IFS= read -r f; do
  [ -f "$f" ] || continue
  body="$(strip_frontmatter "$f")"
  first="$(printf '%s\n' "$body" | grep -m1 -v '^[[:space:]]*$')"
  printf '\n\n' >> "$COMBINED"
  case "$first" in
    '# '*) : ;;  # doc already opens with an H1 — use it as the chapter heading
    *) printf '# %s\n\n' "$(frontmatter_title "$f")" >> "$COMBINED" ;;
  esac
  printf '%s\n' "$body" >> "$COMBINED"
  count=$((count + 1))
done < <(ordered_files)
echo "build-ebooks: assembled $count docs into a combined source"

if [ "${EBOOK_ASSEMBLE_ONLY:-0}" = "1" ]; then
  echo "build-ebooks: EBOOK_ASSEMBLE_ONLY set — file order was:"
  ordered_files
  echo "build-ebooks: combined markdown at $COMBINED ($(wc -l < "$COMBINED") lines)"
  # Keep the combined file for inspection in assemble-only mode.
  cp "$COMBINED" "docs-site/_ebook_combined.preview.md"
  echo "build-ebooks: preview copied to docs-site/_ebook_combined.preview.md"
  exit 0
fi

if ! command -v pandoc >/dev/null 2>&1; then
  echo "build-ebooks: pandoc not found — skipping PDF/ePub (HTML docs unaffected)."
  exit 0
fi

mkdir -p "$OUT/pdf" "$OUT/epub"
RESOURCE_PATH="$DOCS_DIR:$STATIC_DIR:."

# ePub — pandoc's native writer, no external engine needed.
if pandoc "$COMBINED" \
     --metadata title="$TITLE" \
     --resource-path="$RESOURCE_PATH" \
     --toc --toc-depth=2 \
     -o "$OUT/epub/wire-framework.epub"; then
  echo "build-ebooks: ePub written to $OUT/epub/wire-framework.epub"
else
  echo "build-ebooks: ePub build failed — continuing (HTML docs unaffected)."
fi

# PDF — via wkhtmltopdf (HTML/CSS engine; light, headless). Swap to
# --pdf-engine=xelatex (apt: texlive-xetex) for LaTeX-grade typesetting.
if pandoc "$COMBINED" \
     --metadata title="$TITLE" \
     --resource-path="$RESOURCE_PATH" \
     --toc --toc-depth=2 \
     --pdf-engine=wkhtmltopdf \
     -V margin-top=18 -V margin-bottom=18 -V margin-left=18 -V margin-right=18 \
     -o "$OUT/pdf/wire-framework.pdf"; then
  echo "build-ebooks: PDF written to $OUT/pdf/wire-framework.pdf"
else
  echo "build-ebooks: PDF build failed — continuing (HTML docs unaffected)."
fi

# Never leave an empty format directory behind: Read the Docs fails the WHOLE
# build (HTML included) when a declared output format directory exists but
# contains no files ("Build output directory doesn't contain any file"). This
# is exactly what froze the live docs site between 2026-07-21 and 2026-08-08:
# the PDF step failed non-fatally, the empty pdf/ dir stayed, RTD errored.
find "$OUT" -mindepth 1 -maxdepth 1 -type d -empty -delete 2>/dev/null || true

echo "build-ebooks: done"
exit 0
