---
name: market-data
description: Pull LIVE stock, ETF, index, option, and futures data from Schwab for any instrument. Use whenever the user asks about a current/latest price, quote, level, option chain, IV, greeks, open interest, or futures — never answer market-data questions from memory and never skip the check. Also use to refresh prices before discussing positions, proposals, or P&L.
---

# Live Market Data (Schwab)

Fetch live market data with the quiver repo's `scripts/market_data.py`. It is
**read-only** (quotes and option chains only — it cannot place or touch
orders) and uses the Schwab key/token configured in quiver's `config.json`,
working on an isolated token copy so it never disturbs the trading pipeline's
live token.

This is the portable copy of the skill: it assumes the quiver clone lives at
`~/quiver`. If it lives elsewhere on this machine, adjust the path in the
commands below. Run it with plain `python3` — it re-execs itself under the
schwab-py interpreter from `config.json` automatically.

## Quotes: stocks, ETFs, indices, futures, single options

```bash
python3 ~/quiver/scripts/market_data.py quote SPY AAPL
python3 ~/quiver/scripts/market_data.py quote '$SPX' '$VIX'     # indices — quote the $ so the shell doesn't eat it
python3 ~/quiver/scripts/market_data.py quote /ES /NQ /CL       # futures (front month); /ESU26 for a specific contract
python3 ~/quiver/scripts/market_data.py quote 'AAPL  250919C00230000'   # one option contract (note the 2 padding spaces)
```

Output is JSON: per-symbol `last`, `bid`, `ask`, `mark`, `net_change`,
`net_pct_change`, day OHLC, `volume`, and `quote_time_utc`; options add greeks,
IV, and open interest under `option`; futures add expiration/open-interest
under `future`. Unknown symbols land in `errors`, not exceptions. Add `--raw`
for the untouched Schwab payload.

## Option chains

```bash
python3 ~/quiver/scripts/market_data.py chain AAPL                    # both sides, ≤60 DTE, strikes ±15% of spot
python3 ~/quiver/scripts/market_data.py chain SPY --dte 30 --type C --band 0.05
python3 ~/quiver/scripts/market_data.py chain QQQ --expiry 2026-08-21
```

Returns `underlying_price`, `is_delayed`, and a `contracts` list (bid/ask/mark,
delta, theta, IV, OI, volume, Schwab option `symbol`) sorted by expiry then
strike. Use the returned `symbol` values with the `quote` subcommand to track a
specific contract. Default output is capped at 400 contracts
(`--max-contracts 0` to disable); tighten `--band`/`--dte`/`--expiry` instead
of raising the cap.

## Interpreting results

- Always report the `quote_time_utc` / `captured_at_utc` timestamp and flag
  `is_delayed: true` chains as delayed data.
- `last` can be stale outside regular hours; prefer `mark` (or bid/ask) and
  mention `regular_last` when they diverge.
- Symbol not found → check the convention: indices need `$`, futures need `/`,
  option symbols need the underlying padded to 6 characters.

## Failure modes

- **Auth errors / HTTP 401** → the Schwab token has likely expired (Schwab
  forces re-auth roughly weekly). Tell the user to re-authenticate via
  schwab-mcp; do not attempt to regenerate tokens yourself.
- **"schwab-py not importable"** → quiver's `config.json` is missing
  `schwab_py_interpreter`, or the schwab-mcp env moved.
- **"Live token ... missing/empty"** → same re-auth situation as above.
- **No such file** → the quiver clone isn't at `~/quiver` on this machine;
  find it and adjust the path.

Exit code is non-zero on any failure with the reason on stderr — surface that
reason to the user rather than silently falling back to remembered prices.
