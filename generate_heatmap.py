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

# ── Color mapping (GitHub-style green) ──────────────────────────────────────
def color_for(count):
    if count == 0:  return (22, 27, 34)      # dark background (GitHub dark style)
    if count <= 2:  return (14, 68, 41)      # darkest low green
    if count <= 5:  return (0,  109, 50)     # medium dark green
    if count <= 9:  return (38, 166, 65)     # bright green
    return              (57, 211, 83)        # brightest green for max commits

# ── Build calendar per month ─────────────────────────────────────────────────
def days_in_month(year, month):
    if month == 12:
        return (datetime(year + 1, 1, 1) - datetime(year, 12, 1)).days
    return (datetime(year, month + 1, 1) - datetime(year, month, 1)).days

def generate_heatmap(contrib_map):
    BOX         = 13    # box size in px
    GAP         = 2     # gap between boxes
    MONTH_GAP   = 10    # gap between months
    LABEL_H     = 20    # height for month label
    PADDING     = 16    # outer padding
    COLS        = 7     # days per row (Sun–Sat)

    MONTHS      = ["Jan","Feb","Mar","Apr","May","Jun",
                   "Jul","Aug","Sep","Oct","Nov","Dec"]

    now   = datetime.today()
    months = []
    for i in range(11, -1, -1):
        year  = (now.replace(day=1) - timedelta(days=i*28)).year
        month = (now.replace(day=1) - timedelta(days=i*28)).month
        months.append((year, month))

    # Calculate width needed per month block
    def month_width(year, month):
        d    = days_in_month(year, month)
        first_dow = datetime(year, month, 1).weekday()  # Mon=0
        first_dow = (first_dow + 1) % 7                 # shift to Sun=0
        total_cells = first_dow + d
        cols  = -(-total_cells // COLS)                 # ceiling div
        return cols * (BOX + GAP) - GAP

    total_width = PADDING * 2 + sum(month_width(y, m) for y, m in months) + MONTH_GAP * (len(months) - 1)
    total_height = PADDING * 2 + LABEL_H + COLS * (BOX + GAP) - GAP + 30  # +30 for legend

    img  = Image.new("RGB", (total_width, total_height), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 11)
    except Exception:
        font = ImageFont.load_default()

    x = PADDING

    for year, month in months:
        # Month label
        draw.text((x, PADDING), f"{MONTHS[month-1]} {year}", fill=(100, 100, 100), font=font)

        d         = days_in_month(year, month)
        first_dow = datetime(year, month, 1).weekday()
        first_dow = (first_dow + 1) % 7   # Sun=0

        for day in range(1, d + 1):
            cell  = first_dow + day - 1
            col   = cell // COLS
            row   = cell % COLS
            bx    = x + col * (BOX + GAP)
            by    = PADDING + LABEL_H + row * (BOX + GAP)
            date_str = f"{year}-{month:02d}-{day:02d}"
            count = contrib_map.get(date_str, 0)
            color = color_for(count)
            draw.rectangle([bx, by, bx + BOX, by + BOX], fill=color, outline=(200, 200, 200), width=1)

        x += month_width(year, month) + MONTH_GAP

    # ── Legend ───────────────────────────────────────────────────────────────
    legend_colors = [
        (235, 237, 240), (155, 233, 168),
        (64,  196, 99),  (48,  161, 78),  (33, 110, 57)
    ]
    legend_labels = ["0", "1-2", "3-5", "6-9", "10+"]
    lx = PADDING
    ly = total_height - PADDING - BOX
    draw.text((lx, ly), "Less", fill=(100, 100, 100), font=font)
    lx += 30
    for i, (color, label) in enumerate(zip(legend_colors, legend_labels)):
        draw.rectangle([lx, ly, lx + BOX, ly + BOX], fill=color, outline=(200, 200, 200), width=1)
        lx += BOX + GAP + 2
    draw.text((lx + 2, ly), "More", fill=(100, 100, 100), font=font)

    img.save("heatmap.png")
    print(f"Heatmap saved → heatmap.png  ({total_width}x{total_height}px)")

# ── Main ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"Fetching contributions for @{USERNAME} ...")
    contrib_map = fetch_contributions()
    print(f"  Got {len(contrib_map)} days of data.")
    generate_heatmap(contrib_map)
