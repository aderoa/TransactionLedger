#!/usr/bin/env python3
"""build_name_map.py — crosswalk RealGM player names to a canonical nomenclature via a dictionary.

Primary mode is dictionary-driven: you supply an authoritative codes sheet that has a column of
RealGM spellings ("RG CODE") and a column of canonical names ("NAME"). The script extracts that
mapping and writes:

  name_map.csv        realgm_player_id, realgm_name, hh_name   (only rows where the spelling DIFFERS)

The browser loads name_map.csv and substitutes the display name by realgm_name (or realgm_player_id
when present). When you also pass --players (your RealGM master_players.csv), the script fills in
ids AND runs a coverage check, writing:

  name_unmatched.csv  realgm_player_id, realgm_name, suggested_name, match
                      (RealGM-DB players with no exact dictionary entry. 'match=normalized' rows have
                       a likely candidate after accent/suffix folding; 'match=none' need a new entry.)

Usage:
  python build_name_map.py --dict All-Time_Database_Codes.csv \
        [--players .\\out\\master_players.csv] [--rg-col "RG CODE"] [--name-col NAME] [--out-dir .]
"""
import argparse, csv, sys, unicodedata, re
from collections import defaultdict

SUFFIXES = {"jr", "sr", "ii", "iii", "iv"}
SPECIAL = str.maketrans({"\u00df": "ss", "\u00f8": "o", "\u00e6": "a", "\u0153": "o",
                         "\u0111": "d", "\u0142": "l", "\u00f0": "d", "\u00fe": "th"})

def norm(name):
    s = (name or "").lower().strip().translate(SPECIAL)
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    toks = [t for t in re.split(r"[^a-z]+", s) if t and t not in SUFFIXES]
    return "".join(toks).replace("oe", "o").replace("ue", "u").replace("ae", "a")

def load_rows(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.reader(f))

def find_col(header, wanted):
    w = wanted.strip().lower()
    for i, h in enumerate(header):
        if (h or "").strip().lower() == w:
            return i
    return None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dict", required=True)
    ap.add_argument("--players")
    ap.add_argument("--rg-col", default="RG CODE")
    ap.add_argument("--name-col", default="NAME")
    ap.add_argument("--out-dir", default=".")
    a = ap.parse_args()
    od = a.out_dir.rstrip("/\\")

    drows = load_rows(a.dict)
    hdr = drows[0]
    rg_i, nm_i = find_col(hdr, a.rg_col), find_col(hdr, a.name_col)
    if rg_i is None or nm_i is None:
        sys.exit("could not find '%s' / '%s' in header: %s" % (a.rg_col, a.name_col, hdr))

    rg2name, collisions = {}, defaultdict(set)
    for r in drows[1:]:
        if len(r) <= max(rg_i, nm_i):
            continue
        rg, nm = r[rg_i].strip(), r[nm_i].strip()
        if rg and nm:
            if rg in rg2name and rg2name[rg] != nm:
                collisions[rg] |= {rg2name[rg], nm}
            rg2name[rg] = nm
    norm2name = {}
    for rg, nm in rg2name.items():
        norm2name.setdefault(norm(rg), nm)
    overrides = {rg: nm for rg, nm in rg2name.items() if rg != nm}

    name2id, players = {}, []
    if a.players:
        prows = load_rows(a.players)
        ph = prows[0]
        pid = next((i for i, h in enumerate(ph) if h.strip().lower() in ("id", "player_id", "realgm_player_id")), 0)
        pnm = next((i for i, h in enumerate(ph) if h.strip().lower() in ("name", "player_name", "player")), 1)
        for r in prows[1:]:
            if len(r) <= max(pid, pnm):
                continue
            pidv, pnmv = r[pid].strip(), r[pnm].strip()
            if pnmv:
                players.append((pidv, pnmv))
                name2id[pnmv] = pidv

    with open("%s/name_map.csv" % od, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["realgm_player_id", "realgm_name", "hh_name"])
        for rg in sorted(overrides):
            w.writerow([name2id.get(rg, ""), rg, overrides[rg]])

    print("dictionary: %d RG->NAME pairs | spelling overrides: %d -> name_map.csv" % (len(rg2name), len(overrides)))
    if collisions:
        print("  ! %d RG spellings map to >1 NAME (kept last): %s%s" % (
            len(collisions), ", ".join(list(collisions)[:5]), " ..." if len(collisions) > 5 else ""))

    if a.players:
        exact = probable = none = 0
        rows_out = []
        for pid, pname in players:
            if pname in rg2name:
                exact += 1
            else:
                hit = norm2name.get(norm(pname))
                if hit:
                    probable += 1
                    rows_out.append([pid, pname, hit, "normalized"])
                else:
                    none += 1
                    rows_out.append([pid, pname, "", "none"])
        with open("%s/name_unmatched.csv" % od, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["realgm_player_id", "realgm_name", "suggested_name", "match"])
            w.writerows(rows_out)
        print("RealGM database: %d players" % len(players))
        print("  exact dictionary hit       : %5d" % exact)
        print("  no exact entry             : %5d  -> name_unmatched.csv" % (probable + none))
        print("      of which likely (folded): %5d  (match=normalized, has a suggestion)" % probable)
        print("      of which truly missing  : %5d  (match=none, add to dictionary)" % none)

if __name__ == "__main__":
    main()
