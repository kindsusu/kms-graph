# Cloudflare 정적 배포

이 프로젝트는 읽기 전용 정적 사이트다. Google Sheets 또는 Notion 원본은 `build.py`가 읽기만 하며 Cloudflare에는 `out/` 파일만 게시한다. 서버 API, D1, R2, 로그인 기능은 없다.

사용자 환경에서 계정 설정과 자격 증명을 준비한 뒤 실행한다.

```powershell
npm ci
npm --prefix frontend ci
npm run sample:build
npm run deploy:dry-run
# 검토·승인 후에만: npx wrangler deploy
```

`npm run sample:build`는 프런트엔드를 빌드하고 샘플 CSV로 `out/`을 만든다. 실제 Sheets/Notion 자료는 로컬 `config.json`을 써서 기존 `build.py --config ...`로 생성한다. Cloudflare 정적 출력은 `out/`이므로 실제 설정에서는 `repo_dir`을 이 저장소 경로, `out_subdir`을 `out`으로 지정한다. 자격 증명과 `config.json`은 커밋하지 않는다.

원본 자료를 수정하면 다시 빌드하고 재배포해야 한다. 이 저장소에는 Sheets/Notion 계정이나 자격 증명이 없어 실제 연동은 검증하지 않았다. 이 작업에서는 Cloudflare 로그인, 리소스 생성, 원격 배포를 실행하지 않았다.
