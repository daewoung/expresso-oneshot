#!/usr/bin/env bash
# Reproduce the expresso_split_v2 pipeline end-to-end on a fresh machine.
#
# What this does (all idempotent — safe to re-run):
#   1. Create Python venv
#   2. Install dependencies
#   3. Download original Expresso tar (~30 GB) and extract -> audio_48khz, splits, read_transcriptions.txt
#   4. Download nytopop/expresso-conversational from HuggingFace (~14.8 GB, parquet)
#   5. Build read split (symlinks + .txt pairs) -> expresso_split_v2/
#   6. Build conv split (parquet -> wav + .txt) -> expresso_split_v2/conv/
#   7. Merge conv into main split tree with `conv-` prefix
#   8. Filter animal/child styles into <split>-exclude/ siblings
#   9. (Optional) Make dereferenced tarball for distribution (skips *-exclude/)
#
# If expresso_split_v2/ is already present, steps 1–7 are skipped automatically;
# only the filter step (8) and optional tarball (9) run.
#
# Usage:
#   bash setup.sh              # full pipeline
#   bash setup.sh --skip-tar   # skip step 9 (no distribution tarball)
#   bash setup.sh --tar-only   # only run step 9

set -euo pipefail

# ────── Config ──────
ROOT="${ROOT:-$(cd "$(dirname "$0")" && pwd)}"
VENV="$ROOT/.venv"
PYTHON_BIN="${PYTHON_BIN:-python3}"
EXPRESSO_TAR_URL="https://dl.fbaipublicfiles.com/textless_nlp/expresso/data/expresso.tar"
NYTOPOP_REPO="nytopop/expresso-conversational"

MAKE_TAR=1
TAR_ONLY=0
for arg in "$@"; do
  case "$arg" in
    --skip-tar) MAKE_TAR=0 ;;
    --tar-only) TAR_ONLY=1 ;;
    -h|--help)  sed -n '2,21p' "$0"; exit 0 ;;
    *) echo "unknown arg: $arg"; exit 1 ;;
  esac
done

cd "$ROOT"
echo "==> Working dir: $ROOT"

# Detect already-built split: skip the heavy build steps when present.
NEED_BUILD=1
OUT_DIR="$ROOT/expresso_split_v2"
if [[ -d "$OUT_DIR/dev" && -d "$OUT_DIR/train" && -d "$OUT_DIR/test" ]]; then
  NEED_BUILD=0
  echo "==> $OUT_DIR already built — skipping steps 1–7"
fi

if [[ "$NEED_BUILD" -eq 1 ]]; then

# ────── Step 1: venv ──────
if [[ ! -x "$VENV/bin/python" ]]; then
  echo "==> [1/9] Creating venv at $VENV"
  "$PYTHON_BIN" -m venv "$VENV"
  "$VENV/bin/python" -m ensurepip --upgrade
fi
PY="$VENV/bin/python"

# ────── Step 2: deps ──────
echo "==> [2/9] Installing Python deps"
"$PY" -m pip install -q --upgrade pip >/dev/null
"$PY" -m pip install -q \
  huggingface_hub hf_transfer \
  pyarrow pandas soundfile tqdm

# ────── Step 3: download + extract Expresso tar ──────
if [[ ! -d "$ROOT/audio_48khz" ]] || [[ ! -f "$ROOT/read_transcriptions.txt" ]]; then
  if [[ ! -f "$ROOT/expresso.tar" ]]; then
    echo "==> [3/9] Downloading Expresso tar (~30 GB)"
    if command -v aria2c >/dev/null; then
      aria2c -x 8 -s 8 -d "$ROOT" -o expresso.tar "$EXPRESSO_TAR_URL"
    else
      curl -fL -C - -o "$ROOT/expresso.tar" "$EXPRESSO_TAR_URL"
    fi
  fi
  echo "==> Extracting expresso.tar"
  # The tar embeds UIDs/GIDs from Meta's build server. On a different host
  # (especially inside a container where uid_map doesn't include those IDs)
  # `chown` returns EINVAL and tar exits with status 2. Data is extracted
  # correctly anyway, so we explicitly silence the chown attempt and accept
  # a non-zero exit if the only issue was ownership.
  set +e
  tar --no-same-owner --no-same-permissions -xf "$ROOT/expresso.tar" -C "$ROOT" 2> >(grep -v "Cannot change ownership" >&2)
  rc=$?
  set -e
  # Verify extraction succeeded by checking expected outputs.
  if [[ ! -d "$ROOT/expresso/audio_48khz" ]] && [[ ! -d "$ROOT/audio_48khz" ]]; then
    echo "    tar failed (rc=$rc) and audio_48khz/ not found — aborting"
    exit "$rc"
  fi
  if [[ "$rc" -ne 0 ]]; then
    echo "    (tar exited rc=$rc; ownership warnings are non-fatal — data extracted successfully)"
  fi
  # The tar extracts into ./expresso/ — flatten if so
  if [[ -d "$ROOT/expresso/audio_48khz" ]] && [[ ! -d "$ROOT/audio_48khz" ]]; then
    mv "$ROOT/expresso/"* "$ROOT/" 2>/dev/null || true
    rmdir "$ROOT/expresso" 2>/dev/null || true
  fi
