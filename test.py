#!/usr/local/bin/python3
"""Fixtures for thinpool. Real signed data + tamper + age-boundary cases."""
import copy
import datetime
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build  # noqa: E402

REPORT = "/opt/data/projects/swapcheck/report.json"
env = json.load(open(REPORT))
checks = []


def check(name, cond):
    checks.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name)


# 1 — real signed snapshot renders and recovers the declared signer
out, recovered, rounds, stale = build.render(env, now=datetime.datetime(2026, 11, 22, 12, 0, tzinfo=datetime.timezone.utc))
check("signature recovers declared signer", recovered.lower() == env["payload"]["signer"].lower())
check("two rounds derived", len(rounds) == 2)
by_sell = {r["sell"]: r for r in rounds}
check("DAI spread 1.415x from signed routes", by_sell["DAI"]["spread_x"] == 1.415)
check("EURC spread 16.915x from signed routes", by_sell["EURC"]["spread_x"] == 16.915)
check("DAI wrong-route loss matches signed value", abs(by_sell["DAI"]["wrong_route_loss"] - 292.7115) < 1e-9)
check("EURC wrong-route loss matches signed value", abs(by_sell["EURC"]["wrong_route_loss"] - 1034.0518) < 1e-9)
check("58h-old snapshot flagged STALE on face", stale and "STALE" in out and "read 19-11 12:04Z" in out)
check("full ISO kept in title", env["payload"]["generated_at"] in out)
check("agent identity disclosed", "autonomous AI agent" in out and "not financial advice" in out)
check("no hand-typed '$292.71' literal in template", "$292.71" not in build.TPL)

# 2 — best/worst derived from route nets, not from signed labels
tampered_labels = copy.deepcopy(env["payload"])
tampered_labels["pairs"][0]["best"] = {"path": ["DAI", "WETH", "USDC"], "net_usdc": 1}
derived = build.rounds_from_payload(tampered_labels)
check("mislabeled 'best' ignored; net math wins", derived[0]["best_net"] == 998.4185)

# 3 — tampering the number breaks the signature and build refuses
bad = copy.deepcopy(env)
bad["payload"]["pairs"][0]["routes"][0]["net_usdc"] = 1.0
try:
    build.render(bad)
    refused = False
except ValueError:
    refused = True
check("tampered net refused at build (signature fails)", refused)

# 4 — age boundary, pinned clock
iso = env["payload"]["generated_at"]
t0 = datetime.datetime(2026, 11, 19, 13, 0, tzinfo=datetime.timezone.utc)  # ~1h old
face0, stale0, h0 = build.age_fields(iso, now=t0)
check("fresh snapshot: face date, no STALE", face0 == "read 19-11 12:04Z" and not stale0)
face1, stale1, h1 = build.age_fields(iso, now=t0 + datetime.timedelta(hours=48))
check("same data +48h: STALE, face unchanged", stale1 and face1 == face0)
face2, stale2, h2 = build.age_fields(None, now=t0)
check("missing timestamp: 'read ?' always stale", face2 == "read ?" and stale2 and h2 is None)

failed = [n for n, ok in checks if not ok]
print("\n%d/%d PASS" % (len(checks) - len(failed), len(checks)))
if failed:
    print("FAILED:", failed)
sys.exit(1 if failed else 0)
