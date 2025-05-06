import json
from dotenv import load_dotenv
import requests
import os
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

# Load environment variables (e.g., access key for API)
load_dotenv()
ACCESS_ID = os.getenv("ACCESS_ID")  

def get_direction_group(direction, line):
    """Assign a direction group based on the bus direction and line."""
    if direction in {"Aalborg St.", "Hals", "Grindsted", "Langholt", "Vodskov", "Klarup", "Storvorde", "Uttrup Nord", "Troensevej"}:
        return ["Stationen"]
    elif direction in {"Godthåb", "City Syd", "Skelagervej", "Aalstrup", "Ferslev", "Aars", "Dall Villaby", "Skalborg"}:
        if line in {"1", "52"}:
            return ["Skalborg/Svenstrup"]
        elif line == "14":
            return ["School"]
        else:
            return ["Southbound"]
    else:
        return ["Unknown Direction"]

def parse_departure(dep, now):
    """Parse and format the bus departure data."""
    product = dep.get("ProductAtStop", {})
    line = product.get("line", "N/A")
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

    # Calculate the delay and format the status
    delay = int((full_rt - full_scheduled).total_seconds() / 60)
    if delay == 0:
        status = "On time"
    elif delay > 0:
        status = f"Late by {delay} min"

    output = f"""Line: {line}
Direction: {direction}
Scheduled: {full_scheduled.strftime("%H:%M")} | Status: {status}"""

    return [{
        "groups": get_direction_group(direction, line),
        "line": line,
        "full_rt": full_rt,
        "unique_id": unique_id,
        "output": output
    }]

def fetch_departures(access_id):
    """Fetch bus departures from the API."""
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

def generate_image(grouped_data, image_path="departures.png"):
    """Generate an image of bus departures."""
    WIDTH, HEIGHT = 480, 648
    BG_COLOR = 255  # White background
    FG_COLOR = 0    # Black text

    image = Image.new("1", (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(image)

    try:
        font = ImageFont.truetype("DejaVuSansMono.ttf", 17)  # Normal text size
        header_font = ImageFont.truetype("DejaVuSansMono-Bold.ttf", 20)  # Header text size
    except:
        font = ImageFont.load_default()
        header_font = font

    x, y = 10, 10
    line_height = font.getbbox("A")[3] - font.getbbox("A")[1] + 10
    header_height = header_font.getbbox("A")[3] - header_font.getbbox("A")[1] + 16
    separator_margin = 10

    def draw_bold_text(draw, position, text, font):
        x, y = position
        draw.text((x, y), text, font=font, fill=FG_COLOR)
        draw.text((x + 1, y), text, font=font, fill=FG_COLOR)

    def draw_separator(y):
        # Dotted separator for separation between buses or groups
        draw.line((x + 5, y, WIDTH - 10, y), fill=FG_COLOR, width=2)

    # Loop through each group of departures
    for group in sorted(grouped_data.keys(), reverse=True):
        if y + header_height >= HEIGHT:
            break
        
        # Draw the group title (e.g., "Stationen")
        draw_bold_text(draw, (x, y), f"--- {group} ---", header_font)
        y += header_height

        for _, output in sorted(grouped_data[group], key=lambda x: x[0])[:3]:
            for line in output.splitlines():
                if y + line_height >= HEIGHT:
                    break
                # Add the bus information (simplified)
                line = line.replace("Line:", "Line:")
                line = line.replace("Scheduled:", "Scheduled:")
                line = line.replace("Status:", "Status:")
                draw.text((x + 10, y), line, font=font, fill=FG_COLOR)
                y += line_height

            # Add separator between buses
            if y + line_height < HEIGHT:
                draw_separator(y)
                y += separator_margin

        # Add a bit of extra space between groups
        y += separator_margin

    # Save the image
    image.save(image_path)
    print(f"🖼 Image saved as '{image_path}'")

def main():
    now = datetime.now()
    try:
        departures = fetch_departures(ACCESS_ID)
    except Exception as e:
        print(f"Failed to fetch data: {e}")
        return

    grouped = {}
    seen_ids = set()

    # Process each departure
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
    generate_image(grouped)

if __name__ == "__main__":
    main()
