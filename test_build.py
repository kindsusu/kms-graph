# -*- coding: utf-8 -*-
"""python test_build.py 로 실행하는 최소 점검 스크립트."""
import argparse
import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build  # noqa: E402

SAMPLE = os.path.join(HERE, "sample")


def fresh():
    raw = build.read_csv_dir(SAMPLE)
    return raw, build.build_domains(raw["domains"]), build.build_data(raw["data"])


raw, domains, datas = fresh()
sites, pending, errors, unclassified = build.build_sites(raw["sites"], domains, datas)

# 승인 / 검증 결과
assert len(sites) == 7, "유효 사이트 7개여야 함, 실제 %d" % len(sites)
assert len(pending) == 2, "승인 대기 2건이어야 함, 실제 %d" % len(pending)
errs = {e["사이트명"]: e["reason"] for e in errors}
assert "연차 계산기 구버전" in errs and "URL 중복" in errs["연차 계산기 구버전"], errs
assert len(errors) == 1, errors

# 마스터에 없는 참조데이터는 이제 오류가 아니라 분류 대기
assert [u["사이트명"] for u in unclassified] == ["사규 검색 챗봇"], unclassified
unmatched = build.build_unmatched(unclassified, domains, datas)
assert build.has_unmatched(unmatched)
assert [x["value"] for x in unmatched["참조데이터"]] == ["인사규정 노션"], unmatched
assert unmatched["참조데이터"][0]["sites"] == ["사규 검색 챗봇"], unmatched
assert unmatched["참조데이터"][0]["desc_samples"], unmatched
assert {m["데이터명"] for m in unmatched["masters"]["참조데이터"]} >= {"그룹웨어 사규 PDF"}, unmatched

# (1) to 매핑을 적용하면 그 행이 유효해진다
raw, domains, datas = fresh()
used = build.apply_mappings(raw["sites"], domains, datas, {
    "참조데이터": {"인사규정 노션": {"to": "그룹웨어 사규 PDF", "why": "같은 원문", "by": "claude", "date": "2026-09-02"}}})
sites, pending, errors, unclassified = build.build_sites(raw["sites"], domains, datas)
assert len(sites) == 8 and not unclassified, (len(sites), unclassified)
assert used == [{"종류": "참조데이터", "원본": "인사규정 노션", "결과": "그룹웨어 사규 PDF",
                 "why": "같은 원문", "date": "2026-09-02"}], used
bot = [s for s in sites if s["name"] == "사규 검색 챗봇"][0]
assert bot["data"] == ["그룹웨어 사규 PDF"], bot["data"]  # 중복 병합

# (2) new 매핑은 마스터에 source=claude 로 추가된다
raw, domains, datas = fresh()
build.apply_mappings(raw["sites"], domains, datas, {
    "참조데이터": {"인사규정 노션": {"new": {"데이터명": "인사규정 노션 DB", "종류": "노션",
                                    "담당팀": "인사팀", "설명": "노션에 옮긴 인사규정"},
                            "why": "맞는 항목 없음", "by": "claude", "date": "2026-09-02"}}})
sites, pending, errors, unclassified = build.build_sites(raw["sites"], domains, datas)
added_master = [d for d in datas if d["name"] == "인사규정 노션 DB"]
assert added_master and added_master[0]["source"] == "claude", datas
assert added_master[0]["team"] == "인사팀", added_master
assert not unclassified and len(sites) == 8, (unclassified, len(sites))

# (3) 사이트도메인 매핑은 도메인이 빈 행만 채운다
raw, domains, datas = fresh()
raw["sites"][4]["도메인"] = ""  # 회의록 요약기
build.apply_mappings(raw["sites"], domains, datas, {
    "사이트도메인": {"회의록 요약기": {"to": "경영", "why": "소개문 기준", "by": "claude", "date": "2026-09-02"}}})
