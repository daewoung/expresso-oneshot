# expresso-oneshot

A reproducible pipeline that turns Meta's [Expresso](https://arxiv.org/abs/2308.05725) dataset (read 11h + improvised conversational 33h, 4 speakers, 48kHz) into a unified, training-ready directory layout with paired transcripts and the official train/dev/test splits applied.

[한국어](README.md)

## Setup

```
git clone https://github.com/daewoung/expresso-oneshot.git
cd expresso-oneshot
bash setup.sh
```

`setup.sh` provisions the venv, installs dependencies, downloads the original Meta tar and the `nytopop/expresso-conversational` parquet shards, builds the splits, and packages the result. The script can be interrupted and re-run safely; completed steps are skipped on subsequent invocations.

Runtime 20–70 min · disk ~80 GB · download ~45 GB.

## Output

```
expresso_split_v2/
├── train/{ex01,ex02,ex03,ex04}/
│   ├── confused/, default/, enunciated/, happy/,
│   │   laughing/, sad/, whisper/                ← read 7 styles
│   └── conv-angry/, conv-default/, …            ← conv 23~24 styles
├── dev/, test/                                  (same structure)
├── longform/                                    (8 long read files + splits.json)
├── stats.json
└── README.md
```

Every `*.wav` has a sibling `*.txt` carrying its transcript.

| split | read | conv | total | duration |
| --- | --- | --- | --- | --- |
| train | 10,380 | 29,438 | 39,818 | 41.10 h |
| dev | 628 | 834 | 1,462 | 1.43 h |
| test | 588 | 878 | 1,466 | 1.39 h |
| longform | — | — | 8 | 0.34 h |
| total | 11,596 | 31,150 | 42,754 | 44.26 h |

## Data sources

| Component | Source | Notes |
| --- | --- | --- |
| read audio + transcripts | Meta tar (`dl.fbaipublicfiles.com/textless_nlp/expresso/data/expresso.tar`) | 48kHz mono, human-written transcripts |
| conv audio + transcripts | HuggingFace [`nytopop/expresso-conversational`](https://huggingface.co/datasets/nytopop/expresso-conversational) | Already mono-split + VAD-segmented + Parakeet TDT ASR transcripts |
| train/dev/test definitions | Meta tar's `splits/{train,dev,test}.txt` | Time-range based |

## Pipeline

1. **`build_split.py`** — extracts read entries from `splits/*.txt`, symlinks them from `audio_48khz/`, and pairs each with its transcript line. Files exceeding 30 s (longform) are routed into `longform/` with a `splits.json` describing the time range each split owns.
2. **`build_conv_split.py`** — decodes 36 parquet shards. Each segment id (`{spk1}-{spk2}_{styles}_{dlg_id}_{start_sample}_{end_sample}`) yields a midpoint that determines its split via the time ranges in `splits/*.txt`. The parquet's authoritative `speaker_id` and `style` columns drive folder placement.
3. **Merge** — moves `expresso_split_v2/conv/{split}/{speaker}/{style}/` → `expresso_split_v2/{split}/{speaker}/conv-{style}/`. Read folders keep plain style names; conv folders carry a `conv-` prefix.
4. **Archive** (optional) — `tar czhf` dereferences the read symlinks so the resulting tarball is self-contained.

## Options

```
bash setup.sh                  # full pipeline
bash setup.sh --skip-tar       # skip the redistributable tarball
bash setup.sh --tar-only       # only re-create the tarball

PYTHON_BIN=python3.11 bash setup.sh
ROOT=/data/expresso bash setup.sh    # store data elsewhere
```

Each step checks for its outputs and is skipped if already complete.

## Intended use

The dataset follows the design of the Expresso paper, which targets expressive speech synthesis and resynthesis on the four speakers (ex01–ex04). Train, dev, and test are time-axis cuts of the same source recordings, so all four speakers appear in every split. Accordingly:

- **Suitable for**: multi-speaker TTS on these four speakers, speaker/style-conditional synthesis, expressive resynthesis. Dev/test serve as training-progress monitors (overfitting checks).
- **Not suitable for**: evaluating generalisation to speakers not seen during training (zero-shot speakers, unseen-speaker ASR). For that scenario the official splits should be ignored and the data re-partitioned by speaker — but with only four speakers, a statistically meaningful evaluation is unlikely.

## Data-quality notes

- Conv transcripts come from automatic ASR (Parakeet TDT), so expect occasional errors. Non-verbal styles (`conv-animal`, `conv-nonverbal`) may carry nearly meaningless transcripts (e.g., `"Ribbit Ribbit Ribbit"`).
- Longform transcripts are file-level, not segment-aligned. Slicing longform audio to the split time-ranges desynchronises the text — apply forced alignment or skip longform.

## License

Scripts in this repository: MIT.
Expresso dataset itself: CC BY-NC 4.0 (non-commercial use only).

## References

- [EXPRESSO paper (arXiv:2308.05725)](https://arxiv.org/abs/2308.05725)
- [Demo page](https://speechbot.github.io/expresso/)
- [Original textlesslib processing code](https://github.com/facebookresearch/textlesslib/tree/main/examples/expresso/dataset)
- [`nytopop/expresso-conversational`](https://huggingface.co/datasets/nytopop/expresso-conversational)
- [NVIDIA Parakeet TDT 0.6B V2](https://huggingface.co/nvidia/parakeet-tdt-0.6b-v2)

See [SETUP.md](SETUP.md) for detailed structure and per-style statistics.
