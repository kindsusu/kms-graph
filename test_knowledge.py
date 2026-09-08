# -*- coding: utf-8 -*-
import argparse
import json
import os
import shutil
import tempfile

import build
import knowledge

HERE = os.path.dirname(os.path.abspath(__file__))
sample = knowledge.load_knowledge(os.path.join(HERE, "sample", "knowledge.json"))
assert len(sample["items"]) == 4 and sample["items"][2]["subtype"] == "프롬프트"
assert "prompt" not in sample["items"][0]

def invalid(change):
    p = json.loads(json.dumps(sample)); change(p)
    try:
        knowledge.validate_payload(p)
    except ValueError:
        return
    raise AssertionError("invalid payload accepted")

invalid(lambda p: p["items"].append(dict(p["items"][0])))
invalid(lambda p: p["relations"].append({"id":"x", "source":"missing", "target":"doc-manual", "type":"references", "label":""}))
invalid(lambda p: p["relations"].append({"id":"x", "source":"doc-manual", "target":"doc-manual", "type":"references", "label":""}))
invalid(lambda p: p["items"][0].update(prompt="leak"))
invalid(lambda p: p["items"][3].update(url="https://u:p@example.com"))
invalid(lambda p: p["items"][3].update(health="maybe"))
assert knowledge.stable_id("tool", "https://x") == knowledge.stable_id("tool", "https://x")

# Canonical whitespace IDs still connect, and non-contract values never reach output.
trimmed = json.loads(json.dumps(sample))
trimmed["items"][0]["id"] = "  doc-annual-policy  "
trimmed["items"][0]["internal_secret"] = "do not publish"
trimmed["relations"][0]["target"] = " doc-annual-policy "
trimmed = knowledge.validate_payload(trimmed)
assert trimmed["items"][0]["id"] == "doc-annual-policy"
assert trimmed["relations"][0]["target"] == "doc-annual-policy"
assert "internal_secret" not in trimmed["items"][0]

tmp = tempfile.mkdtemp(prefix="kms-v2-")
try:
    args = argparse.Namespace(csv_dir=os.path.join(HERE, "sample"), check_urls=False,
                              knowledge=os.path.join(HERE, "sample", "knowledge.json"))
    out = os.path.join(tmp, "public")
    report = build.build(args, {"site_title":"T", "mappings_file":os.path.join(tmp, "missing")}, out)
    html = open(os.path.join(out, "index.html"), encoding="utf-8").read()
    assert 'schemaVersion' in html and '회계연도 기준이 아니라' not in html, "legacy prompt leaked"
    assert not os.path.exists(os.path.join(out, "report.json"))
    assert os.path.exists(os.path.join(build.state_directory(out, {}), "report.json"))
    assert report["counts"] == {"sites": 7, "data": 9, "domains": 5}
    # Published legacy data contains only references from approved tools, never all masters.
    assert 'ERP 매출 엑셀 export' not in html  # its site is pending approval
    sites = [{"id": "", "name": "old" , "url": "HTTPS://Apps.Example.com:443/a#old", "desc": "",
              "domain": "", "data": [], "author": "", "tool": "", "date": "", "status": "skipped"}]
    renamed = [dict(sites[0], name="new")]
    assert build.legacy_payload(sites, [], {}, "")["items"][0]["id"] == build.legacy_payload(renamed, [], {}, "")["items"][0]["id"]
    # State paths within the public output are rejected before source reading or writes.
    for unsafe in (out, os.path.join(out, "private")):
        try:
            build.validate_publish_paths(out, {"state_dir": unsafe})
        except SystemExit:
            pass
        else:
            raise AssertionError("unsafe state path accepted")
    repo = os.path.join(tmp, "repo"); os.makedirs(repo)
    for unsafe_out in (repo, os.path.join(repo, "..", "escape")):
        try:
            build.validate_publish_paths(unsafe_out, {}, repo)
        except SystemExit:
            pass
        else:
            raise AssertionError("unsafe publish path accepted")
    os.makedirs(os.path.join(tmp, "old")); open(os.path.join(tmp, "old", "report.json"), "w").close()
    try:
        build.build(args, {}, os.path.join(tmp, "old"))
    except SystemExit:
        pass
    else:
        raise AssertionError("legacy public report was accepted")
finally:
    shutil.rmtree(tmp, ignore_errors=True)
print("knowledge tests passed")
