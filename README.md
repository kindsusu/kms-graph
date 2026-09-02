<p align="center"><img src="assets/hero.svg" alt="KMS Graph" width="100%"></p>

# KMS Graph

직원이 만든 사내 웹앱을 한 곳에 모아 **그래프와 목록으로 보여 주는 정적 페이지**를 만드는 Claude Code 스킬입니다.
직원은 구글 시트나 노션 데이터베이스에 앱을 등록하고, 관리자가 승인하면 하루 한 번 페이지가 다시 만들어져 GitHub Pages에 올라가고 결과가 Teams로 전달됩니다.

## 어떻게 동작하나

```
직원   → 시트 또는 노션에 앱 등록 (사이트명 · URL · 소개 · 도메인 · 참조데이터 · 프롬프트)
관리자 → 승인 체크
build.py
   1. 승인된 행 읽기
   2. 마스터 목록(도메인 · 참조데이터)과 대조, 형식 검증
   3. URL 접속 확인
   4. 전날 결과와 비교해 신규 · 변경 · 삭제 추출
   5. index.html 생성 (데이터 내장, 외부 의존은 vis-network 하나)
   6. git push → GitHub Pages 반영
Claude  → 결과를 읽고 관리자용 요약을 Teams 채널에 전송
```

그래프는 세 종류의 노드로 이루어집니다.

| 노드 | 모양 | 뜻 |
|---|---|---|
| 도메인 | 마름모 | 업무 영역. 사이트를 묶는 기준 |
| 사이트 | 원 | 직원이 만든 웹앱 |
| 참조데이터 | 사각형 | 그 앱이 읽는 시트 · 문서 · 시스템 |

페이지는 목록 탭이 기본이고, 그래프 탭에서 노드를 클릭하면 URL, 소개, 작성자, 도구, 프롬프트, 참조데이터가 오른쪽 패널에 나옵니다. 검색과 도메인 필터는 두 탭이 공유합니다.

마스터 목록에 없는 도메인이나 참조데이터 값이 들어오면 그 행은 "분류 대기"로 빠지고, Claude가 기존 항목에 붙일지 새로 만들지 판단해 `mappings.json`에 근거와 함께 기록합니다. 한 번 정한 값은 다시 묻지 않으며, 그날 분류한 내용은 전부 Teams 메시지에 나옵니다. 관리자는 `mappings.json`이나 원본 값을 고쳐 되돌릴 수 있습니다.

## 설치

필요한 것: Python 3.10 이상, `requests`. 구글 시트를 쓰면 `google-auth`도 필요합니다.

```bash
git clone https://github.com/kindsusu/kms-graph "$HOME/.claude/skills/kms-graph"
pip install requests google-auth
```

Claude Code에서 `/kms-graph`를 입력하면 첫 실행 시 입력원(구글 시트 또는 노션)과 필요한 값을 묻고 `config.json`을 만들어 줍니다. 직접 만들려면 `config.example.json`을 복사해 채웁니다.

## 입력원 준비

### 구글 시트

시트 하나에 탭 세 개를 만듭니다. 탭 이름과 1행 헤더가 아래와 같아야 합니다. `sample/` 폴더의 CSV를 그대로 붙여 넣어 시작해도 됩니다.

- `사이트` 탭: 사이트명 · URL · 소개 · 도메인 · 참조데이터 · 작성자 · 도구 · 프롬프트 · 등록일 · 승인 · 비고
- `도메인` 탭: 도메인명 · 설명 · 색상
- `참조데이터` 탭: 데이터명 · 종류 · 담당팀 · 설명

`승인`은 체크박스로 두고, `도메인`은 데이터 확인 드롭다운으로 `도메인` 탭을 가리키게 합니다. `참조데이터`는 여러 개면 쉼표로 구분합니다. 구글 폼을 `사이트` 탭에 연결하면 직원이 폼으로 등록할 수 있습니다.

읽기 권한은 서비스 계정으로 줍니다. Google Cloud에서 Sheets API를 켜고 서비스 계정 키(JSON)를 만든 뒤, 시트를 그 서비스 계정 이메일에 뷰어로 공유합니다. 키 파일 경로를 `config.json`의 `service_account_json`에 적습니다.

