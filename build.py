# -*- coding: utf-8 -*-
"""KMS 그래프 페이지 빌더.

사용 예:
  python build.py --csv-dir sample --out out --no-check-urls
  python build.py --config config.json --push
  python build.py --config config.json --notify out/message.md
"""
import argparse
import csv
import json
import os
import re
import subprocess
import sys
import traceback
import urllib.parse
from datetime import datetime

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
TABS = {"sites": "사이트", "domains": "도메인", "data": "참조데이터"}
SITE_HEADERS = ["사이트명", "URL", "소개", "도메인", "참조데이터", "작성자", "도구", "프롬프트", "등록일", "승인", "비고"]
TRUE_VALUES = {"true", "예", "y", "yes", "o", "1", "✓", "v", "체크"}
PALETTE = ["#4F86C6", "#E2703A", "#5BA87A", "#B06AB3", "#D9A441", "#7A8B99", "#C25A7C"]
SPLIT_RE = re.compile(r"[,;\n]")
HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")
NOTION_COLORS = {"blue": "#4F86C6", "green": "#4C9A6A", "red": "#C8553D", "orange": "#E08E45",
                 "yellow": "#D4B13F", "purple": "#7A5CA8", "pink": "#C86B98", "brown": "#8B6A4E",
                 "gray": "#7A8B99", "default": "#7A8B99"}


# ---------- 입력 ----------

def read_csv_dir(csv_dir):
    out = {}
    for key, tab in TABS.items():
        path = os.path.join(csv_dir, tab + ".csv")
        if not os.path.exists(path):
            raise SystemExit("CSV 파일이 없습니다: %s" % path)
        with open(path, encoding="utf-8-sig", newline="") as f:
            out[key] = [dict(r) for r in csv.DictReader(f)]
    return out


