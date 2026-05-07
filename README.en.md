# Expresso One-Shot

> Read this in [한국어](README.md).

A one-command pipeline that takes you from **zero to a training-ready Expresso dataset** with unified read + conversational speech, transcripts, and train/dev/test splits.

```bash
git clone https://github.com/daewoung/Expresso_one_type.git
cd Expresso_one_type
bash setup.sh
```

That's it. The script handles venv, dependency install, dataset downloads, segmentation, transcript pairing, and packaging.

---

## What you get

```
expresso_split_v2/
├── train/{ex01..ex04}/
│   ├── confused/, default/, ...        ← read 7 styles (~40 min/style/speaker)
│   └── conv-angry/, conv-default/, ... ← conv 23~24 styles (auto-ASR transcripts)
├── dev/   (same structure, ~1.4 h)
├── test/  (same structure, ~1.4 h)
├── longform/  (8 long read files, with split-time metadata)
├── stats.json
└── README.md
```

Every `.wav` has a sibling `.txt` with its transcript.

| split | read | conv | total | duration |
| --- | --- | --- | --- | --- |
| train | 10,380 | 29,438 | **39,818** | **41.10 h** |
| dev | 628 | 834 | 1,462 | 1.43 h |
| test | 588 | 878 | 1,466 | 1.39 h |
| longform | — | — | 8 | 0.34 h |
| **GRAND** | **11,596** | **31,150** | **42,754** | **44.26 h** |

Close to the paper-cited 45.9 h (read 11h + conv 33h ≈ 44h; the small gap reflects ASR-defined segment boundaries in the conv portion).

### Per-speaker totals (all splits combined)

| speaker | files | duration |
| --- | --- | --- |
| ex01 | 9,992 | 10.78 h |
| ex02 | 9,937 | 11.71 h |
| ex03 | 10,035 | 10.39 h |
| ex04 | 12,790 | 11.37 h |

---

## How it works

### Data sources

| Component | Source | Notes |
| --- | --- | --- |
| read audio (short + longform) | Meta Expresso tar (`dl.fbaipublicfiles.com`) | Original 48kHz mono |
| read transcripts | Same tar (`read_transcriptions.txt`) | Human-written, accurate |
| conv audio (mono per speaker) | HuggingFace `nytopop/expresso-conversational` | 31,150 segments, 14.8 GB parquet |
| conv transcripts | Same HF dataset | NVIDIA Parakeet TDT 0.6B V2 ASR — **may contain errors** |
| train/dev/test split definitions | Meta tar (`splits/{train,dev,test}.txt`) | Time-range-based |

### Pipeline

1. **Read processing** (`build_split.py`)
   - Reads `splits/*.txt`, filters out conv entries (those with `-` in the speaker portion)
   - Symlinks each wav into `expresso_split_v2/{split}/{speaker}/{style}/`
   - Writes the matching transcript line as `{filename}.txt` next to it
   - Files over 30 s (longform) go into `longform/` with a `splits.json` describing which time-range belongs to which split

2. **Conv processing** (`build_conv_split.py`)
   - Decodes 36 parquet shards from `nytopop/expresso-conversational`
   - Parses each `id` of the form `{spk1}-{spk2}_{styles}_{dlg_id}_{start_sample}_{end_sample}`
   - Maps each segment to a split by checking which time range in `splits/*.txt` contains its midpoint
   - Writes the embedded mono wav bytes to disk + `.txt` pair using the parquet's authoritative `speaker_id` and `style` columns

3. **Merge** (in `setup.sh`)
   - Moves `expresso_split_v2/conv/{split}/{speaker}/{style}/` → `expresso_split_v2/{split}/{speaker}/conv-{style}/`
   - Read folders keep plain style names; conv folders carry a `conv-` prefix

4. **Distribute** (optional)
   - `tar czhf expresso_split_v2.tar.gz expresso_split_v2/` (the `-h` flag dereferences read symlinks so the archive is self-contained)

