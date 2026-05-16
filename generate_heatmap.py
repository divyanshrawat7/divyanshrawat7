import requests
import json
import os
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont

USERNAME = os.environ.get("GITHUB_USERNAME", "divyanshrawat7")
TOKEN    = os.environ.get("GITHUB_TOKEN", "")

# ── Fetch contribution data via GitHub GraphQL API ──────────────────────────
def fetch_contributions():
    query = """
    query($username: String!) {
      user(login: $username) {
        contributionsCollection {
          contributionCalendar {
            weeks {
              contributionDays {
                date
                contributionCount
              }
            }
          }
        }
      }
    }
    """
    headers = {"Authorization": f"bearer {TOKEN}"}
    response = requests.post(
        "https://api.github.com/graphql",
        json={"query": query, "variables": {"username": USERNAME}},
        headers=headers,
        timeout=15
    )
    data = response.json()
    weeks = (
        data["data"]["user"]
           ["contributionsCollection"]
           ["contributionCalendar"]
           ["weeks"]
    )
    contrib_map = {}
    for week in weeks:
        for day in week["contributionDays"]:
            contrib_map[day["date"]] = day["contributionCount"]
    return contrib_map

# ── Color mapping (GitHub dark mode style) ───────────────────────────────────
def color_for(count):
    if count == 0:  return (22,  27,  34)    # dark empty box
    if count <= 2:  return (14,  68,  41)    # darkest green
    if count <= 5:  return (0,   109, 50)    # medium dark green
    if count <= 9:  return (38,  166, 65)    # bright green
    return              (57,  211, 83)       # brightest green

# ── Build calendar per month ─────────────────────────────────────────────────
def days_in_month(year, month):
    if month == 12:
        return (datetime(year + 1, 1, 1) - datetime(year, 12, 1)).days
    return (datetime(year, month + 1, 1) - datetime(year, month, 1)).days

def generate_heatmap(contrib_map):
    BOX         = 13
    GAP         = 2
    MONTH_GAP   = 10
    LABEL_H     = 20
    PADDING     = 16
    COLS        = 7

    BG_COLOR    = (13, 17, 23)       # dark background
    TEXT_COLOR  = (139, 148, 158)    # muted light text
    BORDER_COLOR= (48, 54, 61)       # subtle border

    MONTHS      = ["Jan","Feb","Mar","Apr","May","Jun",
                   "Jul","Aug","Sep","Oct","Nov","Dec"]

    now    = datetime.today()
    months = []
    for i in range(11, -1, -1):
        year  = (now.replace(day=1) - timedelta(days=i*28)).year
        month = (now.replace(day=1) - timedelta(days=i*28)).month
        months.append((year, month))

    def month_width(year, month):
        d         = days_in_month(year, month)
        first_dow = datetime(year, month, 1).weekday()
        first_dow = (first_dow + 1) % 7
        total_cells = first_dow + d
        cols      = -(-total_cells // COLS)
        return cols * (BOX + GAP) - GAP

    total_width  = PADDING * 2 + sum(month_width(y, m) for y, m in months) + MONTH_GAP * (len(months) - 1)
    total_height = PADDING * 2 + LABEL_H + COLS * (BOX + GAP) - GAP + 30

    img  = Image.new("RGB", (total_width, total_height), BG_COLOR)
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 11)
    except Exception:
        font = ImageFont.load_default()

    x = PADDING

    for year, month in months:
        draw.text((x, PADDING), f"{MONTHS[month-1]} {year}", fill=TEXT_COLOR, font=font)

        d         = days_in_month(year, month)
        first_dow = datetime(year, month, 1).weekday()
        first_dow = (first_dow + 1) % 7

        for day in range(1, d + 1):
            cell  = first_dow + day - 1
            col   = cell // COLS
            row   = cell % COLS
            bx    = x + col * (BOX + GAP)
            by    = PADDING + LABEL_H + row * (BOX + GAP)
            date_str = f"{year}-{month:02d}-{day:02d}"
            count = contrib_map.get(date_str, 0)
            color = color_for(count)
            draw.rectangle([bx, by, bx + BOX, by + BOX], fill=color, outline=BORDER_COLOR, width=1)

        x += month_width(year, month) + MONTH_GAP

    # ── Legend ────────────────────────────────────────────────────────────────
    legend_colors = [
        (22, 27, 34), (14, 68, 41),
        (0, 109, 50), (38, 166, 65), (57, 211, 83)
    ]
    lx = PADDING
    ly = total_height - PADDING - BOX
    draw.text((lx, ly), "Less", fill=TEXT_COLOR, font=font)
    lx += 30
    for color in legend_colors:
        draw.rectangle([lx, ly, lx + BOX, ly + BOX], fill=color, outline=BORDER_COLOR, width=1)
        lx += BOX + GAP + 2
    draw.text((lx + 2, ly), "More", fill=TEXT_COLOR, font=font)

    img.save("heatmap.png")
    print(f"Heatmap saved → heatmap.png  ({total_width}x{total_height}px)")

# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"Fetching contributions for @{USERNAME} ...")
    contrib_map = fetch_contributions()
    print(f"  Got {len(contrib_map)} days of data.")
    generate_heatmap(contrib_map)
