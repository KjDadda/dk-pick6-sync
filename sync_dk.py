#!/usr/bin/env python3
"""Fetch DK Pick6 player props and save to dk_pick6_data.json.
Runs on GitHub Actions US-based runner to bypass DK geo-blocking."""

import json, urllib.request, os, sys, traceback
from datetime import datetime, timezone

HEADERS = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://pick6.draftkings.com/",
}

def fetch_json(url, timeout=15):
    req = urllib.request.Request(url, headers=HEADERS)
    resp = urllib.request.urlopen(req, timeout=timeout)
    data = resp.read()
    import gzip
    if resp.headers.get("Content-Encoding") == "gzip":
        data = gzip.decompress(data)
    return json.loads(data)

SPORT_MAP = {"1":"MLB","2":"NFL","3":"NBA","4":"NHL","5":"Golf","6":"Soccer","7":"UFC","8":"WNBA"}

def main():
    result = {"updated": datetime.now(timezone.utc).isoformat(), "players": []}
    
    print("Fetching lobby...")
    try:
        data = fetch_json("https://www.draftkings.com/lobby/getcontests")
        contests = data.get("Contests", [])
        print(f"Total contests: {len(contests)}")
        
        # Show sample contest types
        contest_types = set()
        for c in contests[:50]:
            ct = c.get("contestType", c.get("ct", "?"))
            contest_types.add(str(ct))
        print(f"Contest types: {sorted(contest_types)}")
        
        # Filter for Pick6 — look for 'Pick6' or 'pick6' in name or game type
        pick6_contests = []
        for c in contests:
            name = str(c.get("n", "")).lower()
            game_type = str(c.get("gameType", c.get("gt", ""))).lower()
            if "pick6" in name or "pick6" in game_type or "pick 6" in name:
                pick6_contests.append(c)
        
        if not pick6_contests:
            # Try all contests — maybe Pick6 uses regular DFS contests
            print("No Pick6-specific contests found. Trying first 5 draft groups...")
            pick6_contests = contests[:5]
        
        print(f"Pick6 contests: {len(pick6_contests)}")
        
        # Show first 3 contest names
        for c in pick6_contests[:3]:
            print(f"  Contest: {c.get('n','?')[:80]} | dg={c.get('dg')} | sport={c.get('s')} | type={c.get('gameType','?')}")
        
    except Exception as e:
        print(f"FAILED: {e}")
        contests = []
        pick6_contests = []
    
    seen_dgs = set()
    
    for c in pick6_contests:
        dg = c.get("dg")
        sport_id = str(c.get("s", ""))
        sport = SPORT_MAP.get(sport_id, sport_id)
        
        if not dg or dg in seen_dgs:
            continue
        seen_dgs.add(dg)
        if len(seen_dgs) > 10:
            break
        
        try:
            url = f"https://api.draftkings.com/draftgroups/v1/draftgroups/{dg}/draftables"
            print(f"  DG {dg} ({sport})...")
            dg_data = fetch_json(url)
            
            draftables = dg_data.get("draftables", [])
            added = 0
            
            if draftables:
                # Show first draftable to debug
                d0 = draftables[0]
                print(f"    First draftable keys: {list(d0.keys())[:10]}")
                stats_list = d0.get("stats", [])
                if stats_list:
                    print(f"    Has stats! Example: {stats_list[0]}")
            
            for item in draftables:
                player_name = f"{item.get('firstName','')} {item.get('lastName','')}".strip()
                if not player_name:
                    continue
                
                team = item.get("teamAbbreviation", "")
                
                for stat in item.get("stats", []):
                    stat_name = stat.get("name", "")
                    stat_value = stat.get("value", "")
                    
                    if not stat_name or not stat_value:
                        continue
                    
                    try:
                        line = float(stat_value)
                    except ValueError:
                        line = stat_value
                    
                    result["players"].append({
                        "player": player_name, "sport": sport, "team": team,
                        "stat": stat_name, "line": line, "draft_group": dg,
                    })
                    added += 1
            
            print(f"    {added} player-stat pairs" if added else "    No stats found in draftables")
            
        except Exception as e:
            print(f"    FAILED: {e}")
    
    with open("dk_pick6_data.json", "w") as f:
        json.dump(result, f, indent=2)
    
    print(f"Done. {len(result['players'])} total player-stat pairs.")

if __name__ == "__main__":
    main()
