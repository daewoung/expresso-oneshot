# Expresso Split v2 — One-shot Setup

다른 머신에서 처음부터 자동으로 재현하기.

## Quick Start

```bash
# 깃 리포지토리에서 클론한 폴더 안으로 들어간 뒤:
bash setup.sh
```

이 한 줄이 다음을 모두 처리:

1. `python3 -m venv .venv` (Python 3.10+)
2. pip 의존성 설치 (`huggingface_hub`, `hf_transfer`, `pyarrow`, `pandas`, `soundfile`, `tqdm`)
3. **Expresso 원본 tar 다운로드** (~30GB) → `audio_48khz/`, `splits/`, `read_transcriptions.txt` 추출
   - URL: `https://dl.fbaipublicfiles.com/textless_nlp/expresso/data/expresso.tar`
4. **HuggingFace nytopop/expresso-conversational 다운로드** (~14.8GB parquet)
5. read 처리 (symlink + .txt 페어)
6. conv 처리 (parquet → wav + .txt, splits 시간 매칭)
7. conv를 메인 split 폴더로 병합 (`conv-` prefix)
8. 배포용 tarball 생성 (`expresso_split_v2.tar.gz`, ~17GB, dereferenced)

## Requirements

- **Python 3.10+** (`PYTHON_BIN` 환경변수로 override 가능)
- **디스크 공간 ~80GB** (원본 tar 30GB + nytopop 15GB + 결과 16GB + tarball 17GB)
- **인터넷** (총 ~45GB 다운로드)
- 선택: `aria2c` (있으면 8커넥션 병렬 다운로드, 없으면 curl 단일 연결)

## Options

```bash
bash setup.sh              # 전체 파이프라인
bash setup.sh --skip-tar   # tarball 안 만듦 (학습용 폴더만)
bash setup.sh --tar-only   # 폴더 빌드 끝나 있을 때 tarball만 다시
```

## 환경변수

```bash
PYTHON_BIN=python3.11 bash setup.sh    # Python 인터프리터 지정
ROOT=/data/expresso bash setup.sh      # 작업 디렉토리 지정 (기본: 스크립트 위치)
OUT_DIR=/data/exp_v2 bash setup.sh     # 출력 폴더 지정 (기본: $ROOT/expresso_split_v2)
```

## 멱등성 (idempotency)

모든 단계가 멱등 — 중간에 끊겨도 같은 명령 다시 치면 이어서 진행:

| 단계 | 스킵 조건 |
| --- | --- |
| 1. venv | `.venv/bin/python` 존재 |
| 3. expresso.tar 다운/풀기 | `audio_48khz/` + `read_transcriptions.txt` 존재 |
| 4. nytopop 다운로드 | `nytopop_expresso_conv/conversational/*.parquet` 비어 있지 않음 |
| 5-7. 빌드 | 빌더 스크립트 자체가 멱등 (이미 만든 파일은 덮어쓰지 않거나 그대로 유지) |
| 8. tarball | `expresso_split_v2.tar.gz` 존재 |

## 예상 소요 시간

| 단계 | 시간 (네트워크/CPU 따라) |
| --- | --- |
| 다운로드 expresso.tar (30GB) | 5~30분 |
| 압축 해제 | 5~10분 |
| nytopop 다운로드 (14.8GB) | 3~10분 (hf_transfer 사용) |
| read 빌드 (symlink) | <10초 |
| conv 빌드 (31k 파일 쓰기) | 1~3분 |
| conv 병합 | <1초 |
| tarball (17GB, gzip) | 5~15분 |

총 **20~70분** 정도.

## 파일 구성 (이 리포지토리에 있어야 할 것)

```
expresso/
├── setup.sh                  ← 이 한 파일이 진입점
├── SETUP.md                  ← 이 문서
├── build_split.py            ← read 빌더 (env var 기반 경로)
├── build_conv_split.py       ← conv 빌더 (env var 기반 경로)
└── (스크립트 실행 시 생성됨)
    ├── .venv/
    ├── audio_48khz/          ← expresso.tar에서
    ├── splits/
    ├── read_transcriptions.txt
    ├── VAD_segments.txt
    ├── nytopop_expresso_conv/
    ├── expresso_split_v2/    ← 결과물
    └── expresso_split_v2.tar.gz
```

## 다른 머신으로 옮길 때

옵션 1: **결과물(tarball)만 전달**
```bash
# 받는 쪽
tar xzf expresso_split_v2.tar.gz
# 끝. 학습 코드에서 expresso_split_v2/ 사용
```

옵션 2: **소스부터 자동 빌드**
```bash
# 받는 쪽 (아무것도 없는 머신)
git clone <repo-url> expresso && cd expresso
bash setup.sh
```

옵션 1이 빠름 (다운로드 17GB만), 옵션 2가 깨끗함 (자체 검증 가능).
