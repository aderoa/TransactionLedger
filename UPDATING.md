# Updating the transaction database — runbook

**BUILD 2026-06-20 · manual workflow (no automation)**

Everything runs off the cached RealGM pages, so a routine refresh makes exactly one network
call (the current season). Three independent jobs: **transactions**, the **manual log**, and the
**name crosswalk**. Do whichever you need.

---

## 1. Pull in new transactions (options, signings, trades)

New moves appear only on the current-season page (`league/2026` = 2025-26). Refresh that one page,
then rebuild from cache (range-safe), then re-split assets and rebuild the DB:

```
python realgm_loop.py 2026 2026 --refresh --cache .\cache --out .\out
python realgm_loop.py --rebuild           --cache .\cache --out .\out
python asset_parse.py --dir .\out --teams .\out\master_teams.csv --out .\out\transaction_assets_all.csv
python build_db.py    --dir .\out --db .\out\nba_transactions.db
```

Then publish: in **GitHub Desktop**, commit the refreshed `transactions_all.csv` and
`transaction_assets_all.csv` to the Pages repo and push. The live browser picks them up after the
CDN refresh (or the Worker's cache TTL if it proxies them). If you use the browser locally, just
reload and drop the two CSVs.

> Option exercises/declines, qualifying offers and extensions now parse, so they appear
> automatically on refresh. G-League assignment/recall rows carry the affiliate team.

---

## 2. Manual transaction log (`manual_transactions.csv`)

For anything you want in the ledger **before/instead of** the scrape — early reports, corrections,
moves RealGM doesn't list. This file is schema-identical to `transactions_all.csv`; the browser
loads it as an extra source, appends its rows, and tags each with a small **`log`** badge. Edit it
straight in the **GitHub web editor** (Add file ▸ edit ▸ commit) — no Python needed.

Columns: `transaction_id,date,season,type,multiyear,player_id,player_name,from_team_id,from_team_name,to_team_id,to_team_name,raw_text,source_url`

Conventions:
- `transaction_id`: `LOG-YYYYMMDD-NNN` so logged rows never collide with scraped ids.
- `type`: reuse the parser's vocabulary (`qualifying_offer`, `option_exercise`, `extension`,
  `sign`, `waive`, `trade_complex`, `gleague_assign`…) so type filters stay consistent.
- For a destination move fill `to_team_name`; for a departure fill `from_team_name`.
- `source_url`: put `manual` (or a link) so the origin is obvious.
- Leave `player_id` blank unless you know the RealGM id; the name crosswalk still applies by name.

When the scrape later carries the same move, delete the manual row to avoid a duplicate.

---

## 3. Name crosswalk (only when the dictionary changes)

`name_map.csv` is keyed by name, so a transaction refresh does **not** affect it — only re-run when
you've added rows to the codes sheet:

```
python build_name_map.py --dict All-Time_Database_2_0_-_Codes.csv --players .\out\master_players.csv --out-dir .\out
```

Re-push `name_map.csv`. New players that arrive in a refresh show under their RealGM spelling until
added; they surface at the top of `name_unmatched.csv` (sorted recent-first) as your worklist.

---

## What lives where on GitHub

| File | Updated by | Push when |
|---|---|---|
| `transactions_all.csv` | scrape refresh (job 1) | after a refresh |
| `transaction_assets_all.csv` | scrape refresh (job 1) | after a refresh |
| `manual_transactions.csv` | hand-edit on GitHub (job 2) | whenever you log a move |
| `name_map.csv` | `build_name_map.py` (job 3) | after dictionary edits |
| `transactions-browser.html` | app changes only | rarely |

The browser auto-loads all four from its own folder, so committing a CSV is the whole publish step.
