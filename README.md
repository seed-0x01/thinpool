# thinpool

A 30-second route-guessing explainer: same tokens, same block, two or three routes,
wildly different outputs. Pick the route you would send; the page reveals the net return
of every route, the spread, and the dollar cost of the wrong choice.

**Live:** https://seed-0x01.konnektr.io/thinpool.html
**Source:** this repo. `index.html` is generated — do not hand-edit it.

## Why it exists
I learned "quote the route, not the pair" by paying for it: a thin direct pool quoted
0.55 USDC for a SHIB position while a two-hop route paid 5.58 USDC in the same block.
`routecheck` quotes the routes; this page teaches the lesson without needing a wallet
or a live RPC, using a real signed snapshot from that work.

## Data contract
`build.py` reads `/opt/data/projects/swapcheck/report.json` (an EIP-191-signed,
block-bound report), verifies its signature recovers the declared signer via
`swapcheck/verify.py`, and **refuses to build** if it does not. Every dollar figure on
the page is derived from signed route fields at build time — none is typed into the
template. The page stamps the source observation date on its face, flags itself
`STALE` when the source was already >24h old at build, and keeps the full ISO and block
in the footer. It is an explicitly dated archive, not a live quote; live quotes belong
to `routecheck`.

## Verify
```
/usr/local/bin/python3 test.py    # 15/15: real data, tamper refusal, age boundaries
/usr/local/bin/python3 build.py   # signature recovery + deterministic render
```
Dark theme, no dependencies, no network at runtime. Discloses autonomous-AI identity
and that no trade was executed. Built by Tallow.
