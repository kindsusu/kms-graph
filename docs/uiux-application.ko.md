# UI UX Pro Max 적용 기록

2026-09-08. 사용자 지정 저장소 `nextlevelbuilder/ui-ux-pro-max-skill`의 `.claude/skills/ui-ux-pro-max`를 개인 Codex skills에 설치했다. 설치된 SKILL.md, quick-reference.md의 접근성·조작·성능 항목, pro-rules.md의 적용 범위를 확인했다.

## 조회와 채택

- `knowledge management internal dashboard --design-system --density 8`: Flat Design은 참고했으나, 마케팅용 Hero/CTA 및 장식적인 서체 조합은 사내 한국어 자료 목록에 맞지 않아 채택하지 않았다.
- 좁힌 조회 `enterprise data dashboard --design-system --density 8`: Data-Dense Dashboard의 정렬된 데이터 행, 공간 효율, 필터, 행 강조를 채택했다. 함께 반환된 영업 랜딩 페이지 구조는 적용하지 않았다.
- `list sorting accessibility --stack react`: 안정적인 ID 기반 key, 의미에 맞는 HTML button/nav 지침을 확인했다.

## 페이지 적용 원칙

목록을 기본으로 제공하고, 모든 자료와 연결 그래프의 탐색을 구분한다. 자료명·유형·분야·담당자·연결 수·업데이트를 같은 열에 배치한다. 정렬은 실제 데이터에 적용한다. 아이콘은 일관된 SVG, 텍스트와 색은 의미별 토큰을 사용한다.

한국어 자료를 빠르게 훑는 사용 맥락과 작은 UI를 원한 사용자 요청을 우선해 목록 본문은 13~14px를 기준으로 한다. 웹과 네이티브 터치 기준은 구분하며 모바일에서는 넉넉한 조작 영역을 확보한다. 대비, 키보드 포커스, 축소된 모션, 작은 화면의 가로 넘침을 검수한다.

스킬 추천을 그대로 복제하지 않고 기존 그래프와 회사 지식관리 목적에 맞는 항목만 적용했다. 그래프 노드 크기 변경은 별도 `node-size-review.ko.md`의 검토안으로 남긴다.

## 검수 결과

- TypeScript/Vite 빌드 및 기존 프런트엔드 테스트 15개 통과.
- Chrome에서 기본 목록, 날짜/연결 수 정렬, 검색, 목록 내 상세 열기, 그래프 전환, 프로덕션 샘플 기본 목록을 확인했다.
- 375/768/1024/1440px 화면 폭과 reduced-motion 환경을 확인했다. 작은 화면의 하단 메뉴 잘림과 유형 텍스트 대비를 수정했다.
- 패널 배경 대비 유형/보조 텍스트 토큰의 계산값: 밝은 테마 4.58~5.59:1, 어두운 테마 6.44~8.77:1. 이는 해당 텍스트 토큰 검증이며 전체 접근성 인증을 의미하지 않는다.
