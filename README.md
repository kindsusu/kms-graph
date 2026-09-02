<p align="center"><img src="assets/hero.svg" alt="kms-graph: 그래프와 목록으로 보는 사내 지식 지도" width="100%"></p>

# kms-graph 설치 안내

직원이 만든 사내 웹앱을 구글 시트나 노션 데이터베이스에 등록하면, 하루 한 번 그래프 + 목록 페이지를
다시 만들어 GitHub Pages 로 올리고 Teams 로 결과를 알린다.

필요한 것: Python 3.10 이상, `requests` (노션만 쓸 경우 이것뿐), 구글 시트를 쓸 경우 `google-auth`.

입력원은 둘 중 하나를 고른다. `config.json` 의 `"source"` 가 `"sheets"` 면 1~2장, `"notion"` 이면 1-N장을 따른다.

---

## 1. 구글 시트 만들기

시트 하나에 탭 3개를 만든다. **탭 이름과 1행 헤더 이름이 정확히 같아야 한다.**

**`사이트` 탭** (직원이 등록하는 곳)

| 사이트명 | URL | 소개 | 도메인 | 참조데이터 | 작성자 | 도구 | 프롬프트 | 등록일 | 승인 | 비고 |
|---|---|---|---|---|---|---|---|---|---|---|

- `승인`: 삽입 > 체크박스. 체크된 행만 페이지에 나온다. (`TRUE`, `예`, `Y`, `✓` 도 승인으로 본다)
- `도메인`: 데이터 > 데이터 확인 > 목록(범위) 로 `도메인!A2:A` 를 가리키게 한다.
- `참조데이터`: 여러 개면 쉼표, 세미콜론, 줄바꿈으로 구분한다. 값은 `참조데이터` 탭에 있는 이름이어야 한다.
- 구글 폼을 만들어 응답 대상 시트를 이 탭으로 연결하면 직원이 폼으로 등록할 수 있다.
  폼에는 `승인` 항목을 두지 않는다. 관리자가 시트에서 직접 체크한다.

**`도메인` 탭**

| 도메인명 | 설명 | 색상 |
|---|---|---|

- `색상`은 `#4F86C6` 형식. 비워 두면 기본 팔레트에서 자동으로 채운다.

**`참조데이터` 탭**

| 데이터명 | 종류 | 담당팀 | 설명 |
|---|---|---|---|

형식은 `sample/` 폴더의 CSV 3개와 같다. 그대로 시트에 붙여 넣어 시작해도 된다.

## 2. 구글 클라우드 서비스 계정

1. console.cloud.google.com 에서 프로젝트를 만들거나 고른다.
2. **API 및 서비스 > 라이브러리 > Google Sheets API > 사용**.
3. **API 및 서비스 > 사용자 인증 정보 > 서비스 계정 만들기**. 역할은 없어도 된다.
4. 만든 서비스 계정 > 키 > 키 추가 > JSON. 내려받은 파일을 PC의 안전한 경로에 둔다.
   이 파일은 저장소나 볼트에 올리지 않는다.
5. 시트를 열고 **공유**에서 서비스 계정 이메일(`...@....iam.gserviceaccount.com`)을 **뷰어**로 추가한다.

## 1-N. 노션에서 읽기 (구글 시트 대신)

노션을 쓰면 1장, 2장 대신 여기만 하면 된다. `config.json` 에 `"source": "notion"` 을 넣는다.

**(a) 통합(integration) 만들기**

