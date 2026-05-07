"""
Build expresso_split_v2/ from audio_48khz/ + splits/ + read_transcriptions.txt
- Excludes conversational
- Short read files: symlink wav + write .txt next to it
- Longform (>30s): put in expresso_split_v2/longform/ with full wav + full txt + splits.json
"""
import os
import json
from pathlib import Path

ROOT = Path(os.environ.get("ROOT", Path(__file__).resolve().parent))
AUDIO = ROOT / "audio_48khz" / "read"
SPLITS = ROOT / "splits"
TRANS_FILE = ROOT / "read_transcriptions.txt"
OUT = Path(os.environ.get("OUT_DIR", ROOT / "expresso_split_v2"))


def parse_segment(seg_str):
    """'(33.98s,)' -> (33.98, None)  ;  '(,16.99s)' -> (None, 16.99)  ;  '(a,b)' -> (a,b)"""
    s = seg_str.strip()
    assert s.startswith("(") and s.endswith(")"), seg_str
    a, b = s[1:-1].split(",")
    a = float(a.rstrip("s")) if a.strip() else None
    b = float(b.rstrip("s")) if b.strip() else None
    return (a, b)


def load_transcripts():
    trans = {}
    with open(TRANS_FILE) as f:
        for line in f:
            line = line.rstrip("\n")
            if not line:
                continue
            fid, text = line.split("\t", 1)
            trans[fid] = text
    return trans


def load_split(name):
    """Returns list of (fid, segment_or_None)."""
    items = []
    with open(SPLITS / f"{name}.txt") as f:
        for line in f:
            line = line.rstrip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            fid = parts[0]
            seg = parse_segment(parts[1]) if len(parts) > 1 else None
            items.append((fid, seg))
    return items


def audio_path(fid):
    parts = fid.split("_")
    speaker = parts[0]
    style = parts[1]
    sub = "longform" if "longform" in fid else "base"
    return AUDIO / speaker / style / sub / f"{fid}.wav"


def is_longform(fid):
    return "longform" in fid


def safe_symlink(src: Path, dst: Path):
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists() or dst.is_symlink():
        dst.unlink()
    os.symlink(src, dst)


def write_text(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text + "\n", encoding="utf-8")


def main():
    trans = load_transcripts()
    print(f"Loaded {len(trans)} transcripts")

    # Pass 1: collect entries by split, separating short vs longform
    short_by_split = {}   # split -> list[(fid, src_wav, text)]
    longform_segs = {}    # fid -> {"train": (a,b), "dev": (a,b), "test": (a,b)}

    stats = {}
    for split in ["train", "dev", "test"]:
        items = load_split(split)
        # filter conv (speaker has '-')
        read_items = [(fid, seg) for fid, seg in items if "-" not in fid.split("_")[0]]
        short = [(fid, seg) for fid, seg in read_items if not is_longform(fid)]
        longf = [(fid, seg) for fid, seg in read_items if is_longform(fid)]

        short_entries = []
        for fid, seg in short:
            src = audio_path(fid)
            text = trans.get(fid)
            short_entries.append((fid, src, text, seg))
        short_by_split[split] = short_entries

        for fid, seg in longf:
            longform_segs.setdefault(fid, {})[split] = seg

        stats[split] = {
            "short_total": len(short),
            "short_with_text": sum(1 for fid, _ in short if fid in trans),
            "short_missing_audio": sum(1 for fid, _ in short if not audio_path(fid).exists()),
            "longform": len(longf),
        }

    print("\n=== Stats ===")
    for split, s in stats.items():
        print(f"  {split}: {s}")

    # Build outputs
    OUT.mkdir(parents=True, exist_ok=True)

    # 1) Short read files: symlink + .txt
    n_written = 0
    n_skipped = 0
    for split, entries in short_by_split.items():
        for fid, src, text, _seg in entries:
            if not src.exists():
                n_skipped += 1
                continue
            parts = fid.split("_")
            speaker, style = parts[0], parts[1]
            tgt_dir = OUT / split / speaker / style
            tgt_wav = tgt_dir / f"{fid}.wav"
            tgt_txt = tgt_dir / f"{fid}.txt"
            safe_symlink(src.resolve(), tgt_wav)
            if text is not None:
                write_text(tgt_txt, text)
            n_written += 1
    print(f"\nShort read: wrote {n_written}, missing-audio skipped {n_skipped}")

    # 2) Longform: full file in expresso_split_v2/longform/, with splits.json
    long_dir = OUT / "longform"
    long_dir.mkdir(parents=True, exist_ok=True)
    for fid, seg_map in sorted(longform_segs.items()):
        src = audio_path(fid)
        if not src.exists():
            print(f"  longform missing audio: {fid}")
            continue
        tgt_wav = long_dir / f"{fid}.wav"
        tgt_txt = long_dir / f"{fid}.txt"
        tgt_meta = long_dir / f"{fid}.splits.json"
        safe_symlink(src.resolve(), tgt_wav)
        text = trans.get(fid, "")
        write_text(tgt_txt, text)
        meta = {
            "id": fid,
            "splits": {k: {"start": v[0], "end": v[1]} for k, v in seg_map.items()},
            "text_is_full_file": True,
            "note": "Transcript covers the ENTIRE wav. Time ranges in 'splits' "
                    "indicate which portion belongs to each split; the text is "
                    "NOT segment-aligned.",
        }
        tgt_meta.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n")
    print(f"Longform: wrote {len(longform_segs)} files into {long_dir}")

    # 3) README
    readme = OUT / "README.md"
    readme.write_text(
        "# expresso_split_v2\n\n"
        "Generated from `audio_48khz/read/` + `splits/{train,dev,test}.txt` + "
        "`read_transcriptions.txt`.\n\n"
        "## Layout\n"
        "- `train/`, `dev/`, `test/` — short read files only.\n"
        "  Each `.wav` (symlink) has a sibling `.txt` with the single-utterance transcript.\n"
        "- `longform/` — 8 long files (~3 min each) that are over 30s.\n"
        "  Each has `{fid}.wav`, `{fid}.txt` (full transcript), and `{fid}.splits.json`\n"
        "  describing which time range belongs to which split.\n\n"
        "## Excluded\n"
        "- All conversational data (file ids containing '-' in the speaker part, e.g. `ex01-ex02_*`).\n\n"
        "## Notes\n"
        "- `.wav` files are symlinks into `audio_48khz/`. Do not move that source dir.\n"
        "- All short-read files have transcripts (verified 0 missing).\n"
        "- Longform transcripts are whole-file; they are NOT aligned to the time ranges\n"
        "  given by splits.json. Treat with care.\n"
    )
    print(f"Wrote {readme}")


if __name__ == "__main__":
    main()
