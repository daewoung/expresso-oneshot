<div align="center">

# Expresso One-Shot

**Zero to a training-ready Expresso dataset in one command.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Dataset: CC BY-NC 4.0](https://img.shields.io/badge/Dataset-CC%20BY--NC%204.0-orange.svg)](https://creativecommons.org/licenses/by-nc/4.0/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![Paper](https://img.shields.io/badge/arXiv-2308.05725-b31b1b.svg)](https://arxiv.org/abs/2308.05725)

English · [한국어](README.md)

</div>

---

A one-command pipeline that downloads, segments, transcribes, and packages Meta's [Expresso dataset](https://arxiv.org/abs/2308.05725) (read 11h + improvised conversational 33h, 4 speakers, 48kHz) into a training-ready folder with unified read + conv structure, transcripts, and official train/dev/test splits.

## ⚡ Quick Start

```bash
git clone <YOUR_REPO_URL>
cd <REPO_DIR>
bash setup.sh
```

20–70 minutes later, your dataset is ready. Needs ~80 GB disk, ~45 GB download.

## 🎯 Features

- 🚀 **One-command setup** — venv, deps, downloads, builds, all automatic
- 🔁 **Idempotent** — interrupt anytime, re-run picks up where it left off
- 📦 **Self-contained tarball** — symlinks dereferenced, recipient just extracts
- 🎙️ **Read + Conv unified** — single folder hierarchy for everything
- 📝 **Transcripts paired with every wav** — `.txt` next to each `.wav`
- 🎚️ **Official splits respected** — time-range based, zero audio leakage between train/dev/test

## 📦 What you get

```
expresso_split_v2/
├── train/{ex01..ex04}/
│   ├── confused/, default/, ...        ← read 7 styles
│   └── conv-angry/, conv-default/, ... ← conv 23~24 styles
├── dev/, test/   (same structure)
├── longform/     (8 long read files + splits.json)
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

## 🔧 Requirements

- **Python ≥ 3.10**
- **~80 GB free disk** (30 GB raw tar + 15 GB parquet + 16 GB output + 17 GB redistributable archive)
- **Internet** (~45 GB download)
- Optional: `aria2c` (parallel download), falls back to `curl`

## ⚙️ Options

```bash
bash setup.sh                 # full pipeline
bash setup.sh --skip-tar      # skip the redistributable tarball
bash setup.sh --tar-only      # only re-create the tarball

PYTHON_BIN=python3.11 bash setup.sh
ROOT=/data/expresso bash setup.sh    # store data elsewhere
```

## 🧩 Data sources

| Component | Source | Notes |
| --- | --- | --- |
| read audio + transcripts | Meta tar (`dl.fbaipublicfiles.com`) | Original 48kHz mono, human transcripts |
| conv audio + transcripts | HuggingFace [`nytopop/expresso-conversational`](https://huggingface.co/datasets/nytopop/expresso-conversational) | Already mono-split + segmented + Parakeet ASR |
| train/dev/test definitions | Meta tar (`splits/*.txt`) | Time-range based |

## 🔬 Pipeline

1. **`build_split.py`** — read processing: extracts read entries from `splits/*.txt`, symlinks into `audio_48khz/`, pairs with transcripts. Files over 30 s (longform) get a separate folder.
2. **`build_conv_split.py`** — conv processing: decodes 36 parquet shards, parses each segment's ID, maps midpoint to a split's time range, writes mono wavs.
3. **Merge** — moves `conv/{split}/…` under `{split}/{speaker}/conv-{style}/` (read keeps plain style names).
4. **Optionally** — `tar czhf` to dereference symlinks and produce a self-contained archive.

## ⚠️ Known limitations

- **Conv transcripts are auto-generated** by Parakeet ASR. Non-verbal styles (`conv-animal`, `conv-nonverbal`) may have nearly meaningless transcripts (e.g., `"Ribbit Ribbit Ribbit"`).
- **Longform transcripts are file-level, not segment-aligned.** Use forced alignment or skip longform when slicing.
- **Speaker leakage exists.** Splits divide audio by time, so every speaker appears in train, dev, and test. Not suitable for unseen-speaker evaluation.

## 📜 License

- Scripts (this repo): **MIT**
- Expresso dataset itself: **CC BY-NC 4.0** (non-commercial)

## 📚 References

- 📄 [EXPRESSO paper](https://arxiv.org/abs/2308.05725)
- 🎧 [Demo page](https://speechbot.github.io/expresso/)
- 🛠️ [Original textlesslib processing code](https://github.com/facebookresearch/textlesslib/tree/main/examples/expresso/dataset)
- 🤗 [`nytopop/expresso-conversational`](https://huggingface.co/datasets/nytopop/expresso-conversational)
- 🎤 [NVIDIA Parakeet TDT 0.6B V2](https://huggingface.co/nvidia/parakeet-tdt-0.6b-v2)

---

Detailed structure, per-style stats, and usage examples in [SETUP.md](SETUP.md).
