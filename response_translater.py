import json
from dotenv import load_dotenv
import requests
import os
from datetime import datetime

load_dotenv()
ACCESS_ID = os.getenv("ACCESS_ID")  

def get_direction_group(direction, line):
    if direction in {"Aalborg St.", "Hals", "Grindsted", "Langholt", "Vodskov", "Klarup", "Storvorde", "Uttrup Nord", "Troensevej"}:
        if line in {"1", "11", "16", "60X"}:  # Include 11, 16, and 60X in the "Stationen" group
            return ["Stationen"]
        return ["Stationen"]
    elif direction in {"Godthåb", "City Syd", "Skelagervej", "Aalstrup", "Ferslev", "Aars", "Dall Villaby","Skalborg"}:
        if line in {"1", "52"}:
            return ["Skalborg/Svenstrup"]
        elif line == "14":
            return ["School"]
        else:
            return ["Southbound"]
    else:
        return ["Unknown Direction"]

def parse_departure(dep, now):
    product = dep.get("ProductAtStop", {})
    name = product.get("name", "Unknown")
    line = product.get("line", "N/A")
    stop = dep.get("stop", "Unknown")
    direction = dep.get("direction", "Unknown")
    scheduled_time = dep.get("time")
    rt_time = dep.get("rtTime", scheduled_time)
    date = dep.get("date")
    unique_id = dep.get("JourneyDetailRef", {}).get("ref")

    if not (scheduled_time and date and rt_time and unique_id):
        return []

    try:
        full_scheduled = datetime.strptime(f"{date} {scheduled_time}", "%Y-%m-%d %H:%M:%S")
        full_rt = datetime.strptime(f"{date} {rt_time}", "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return []

    # Filter out southbound lines 11, 16, and 60X
    if line in {"11", "16", "60X"} and direction == "Southbound":
        return []

    delay = int((full_rt - full_scheduled).total_seconds() / 60)
    if delay == 0:
        status = "✅ On time"
    elif delay > 0:
        status = f"❌ Late by {delay} min"

    output = f"""🚌 Line: {name} (#{line})
➡️ Direction: {direction}
🕒 Scheduled: {full_scheduled.strftime("%H:%M")} | Real-time: {full_rt.strftime("%H:%M")}
ℹ️ Status: {status}
----------------------------------------"""

    return [{
        "groups": get_direction_group(direction, line),
        "line": line,
        "full_rt": full_rt,
        "unique_id": unique_id,
        "output": output
    }]

def fetch_departures(access_id):
    url = "https://www.rejseplanen.dk/api/departureBoard"
    params = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "format": "json",
        "id": "851003502",
        "accessId": access_id
    }

    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json().get("Departure", [])


def main():
    now = datetime.now()
    try:
        departures = fetch_departures(ACCESS_ID)
    except Exception as e:
        print(f"Failed to fetch data: {e}")
        return

    grouped = {}
    seen_ids = set()

    for dep in departures:
        parsed_items = parse_departure(dep, now)
        for parsed in parsed_items:
            uid = parsed["unique_id"]
            if uid in seen_ids:
                continue
            seen_ids.add(uid)
            for group in parsed["groups"]:
                if group == "Unknown Direction" or group == "Southbound":
                    continue
                grouped.setdefault(group, []).append((parsed["full_rt"], parsed["output"]))

    for group in sorted(grouped.keys()):
        print(f"\n=== {group} ===\n")
        # Sort the group by real-time and take the top 3
        for _, output in sorted(grouped[group], key=lambda x: x[0])[:3]:
            print(output)

if __name__ == "__main__":
    main()
