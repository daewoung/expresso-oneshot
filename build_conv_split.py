"""
Unpack nytopop/expresso-conversational parquet shards and write per-segment
wav + txt files into expresso_split_v2/conv/{train,dev,test}/...

Mapping logic
-------------
nytopop id format:  {spk1}-{spk2}_{style1}-{style2}_{dialogue_id}_{start_sample}_{end_sample}
                    (samples at 48kHz)

splits/{split}.txt entry format:
    "{file_id}\t({start_s},{end_s})"  where either side may be empty
    file_id = {spk1}-{spk2}_{styles}_{dialogue_id}

Each nytopop segment is assigned to whichever split's time range it falls inside
(by midpoint). If no match -> dropped (logged).
"""
import os
import re
from pathlib import Path
from collections import defaultdict
import pyarrow.parquet as pq

ROOT = Path(os.environ.get("ROOT", Path(__file__).resolve().parent))
PARQUET_DIR = ROOT / "nytopop_expresso_conv" / "conversational"
SPLITS_DIR = ROOT / "splits"
OUT_BASE = Path(os.environ.get("OUT_DIR", ROOT / "expresso_split_v2"))
OUT = OUT_BASE / "conv"
SR = 48000


def parse_segment(seg_str):
    """'(60.0s,)' -> (60.0, None) ; '(,60.0s)' -> (None, 60.0)"""
    s = seg_str.strip()
    assert s.startswith("(") and s.endswith(")"), seg_str
    a, b = s[1:-1].split(",")
    a = float(a.rstrip("s")) if a.strip() else None
    b = float(b.rstrip("s")) if b.strip() else None
    return (a, b)


def load_split_ranges():
    """Returns dict: file_id -> list of (split_name, start_s, end_s)."""
    ranges = defaultdict(list)
    for split in ["train", "dev", "test"]:
        with open(SPLITS_DIR / f"{split}.txt") as f:
            for line in f:
                line = line.rstrip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split("\t")
                fid = parts[0]
                # only conv
                if "-" not in fid.split("_")[0]:
                    continue
                if len(parts) > 1:
                    start, end = parse_segment(parts[1])
                else:
                    start, end = (None, None)
                ranges[fid].append((split, start, end))
    return ranges


def in_range(mid, start, end):
    if start is not None and mid < start:
        return False
    if end is not None and mid >= end:
        return False
    return True


# id like: ex04-ex01_animal-animaldir_007_312480_1378320
ID_RE = re.compile(r"^(.+)_(\d+)_(\d+)$")


def parse_nytopop_id(seg_id):
    """Returns (file_id, start_sample, end_sample)."""
    m = ID_RE.match(seg_id)
    if not m:
        return None
    return m.group(1), int(m.group(2)), int(m.group(3))


def main():
    print("Loading split ranges...")
    split_ranges = load_split_ranges()
    print(f"  {len(split_ranges)} unique conv file_ids across splits")

    OUT.mkdir(parents=True, exist_ok=True)

    parquet_files = sorted(PARQUET_DIR.glob("*.parquet"))
    print(f"Found {len(parquet_files)} parquet shards")

    stats = {
        "total_rows": 0,
        "by_split": defaultdict(int),
        "no_split_match": 0,
        "missing_ranges": 0,
        "id_parse_fail": 0,
    }
    unmatched_examples = []

    for pi, pf_path in enumerate(parquet_files):
        pf = pq.ParquetFile(pf_path)
        n_rows = pf.metadata.num_rows
        print(f"[{pi+1}/{len(parquet_files)}] {pf_path.name}  rows={n_rows}")
        for rg_idx in range(pf.num_row_groups):
            tbl = pf.read_row_group(rg_idx)
            ids = tbl.column("id").to_pylist()
            speakers = tbl.column("speaker_id").to_pylist()
            styles = tbl.column("style").to_pylist()
            texts = tbl.column("text").to_pylist()
            audios = tbl.column("audio").to_pylist()  # list of {bytes, path}

            for i in range(len(ids)):
                stats["total_rows"] += 1
                seg_id = ids[i]
                speaker = speakers[i]
                style = styles[i]
                text = texts[i] or ""
                audio_bytes = audios[i]["bytes"]

                parsed = parse_nytopop_id(seg_id)
                if not parsed:
                    stats["id_parse_fail"] += 1
                    continue
                file_id, start_samp, end_samp = parsed

                ranges = split_ranges.get(file_id)
                if ranges is None:
                    stats["missing_ranges"] += 1
                    continue

                start_s = start_samp / SR
                end_s = end_samp / SR
                mid = (start_s + end_s) / 2.0

                target_split = None
                for sp, rs, re_ in ranges:
                    if in_range(mid, rs, re_):
                        target_split = sp
                        break

                if target_split is None:
                    stats["no_split_match"] += 1
                    if len(unmatched_examples) < 5:
                        unmatched_examples.append((seg_id, mid, ranges))
                    continue

                # Write
                tgt_dir = OUT / target_split / speaker / style
                tgt_dir.mkdir(parents=True, exist_ok=True)
                wav_path = tgt_dir / f"{seg_id}.wav"
                txt_path = tgt_dir / f"{seg_id}.txt"
                wav_path.write_bytes(audio_bytes)
                txt_path.write_text(text + "\n", encoding="utf-8")
                stats["by_split"][target_split] += 1

    print("\n=== Stats ===")
    print(f"  total rows:          {stats['total_rows']}")
    for split, n in stats["by_split"].items():
        print(f"  -> {split}: {n}")
    print(f"  no_split_match:      {stats['no_split_match']}")
    print(f"  missing_ranges:      {stats['missing_ranges']}")
    print(f"  id_parse_fail:       {stats['id_parse_fail']}")

    if unmatched_examples:
        print("\n  unmatched samples:")
        for sid, mid, ranges in unmatched_examples:
            print(f"    {sid}  mid={mid:.2f}s  ranges={ranges}")


if __name__ == "__main__":
    main()
