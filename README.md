# Expresso One-Type

Meta/Facebook Research의 [Expresso](https://arxiv.org/abs/2308.05725) 데이터셋(read 11h + improvised conversational 33h, 4 화자, 48kHz)을 학습용으로 재구성하는 자동화 파이프라인.

**한 줄로 끝.** 빈 머신에서 `bash setup.sh` 한 번이면 다운로드부터 split 분할, 대본 매칭, 배포용 tarball까지 자동.

## 무엇을 만드나

```
expresso_split_v2/
├── train/{ex01..ex04}/
│   ├── confused/, default/, ...        ← read 7 styles (40분/스타일/화자)
│   └── conv-angry/, conv-default/, ... ← conv 23~24 styles (자동 ASR 대본)
├── dev/   (동일 구조, 약 1.4h)
├── test/  (동일 구조, 약 1.4h)
├── longform/  (8 long read files, 시간 분할 메타 포함)
├── stats.json
└── README.md
```

각 `.wav` 옆에 같은 이름의 `.txt` 페어 (대본).

| split | read | conv | 합계 | 길이 |
| --- | --- | --- | --- | --- |
| train | 10,380 | 29,438 | 39,818 | 41.10 h |
| dev | 628 | 834 | 1,462 | 1.43 h |
| test | 588 | 878 | 1,466 | 1.39 h |
| **GRAND** | **11,596** | **31,150** | **42,754** | **44.26 h** |

## Quick Start

```bash
git clone https://github.com/daewoung/Expresso_one_type.git
cd Expresso_one_type
bash setup.sh
```

요구사항: Python 3.10+, ~80GB 디스크, 인터넷.

상세 설명은 [SETUP.md](SETUP.md) 참고.

## 데이터 출처

- **read 음성/대본**: Meta 공식 tar (`https://dl.fbaipublicfiles.com/textless_nlp/expresso/data/expresso.tar`)
- **conv 음성**: HuggingFace [`nytopop/expresso-conversational`](https://huggingface.co/datasets/nytopop/expresso-conversational) — stereo→mono 분리 + VAD 세그먼트 + Parakeet ASR 자동 대본 까지 처리되어 있음
- **train/dev/test 분할 정의**: Meta 공식 tar 안의 `splits/{train,dev,test}.txt` (시간 범위 기반)

## 라이선스

원본 Expresso 데이터: CC BY-NC 4.0 (비상업).
이 리포지토리의 스크립트만: MIT.

## 참고

- [EXPRESSO 논문 (arXiv 2308.05725)](https://arxiv.org/abs/2308.05725)
- [데모 페이지](https://speechbot.github.io/expresso/)
- [원본 textlesslib 처리 코드](https://github.com/facebookresearch/textlesslib/tree/main/examples/expresso/dataset)
