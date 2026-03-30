# Blog Tracker

네이버 블로그 이웃 글을 RSS로 가져와서 분류하고, 요약해서, 텔레그램으로 보내는 GitHub Actions용 자동화 프로젝트입니다.

## 포함된 기능

- 네이버 블로그 RSS 기반 새 글 수집
- 중복 글 방지용 상태 저장
- 규칙 기반 분류
- OpenAI 기반 선택형 요약
- 텔레그램 메시지 발송
- 팔로잉 목록 텍스트를 `blogs.csv`로 변환하는 import 스크립트
- 네이버 팔로잉 페이지 URL에서 실제 `blogId`를 복구하는 동기화 스크립트
- GitHub Actions 스케줄 실행

## 빠른 시작

```bash
py -3 -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
copy .env.example .env
python scripts/run_tracker.py --dry-run
```

## 설정 파일

블로그 목록은 `config/blogs.csv` 에서 관리합니다.
우선 블로거 목록은 `config/priority_bloggers.txt` 에서 관리합니다.

컬럼:

- `blog_id`: 네이버 블로그 아이디
- `display_name`: 표시명
- `blog_title`: 블로그 제목
- `group_name`: 사용자 그룹
- `relationship`: `이웃` 또는 `서로이웃`
- `enabled`: `true` / `false`
- `rss_url`: 비워두면 `https://rss.blog.naver.com/{blog_id}.xml`
- `notes`: 메모

주의:

- 지금 들어 있는 `config/blogs.csv` 는 예시 시작본입니다.
- 붙여 넣어주신 팔로잉 목록 원문은 `scripts/import_followings.py` 로 CSV로 바꿀 수 있습니다.
- 한글 표시명과 실제 `blog_id` 가 다른 경우가 있으니, RSS가 안 뜨는 항목은 실제 블로그 아이디로 보정해야 합니다.

## 팔로잉 URL에서 자동 동기화

주신 네이버 이웃 페이지 URL처럼 공개로 열리는 경우, 실제 블로그 주소를 자동 수집해서 `blogs.csv`를 만들 수 있습니다.

```bash
python scripts/sync_followings.py --url "https://section.blog.naver.com/connect/ViewMoreFollowings.naver?blogId=neo-anderson&widgetSeq=1306670"
```

이 방식은 한글 닉네임이어도 실제 `blogId`를 링크에서 복구할 수 있어서 가장 추천합니다.

## 팔로잉 목록 텍스트 가져오기

1. 사용자가 복사한 원문을 예를 들어 `data/followings_raw.txt` 로 저장
2. 아래 실행

```bash
python scripts/import_followings.py data/followings_raw.txt
```

그러면 `config/blogs.csv` 가 생성됩니다.

## 환경 변수

- `TELEGRAM_BOT_TOKEN`: 텔레그램 봇 토큰
- `TELEGRAM_CHAT_ID`: 받을 채팅방 ID
- `OPENAI_API_KEY`: 선택, AI 요약용
- `OPENAI_MODEL`: 선택, 예: 사용하는 OpenAI 모델명
- `GEMINI_API_KEY`: 선택, Gemini 요약용
- `GEMINI_MODEL`: 선택, 예: `gemini-2.5-flash`
- `BLOG_TRACKER_TIMEZONE`: 기본 `Asia/Seoul`
- `BLOG_TRACKER_DAYS_BACK`: 최근 며칠 글까지 볼지, 기본 `2`
- `NAVER_FOLLOWINGS_URL`: 기본 팔로잉 동기화 URL

`GEMINI_*` 또는 `OPENAI_*` 가 있으면 AI 요약을 사용하고, 둘 다 없으면 RSS 설명 기반 요약으로 동작합니다.

## GitHub Actions

워크플로 파일은 `.github/workflows/blog-tracker.yml` 입니다.

현재 스케줄:

- 매일 한국시간 오전 7시 실행

GitHub Secrets:

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `OPENAI_API_KEY`
- `OPENAI_MODEL`
- `GEMINI_API_KEY`
- `GEMINI_MODEL`

## GitHub Pages

정적 대시보드는 `docs/` 아래에 있고, 워크플로가 실행될 때 `docs/data/latest.json` 이 갱신됩니다.

페이지 구성:

- 상단 요약 통계
- 우선 블로거 섹션
- 전체 새 글 목록
- 분류 필터와 검색

## 로컬 테스트

```bash
python -m pytest
python scripts/run_tracker.py --dry-run
```

## 출력

- 발송용 리포트: `output/digest_YYYYMMDD_HHMMSS.md`
- 중복 방지 상태: `data/runtime/state.json`
