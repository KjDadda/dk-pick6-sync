#!/usr/bin/env python3
"""Fetch DK Pick6 player props and save to dk_pick6_data.json.
Runs on GitHub Actions US-based runner to bypass DK geo-blocking.
Output format matches what dk_pick6_cache expects for _apply_dk_pick6_data()."""

import json, urllib.request, os, sys
from datetime import datetime, timezone

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
}

def fetch_json(url, timeout=15):
    req = urllib.request.Request(url, headers=HEADERS)
    resp = urllib.request.urlopen(req, timeout=timeout)
    return json.loads(resp.read())

SPORT_MAP = {
    "1": "MLB", "2": "NFL", "3": "NBA", "4": "NHL",
    "5": "Golf", "6": "Soccer", "7": "UFC", "8": "WNBA",
    "9": "NASCAR", "10": "CFB", "11": "CBB", "12": "Tennis",
}

def main():
    result = {
        "updated": datetime.now(timezone.utc).isoformat(),
        "players": [],  # [{player, sport, team, stat, line, overMultiplier, underMultiplier}]
    }
    
    print("Fetching contest list...")
    try:
        contests_data = fetch_json("https://www.draftkings.com/lobby/getcontests")
        contests = contests_data.get("Contests", [])
        print(f"  Found {len(contests)} contests")
    except Exception as e:
        print(f"  FAILED: {e}")
        contests = []
    
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
            print(f"    FAILED: {e}")
            continue
    
    # Save
    with open("dk_pick6_data.json", "w") as f:
        json.dump(result, f, indent=2)
    
    print(f"\nDone. {len(result['players'])} total player-stat pairs across {len(seen_dgs)} sports.")

if __name__ == "__main__":
    main()
