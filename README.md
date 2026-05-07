# expresso-oneshot

Meta의 [Expresso](https://arxiv.org/abs/2308.05725) 데이터셋(read 11h + improvised conversational 33h, 4 화자, 48kHz)을 학습용 단일 디렉토리 구조로 재구성하는 자동화 스크립트.

[English](README.en.md)

## 설치 및 실행

```
git clone https://github.com/daewoung/expresso-oneshot.git
cd expresso-oneshot
bash setup.sh
```

`setup.sh`가 venv 생성, 의존성 설치, 원본 tar 다운로드, `nytopop/expresso-conversational` 다운로드, 빌드, 압축까지 처리한다. 중간에 끊어도 같은 명령으로 이어서 진행할 수 있다.

소요 시간 20–70분, 디스크 ~80 GB, 다운로드 ~45 GB.

## 결과물

```
expresso_split_v2/
├── train/{ex01,ex02,ex03,ex04}/
│   ├── confused/, default/, enunciated/, happy/,
│   │   laughing/, sad/, whisper/                ← read 7 styles
│   └── conv-angry/, conv-default/, …            ← conv 23~24 styles
├── dev/, test/                                  (동일 구조)
├── longform/                                    (8 long read files + splits.json)
├── stats.json
└── README.md
```

각 `*.wav` 옆에 같은 이름의 `*.txt`가 페어로 존재한다.

| split | read | conv | 합계 | 길이 |
| --- | --- | --- | --- | --- |
| train | 10,380 | 29,438 | 39,818 | 41.10 h |
| dev | 628 | 834 | 1,462 | 1.43 h |
| test | 588 | 878 | 1,466 | 1.39 h |
| longform | — | — | 8 | 0.34 h |
| 총합 | 11,596 | 31,150 | 42,754 | 44.26 h |

## 데이터 출처

| 구성 | 출처 | 비고 |
| --- | --- | --- |
| read 오디오 + 대본 | Meta 공식 tar (`dl.fbaipublicfiles.com/textless_nlp/expresso/data/expresso.tar`) | 48kHz mono, 사람이 작성한 대본 |
| conv 오디오 + 대본 | HuggingFace [`nytopop/expresso-conversational`](https://huggingface.co/datasets/nytopop/expresso-conversational) | stereo→mono 분리, VAD 세그먼트, Parakeet TDT ASR 자동 대본 |
| train/dev/test 정의 | Meta tar 내 `splits/{train,dev,test}.txt` | 시간 범위 기반 |

## 처리 파이프라인

1. **`build_split.py`** — read 항목 추출 후 `audio_48khz/`로 symlink, 대본 매칭. 30초 초과(longform)는 `longform/`으로 분리.
2. **`build_conv_split.py`** — parquet shard 36개 디코드. 각 segment의 ID(`{spk1}-{spk2}_{styles}_{dlg_id}_{start_sample}_{end_sample}`)에서 시간 정보 추출 후, midpoint가 `splits/*.txt`의 어느 시간 구간에 속하는지로 split 결정. parquet의 `speaker_id`와 `style` 컬럼을 그대로 폴더 분류에 사용.
3. **병합** — `expresso_split_v2/conv/{split}/{speaker}/{style}/`를 `expresso_split_v2/{split}/{speaker}/conv-{style}/`로 이동. read 폴더는 prefix 없이, conv 폴더는 `conv-` prefix.
4. **압축** (선택) — `tar czhf`로 symlink dereference하여 self-contained tarball 생성.

## 옵션

```
bash setup.sh                  # 전체 파이프라인
bash setup.sh --skip-tar       # tarball 생성 생략
bash setup.sh --tar-only       # 빌드된 폴더로 tarball만 재생성

PYTHON_BIN=python3.11 bash setup.sh
ROOT=/data/expresso bash setup.sh    # 데이터 저장 위치 변경
```

각 단계는 결과물 존재 여부를 확인하고 이미 완료된 단계는 건너뛴다.

## 한계

- conv 대본은 ASR 자동 생성이라 일부 오류가 있다. 비언어적 스타일(`conv-animal`, `conv-nonverbal`)은 대본이 거의 무의미할 수 있다 (예: `"Ribbit Ribbit Ribbit"`).
- longform 대본은 파일 단위 전체 텍스트로, segment 시간과 정렬되어 있지 않다. 시간 단위로 자르면 텍스트가 일치하지 않으므로 forced alignment를 별도로 적용하거나 longform을 학습에서 제외해야 한다.
- train/dev/test는 같은 원본 wav를 시간 구간으로 나눈 것이므로, 4 화자 모두가 세 split에 동시에 등장한다. 이는 폴더 구조상 화자가 잘못 섞여 있다는 의미가 아니라(화자 라벨은 정확하다), 동일 화자의 음향 특성이 train과 test 양쪽에 노출된다는 뜻이다. 화자 일반화 평가에는 부적합하지만, 표현형 합성·리신서시스처럼 4 화자 모델을 만들 때는 의도된 설계이다.

## 라이선스

스크립트(이 리포지토리): MIT.
Expresso 데이터셋: CC BY-NC 4.0 (비상업 한정).

## 참고

- [EXPRESSO 논문 (arXiv:2308.05725)](https://arxiv.org/abs/2308.05725)
- [데모](https://speechbot.github.io/expresso/)
- [원본 textlesslib 처리 코드](https://github.com/facebookresearch/textlesslib/tree/main/examples/expresso/dataset)
- [`nytopop/expresso-conversational`](https://huggingface.co/datasets/nytopop/expresso-conversational)
- [NVIDIA Parakeet TDT 0.6B V2](https://huggingface.co/nvidia/parakeet-tdt-0.6b-v2)

폴더 구조와 통계 상세는 [SETUP.md](SETUP.md) 참조.
