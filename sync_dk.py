#!/usr/bin/env python3
"""Fetch DK Pick6 player props and save to dk_pick6_data.json.
Runs on GitHub Actions US-based runner to bypass DK geo-blocking.
Output format matches what dk_pick6_cache expects for _apply_dk_pick6_data()."""

import json, urllib.request, os, sys, traceback
from datetime import datetime, timezone

# Mobile Safari headers — matches real iPhone traffic DK expects
HEADERS = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://pick6.draftkings.com/",
    "Origin": "https://pick6.draftkings.com",
}

def fetch_json(url, timeout=15):
    req = urllib.request.Request(url, headers=HEADERS)
    resp = urllib.request.urlopen(req, timeout=timeout)
    data = resp.read()
    # Handle gzip
    import gzip, io
    if resp.headers.get("Content-Encoding") == "gzip":
        data = gzip.decompress(data)
    return json.loads(data)

SPORT_MAP = {
    "1": "MLB", "2": "NFL", "3": "NBA", "4": "NHL",
    "5": "Golf", "6": "Soccer", "7": "UFC", "8": "WNBA",
}

def main():
    result = {
        "updated": datetime.now(timezone.utc).isoformat(),
        "players": [],
    }
    
    # Try multiple endpoints
    endpoints = [
        ("lobby", "https://www.draftkings.com/lobby/getcontests"),
        ("pick6 lobby", "https://pick6.draftkings.com/api/contests"),
    ]
    
    contests = []
    for name, url in endpoints:
        try:
            print(f"Trying {name}...")
            data = fetch_json(url)
            contests = data.get("Contests", data.get("contests", []))
            print(f"  Success! {len(contests)} contests")
            break
        except Exception as e:
            print(f"  FAILED: {type(e).__name__}: {e}")
            traceback.print_exc()
    
    if not contests:
        print("All endpoints failed. Saving empty result.")
        with open("dk_pick6_data.json", "w") as f:
            json.dump(result, f, indent=2)
        return
    
    seen_dgs = set()
    
    for c in contests:
        dg = c.get("dg")
        sport_id = str(c.get("s", ""))
        sport = SPORT_MAP.get(sport_id, sport_id)
        
        if not dg or dg in seen_dgs:
            continue
        seen_dgs.add(dg)
        
        if len(seen_dgs) > 15:
            break
        
        try:
            url = f"https://api.draftkings.com/draftgroups/v1/draftgroups/{dg}/draftables"
            print(f"  DG {dg} ({sport})...")
            dg_data = fetch_json(url)
            
            draftables = dg_data.get("draftables", [])
            added = 0
            
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
                        "player": player_name,
                        "sport": sport,
                        "team": team,
                        "stat": stat_name,
                        "line": line,
                        "draft_group": dg,
                    })
                    added += 1
            
            print(f"    {added} player-stat pairs")
            
        except Exception as e:
            print(f"    FAILED: {type(e).__name__}: {e}")
            continue
    
    with open("dk_pick6_data.json", "w") as f:
        json.dump(result, f, indent=2)
    
    print(f"Done. {len(result['players'])} total player-stat pairs across {len(seen_dgs)} draft groups.")

if __name__ == "__main__":
    main()