assert raw["sites"][4]["도메인"] == "경영", raw["sites"][4]
new_dom = build.build_domains(build.read_csv_dir(SAMPLE)["domains"])
build.apply_mappings([], new_dom, [], {
    "도메인": {"HR": {"new": {"도메인명": "인사지원", "설명": "x", "색상": ""}, "by": "claude"}}})
hr = [d for d in new_dom if d["name"] == "인사지원"][0]
assert hr["source"] == "claude" and hr["color"].startswith("#"), hr

# 색상 비어 있으면 기본 팔레트
raw, domains, datas = fresh()
assert all(d["color"].startswith("#") and len(d["color"]) == 7 for d in domains), domains

# 노션 응답 파싱 (네트워크 없음)
page = {"properties": {
    "사이트명": {"type": "title", "title": [{"plain_text": "연차 "}, {"plain_text": "계산기"}]},
    "URL": {"type": "url", "url": "https://x.internal/a"},
    "소개": {"type": "rich_text", "rich_text": [{"plain_text": "연차를 계산한다"}]},
    "도메인": {"type": "select", "select": {"name": "인사"}},
    "참조데이터": {"type": "multi_select", "multi_select": [{"name": "근태 구글시트"}, {"name": "인사규정 노션"}]},
    "등록일": {"type": "date", "date": {"start": "2026-03-04"}},
    "승인": {"type": "checkbox", "checkbox": True},
}}
row = {h: build.notion_text(page["properties"].get(h)) for h in build.SITE_HEADERS}
assert row["사이트명"] == "연차 계산기" and row["URL"] == "https://x.internal/a", row
assert row["도메인"] == "인사" and row["승인"] == "TRUE" and row["등록일"] == "2026-03-04", row
assert build.split_names(row["참조데이터"]) == ["근태 구글시트", "인사규정 노션"], row
assert row["작성자"] == "" and row["비고"] == "", row  # 없는 속성은 빈 값
assert build.is_approved(row["승인"]) and not build.is_approved("FALSE")
schema = {"도메인": {"type": "select", "select": {"options": [
              {"name": "인사", "color": "blue"}, {"name": "총무", "color": "green"},
              {"name": "기타", "color": "없는색"}]}},
          "참조데이터": {"type": "multi_select", "multi_select": {"options": [{"name": "근태 구글시트"}]}}}
doms = [{"도메인명": o["name"], "설명": "",
         "색상": build.NOTION_COLORS.get(o.get("color", "default"), build.NOTION_COLORS["default"])}
        for o in build.notion_options(schema["도메인"])]
assert doms[0]["색상"] == "#4F86C6" and doms[1]["색상"] == "#4C9A6A" and doms[2]["색상"] == "#7A8B99", doms
assert build.build_domains(doms)[0]["name"] == "인사"
assert [o["name"] for o in build.notion_options(schema["참조데이터"])] == ["근태 구글시트"]
assert build.notion_options(None) == [] and build.notion_options({"type": "url"}) == []

# 스냅샷 비교
raw, domains, datas = fresh()
sites, pending, errors, unclassified = build.build_sites(raw["sites"], domains, datas)
snap = build.snap_of(sites)
added, changed, removed = build.diff(snap, {})
assert len(added) == 7 and not changed and not removed, (added, changed, removed)

old = json.loads(json.dumps(snap))
old["연차 잔여일 계산기"]["author"] = "홍길동"
old["없어진 사이트"] = {}
added, changed, removed = build.diff(snap, old)
assert added == [] and removed == ["없어진 사이트"], (added, removed)
assert changed and changed[0]["사이트명"] == "연차 잔여일 계산기" and "author" in changed[0]["fields"], changed