### Why time-range-based splits?

Each conv recording is several minutes long. The official `splits/*.txt` slices each file by time:

```
[train] ex01-ex02_default_007  (60.0s,)        ← 60s to end
[dev]   ex01-ex02_default_007  (,60.0s)         ← 0 to 60s
[test]  ex01-ex02_default_008  (,60.0s)
```

Each nytopop segment carries explicit `start_sample` and `end_sample`, so we compute the midpoint and look up which range it falls in. This guarantees train/dev/test never share audio. (Speaker leakage still exists — every speaker appears in all splits — but that is by the official design.)

---

## Requirements

- Python ≥ 3.10
- ~80 GB free disk (30 GB raw tar + 15 GB parquet + 16 GB output + 17 GB redistributable archive)
- Internet (~45 GB total download)
- Optional: `aria2c` for faster parallel download (falls back to `curl`)

## Options

```bash
bash setup.sh                # full pipeline
bash setup.sh --skip-tar     # skip the redistributable tarball step
bash setup.sh --tar-only     # only re-create the tarball

PYTHON_BIN=python3.11 bash setup.sh   # specify interpreter
ROOT=/data/expresso bash setup.sh     # store all data under /data/expresso
```

Idempotent — every step is safe to re-run; completed steps are skipped automatically.

## Expected runtime

| Step | Time |
| --- | --- |
| Download `expresso.tar` (30 GB) | 5–30 min |
| Extract | 5–10 min |
| Download nytopop conv (14.8 GB) | 3–10 min (with `hf_transfer`) |
| Build read split (symlinks) | < 10 s |
| Build conv split (write 31 k wavs) | 1–3 min |
| Merge conv folders | < 1 s |
| Create distribution tarball (17 GB, gzip) | 5–15 min |

Total: roughly **20–70 minutes** end-to-end.

---

## File system caveats

- **Read wavs (11,604)** are symlinks into `audio_48khz/` — disk-cheap, but they break if the source dir is moved.
- **Conv wavs (31,150)** are real files (~16 GB) — written directly from parquet bytes.
- **Longform wavs (8)** are symlinks.

When archiving for transfer:

- ❌ `tar czf …` (default) preserves symlinks as links → recipient sees dead links for read files.
- ✅ `tar czhf …` (`-h` = dereference) writes the real bytes → archive is self-contained.

`setup.sh` uses `-h` automatically.

---

## Known limitations

1. **Conv transcripts are auto-generated** by Parakeet ASR. Expect some errors. Non-verbal styles like `conv-animal` or `conv-nonverbal` may have nearly meaningless transcripts (e.g., `"Ribbit Ribbit Ribbit"`).
2. **Longform transcripts are file-level, not segment-aligned.** If you slice longform audio by the split time-ranges, the transcript will not match. Either treat them as whole files, run forced alignment, or drop them.
3. **Speaker leakage exists.** The official splits divide audio by time, so every speaker appears in train, dev, and test. Not suitable for unseen-speaker evaluation.
4. **Conv segments are per-channel mono.** Cross-speaker prosodic interaction is not present within a single segment, only across paired segments.

---

## License

The Expresso dataset itself is released under **CC BY-NC 4.0** (non-commercial). The scripts in this repository are MIT-licensed.

## References

- [EXPRESSO paper (arXiv:2308.05725)](https://arxiv.org/abs/2308.05725)
- [Demo samples](https://speechbot.github.io/expresso/)
- [Original textlesslib processing code](https://github.com/facebookresearch/textlesslib/tree/main/examples/expresso/dataset)
- [`nytopop/expresso-conversational`](https://huggingface.co/datasets/nytopop/expresso-conversational)
- [NVIDIA Parakeet TDT 0.6B V2 (ASR model)](https://huggingface.co/nvidia/parakeet-tdt-0.6b-v2)
