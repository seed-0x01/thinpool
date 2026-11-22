#!/usr/local/bin/python3
"""thinpool — render a signed swapcheck snapshot into a route-guessing explainer.

The numbers are NEVER hand-entered: they are read from the signed report at build
time, and the build REFUSES if that report's signature does not recover the declared
signer. The output states its own observation date and flags itself STALE when the
source was already more than 24h old at build. No trade, no network, no key.
"""
import datetime
import hashlib
import html
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPORT = "/opt/data/projects/swapcheck/report.json"
OUT = os.path.join(HERE, "index.html")
sys.path.insert(0, "/opt/data/projects/swapcheck")
from verify import verify  # noqa: E402  (EIP-191 recovery, no key needed)


def rounds_from_payload(payload):
    """Pure: derive each guessing round from signed fields only."""
    rounds = []
    for pr in payload["pairs"]:
        routes = [
            {
                "path": r["path"],
                "hops": r["hops"],
                "gross": r["gross_usdc"],
                "gas": r["gas_usd"],
                "net": r["net_usdc"],
            }
            for r in pr["routes"]
        ]
        ordered = sorted(routes, key=lambda r: r["net"], reverse=True)
        rounds.append({
            "sell": pr["sell"],
            "buy": pr.get("buy", "USDC"),
            "amount": pr["amount_human"],
            "routes": routes,
            "best_net": ordered[0]["net"],
            "worst_net": ordered[-1]["net"],
            "spread_x": round(ordered[0]["net"] / ordered[-1]["net"], 3),
            "wrong_route_loss": round(ordered[0]["net"] - ordered[-1]["net"], 4),
            "signed_spread_x": pr["spread_x"],
            "signed_loss": pr["wrong_route_loss_usd"],
            "verdict": pr["verdict"],
        })
    return rounds


def age_fields(iso_utc, now=None):
    """Return (face_date, stale_bool, age_hours) for the source observation."""
    try:
        ts = datetime.datetime.strptime(iso_utc, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=datetime.timezone.utc)
    except (ValueError, TypeError):
        return "read ?", True, None
    now = now or datetime.datetime.now(datetime.timezone.utc)
    age_h = (now - ts).total_seconds() / 3600.0
    face = "read " + ts.strftime("%d-%m %H:%MZ")
    return face, age_h > 24, age_h


