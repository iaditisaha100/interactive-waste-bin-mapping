# %% [markdown]
# # Question 1 — Interactive web map of waste-bin observations
#
# **Aditi Saha · HS25M101**
#
# This notebook builds the Folium map for the QField waste-bin survey
# and writes the page that will be hosted on Vercel.
#
# The map reads `HS25M101/HS25M101.gpkg` (layer `notes_point`), joins the
# photograph paths stored in `notes_attachments`, and saves:
#
# - `web/waste-bins.html` — the interactive map
# - `web/index.html` — the portfolio page that embeds the map
# - `web/photos/` — copies of the field photographs, when the image files are available
#
# QField stores only the relative path of each photograph (`DCIM/....jpg`).
# The image files themselves have to sit next to the GeoPackage, in
# `HS25M101/DCIM/`. Put that folder there and run this notebook again
# before deploying, so the popups can load the pictures from the website
# rather than from this computer.

# %%
from html import escape
from pathlib import Path
import shutil

import folium
import geopandas as gpd
import pandas as pd
from branca.element import Element
from folium.plugins import Fullscreen

try:
    from PIL import Image
except ImportError:
    Image = None

# %%
ROOT = Path.cwd()
GPKG = ROOT / "HS25M101" / "HS25M101.gpkg"
WEB = ROOT / "web"
PHOTO_DIR = WEB / "photos"
MAP_HTML = WEB / "waste-bins.html"
PAGE_HTML = WEB / "index.html"

# Shown on every popup. Change a row's collector before mapping if you add
# another student's GeoPackage to this table.
COLLECTOR = "Aditi Saha"

# QField keeps the JPEG files beside the project, not inside the GeoPackage.
PHOTO_SEARCH_DIRS = [
    ROOT / "HS25M101" / "DCIM",
    ROOT / "HS25M101",
    ROOT / "DCIM",
    PHOTO_DIR,
]

CATEGORY_COLORS = {
    "Not segregated": "#e67e22",
    "Dry waste": "#1f78b4",
    "Wet waste": "#33a02c",
    "Segregated": "#6a3d9a",
    "Other": "#e31a1c",
    "Unspecified": "#7f7f7f",
}

# %%
def waste_category(note):
    """Group free-text field notes into a few map layers."""
    if note is None or (isinstance(note, float) and pd.isna(note)):
        return "Unspecified"
    text = str(note).strip().lower()
    if text in {"", "nan", "none"}:
        return "Unspecified"
    if "dry" in text:
        return "Dry waste"
    if "wet" in text or "green" in text:
        return "Wet waste"
    if "non" in text and "segreg" in text:
        return "Not segregated"
    if "not segreg" in text:
        return "Not segregated"
    if "segreg" in text:
        return "Segregated"
    return "Other"


def find_photo(media_path):
    """Return the local JPEG for a QField media path, if it is on disk."""
    if media_path is None or (isinstance(media_path, float) and pd.isna(media_path)):
        return None
    rel = Path(str(media_path))
    candidates = [rel, Path(rel.name)]
    for folder in PHOTO_SEARCH_DIRS:
        for candidate in candidates:
            path = folder / candidate
            if path.is_file():
                return path
    return None


