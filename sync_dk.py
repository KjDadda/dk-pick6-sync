#!/usr/bin/env python3
"""Fetch DK Pick6 player props and save to dk_pick6_data.json.
Runs on GitHub Actions US-based runner to bypass DK geo-blocking."""

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

def main():
    result = {
        "updated": datetime.now(timezone.utc).isoformat(),
        "sports": {},
        "players": [],
    }
    
    # Step 1: Get active contests
    print("Fetching contest list...")
    try:
        contests_data = fetch_json("https://www.draftkings.com/lobby/getcontests")
        contests = contests_data.get("Contests", [])
        print(f"  Found {len(contests)} contests")
    except Exception as e:
        print(f"  FAILED: {e}")
        contests = []
    
    # Step 2: Group by draft group, fetch draftables
    seen_dgs = set()
    sport_names = {}
    
    for c in contests:
        dg = c.get("dg")
        sport = str(c.get("s", ""))
        contest_name = c.get("n", "")
        
        if not dg or dg in seen_dgs:
            continue
        seen_dgs.add(dg)
        
        if len(seen_dgs) > 20:  # Limit to 20 draft groups
            break
        
        try:
            print(f"  Fetching draft group {dg} ({sport})...")
            url = f"https://api.draftkings.com/draftgroups/v1/draftgroups/{dg}/draftables"
            dg_data = fetch_json(url)
            
            draftables = dg_data.get("draftables", [])
            contest_players = []
            
            for item in draftables:
                player_name = f"{item.get('firstName','')} {item.get('lastName','')}".strip()
                if not player_name:
                    continue
                
                player_entry = {
                    "player": player_name,
                    "team": item.get("teamAbbreviation", ""),
                    "position": item.get("position", ""),
                    "sport": sport,
                    "draft_group": dg,
                    "contest": contest_name[:80],
                    "stats": []
                }
                
                for stat in item.get("stats", []):
                    player_entry["stats"].append({
                        "name": stat.get("name", ""),
                        "value": stat.get("value", ""),
                    })
                
                contest_players.append(player_entry)
            
            result["sports"][sport] = {
                "contest_name": contest_name[:80],
                "draft_group": dg,
                "player_count": len(contest_players),
            }
            result["players"].extend(contest_players)
            print(f"    {len(contest_players)} players")
            
        except Exception as e:
            print(f"    FAILED: {e}")
            continue
    
    # Step 3: Save
    output_path = "dk_pick6_data.json"
    with open(output_path, "w") as f:
        json.dump(result, f, indent=2)
    
    print(f"\nDone. {len(result['players'])} total players across {len(result['sports'])} sports.")
    print(f"Sports: {list(result['sports'].keys())}")

if __name__ == "__main__":
    main()