# 전체 파이프라인
tmp = tempfile.mkdtemp(prefix="kms-test-")
try:
    args = argparse.Namespace(csv_dir=SAMPLE, check_urls=False)
    out_dir = os.path.join(tmp, "out")
    cfg = {"site_title": "테스트 KMS", "page_url": "https://kms.example.com",
           "mappings_file": os.path.join(tmp, "none.json")}
    report = build.build(args, cfg, out_dir)
    assert os.path.exists(os.path.join(out_dir, "index.html"))
    assert report["counts"] == {"sites": 7, "data": 9, "domains": 5}, report["counts"]
    assert report["unreachable"] == [] and len(report["added"]) == 7
    assert report["pending_mapping"]["count"] == 1, report["pending_mapping"]
    assert report["claude_classified"] == [], report["claude_classified"]

    with open(os.path.join(out_dir, "unmatched.json"), encoding="utf-8") as f:
        um = json.load(f)
    assert [x["value"] for x in um["참조데이터"]] == ["인사규정 노션"], um

    # 두 번째 실행에서는 변경 없음
    report2 = build.build(args, cfg, out_dir)
    assert not report2["added"] and not report2["changed"] and not report2["removed"], report2

    # mappings.json 을 채우고 다시 빌드하면 그 사이트가 들어온다
    mpath = os.path.join(tmp, "map.json")
    with open(mpath, "w", encoding="utf-8") as f:
        json.dump({"참조데이터": {"인사규정 노션": {"to": "그룹웨어 사규 PDF", "why": "같은 원문",
                                            "by": "claude", "date": "2026-09-02"}}}, f, ensure_ascii=False)
    cfg["mappings_file"] = mpath
    report3 = build.build(args, cfg, out_dir)
    assert report3["counts"]["sites"] == 8 and report3["pending_mapping"]["count"] == 0, report3["counts"]
    assert report3["added"] == ["사규 검색 챗봇"], report3["added"]
    assert len(report3["claude_classified"]) == 1, report3["claude_classified"]
    with open(os.path.join(out_dir, "unmatched.json"), encoding="utf-8") as f:
        assert not build.has_unmatched(json.load(f))

    # JSON 안의 </ 이스케이프
    esc_dir = os.path.join(tmp, "esc")
    os.makedirs(esc_dir)
    build.render(esc_dir, {
        "title": "x", "generated_at": "", "page_url": "", "data": [], "domains": [],
        "sites": [{"name": "</script><img src=x onerror=alert(1)>", "url": "https://x",
                   "desc": "", "domain": "인사", "data": [], "author": "", "tool": "",
                   "prompt": "", "date": "", "status": "ok"}],
    })
    with open(os.path.join(esc_dir, "index.html"), encoding="utf-8") as f:
        html = f.read()
    assert "<\\/script><img" in html, "</ 이스케이프 실패"
    assert "</script><img" not in html, "이스케이프되지 않은 </script> 발견"
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# 예시 매핑 파일이 읽히는 형태인지
ex = build.load_mappings(os.path.join(SAMPLE, "mappings.example.json"))
assert set(ex) == {"도메인", "참조데이터", "사이트도메인"}, ex
assert ex["참조데이터"]["비품 사진 폴더"]["new"]["데이터명"], ex

# 영문 탭·헤더 이름
en = tempfile.mkdtemp(prefix="kms-en-")
NL = chr(10)
open(os.path.join(en, "sites.csv"), "w", encoding="utf-8").write(
    "name,url,description,domain,data_sources,author,tool,prompt,date,approved,note" + NL
    + "Leave Calc,https://apps.example.com/leave,calc,HR,HR export,A,Claude,p,2026-01-01,TRUE," + NL)
open(os.path.join(en, "domains.csv"), "w", encoding="utf-8").write("name,description,color" + NL + "HR,people ops,#4F86C6" + NL)
open(os.path.join(en, "data_sources.csv"), "w", encoding="utf-8").write("name,kind,team,description" + NL + "HR export,excel,HR,monthly" + NL)
en_rows = build.read_csv_dir(en)
assert en_rows["sites"][0]["사이트명"] == "Leave Calc" and en_rows["sites"][0]["승인"] == "TRUE", en_rows["sites"]
assert en_rows["domains"][0]["도메인명"] == "HR" and en_rows["data"][0]["데이터명"] == "HR export", en_rows
shutil.rmtree(en, ignore_errors=True)

print("테스트 통과")