### 노션 데이터베이스

`config.json`의 `source`를 `notion`으로 두고 사이트 데이터베이스 하나를 준비합니다. 속성 이름은 시트 헤더와 같습니다.

| 속성 | 유형 |
|---|---|
| 사이트명 | 제목 |
| URL | URL |
| 도메인 | 선택 (선택지가 도메인 마스터가 됩니다) |
| 참조데이터 | 다중 선택 (선택지가 참조데이터 마스터가 됩니다) |
| 승인 | 체크박스 |
| 소개 · 작성자 · 도구 · 프롬프트 · 비고 | 텍스트 |
| 등록일 | 날짜 |

notion.so/my-integrations에서 읽기 전용 통합을 만들어 토큰을 `notion_token`에 넣고, 데이터베이스 페이지의 연결 메뉴에서 그 통합을 추가합니다. 데이터베이스 ID는 주소의 32자리 값이며 `notion_db_sites`에 넣습니다. 참조데이터의 종류 · 담당팀 · 설명까지 관리하려면 별도 데이터베이스를 만들어 `notion_db_data`에 지정합니다.

## 배포와 알림

- **GitHub Pages**: 페이지용 저장소를 만들어 클론하고 `docs/` 폴더를 커밋한 뒤, Settings > Pages에서 `main` 브랜치의 `/docs`를 지정합니다. 클론 경로를 `repo_dir`에 적습니다.
- **접근 제한**: GitHub Pages는 저장소가 비공개여도 페이지는 공개됩니다. 사내 도메인을 Cloudflare에 연결하고 Zero Trust > Access에서 회사 이메일 도메인만 허용하는 정책을 걸어 두면 회사 계정으로 로그인한 사람만 볼 수 있습니다.
- **Teams**: Power Automate에서 "When a Teams webhook request is received" 트리거와 "Post card in a chat or channel" 동작으로 흐름을 만들고, 생성된 URL을 `teams_webhook`에 넣습니다.

## config.json

```json
{
  "source": "sheets",
  "sheet_id": "",
  "service_account_json": "C:/keys/kms-sheets.json",
  "notion_token": "",
  "notion_db_sites": "",
  "notion_db_data": "",
  "mappings_file": "mappings.json",
  "check_urls": true,
  "repo_dir": "C:/work/kms-pages",
  "out_subdir": "docs",
  "page_url": "https://kms.example.com",
  "teams_webhook": "",
  "site_title": "KMS"
}
```

`config.json`은 깃에 올리지 않습니다. `mappings.json`은 반대로 깃에 올려 보관합니다. 사내망 전용 앱을 외부에서 빌드할 때는 `check_urls`를 `false`로 둡니다.

## 실행

```bash
# 시험 실행 (시트와 저장소를 건드리지 않음)
python build.py --csv-dir sample --out out --no-check-urls

# 실제 갱신과 푸시
python build.py --config config.json --push

# 알림 전송
python build.py --config config.json --notify out/message.md

# 자체 점검
python test_build.py
```

하루 한 번 자동 실행은 두 가지 중 하나를 고릅니다. 관리자 PC의 Claude Code 예약 작업은 사내 URL 접속 확인이 되고 키 파일을 PC에만 두면 되지만 그 시간에 PC가 켜져 있어야 합니다. claude.ai 클라우드 루틴은 PC와 무관하게 돌지만 키와 웹훅을 환경 시크릿으로 등록해야 하고 사내망에는 접속할 수 없습니다.

## 파일

| 파일 | 역할 |
|---|---|
| `SKILL.md` | Claude가 매일 따르는 실행 순서 |
| `build.py` | 읽기 · 검증 · 접속 확인 · 비교 · 렌더 · 푸시 · 알림 |
| `template.html` | 페이지 원본 |
| `config.example.json` | 설정 예시 |
| `sample/` | 시험용 CSV와 매핑 예시 |
| `test_build.py` | 자체 점검 |

## 라이선스

PolyForm Noncommercial 1.0.0. 개인 · 비영리 · 교육 · 연구 목적은 무료이며 상업적 이용은 제한됩니다.
