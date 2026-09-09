# Cloudflare 정적 배포

이 프로젝트는 읽기 전용 정적 사이트다. Google Sheets 또는 Notion 원본은 `build.py`가 읽기만 하며 Cloudflare에는 검증된 `out/`만 게시한다. 서버 API, D1, R2, 로그인 기능은 포함하지 않는다.

## 준비

Node.js 22.12 이상과 Python 3.10 이상을 준비하고 저장소 루트에서 의존성을 설치한다.

```powershell
npm ci
npm --prefix frontend ci
python -m pip install -r requirements.txt
```

`config.example.json`을 `config.json`으로 복사한다. `repo_dir`은 현재 저장소의 정확한 절대 경로, `out_subdir`은 반드시 `out`으로 설정한다.

```json
{
  "repo_dir": "C:/absolute/path/to/kms-graph",
  "out_subdir": "out"
}
```

같은 파일에서 `source`와 해당 Sheets 또는 Notion 읽기 설정을 채운다. 실제 자격 증명 값은 이 문서나 Git에 기록하지 않는다. `config.json`이 없거나 출력 경로가 다르면 운영 빌드는 어떤 빌드도 시작하기 전에 실패한다.

## 운영 빌드와 사전 검증

```powershell
npm run build
```

이 명령은 다음 순서로 중단 우선 실행된다.

1. `config.json`과 정확한 `repo_dir/out_subdir`을 확인한다.
2. 프런트엔드를 빌드한다.
3. `python build.py --config config.json --no-push`를 실행한다.
4. `out/`에 schemaVersion 2 데이터가 포함되었는지, HTML이 참조한 자산이 존재하는지, 심볼릭 링크·관리 파일·알 수 없는 최상위 파일이 없는지 검사한다.

어느 단계든 실패하면 뒤 단계는 실행하지 않는다. 검증기는 파일을 삭제하거나 수정하지 않는다.

로컬 구조와 Cloudflare 패키징만 확인하려면 다음을 실행한다.

```powershell
npm run deploy:dry-run
```

이 명령은 현재 `out/`을 다시 검증한 뒤 `wrangler deploy --dry-run`을 실행하며 원격 게시를 하지 않는다. 샘플 UI만 확인할 때는 별도의 `npm run sample:build`를 사용한다. 샘플 출력은 운영 배포 자료로 간주하지 않는다.

## 배포

Cloudflare 계정과 정적 사이트 대상이 올바른지 확인한 후 다음 명령을 사용한다.

```powershell
npm run deploy
```

이 명령은 `npm run build`, 게시 검증, `wrangler deploy`를 순서대로 실행한다. 따라서 원본이 바뀐 뒤 오래된 `out/`을 그대로 게시하지 않는다. 직접 `wrangler deploy`만 실행하면 이 저장소의 운영 빌드와 검증 절차를 우회하므로 권장하지 않는다.

현재 저장소의 `wrangler.jsonc`는 정적 자산 경로를 `./out`으로 지정한다. Cloudflare 로그인, 프로젝트 생성, 접근 정책과 사용자 조직의 인증 설정은 해당 계정에서 별도로 구성한다. 정적 HTML에는 게시한 자료 전체가 들어가므로 외부 공개 전에 Cloudflare 측 접근 정책을 검토한다.
