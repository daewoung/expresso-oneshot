<div align="center">

# Expresso One-Shot

**Zero to a training-ready Expresso dataset in one command.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Dataset: CC BY-NC 4.0](https://img.shields.io/badge/Dataset-CC%20BY--NC%204.0-orange.svg)](https://creativecommons.org/licenses/by-nc/4.0/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![Paper](https://img.shields.io/badge/arXiv-2308.05725-b31b1b.svg)](https://arxiv.org/abs/2308.05725)

[English](README.en.md) · 한국어

</div>

---

Meta의 [Expresso 데이터셋](https://arxiv.org/abs/2308.05725) (read 11h + improvised conversational 33h, 4 화자, 48kHz)을 학습용으로 한 번에 정리해주는 자동화 파이프라인. 다운로드부터 train/dev/test 분할, 대본 매칭, 배포용 tarball까지 **명령 한 줄**.

## ⚡ Quick Start

```bash
git clone <YOUR_REPO_URL>
cd <REPO_DIR>
bash setup.sh
```

20–70분 후 학습용 데이터셋 완성. 디스크 ~80GB, 인터넷 ~45GB.

## 🎯 Features

- 🚀 **One-command setup** — venv, 의존성, 다운로드, 빌드까지 자동
- 🔁 **멱등성** — 중간에 끊겨도 같은 명령 다시 치면 이어서 진행
- 📦 **Self-contained tarball** — symlink dereferenced, 받는 사람은 풀기만 하면 됨
- 🎙️ **Read + Conv 통합** — 한 폴더 구조로 모든 데이터에 균일하게 접근
- 📝 **모든 wav에 대본 페어링** — `.wav` 옆에 `.txt`
- 🎚️ **공식 splits 사용** — train/dev/test 시간 범위 정의 그대로 적용 (audio leakage 0)

## 📦 결과물

```
expresso_split_v2/
├── train/{ex01..ex04}/
│   ├── confused/, default/, ...        ← read 7 styles
│   └── conv-angry/, conv-default/, ... ← conv 23~24 styles
├── dev/, test/   (동일 구조)
├── longform/     (8 long read files + splits.json)
├── stats.json
└── README.md
```

각 `.wav` 옆에 같은 이름의 `.txt` 페어.

| split | read | conv | 합계 | 길이 |
| --- | --- | --- | --- | --- |
| train | 10,380 | 29,438 | **39,818** | **41.10 h** |
| dev | 628 | 834 | 1,462 | 1.43 h |
| test | 588 | 878 | 1,466 | 1.39 h |
| longform | — | — | 8 | 0.34 h |
| **GRAND** | **11,596** | **31,150** | **42,754** | **44.26 h** |

## 🔧 Requirements

- **Python 3.10+**
- **디스크 ~80 GB** (원본 30GB + 중간 15GB + 결과 16GB + tarball 17GB)
- **인터넷 ~45GB 다운로드**
- 선택: `aria2c` (병렬 다운로드)

## ⚙️ Options

```bash
bash setup.sh                 # 전체 파이프라인
bash setup.sh --skip-tar      # tarball 건너뛰기
bash setup.sh --tar-only      # tarball만 다시 만들기

# 환경변수로 경로/Python 지정
PYTHON_BIN=python3.11 bash setup.sh
ROOT=/data/expresso bash setup.sh        # 데이터 저장 위치 변경
```

## 🧩 데이터 출처

| 구성 | 출처 | 비고 |
| --- | --- | --- |
| read 오디오·대본 | Meta 공식 tar (`dl.fbaipublicfiles.com`) | 원본 48kHz mono |
| conv 오디오·대본 | HuggingFace [`nytopop/expresso-conversational`](https://huggingface.co/datasets/nytopop/expresso-conversational) | stereo→mono 분리·세그먼트 완료, ASR 대본 (Parakeet TDT) |
| train/dev/test 정의 | Meta tar의 `splits/*.txt` | 시간 범위 기반 |

## 🔬 처리 파이프라인

1. **`build_split.py`** — read 처리: `splits/*.txt`에서 read 항목 추출 → `audio_48khz/`로 symlink + 대본 매칭. 30초 초과 longform은 별도 폴더.
2. **`build_conv_split.py`** — conv 처리: 36개 parquet shard → 각 segment의 ID 파싱 → midpoint가 `splits/*.txt`의 어느 시간 구간에 속하는지로 split 결정 → mono wav 저장.
3. **병합** — `conv/{split}/...` 트리를 `{split}/{speaker}/conv-{style}/`로 통합 (read는 prefix 없음).
4. **(선택) 압축** — `tar czhf`로 symlink 풀어서 self-contained tarball 생성.

## ⚠️ 알려진 한계

- **conv 대본은 ASR 자동 생성** — 일부 오류 가능. 비언어적 스타일(`conv-animal`, `conv-nonverbal`)은 의미 없는 대본일 수 있음.
- **longform 대본은 segment-aligned가 아님** — 전체 텍스트만 있음. forced alignment 필요.
- **화자 leakage 존재** — 공식 splits가 시간 분할 기반이라 모든 화자가 train/dev/test 모두에 등장. unseen-speaker 평가에는 부적합.

## 📜 License

- 스크립트(이 리포지토리): **MIT**
- Expresso 데이터셋 자체: **CC BY-NC 4.0** (비상업 only)

## 📚 References

- 📄 [EXPRESSO 논문](https://arxiv.org/abs/2308.05725)
- 🎧 [데모 페이지](https://speechbot.github.io/expresso/)
- 🛠️ [원본 textlesslib 처리 코드](https://github.com/facebookresearch/textlesslib/tree/main/examples/expresso/dataset)
- 🤗 [`nytopop/expresso-conversational`](https://huggingface.co/datasets/nytopop/expresso-conversational)
- 🎤 [NVIDIA Parakeet TDT 0.6B V2](https://huggingface.co/nvidia/parakeet-tdt-0.6b-v2)

---

상세 구조·통계·사용 예제는 [SETUP.md](SETUP.md) 참조.