def read_sheets(cfg):
    from google.oauth2 import service_account
    from google.auth.transport.requests import AuthorizedSession

    key_path = cfg.get("service_account_json", "")
    sheet_id = cfg.get("sheet_id", "")
    if not key_path or not sheet_id:
        raise SystemExit("config.json 에 sheet_id / service_account_json 이 필요합니다.")
    creds = service_account.Credentials.from_service_account_file(
        key_path, scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"])
    sess = AuthorizedSession(creds)
    out = {}
    for key, tab in TABS.items():
        url = "https://sheets.googleapis.com/v4/spreadsheets/%s/values/%s" % (
            urllib.parse.quote(sheet_id), urllib.parse.quote(tab))
        r = sess.get(url, timeout=30)
        if r.status_code != 200:
            raise SystemExit("시트를 읽지 못했습니다 (%s 탭, HTTP %s): %s" % (tab, r.status_code, r.text[:300]))
        values = r.json().get("values", [])
        if not values:
            raise SystemExit("시트 %s 탭이 비어 있습니다." % tab)
        header = [str(h).strip() for h in values[0]]
        rows = []
        for raw in values[1:]:
            raw = list(raw) + [""] * (len(header) - len(raw))
            rows.append({header[i]: str(raw[i]) for i in range(len(header))})
        out[key] = rows
    return out


def notion_call(token, method, path, body=None):
    r = requests.request(method, "https://api.notion.com/v1" + path, timeout=30, json=body,
                         headers={"Authorization": "Bearer " + token,
                                  "Notion-Version": "2022-06-28",
                                  "Content-Type": "application/json"})
    if r.status_code != 200:
        raise SystemExit("노션 API 실패 (%s %s, HTTP %s): %s" % (method, path, r.status_code, r.text[:300]))
    return r.json()


def notion_query(token, db_id):
    """데이터베이스 전체 페이지를 커서로 넘겨 가며 읽는다."""
    rows, cursor = [], None
    while True:
        body = {"page_size": 100}
        if cursor:
            body["start_cursor"] = cursor
        j = notion_call(token, "POST", "/databases/%s/query" % urllib.parse.quote(db_id), body)
        rows.extend(j.get("results", []))
        if not j.get("has_more"):
            return rows
        cursor = j.get("next_cursor")


def notion_text(prop):
    """속성 하나를 문자열로. 없는 속성은 빈 문자열."""
    t = (prop or {}).get("type")
    if t in ("title", "rich_text"):
        return "".join(x.get("plain_text", "") for x in prop.get(t) or [])
    if t == "url":
        return prop.get("url") or ""
    if t == "select":
        return (prop.get("select") or {}).get("name") or ""
    if t == "multi_select":
        return ", ".join(x.get("name", "") for x in prop.get("multi_select") or [])
    if t == "date":
        return (prop.get("date") or {}).get("start") or ""
    if t == "checkbox":
        return "TRUE" if prop.get("checkbox") else "FALSE"
    return ""


def notion_options(prop):
    """select / multi_select 속성의 선택지 목록."""
    t = (prop or {}).get("type")
    if t not in ("select", "multi_select"):
        return []
    return (prop.get(t) or {}).get("options") or []


def read_notion(cfg):
    token = cfg.get("notion_token", "")
    db_sites = cfg.get("notion_db_sites", "")
    if not token or not db_sites:
        raise SystemExit("config.json 에 notion_token / notion_db_sites 가 필요합니다.")
    schema = notion_call(token, "GET", "/databases/%s" % urllib.parse.quote(db_sites)).get("properties", {})
    missing = [k for k in ("사이트명", "URL", "승인") if k not in schema]
    if missing:
        raise SystemExit("노션 사이트 DB 에 다음 속성이 없습니다: %s" % ", ".join(missing))

    sites = [{h: notion_text(p.get("properties", {}).get(h)) for h in SITE_HEADERS}
             for p in notion_query(token, db_sites)]
    domains = [{"도메인명": o.get("name", ""), "설명": "",
                "색상": NOTION_COLORS.get(o.get("color", "default"), NOTION_COLORS["default"])}
               for o in notion_options(schema.get("도메인"))]
    datas = [{"데이터명": o.get("name", ""), "종류": "", "담당팀": "", "설명": ""}
             for o in notion_options(schema.get("참조데이터"))]

    if cfg.get("notion_db_data"):
        detail = {}
        for p in notion_query(token, cfg["notion_db_data"]):
            pr = p.get("properties", {})
            nm = notion_text(pr.get("데이터명"))
            if nm:
                detail[nm] = {"데이터명": nm, "종류": notion_text(pr.get("종류")),
                              "담당팀": notion_text(pr.get("담당팀")), "설명": notion_text(pr.get("설명"))}
        seen = {d["데이터명"] for d in datas}
        for d in datas:
            d.update(detail.get(d["데이터명"], {}))
        datas += [v for k, v in detail.items() if k not in seen]
    return {"sites": sites, "domains": domains, "data": datas}


def read_source(args, cfg):
    if args.csv_dir:
        return read_csv_dir(args.csv_dir)
    src = getattr(args, "source", None) or cfg.get("source") or "sheets"
    if src == "notion":
        return read_notion(cfg)
    if src == "sheets":
        return read_sheets(cfg)
    raise SystemExit("source 는 sheets 또는 notion 이어야 합니다. 지금 값: %s" % src)


# ---------- 정리 / 검증 ----------

def txt(row, key):
    return str(row.get(key) or "").strip()


def split_names(cell):
    return list(dict.fromkeys(p.strip() for p in SPLIT_RE.split(cell or "") if p.strip()))


def is_approved(value):
    return str(value or "").strip().lower() in TRUE_VALUES


def build_domains(rows):
    out, seen = [], set()
    for i, r in enumerate(rows):
        name = txt(r, "도메인명")
        if not name or name in seen:
            continue
        seen.add(name)
        color = txt(r, "색상")
        if not HEX_RE.match(color):
            color = PALETTE[len(out) % len(PALETTE)]
        out.append({"name": name, "desc": txt(r, "설명"), "color": color})
    return out


def build_data(rows):
    out, seen = [], set()
    for r in rows:
        name = txt(r, "데이터명")
        if not name or name in seen:
            continue
        seen.add(name)
        out.append({"name": name, "kind": txt(r, "종류"), "team": txt(r, "담당팀"), "desc": txt(r, "설명")})
    return out


# ---------- 매핑 (mappings.json) ----------

def load_mappings(path):
    if not path or not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        m = json.load(f)
    if not isinstance(m, dict):
        raise SystemExit("mappings.json 최상위는 객체여야 합니다: %s" % path)
    return m


def apply_mappings(rows, domains, datas, mappings):
    """검증 전에 매핑을 적용한다. 값 치환 + new 마스터 추가 + 빈 도메인 채우기.
    실제로 쓰인 claude 분류 목록을 돌려준다."""
    used, seen_used = [], set()

    def note(kind, raw, target, m):
        if m.get("by") != "claude" or (kind, raw) in seen_used:
            return
        seen_used.add((kind, raw))
        used.append({"종류": kind, "원본": raw, "결과": target,
                     "why": m.get("why", ""), "date": m.get("date", "")})

    def prep(kind, master, name_key, make):
        """{원본값: (대상이름, 매핑)} 을 만들고 new 항목은 마스터에 붙인다."""
        table, names = {}, {d["name"] for d in master}
        for raw, m in (mappings.get(kind) or {}).items():
            if not isinstance(m, dict):
                continue
            target = txt(m, "to")
            if not target and isinstance(m.get("new"), dict):
                target = txt(m["new"], name_key)
                if target and target not in names:
                    names.add(target)
                    entry = make(m["new"])
                    entry["source"] = "claude" if m.get("by") == "claude" else "mapping"
                    master.append(entry)
            if target:
                table[raw] = (target, m)
        return table

    def new_domain(n):
        color = txt(n, "색상")
        return {"name": txt(n, "도메인명"), "desc": txt(n, "설명"),
                "color": color if HEX_RE.match(color) else PALETTE[len(domains) % len(PALETTE)]}

    dom_map = prep("도메인", domains, "도메인명", new_domain)
    data_map = prep("참조데이터", datas, "데이터명",
                    lambda n: {"name": txt(n, "데이터명"), "kind": txt(n, "종류"),
                               "team": txt(n, "담당팀"), "desc": txt(n, "설명")})
    site_dom = mappings.get("사이트도메인") or {}

    for r in rows:
        name = txt(r, "사이트명")
        dom = txt(r, "도메인")
        if not dom and isinstance(site_dom.get(name), dict):
            m = site_dom[name]
            target = txt(m, "to")
            if target:
                r["도메인"] = dom = target
                note("사이트도메인", name, target, m)
        if dom in dom_map:
            target, m = dom_map[dom]
            r["도메인"] = target
            note("도메인", dom, target, m)
        refs = split_names(txt(r, "참조데이터"))
        if any(x in data_map for x in refs):
            out = []
            for x in refs:
                if x in data_map:
                    target, m = data_map[x]
                    note("참조데이터", x, target, m)
                    out.append(target)
                else:
                    out.append(x)
            r["참조데이터"] = ", ".join(dict.fromkeys(out))
    return used


def build_unmatched(unclassified, domains, datas):
    """매핑이 아직 없는 값들을 Claude 가 읽을 형태로 모은다."""
    buckets = {"도메인": {}, "참조데이터": {}}
    blank_domain = []
    for u in unclassified:
        for it in u["items"]:
            if it["kind"] == "사이트도메인":
                blank_domain.append({"사이트명": u["사이트명"], "소개": u["소개"]})
                continue
            b = buckets[it["kind"]].setdefault(
                it["value"], {"value": it["value"], "sites": [], "desc_samples": []})
            if u["사이트명"] not in b["sites"]:
                b["sites"].append(u["사이트명"])
            if u["소개"] and len(b["desc_samples"]) < 3:
                b["desc_samples"].append(u["소개"])
    key = lambda x: x["value"]  # noqa: E731
    return {
        "도메인": sorted(buckets["도메인"].values(), key=key),
        "참조데이터": sorted(buckets["참조데이터"].values(), key=key),
        "사이트도메인": blank_domain,
        "masters": {
            "도메인": [{"도메인명": d["name"], "설명": d["desc"]} for d in domains],
            "참조데이터": [{"데이터명": d["name"], "종류": d["kind"],
                       "담당팀": d["team"], "설명": d["desc"]} for d in datas],
        },
    }


def has_unmatched(u):
    return bool(u["도메인"] or u["참조데이터"] or u["사이트도메인"])


def build_sites(rows, domains, datas):
    """승인·검증 통과 사이트, 승인 대기, 오류, 분류 대기 목록을 돌려준다."""
    dom_names = {d["name"] for d in domains}
    data_names = {d["name"] for d in datas}
    sites, pending, errors, unclassified = [], [], [], []
    seen_name, seen_url = {}, {}
    for idx, r in enumerate(rows):
        rownum = idx + 2  # 1행은 헤더
        name = txt(r, "사이트명")
        if not name and not txt(r, "URL"):
            continue  # 빈 줄
        if not is_approved(r.get("승인")):
            pending.append({"row": rownum, "사이트명": name or "(이름 없음)", "작성자": txt(r, "작성자")})
            continue
        url = txt(r, "URL")
        domain = txt(r, "도메인")
        refs = split_names(txt(r, "참조데이터"))
        reasons = []
        if not name:
            reasons.append("사이트명이 비어 있음")
        if not url:
            reasons.append("URL이 비어 있음")
        elif not (url.startswith("http://") or url.startswith("https://")):
            reasons.append("URL이 http:// 또는 https:// 로 시작하지 않음")
        if name and name in seen_name:
            reasons.append("사이트명 중복 (%d행과 같음)" % seen_name[name])
        if url and url in seen_url:
            reasons.append("URL 중복 (%d행과 같음)" % seen_url[url])
        if reasons:
            errors.append({"row": rownum, "사이트명": name or "(이름 없음)", "reason": " / ".join(reasons)})
            continue

        # 마스터에 없는 값은 오류가 아니라 분류 대기 — mappings.json 이 채워지면 통과한다.
        waits = []
        if not domain:
            waits.append({"kind": "사이트도메인", "value": name})
        elif domain not in dom_names:
            waits.append({"kind": "도메인", "value": domain})
        for ref in refs:
            if ref not in data_names:
                waits.append({"kind": "참조데이터", "value": ref})
        if waits:
            unclassified.append({"row": rownum, "사이트명": name, "소개": txt(r, "소개"),
                                 "items": waits,
                                 "reason": "분류 대기: " + ", ".join(w["value"] for w in waits)})
            continue

        seen_name[name] = rownum
        seen_url[url] = rownum
        sites.append({
            "row": rownum, "name": name, "url": url, "desc": txt(r, "소개"),
            "domain": domain, "data": refs, "author": txt(r, "작성자"),
            "tool": txt(r, "도구"), "prompt": txt(r, "프롬프트"),
            "date": txt(r, "등록일"), "note": txt(r, "비고"), "status": "skipped",
        })
    return sites, pending, errors, unclassified


# ---------- 접속 확인 ----------

def check_urls(sites):
    for s in sites:
        try:
            r = requests.get(s["url"], timeout=5, allow_redirects=True)
            s["status"] = "ok" if r.status_code < 400 else "error:%d" % r.status_code
        except Exception as e:
            s["status"] = "error:%s" % type(e).__name__


# ---------- 스냅샷 비교 ----------

COMPARE = ["url", "desc", "domain", "author", "tool", "prompt", "date"]


def snap_of(sites):
    out = {}
    for s in sites:
        d = {k: s[k] for k in COMPARE}
        d["data"] = sorted(s["data"])
        out[s["name"]] = d
    return out


def diff(new, old):
    added = sorted(set(new) - set(old))
    removed = sorted(set(old) - set(new))
    changed = []
    for name in sorted(set(new) & set(old)):
        fields = [k for k in list(COMPARE) + ["data"] if new[name].get(k) != old[name].get(k)]
        if fields:
            changed.append({"사이트명": name, "fields": fields})
    return added, changed, removed


# ---------- 출력 ----------

def render(out_dir, payload):
    with open(os.path.join(HERE, "template.html"), encoding="utf-8") as f:
        html = f.read()
    blob = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    if "/*__KMS_DATA__*/" not in html:
        raise SystemExit("template.html 에 /*__KMS_DATA__*/ 자리표시자가 없습니다.")
    html = html.replace("/*__KMS_DATA__*/", blob)
    path = os.path.join(out_dir, "index.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    return path


def git_push(repo_dir, out_dir):
    def run(*args):
        return subprocess.run(args, cwd=repo_dir, capture_output=True, text=True, encoding="utf-8", errors="replace")

    rel = os.path.relpath(out_dir, repo_dir)
    r = run("git", "add", "-A", rel)
    if r.returncode != 0:
        print("git add 실패: %s" % r.stderr.strip())
        return False
    msg = "kms: %s" % datetime.now().strftime("%Y-%m-%d")
    r = run("git", "commit", "-m", msg)
    if r.returncode != 0:
        print("커밋할 변경이 없습니다. (%s)" % (r.stdout.strip().splitlines() or [""])[0])
        return True
    r = run("git", "push")
    if r.returncode != 0:
        print("git push 실패: %s" % r.stderr.strip())
        return False
    print("푸시 완료: %s" % msg)
    return True


def notify(cfg, md_path):
    hook = cfg.get("teams_webhook", "")
    if not hook:
        raise SystemExit("config.json 에 teams_webhook 이 없습니다.")
    with open(md_path, encoding="utf-8") as f:
        text = f.read()
    payload = {"type": "message", "attachments": [{
        "contentType": "application/vnd.microsoft.card.adaptive",
        "content": {"type": "AdaptiveCard", "version": "1.4",
                    "body": [{"type": "TextBlock", "text": text, "wrap": True}]}}]}
    r = requests.post(hook, json=payload, timeout=15)
    print("Teams 전송 HTTP %s %s" % (r.status_code, r.text[:200]))
    if r.status_code >= 400:
        raise SystemExit("Teams 전송 실패")


# ---------- 메인 ----------

def mappings_path(cfg):
    p = cfg.get("mappings_file") or "mappings.json"
    return p if os.path.isabs(p) else os.path.join(HERE, p)


def build(args, cfg, out_dir):
    raw = read_source(args, cfg)
    domains = build_domains(raw["domains"])
    datas = build_data(raw["data"])
    claude_classified = apply_mappings(raw["sites"], domains, datas, load_mappings(mappings_path(cfg)))
    sites, pending, errors, unclassified = build_sites(raw["sites"], domains, datas)

    do_check = cfg.get("check_urls", True) if args.check_urls is None else args.check_urls
    if do_check:
        check_urls(sites)

    os.makedirs(out_dir, exist_ok=True)
    snap_path = os.path.join(out_dir, "snapshot.json")
    old = {}
    if os.path.exists(snap_path):
        try:
            with open(snap_path, encoding="utf-8") as f:
                old = json.load(f)
        except Exception as e:
            print("이전 스냅샷을 읽지 못해 전체를 신규로 처리합니다: %s" % e)
    new = snap_of(sites)
    added, changed, removed = diff(new, old)

    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    page = render(out_dir, {
        "title": cfg.get("site_title", "KMS"),
        "generated_at": generated_at,
        "page_url": cfg.get("page_url", ""),
        "sites": [{k: s[k] for k in
                   ("name", "url", "desc", "domain", "data", "author", "tool", "prompt", "date", "status")}
                  for s in sites],
        "data": datas,
        "domains": domains,
    })
    with open(snap_path, "w", encoding="utf-8") as f:
        json.dump(new, f, ensure_ascii=False, indent=1)

    unmatched = build_unmatched(unclassified, domains, datas)
    with open(os.path.join(out_dir, "unmatched.json"), "w", encoding="utf-8") as f:
        json.dump(unmatched, f, ensure_ascii=False, indent=1)

    report = {
        "generated_at": generated_at,
        "counts": {"sites": len(sites), "data": len(datas), "domains": len(domains)},
        "added": added, "changed": changed, "removed": removed,
        "pending_approval": pending, "errors": errors,
        "pending_mapping": {"count": len(unclassified), "items": unclassified},
        "claude_classified": claude_classified,
        "unreachable": [{"사이트명": s["name"], "url": s["url"], "status": s["status"]}
                        for s in sites if s["status"].startswith("error")],
        "page_url": cfg.get("page_url", ""),
    }
    with open(os.path.join(out_dir, "report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=1)

    print("생성: %s" % page)
    print("사이트 %d개 / 참조데이터 %d개 / 도메인 %d개" % (len(sites), len(datas), len(domains)))
    print("신규 %d, 변경 %d, 삭제 %d, 승인대기 %d, 오류 %d, 분류대기 %d, 접속불가 %d"
          % (len(added), len(changed), len(removed), len(pending), len(errors),
             len(unclassified), len(report["unreachable"])))
    for e in errors:
        print("  [오류] %s행 %s: %s" % (e["row"], e["사이트명"], e["reason"]))
    for u in unclassified:
        print("  [분류대기] %s행 %s: %s" % (u["row"], u["사이트명"], u["reason"]))
    for c in claude_classified:
        print("  [Claude 분류] %s '%s' -> '%s' (%s)" % (c["종류"], c["원본"], c["결과"], c["why"]))
    if has_unmatched(unmatched):
        print("분류 대기 값이 있습니다. %s 를 읽고 %s 에 매핑을 추가한 뒤 다시 빌드하세요."
              % (os.path.join(out_dir, "unmatched.json"), mappings_path(cfg)))
    return report


def main():
    p = argparse.ArgumentParser(description="KMS 그래프 페이지 빌더")
    p.add_argument("--config", help="config.json 경로")
    p.add_argument("--source", choices=["sheets", "notion"], help="config.json 의 source 를 덮어쓴다")
    p.add_argument("--csv-dir", help="CSV 폴더에서 읽기 (사이트.csv / 도메인.csv / 참조데이터.csv)")
    p.add_argument("--out", default="out", help="--csv-dir 일 때 출력 폴더 (기본 out)")
    p.add_argument("--push", action="store_true", help="빌드 후 git commit/push")
    p.add_argument("--no-push", action="store_true", help="푸시하지 않음 (기본값)")
    p.add_argument("--check-urls", dest="check_urls", action="store_true", default=None)
    p.add_argument("--no-check-urls", dest="check_urls", action="store_false")
    p.add_argument("--notify", metavar="PATH", help="마크다운 파일을 Teams 로 전송하고 종료")
    args = p.parse_args()

    cfg = {}
    if args.config:
        with open(args.config, encoding="utf-8") as f:
            cfg = json.load(f)

    if args.notify:
        notify(cfg, args.notify)
        return 0

    if not args.config and not args.csv_dir:
        p.error("--config 또는 --csv-dir 중 하나가 필요합니다.")

    if args.csv_dir:
        out_dir = os.path.abspath(args.out)
    else:
        repo = cfg.get("repo_dir", "")
        if not repo:
            raise SystemExit("config.json 에 repo_dir 이 필요합니다.")
        out_dir = os.path.abspath(os.path.join(repo, cfg.get("out_subdir", "docs")))

    build(args, cfg, out_dir)

    if args.push and not args.no_push:
        if not cfg.get("repo_dir"):
            raise SystemExit("--push 에는 config.json 의 repo_dir 이 필요합니다.")
        git_push(cfg["repo_dir"], out_dir)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception:
        traceback.print_exc()
        print("\n빌드 실패: 위 오류를 확인하세요.", file=sys.stderr)
        sys.exit(1)