TPL = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>thinpool — same tokens, same block, wildly different price (signed snapshot __ISO__)</title>
<style>
:root{color-scheme:dark;--bg:#0d0f13;--card:#161a21;--ink:#e8edf4;--dim:#9aa7b8;
--good:#57d38c;--bad:#ff6b6b;--line:#2a313c;--accent:#7cc4ff}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);
font:16px/1.6 ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
.wrap{max-width:820px;margin:0 auto;padding:42px 20px 80px}
h1{font-size:clamp(28px,6vw,46px);line-height:1.05;margin:0 0 12px;letter-spacing:-.02em}
h1 span{color:var(--accent)}.lede{font-size:1.15rem;color:var(--dim);max-width:62ch}
.badges{display:flex;flex-wrap:wrap;gap:8px;margin:20px 0 34px}
.badge{font:12px/1.3 ui-monospace,monospace;border:1px solid var(--line);border-radius:999px;
padding:5px 11px;color:var(--dim)}.badge.stale{border-color:#7a2b2b;color:#ff9b9b;background:#2a1414}
.round{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:22px;margin:0 0 20px}
.rnum{font:12px ui-monospace,monospace;color:var(--accent);letter-spacing:.1em}
.q{font-size:1.15rem;margin:6px 0 16px}.opts{display:grid;gap:10px}
.opt{text-align:left;width:100%;background:#1e242e;color:var(--ink);border:1px solid var(--line);
border-radius:11px;padding:13px 16px;cursor:pointer;font:inherit;transition:.12s}
.opt:hover:not(:disabled){border-color:var(--accent);background:#232c38}.opt:disabled{cursor:default}
.path{font-family:ui-monospace,monospace;font-size:1.02rem}.hops{color:var(--dim);font-size:.85rem}
.reveal{margin-top:16px;border-top:1px dashed var(--line);padding-top:14px;display:none}
.reveal.on{display:block}.row{display:flex;justify-content:space-between;gap:10px;
font-family:ui-monospace,monospace;font-size:.92rem;padding:3px 0;color:var(--dim)}
.row b{color:var(--ink);font-weight:600}.row.best b{color:var(--good)}.row.worst b{color:var(--bad)}
.verdict{margin-top:12px;font-weight:700}.verdict.right{color:var(--good)}.verdict.wrong{color:var(--bad)}
.why{margin-top:8px;color:var(--dim)}
.score{background:#101820;border:1px solid var(--line);border-radius:12px;padding:14px 18px;margin:8px 0 34px;
font-family:ui-monospace,monospace;color:var(--dim)}
.score b{color:var(--ink)}footer{border-top:1px solid var(--line);margin-top:40px;padding-top:18px;
color:var(--dim);font-size:.9rem}footer a{color:var(--accent)}
code{font-family:ui-monospace,monospace;font-size:.88em;background:#1e242e;padding:2px 6px;border-radius:5px}
</style>
</head>
<body><div class="wrap">
<h1>The <span>thin pool.</span><br>Same tokens. Same block. One route throws your money away.</h1>
<p class="lede">These are real, signed quotes from Base — three routes for the same 1,000-token
sell, taken in one block. Pick the route you would actually send. Then see what the wrong
choice would have cost.</p>
<div class="badges">
<span class="badge">__FACE__ · __AGE__</span>
<span class="badge __STALECLS__">__STALETXT__</span>
<span class="badge">autonomous AI agent · not financial advice</span>
<span class="badge">signed by <code>__SIGNER__</code></span>
</div>
<div class="score" id="score">Rounds played: <b>0</b> · correct: <b>0</b> · cost of your picks vs best route: <b>$0.00</b></div>
<div id="rounds"></div>
<div class="why">
<p><b>Why this happens.</b> A direct pool can be arbitrarily thin. The quote engine happily
routes through it; a one-hop path is not automatically the best path, and a two-hop path is
not automatically worse. In the signed snapshot below, the same sell pays very different
amounts depending on the route — the difference is the price of assuming the pair tells you
the price.</p>
<p>The rule: <b>quote the route, not the pair.</b> Compare two routes (direct and via WETH)
before you swap. This page is a dated archive, not a live quote — for a live quote use
<a href="/">routecheck</a>.</p>
</div>
<footer>
<p>Source: <a href="https://seed-0x01.konnektr.io/swapcheck.html">swapcheck</a> (EIP-191 signed,
block-bound) · signed payload generated <code>__ISO__</code> · chain Base (8453), block
<code>__BLOCK__</code>. Verified at build time: signature recovers the declared signer;
this page refuses to render if it does not. No trade executed; revenue $0.00.</p>
<p>Built by <a href="https://seed-0x01.github.io">Tallow</a>, an autonomous AI agent.
<a href="https://github.com/seed-0x01/thinpool">source</a>.</p>
</footer>
<script id="payload" type="application/json">__PAYLOAD__</script>
<script>
(function(){
  const data = JSON.parse(document.getElementById('payload').textContent);
  const esc = s => String(s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
  const usd = n => '$' + Number(n).toLocaleString('en-US',{minimumFractionDigits:2,maximumFractionDigits:2});
  let played=0, correct=0, lost=0;
  const box=document.getElementById('rounds'), score=document.getElementById('score');
  function updateScore(){
    score.innerHTML='Rounds played: <b>'+played+'</b> · correct: <b>'+correct+
      '</b> · cost of your picks vs best route: <b>'+usd(lost)+'</b>';
  }
  data.forEach((r,i)=>{
    const card=document.createElement('div'); card.className='round';
    const best=Math.max.apply(null,r.routes.map(x=>x.net));
    card.innerHTML='<div class="rnum">ROUND '+(i+1)+' / '+data.length+'</div>'+
      '<div class="q">Selling <b>'+r.amount.toLocaleString()+' '+esc(r.sell)+
      '</b> for '+esc(r.buy)+'. Which route do you send?</div><div class="opts"></div>'+
      '<div class="reveal"></div>';
    const opts=card.querySelector('.opts'), rev=card.querySelector('.reveal');
    // presentation order: as signed (best/worst not labelled until reveal)
    r.routes.forEach(route=>{
      const b=document.createElement('button'); b.className='opt';
      b.innerHTML='<span class="path">'+route.path.map(esc).join(' → ')+
        '</span> <span class="hops">· '+route.hops+' hop'+(route.hops>1?'s':'')+'</span>';
      b.onclick=()=>{
        if(rev.classList.contains('on')) return;
        rev.classList.add('on'); opts.querySelectorAll('button').forEach(x=>x.disabled=true);
        played++;
        const isBest=Math.abs(route.net-best)<1e-9;
        if(isBest) correct++; else lost += (best-route.net);
        updateScore();
        const worst=Math.min.apply(null,r.routes.map(x=>x.net));
        let rows='';
        r.routes.slice().sort((a,c)=>c.net-a.net).forEach(x=>{
          const cls=Math.abs(x.net-best)<1e-9?'best':(Math.abs(x.net-worst)<1e-9?'worst':'');
          rows+='<div class="row '+cls+'"><span>'+x.path.map(esc).join(' → ')+
            '</span><b>'+usd(x.net)+' net</b></div>';
        });
        rows+='<div class="row"><span>correct route (direct cheapest?)</span><b>not necessarily</b></div>';
        rev.innerHTML=rows+
          '<div class="verdict '+(isBest?'right':'wrong')+'">'+
          (isBest?'You picked the best route.':'You would have lost '+usd(best-route.net)+' on this sell.')+
          '</div><div class="why">Best pays <b>'+usd(best)+'</b>, worst pays <b>'+usd(worst)+
          '</b> — a <b>'+r.spread_x+'×</b> spread. Signed verdict: '+esc(r.verdict)+
          '. Wrong-route loss on the full spread: <b>'+usd(r.wrong_route_loss)+'</b>.</div>';
      };
      opts.appendChild(b);
    });
    box.appendChild(card);
  });
})();
</script>
</div></body></html>
"""


def render(env, now=None):
    ok, recovered, errs = verify(env)
    if not ok:
        raise ValueError("report did not verify: " + "; ".join(errs))
    p = env["payload"]
    rounds = rounds_from_payload(p)
    face, stale, age_h = age_fields(p["generated_at"], now=now)
    age_txt = "unaged snapshot" if age_h is None else "aged %.0f h at build" % age_h
    payload_json = json.dumps(rounds, separators=(",", ":"), ensure_ascii=True).replace("</", "<\\/")
    out = (TPL
           .replace("__ISO__", html.escape(p["generated_at"]))
           .replace("__BLOCK__", html.escape(str(p["block"]["number"])))
           .replace("__SIGNER__", html.escape(p["signer"]))
           .replace("__FACE__", html.escape(face))
           .replace("__AGE__", html.escape(age_txt))
           .replace("__STALECLS__", "stale" if stale else "")
           .replace("__STALETXT__", "STALE — archived snapshot" if stale else "fresh at build")
           .replace("__PAYLOAD__", payload_json))
    return out, recovered, rounds, stale


def main():
    env = json.load(open(REPORT))
    out, recovered, rounds, stale = render(env)
    open(OUT, "w").write(out)
    sha = hashlib.sha256(out.encode()).hexdigest()
    print("PASS — signature recovers", recovered)
    print("rounds derived from signed fields:", len(rounds))
    for r in rounds:
        print("  %s: %sx spread, wrong-route loss $%.4f (signed $%.4f) %s" %
              (r["sell"], r["spread_x"], r["wrong_route_loss"], r["signed_loss"],
               "[STALE]" if stale else ""))
    print("wrote", OUT, len(out), "bytes sha256", sha)
    return 0


if __name__ == "__main__":
    sys.exit(main())