1. [notion.so/my-integrations](https://www.notion.so/my-integrations) > **New integration**.
2. 워크스페이스를 고르고 이름을 정한다. 권한은 **Read content** 만 있으면 된다.
3. **Internal Integration Secret** (`secret_...` 또는 `ntn_...`) 을 복사해 `config.json` 의 `notion_token` 에 넣는다.
4. **데이터베이스를 통합에 공유해야 한다.** 데이터베이스 페이지 우상단 `...` > **연결 > (만든 통합 이름)**.
   이걸 안 하면 API 가 404 를 돌려준다. 데이터베이스가 두 개면 둘 다 공유한다.

**(b) 데이터베이스 ID**

데이터베이스를 전체 페이지로 열었을 때 주소가 이렇다.

```
https://www.notion.so/myteam/1f2e3d4c5b6a7890abcdef1234567890?v=...
                            └────────── 이 32자리가 데이터베이스 ID ──────────┘
```

`?v=` 앞의 32자리(하이픈이 있어도 된다)를 `notion_db_sites` 에 넣는다.
사이드바에서 인라인 데이터베이스를 쓰고 있다면 `...` > **Open as full page** 로 연 뒤 주소를 본다.

**(c) 사이트 데이터베이스 속성** — 이름이 시트 헤더와 똑같아야 한다.

| 속성 이름 | 노션 속성 유형 | 비고 |
|---|---|---|
| 사이트명 | 제목(Title) | 필수 |
| URL | URL | 필수 |
| 소개 | 텍스트(Text) | |
| 도메인 | 선택(Select) | **선택지 목록이 도메인 마스터가 된다** |
| 참조데이터 | 다중 선택(Multi-select) | **선택지 목록이 참조데이터 마스터가 된다** |
| 작성자 | 텍스트 | |
| 도구 | 텍스트 | |
| 프롬프트 | 텍스트 | |
| 등록일 | 날짜(Date) | 시작일만 쓴다 |
| 승인 | 체크박스(Checkbox) | **필수.** 체크된 행만 페이지에 나온다 |
| 비고 | 텍스트 | |

`사이트명`, `URL`, `승인` 이 없으면 빌드가 그 자리에서 멈춘다. 나머지는 없어도 빈 값으로 넘어간다.
사람 속성(Person)이나 관계형(Relation)은 읽지 않는다. 작성자는 텍스트로 둔다.

**(d) 참조데이터 상세를 따로 관리하고 싶을 때 (선택)**

다중 선택 선택지만으로는 `종류`·`담당팀`·`설명` 을 담을 수 없다. 필요하면 데이터베이스를 하나 더 만들고
`notion_db_data` 에 그 ID 를 넣는다. 속성은 `데이터명`(제목), `종류`(선택 또는 텍스트),
`담당팀`(텍스트), `설명`(텍스트). 이름이 같은 항목끼리 합쳐진다.

**(e) 도메인 색상**

노션 선택지 색을 그대로 쓴다. `blue #4F86C6`, `green #4C9A6A`, `red #C8553D`, `orange #E08E45`,
`yellow #D4B13F`, `purple #7A5CA8`, `pink #C86B98`, `brown #8B6A4E`, `gray`·`default` `#7A8B99`.
색을 고르고 싶으면 노션에서 선택지 색을 바꾸면 된다.

## 3. GitHub 저장소와 Cloudflare Access

1. 페이지용 저장소를 만들고 PC에 클론한다. (예: `C:/work/kms-pages`)
2. 저장소에 `docs/` 폴더를 만들고 커밋한다. 빌드 결과가 여기에 쌓인다.
3. 저장소 **Settings > Pages > Source: Deploy from a branch**, 브랜치 `main`, 폴더 `/docs`.
4. 사내 도메인을 쓸 경우 Cloudflare 에 사이트를 등록하고 Pages 주소로 CNAME 을 건다.
5. 접근 제한: **Cloudflare Zero Trust > Access > Applications > Add an application (Self-hosted)**.
   도메인을 지정하고 정책을 하나 만든다. Action `Allow`, Include `Emails ending in` = 회사 도메인.
   이후 회사 계정으로 로그인한 사람만 페이지를 볼 수 있다.
6. `git push` 가 비밀번호를 묻지 않도록 미리 인증을 끝내 둔다. (GitHub CLI 로그인 또는 자격 증명 관리자)

## 4. Teams 알림

1. Power Automate 에서 흐름을 새로 만든다.
2. 트리거: **When a Teams webhook request is received**. 저장하면 HTTP POST URL 이 생긴다.
3. 동작: **Post card in a chat or channel**. 게시자 `Flow bot`, 대상은 관리자 채널.
   Adaptive Card 본문에 트리거 본문(`triggerBody()`)을 그대로 넣는다.
4. 저장하고 URL 을 복사해 `config.json` 의 `teams_webhook` 에 넣는다.

## 5. config.json

`config.example.json` 을 `config.json` 으로 복사하고 채운다.

```json
{
  "source": "sheets",
  "sheet_id": "구글 시트 URL 의 /d/ 와 /edit 사이 값",
  "service_account_json": "C:/keys/kms-sheets.json",
  "notion_token": "",
  "notion_db_sites": "",
  "notion_db_data": "",
  "mappings_file": "mappings.json",
  "check_urls": true,
  "repo_dir": "C:/work/kms-pages",
  "out_subdir": "docs",
  "page_url": "https://kms.example.com",
  "teams_webhook": "https://prod-00.westus.logic.azure.com/...",
  "site_title": "KMS"
}
```

노션을 쓰면 `"source": "notion"` 으로 바꾸고 `notion_token` / `notion_db_sites` 를 채운다.
`sheet_id` 와 `service_account_json` 은 비워 두면 된다. 한 번만 반대로 돌려 보려면 `--source notion` 을 붙인다.

출력 폴더는 `repo_dir/out_subdir` 이다. `config.json` 은 깃에 올리지 않는다. (스킬 폴더의 `.gitignore` 에 이미 들어 있다)
`mappings.json` 은 반대로 **깃에 올려서 보관한다.** 지우면 분류를 처음부터 다시 묻게 된다.

## 5-N. Claude 분류와 mappings.json

`도메인` 과 `참조데이터` 는 **마스터 목록이 기준**이다. 직원이 마스터에 없는 값을 적거나 도메인을 비워 두면
예전에는 그 행 전체가 오류로 빠졌다. 지금은 이렇게 돈다.

1. 빌드가 마스터에 없는 값을 모아 출력 폴더의 `unmatched.json` 에 쓴다. 그 행은 "분류 대기" 로 페이지에서 빠진다.
2. Claude 가 `unmatched.json` 과 마스터 목록을 읽고 항목마다 정한다.
   뜻이 같은 항목이 마스터에 있으면 그쪽으로 보내고(`to`), 정말 없을 때만 새 마스터 항목을 만든다(`new`).
   도메인이 빈 사이트는 `소개` 를 읽고 도메인을 고른다.
3. 결정이 `mappings.json` 에 쌓인다. **한 번 정하면 다시 묻지 않는다.**
4. 빌드를 다시 돌리면 매핑이 검증 **전에** 적용되어 그 행이 정상 처리된다.
5. Claude 가 만든 마스터 항목은 페이지에서 `Claude 분류` 라는 회색 표시가 붙는다.
   그날 한 분류는 전부 Teams 메시지에 나온다.

`mappings.json` 한 항목의 모양은 이렇다. 전체 예시는 `sample/mappings.example.json`.

```json
{
  "도메인": { "HR": {"to": "인사", "why": "인사 업무 영역 약어", "by": "claude", "date": "2026-09-02"} },
  "참조데이터": {
    "인사규정 노션": {"to": "그룹웨어 사규 PDF", "why": "같은 사규 원문의 노션 사본", "by": "claude", "date": "2026-09-02"},
    "비품 사진 폴더": {"new": {"데이터명": "구글드라이브 비품사진 폴더", "종류": "구글드라이브",
                          "담당팀": "총무팀", "설명": "비품 사진 공유 폴더"},
                  "why": "맞는 항목 없음", "by": "claude", "date": "2026-09-02"}
  },
  "사이트도메인": { "회의록 요약기": {"to": "경영", "why": "소개문 기준", "by": "claude", "date": "2026-09-02"} }
}
```

**되돌리는 법 (관리자)**

- 분류가 틀렸다 → `mappings.json` 에서 그 항목의 `to` / `new` 를 고치거나 통째로 지운다. 지우면 다음 빌드에서 다시 묻는다.
- 애초에 값이 잘못 적혔다 → 시트나 노션에서 값을 마스터에 있는 이름으로 고친다. 이쪽이 더 깔끔하다.
- 사람이 정한 것으로 확정하고 싶다 → `"by"` 를 `"admin"` 으로 바꾼다. Teams 메시지에서 빠지고 Claude 도 손대지 않는다.

## 6. 하루 한 번 실행하기

하루 한 번 도는 흐름은 이렇다.

1. 빌드 (`build.py --config config.json --push`) — 시트/노션을 읽고 매핑을 적용해 페이지를 만든다
2. `unmatched.json` 이 비어 있지 않으면 Claude 가 분류해 `mappings.json` 에 넣고 **1번을 다시 실행**한다
3. `report.json` 을 보고 관리자용 메시지를 쓴다 (그날 한 Claude 분류 포함)
4. Teams 로 보낸다

**(a) 관리자 PC 의 Claude Code 데스크톱 예약 작업 — 사내망 전용 앱이면 이쪽을 권한다**

- 프롬프트: `kms-graph 스킬로 KMS 페이지를 갱신하고 결과를 Teams 로 알려줘`
- 장점: 사내 URL 접속 확인이 되고, 키 파일과 토큰을 PC 에만 두면 된다.
- 조건: 그 시간에 PC 가 켜져 있고 Claude Code 가 실행 중이어야 한다.
- `mappings.json` 이 이 PC 에만 쌓인다. 스킬 폴더를 깃으로 관리하면 다른 PC 와 맞출 수 있다.

**(b) claude.ai 클라우드 루틴**

- 서비스 계정 키 JSON(또는 노션 토큰)과 웹훅 URL 을 클라우드 환경 시크릿으로 등록해야 한다.
- 사내망(`*.internal`)에는 접속할 수 없으므로 `"check_urls": false` 로 둔다.
- PC 전원과 무관하게 돈다. 앱이 모두 외부에서 접속 가능한 주소면 이쪽이 편하다.

## 7. 수동 실행

```powershell
# 시험 실행 (시트/저장소 안 건드림)
python build.py --csv-dir sample --out out --no-check-urls

# 실제 갱신 + 푸시
python build.py --config config.json --push

# 입력원을 이번만 바꿔서
python build.py --config config.json --source notion --no-push

# 알림만 다시 보내기
python build.py --config config.json --notify out/message.md

# 자체 점검
python test_build.py
```

`--csv-dir` 로 만든 결과는 `out/` 에 남는다. 이 폴더는 깃 추적에서 빼 두었다.

## 함정

- **PowerShell 5.1 에는 `&&` 가 없다.** 명령을 이어 붙일 때는 `;` 를 쓴다.
- **접속 확인은 실행 위치를 탄다.** 사내 주소는 사내망에서 돌릴 때만 확인된다.
  클라우드에서 돌리면 전부 접속 불가로 뜨므로 `check_urls` 를 `false` 로 둔다.
- **Sheets API 할당량**: 분당 읽기 제한이 있다. 하루 한 번 실행은 문제없지만
  디버깅으로 연달아 돌릴 때는 `--csv-dir sample` 을 쓴다.
- **체크박스 값**: 구글 시트 체크박스는 `TRUE`/`FALSE` 로 읽힌다. 체크박스 대신 손으로
  `예`, `Y`, `✓` 를 적어도 승인으로 처리한다. 그 외 값은 전부 미승인이다.
- **Cloudflare Access 쿠키는 만료된다.** 오래 안 들어가면 다시 로그인 창이 뜬다.
  링크를 눌렀는데 회사 로그인이 나오면 정상이다.
- **사이트명이 키다.** 시트에서 사이트명을 바꾸면 신규 등록 1건 + 삭제 1건으로 잡힌다.
  `mappings.json` 의 `사이트도메인` 도 사이트명으로 걸려 있으므로 이름을 바꾸면 그 매핑이 죽는다.
- **참조데이터 이름 오타는 그 행을 "분류 대기" 로 뺀다.** 오류가 아니라 `unmatched.json` 으로 간다.
  Claude 가 매핑을 만들면 다음 빌드에서 들어온다. 오타 자체는 시트/노션에서 고치는 게 낫다.
- **노션 통합에 DB 를 공유하지 않으면 404 가 뜬다.** 토큰이 맞아도 그렇다. `...` > 연결 에서 통합을 붙인다.
  데이터베이스가 두 개(`notion_db_sites`, `notion_db_data`)면 둘 다 붙여야 한다.
- **노션 API 는 초당 3회 제한이 있다.** 하루 한 번 실행은 문제없지만, 페이지가 수백 개로 늘거나
  디버깅으로 연달아 돌리면 429 가 뜬다. 그럴 때는 `--csv-dir sample` 로 시험한다.
- **노션 도메인 색은 선택지 색이 그대로 온다.** 마음에 안 들면 노션에서 선택지 색을 바꾼다.
  `색상` 텍스트 속성을 만들어 봐야 읽지 않는다. 색을 직접 지정하려면 구글 시트를 쓴다.
- **다중 선택 선택지 이름에 쉼표를 넣지 않는다.** 참조데이터를 쉼표로 쪼개므로 하나가 둘로 갈린다.
- **`mappings.json` 은 지우면 안 된다.** 지우면 분류를 전부 다시 하게 되고, Claude 가 지난번과 다르게
  판단할 수 있다. `config.json` 과 달리 깃에 올려 둔다.