def publish_photo(src, dest_dir):
    """Copy a field photo into the website folder and return its URL path.

    Pictures are scaled down so the hosted page stays small enough to deploy.
    The map then refers to `photos/<file>`, which the browser loads from the
    same site after the page is on Vercel.
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / src.name
    if Image is not None:
        with Image.open(src) as image:
            image = image.convert("RGB")
            image.thumbnail((1200, 1200))
            image.save(dest, "JPEG", quality=74, optimize=True)
    else:
        shutil.copy2(src, dest)
    return f"photos/{dest.name}"


def popup_html(row):
    title = row["title_label"]
    note = row["note_label"]
    recorded = row["recorded_label"]
    photo_block = ""
    image_tags = []
    for url in row["photo_urls"]:
        image_tags.append(
            f'<img src="{escape(url)}" alt="Photograph of {escape(title)}"'
            ' style="display:block;width:100%;max-height:240px;object-fit:cover;'
            'margin-top:8px;border-radius:4px;">'
        )
    if image_tags:
        photo_block = "".join(image_tags)
    elif row["photo_names"]:
        listed = ", ".join(escape(name) for name in row["photo_names"])
        photo_block = (
            '<p style="margin:8px 0 0;color:#8a4b08;">Photograph recorded in QField as '
            f"{listed}, but the image file is not in this project yet.</p>"
        )
    else:
        photo_block = '<p style="margin:8px 0 0;color:#666;">No photograph was attached.</p>'

    return (
        '<div style="width:280px;font-family:Segoe UI,sans-serif;font-size:13px;line-height:1.4;">'
        f"<strong>{escape(title)}</strong><br>"
        f"<b>Collected by:</b> {escape(row['collector'])}<br>"
        f"<b>Field note:</b> {escape(note)}<br>"
        f"<b>Category:</b> {escape(row['category'])}<br>"
        f"<b>Recorded:</b> {escape(recorded)}<br>"
        f"<b>Latitude, longitude:</b> {row['lat']:.5f}, {row['lon']:.5f}"
        f"{photo_block}</div>"
    )

# %%
points = gpd.read_file(GPKG, layer="notes_point")
attachments = gpd.read_file(GPKG, layer="notes_attachments")

if points.crs is None or points.crs.to_epsg() != 4326:
    points = points.to_crs(epsg=4326)

photos = (
    attachments.dropna(subset=["media"])
    .groupby("note_uuid")["media"]
    .apply(list)
    .rename("media_files")
)
points = points.merge(photos, left_on="uuid", right_index=True, how="left")
points["collector"] = COLLECTOR
points["category"] = points["note"].map(waste_category)
points["title_label"] = points["title"].fillna("Untitled observation").str.strip()
points["note_label"] = points["note"].fillna("No field note").str.strip()
points["recorded_label"] = (
    pd.to_datetime(points["timestamp"], utc=True).dt.strftime("%d %b %Y, %H:%M UTC")
)
points["lat"] = points.geometry.y
points["lon"] = points.geometry.x

published_urls = []
published_names = []
missing = []
for media_files in points["media_files"]:
    files = media_files if isinstance(media_files, list) else []
    urls = []
    for media in files:
        src = find_photo(media)
        if src is None:
            missing.append(media)
        else:
            urls.append(publish_photo(src, PHOTO_DIR))
    published_urls.append(urls)
    published_names.append(files)

points["photo_urls"] = published_urls
points["photo_names"] = published_names

print(f"Observations: {len(points)}")
print(f"Attachment records: {len(attachments)}")
print(f"Photographs found on disk: {sum(len(urls) for urls in points['photo_urls'])}")
print(f"Photographs named in QField but missing as files: {len(missing)}")
print(points["category"].value_counts().to_string())

# %%
center = [points["lat"].mean(), points["lon"].mean()]
m = folium.Map(
    location=center,
    zoom_start=16,
    tiles=None,
    control_scale=True,
)

folium.TileLayer("OpenStreetMap", name="OpenStreetMap").add_to(m)
folium.TileLayer(
    tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    attr="Esri, Maxar, Earthstar Geographics",
    name="Satellite imagery",
).add_to(m)

for category, color in CATEGORY_COLORS.items():
    subset = points[points["category"] == category]
    if subset.empty:
        continue
    group = folium.FeatureGroup(name=f"{category} ({len(subset)})")
    for _, row in subset.iterrows():
        folium.CircleMarker(
            location=[row["lat"], row["lon"]],
            radius=7,
            color="#ffffff",
            weight=1,
            fill=True,
            fill_color=color,
            fill_opacity=0.92,
            tooltip=f"{row['title_label']} — {row['collector']}",
            popup=folium.Popup(popup_html(row), max_width=320),
        ).add_to(group)
    group.add_to(m)

legend_rows = "".join(
    (
        "<div style='margin:2px 0;'>"
        f"<span style='display:inline-block;width:10px;height:10px;border-radius:50%;"
        f"background:{color};margin-right:6px;'></span>{escape(name)}</div>"
    )
    for name, color in CATEGORY_COLORS.items()
    if (points["category"] == name).any()
)
legend = f"""
<div style="position:fixed;bottom:36px;left:12px;z-index:9999;background:#fff;
padding:8px 10px;border-radius:6px;box-shadow:0 1px 4px rgba(0,0,0,.25);
font-family:Segoe UI,sans-serif;font-size:12px;line-height:1.35;">
<b>Waste bins, IIT Tirupati</b><br>
Collected by {escape(COLLECTOR)}<br>
{legend_rows}
</div>
"""
m.get_root().html.add_child(Element(legend))
Fullscreen(position="topleft").add_to(m)
folium.LayerControl(collapsed=False).add_to(m)

minx, miny, maxx, maxy = points.total_bounds
m.fit_bounds([[miny, minx], [maxy, maxx]], padding=(24, 24))

WEB.mkdir(parents=True, exist_ok=True)
m.save(MAP_HTML)
print(f"Saved {MAP_HTML}")

# %%
counts = points["category"].value_counts()
count_rows = "".join(
    f"<tr><td>{escape(name)}</td><td>{int(counts[name])}</td></tr>"
    for name in CATEGORY_COLORS
    if name in counts.index
)
photo_found = int(sum(len(urls) for urls in points["photo_urls"]))
photo_missing = len(missing)
no_photo = int(sum(len(names) == 0 for names in points["photo_names"]))

if photo_missing:
    photo_note = (
        f"<p class='warn'><strong>Photographs are not on this computer yet.</strong> "
        f"QField recorded {photo_missing} photograph file names, but those JPEG "
        f"files are not in <code>HS25M101/DCIM</code>. The popups name the missing file. "
        f"Copy the QField <code>DCIM</code> folder into <code>HS25M101/DCIM</code>, "
        f"run the notebook again, and deploy. The map already points at "
        f"<code>photos/&hellip;</code> on this website, so the pictures will load for "
        f"anyone who opens the hosted page.</p>"
    )
else:
    photo_note = (
        f"<p>{photo_found} field photographs are stored in <code>photos/</code> on this "
        f"website and open inside the popup. They are ordinary image links, so they "
        f"remain visible after the page is hosted.</p>"
    )

page = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Waste-bin observations · Aditi Saha</title>
  <style>
    :root {{ color-scheme: light; }}
    body {{ margin: 0; font-family: Georgia, "Times New Roman", serif; color: #1c1c1c; background: #f7f4ef; }}
    header {{ background: #1f3d32; color: #f7f4ef; padding: 28px 20px 22px; }}
    header, main {{ max-width: 980px; margin: 0 auto; }}
    header {{ max-width: none; }}
    header .inner, main {{ max-width: 980px; margin: 0 auto; }}
    h1 {{ font-weight: 600; font-size: 1.8rem; margin: 0 0 6px; }}
    h2 {{ font-size: 1.35rem; margin: 1.6rem 0 0.5rem; }}
    p, li {{ line-height: 1.5; }}
    .byline {{ margin: 0; font-family: "Segoe UI", sans-serif; font-size: 0.95rem; }}
    main {{ padding: 8px 20px 48px; }}
    iframe {{ width: 100%; height: 72vh; min-height: 480px; border: 1px solid #d9d3c8; border-radius: 8px; background: #fff; }}
    a {{ color: #1f3d32; }}
    table {{ border-collapse: collapse; font-family: "Segoe UI", sans-serif; font-size: 0.95rem; }}
    th, td {{ border-bottom: 1px solid #d9d3c8; text-align: left; padding: 6px 18px 6px 0; }}
    .warn {{ background: #fff6e8; border: 1px solid #e2c48a; padding: 12px 14px; border-radius: 8px; }}
    code {{ font-family: Consolas, monospace; font-size: 0.9em; }}
    .note {{ font-family: "Segoe UI", sans-serif; }}
  </style>
</head>
<body>
  <header>
    <div class="inner">
      <h1>Waste-bin observations at IIT Tirupati</h1>
      <p class="byline">Aditi Saha · HS25M101 · collected with QField on 2 September 2026</p>
    </div>
  </header>
  <main>
    <h2>Question 1 — Interactive map</h2>
    <p>Click a point for the place name, field note, category, time, coordinates, and photograph. Hover for a short tooltip. Use the layer control to switch between the street map and satellite imagery, and to turn waste categories on and off.</p>
    <p><a href="waste-bins.html">Open the map on its own page</a></p>
    <iframe src="waste-bins.html" title="Interactive map of waste-bin observations at IIT Tirupati"></iframe>

    <h2>What the survey shows</h2>
    <p>There are {len(points)} point observations from one walk around campus. The points run from the south gate and faculty quarters through the grocery, cafeteria, lecture hall complex, and labs, and up to the sports complex, Malhar and Des hostels, and the north mess. {int(counts.get("Not segregated", 0))} notes describe bins that were not segregated. Dry-waste and wet-waste bins show up mainly around the grocery, the cafeteria, and the paths toward the hostels and the north mess. {int(counts.get("Unspecified", 0))} records have no title or note. Two further notes stay in their own group: a dumping area recorded as “Too much garbage”, and one lab bin labelled only “Waste bin”.</p>
    <table>
      <thead><tr><th>Category</th><th>Observations</th></tr></thead>
      <tbody>
        {count_rows}
      </tbody>
    </table>
    <p class="note">Green-bin notes are grouped with wet waste, which is the usual campus colour code. Every popup names the student who collected that point. These records were all collected by Aditi Saha. No other student's observations are included.</p>

    <h2>Photographs</h2>
    {photo_note}
    <p class="note">Photograph files published on this site: {photo_found}. Photograph files named by QField but not in the project folder: {photo_missing}. Observations with no attachment: {no_photo}.</p>

    <h2>How to read the controls</h2>
    <ul>
      <li>The street map is the default, because hostel and building names make the bin locations easier to place. Satellite imagery is in the layer control.</li>
      <li>Each colour is a separate layer, so a category can be hidden.</li>
      <li>The scale bar and full-screen control sit on the map.</li>
    </ul>

    <h2>Question 2</h2>
    <p>Question 2 will be added on this page alongside the map above.</p>
  </main>
</body>
</html>
"""
PAGE_HTML.write_text(page, encoding="utf-8")
print(f"Saved {PAGE_HTML}")