else
  echo "==> [3/9] Expresso already extracted, skipping"
fi

if [[ "$TAR_ONLY" -ne 1 ]]; then
  # ────── Step 4: download nytopop conv ──────
  NYTOPOP_DIR="$ROOT/nytopop_expresso_conv"
  if [[ ! -d "$NYTOPOP_DIR/conversational" ]] || [[ -z "$(ls -A "$NYTOPOP_DIR/conversational" 2>/dev/null)" ]]; then
    echo "==> [4/9] Downloading $NYTOPOP_REPO (~14.8 GB)"
    HF_HUB_ENABLE_HF_TRANSFER=1 "$PY" - <<PYEOF
from huggingface_hub import snapshot_download
snapshot_download(
    repo_id="$NYTOPOP_REPO",
    repo_type="dataset",
    local_dir="$NYTOPOP_DIR",
    allow_patterns=["*.parquet", "*.json", "*.md"],
)
PYEOF
  else
    echo "==> [4/9] nytopop already downloaded, skipping"
  fi

  # ────── Step 5: build read split ──────
  echo "==> [5/9] Building read split"
  "$PY" "$ROOT/build_split.py"

  # ────── Step 6: build conv split ──────
  echo "==> [6/9] Building conv split"
  "$PY" "$ROOT/build_conv_split.py"

  # ────── Step 7: merge conv with conv- prefix ──────
  echo "==> [7/9] Merging conv into main split tree"
  "$PY" - <<'PYEOF'
import os, shutil
from pathlib import Path
ROOT = Path(os.environ.get("ROOT", "."))
OUT = Path(os.environ.get("OUT_DIR", str(ROOT / "expresso_split_v2")))
CONV = OUT / "conv"
if CONV.exists():
    moved = 0
    for split in ["train", "dev", "test"]:
        src = CONV / split
        if not src.exists(): continue
        for spk in sorted(src.iterdir()):
            if not spk.is_dir(): continue
            for style in sorted(spk.iterdir()):
                if not style.is_dir(): continue
                tgt = OUT / split / spk.name / f"conv-{style.name}"
                if tgt.exists(): continue
                tgt.parent.mkdir(parents=True, exist_ok=True)
                os.rename(style, tgt)
                moved += 1
    print(f"  moved {moved} style folders")
    if not list(CONV.rglob("*.wav")):
        shutil.rmtree(CONV)
        print(f"  removed empty {CONV}")
else:
    print("  conv/ already merged, skipping")
PYEOF
fi

fi  # end if NEED_BUILD

# ────── Step 8: filter animal/child styles ──────
echo "==> [8/9] Filtering animal/child styles into <split>-exclude/"
filter_moved=0
for split in train dev test; do
  src_root="$OUT_DIR/$split"
  [[ -d "$src_root" ]] || continue
  excl_root="$OUT_DIR/${split}-exclude"
  while IFS= read -r style_dir; do
    [[ -n "$style_dir" ]] || continue
    spk=$(basename "$(dirname "$style_dir")")
    style=$(basename "$style_dir")
    mkdir -p "$excl_root/$spk"
    mv "$style_dir" "$excl_root/$spk/$style"
    filter_moved=$((filter_moved + 1))
  done < <(find "$src_root" -mindepth 2 -maxdepth 2 -type d \
              \( -iname '*animal*' -o -iname '*child*' \) 2>/dev/null)
done
echo "    moved $filter_moved style folder(s) to *-exclude/"

TAR_OUT="$ROOT/expresso_split_v2.tar.gz"
if [[ "$filter_moved" -gt 0 && -f "$TAR_OUT" ]]; then
  echo "    NOTE: $TAR_OUT predates the filter — delete it and re-run if you"
  echo "          want a fresh tarball without animal/child styles."
fi

# ────── Step 9: distribution tarball ──────
if [[ "$MAKE_TAR" -eq 1 ]]; then
  if [[ ! -f "$TAR_OUT" ]]; then
    echo "==> [9/9] Creating distribution tarball (dereferenced, excludes *-exclude/)"
    tar czhf "$TAR_OUT" -C "$ROOT" --exclude='*-exclude' expresso_split_v2/
  else
    echo "==> [9/9] tarball exists at $TAR_OUT, skipping"
  fi
fi

echo "==> Done!"
echo "    Output:   $OUT_DIR/"
echo "    Excluded: $OUT_DIR/{train,dev,test}-exclude/  (animal/child styles)"
[[ "$MAKE_TAR" -eq 1 ]] && echo "    Tarball: $TAR_OUT"
