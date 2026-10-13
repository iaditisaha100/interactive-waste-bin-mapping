"""Build the Question 2 Jupyter notebook."""
from pathlib import Path

import nbformat
from nbformat.v4 import new_code_cell, new_markdown_cell, new_notebook

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "HS25M101_Q2_TEST_2.ipynb"

cells = []

def md(text):
    cells.append(new_markdown_cell(text))

def code(text):
    cells.append(new_code_cell(text))

md(
    """# Question 2 — Mumbai 2020 tropospheric NO₂ and residents aged 65+

**Aditi Saha · HS25M101 · Master of Public Policy, IIT Tirupati**  
**Course:** Urban Informatics and Spatial Analytics

## Assigned task
Map **2020 mean tropospheric NO₂** for **Greater Mumbai**. Estimate the number and share of residents **aged 65+** living in the city's **highest-NO₂ quartile**.

## Datasets and period
- Sentinel-5P OFFL L3 NO₂ (`COPERNICUS/S5P/OFFL/L3_NO2`), calendar year **2020**
- WorldPop age–sex structures (`WorldPop/GP/100m/pop_age_sex_cons_unadj`), year **2020**

## Required outputs
1. Monthly 2020 NO₂ GIF / time slider  
2. Annual mean NO₂ map  
3. 65+ exposure map and summary table  
4. Interpretation / discussion  

## City boundary source
Greater Mumbai Urban Local Body boundary from the Indian urban-boundary release  
(Swachh Bharat Mission ULBs via [ramSeraph/indian_admin_boundaries urban release](https://github.com/ramSeraph/indian_admin_boundaries/releases/tag/urban)).  
Local file: `question2/data/mumbai_ulb_boundary.geojson` (ULB name: **GREATER MUMBAI**, code 802794).
"""
)

code(
    """# 1. Import libraries
from pathlib import Path
import json

import ee
import geemap
import geemap.colormaps as cm
import geopandas as gpd
import pandas as pd
import requests
from PIL import Image, ImageDraw

PROJECT_ID = "solar-grail-510708-p8"
print("Project ID:", PROJECT_ID)
"""
)

code(
    """# 2. Initialize Google Earth Engine
# If Initialize fails with "authorize access" or expired token, run this once:
# ee.Authenticate()
ee.Initialize(project=PROJECT_ID)
print("Google Earth Engine initialized successfully.")
"""
)

code(
    """# 3. Paths for data and webpage outputs
# Works whether the notebook kernel cwd is the repo root or question2/
if Path("question2/data/mumbai_ulb_boundary.geojson").exists():
    DATA_DIR = Path("question2/data")
    OUT_DIR = Path("web/q2/outputs")
elif Path("data/mumbai_ulb_boundary.geojson").exists():
    DATA_DIR = Path("data")
    OUT_DIR = Path("../web/q2/outputs")
else:
    raise FileNotFoundError(
        "Could not find mumbai_ulb_boundary.geojson. "
        "Open the notebook from the repo root or the question2 folder."
    )

OUT_DIR.mkdir(parents=True, exist_ok=True)
BOUNDARY_PATH = DATA_DIR / "mumbai_ulb_boundary.geojson"
print("Boundary file:", BOUNDARY_PATH.resolve())
print("Output folder:", OUT_DIR.resolve())
"""
)

code(
    """# 4. Load Greater Mumbai boundary and convert to Earth Engine
mumbai_gdf = gpd.read_file(BOUNDARY_PATH)

if mumbai_gdf.crs is None or mumbai_gdf.crs.to_epsg() != 4326:
    mumbai_gdf = mumbai_gdf.to_crs(epsg=4326)

print(mumbai_gdf[["ulbnm", "ulbcode", "distnm"]])
print("CRS:", mumbai_gdf.crs)
print("Bounds:", mumbai_gdf.total_bounds)

mumbai = geemap.geopandas_to_ee(mumbai_gdf)
print(type(mumbai))
"""
)

code(
    """# 5. Preview the city boundary
Map = geemap.Map()
Map.centerObject(mumbai, 10)
Map.addLayer(mumbai, {"color": "black"}, "Greater Mumbai ULB")
Map
"""
)

md(
    """## 6. Sentinel-5P tropospheric NO₂ for 2020

We use the offline L3 product and the band  
`tropospheric_NO2_column_number_density` (mol/m²).

Pixels with cloud fraction ≥ 0.3 are masked before averaging.  
Annual and monthly means use the same calendar year **2020** and the same visualisation scale.
"""
)

code(
    """# 6. Load and filter Sentinel-5P NO2 for 2020
NO2_BAND = "tropospheric_NO2_column_number_density"
CLOUD_BAND = "cloud_fraction"
START = "2020-01-01"
END = "2021-01-01"

# Shared colour scale for annual and monthly maps (mol/m2)
NO2_VIS = {
    "min": 0,
    "max": 0.0002,
    "palette": cm.palettes.YlOrRd,
}


def mask_no2(image):
    cloud = image.select(CLOUD_BAND)
    return (
        image.select(NO2_BAND)
        .updateMask(cloud.lt(0.3))
        .copyProperties(image, ["system:time_start"])
    )


no2_col = (
    ee.ImageCollection("COPERNICUS/S5P/OFFL/L3_NO2")
    .filterBounds(mumbai)
    .filterDate(START, END)
    .map(mask_no2)
)

print("Number of NO2 images in 2020 after filtering:", no2_col.size().getInfo())
"""
)

code(
    """# 7. Annual mean tropospheric NO2 (2020)
no2_annual = no2_col.mean().clip(mumbai)

Map_no2 = geemap.Map()
Map_no2.centerObject(mumbai, 10)
Map_no2.addLayer(no2_annual, NO2_VIS, "2020 mean tropospheric NO2")
Map_no2.addLayer(mumbai, {"color": "black"}, "Greater Mumbai boundary")
Map_no2.add_colorbar(NO2_VIS, label="Tropospheric NO2 (mol/m2)", layer_name="NO2")
Map_no2
"""
)

code(
    """# 8. Export annual NO2 thumbnail for the webpage
region = mumbai.geometry().bounds()
thumb_no2 = no2_annual.getThumbURL({
    "min": NO2_VIS["min"],
    "max": NO2_VIS["max"],
    "palette": NO2_VIS["palette"],
    "region": region,
    "dimensions": 800,
    "format": "png",
})

annual_path = OUT_DIR / "mumbai_2020_mean_no2.png"
annual_path.write_bytes(requests.get(thumb_no2, timeout=120).content)
print("Saved", annual_path)
"""
)

md(
    """## 9. Monthly 2020 NO₂ time series

Each month uses the same cloud mask and the same colour scale as the annual map.
"""
)

code(
    """# 9. Build monthly mean NO2 images for 2020
months = list(range(1, 13))
month_names = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
]

monthly_images = []
monthly_stats = []

for month in months:
    start = ee.Date.fromYMD(2020, month, 1)
    end = start.advance(1, "month")
    month_img = (
        no2_col
        .filterDate(start, end)
        .mean()
        .clip(mumbai)
        .set("month", month)
        .set("label", month_names[month - 1] + " 2020")
    )
    monthly_images.append(month_img)

    mean_val = month_img.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=mumbai.geometry(),
        scale=1000,
        maxPixels=1e13,
        bestEffort=True,
    ).get(NO2_BAND)

    monthly_stats.append({
        "month": month,
        "label": month_names[month - 1],
        "mean_no2_mol_m2": mean_val.getInfo(),
    })

monthly_df = pd.DataFrame(monthly_stats)
print(monthly_df.to_string(index=False))
"""
)

code(
    """# 10. Interactive month map (change MONTH_TO_SHOW between 1 and 12)
MONTH_TO_SHOW = 1

month_img = monthly_images[MONTH_TO_SHOW - 1]
Map_month = geemap.Map()
Map_month.centerObject(mumbai, 10)
Map_month.addLayer(
    month_img,
    NO2_VIS,
    month_names[MONTH_TO_SHOW - 1] + " 2020 NO2",
)
Map_month.addLayer(mumbai, {"color": "black"}, "Greater Mumbai boundary")
Map_month.add_colorbar(NO2_VIS, label="Tropospheric NO2 (mol/m2)")
Map_month
"""
)

code(
    """# 11. Save monthly PNG frames and build an animated GIF for the webpage
frames_dir = OUT_DIR / "monthly_frames"
frames_dir.mkdir(exist_ok=True)
frame_paths = []

for i, img in enumerate(monthly_images):
    url = img.getThumbURL({
        "min": NO2_VIS["min"],
        "max": NO2_VIS["max"],
        "palette": NO2_VIS["palette"],
        "region": region,
        "dimensions": 700,
        "format": "png",
    })
    frame_path = frames_dir / f"no2_2020_{i+1:02d}.png"
    frame_path.write_bytes(requests.get(url, timeout=120).content)

    # Add a simple month label strip for the GIF
    im = Image.open(frame_path).convert("RGBA")
    label_bar = Image.new("RGBA", (im.width, 36), (11, 61, 74, 230))
    im2 = Image.new("RGBA", (im.width, im.height + 36), (255, 255, 255, 255))
    im2.paste(label_bar, (0, 0))
    im2.paste(im, (0, 36))
    draw = ImageDraw.Draw(im2)
    draw.text(
        (12, 8),
        f"Greater Mumbai — {month_names[i]} 2020 tropospheric NO2",
        fill=(255, 255, 255),
    )
    labeled = frames_dir / f"labeled_{i+1:02d}.png"
    im2.convert("RGB").save(labeled)
    frame_paths.append(labeled)
    print("Saved frame", labeled.name)

gif_path = OUT_DIR / "mumbai_2020_monthly_no2.gif"
frames = [Image.open(p).convert("RGB") for p in frame_paths]
frames[0].save(
    gif_path,
    save_all=True,
    append_images=frames[1:],
    duration=700,
    loop=0,
)
print("Saved GIF", gif_path)
"""
)

code(
    """# 12. Simple HTML time slider for monthly frames (webpage dynamic output)
slider_html = '''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Mumbai 2020 monthly NO2 time slider</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 16px; background: #f4f7f8; color: #10262f; }
    img { max-width: 100%; border: 1px solid #c9d6dc; border-radius: 8px; background: white; }
    input[type=range] { width: min(640px, 100%); }
  </style>
</head>
<body>
  <h2>Greater Mumbai — monthly mean tropospheric NO2 (2020)</h2>
  <p>Drag the slider to change month. Colour scale is fixed across months.</p>
  <p><b>Month: <span id="label">Jan 2020</span></b></p>
  <input id="slider" type="range" min="1" max="12" value="1" step="1">
  <div style="margin-top:12px"><img id="frame" alt="Monthly NO2 map"></div>
  <script>
    const names = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
    const slider = document.getElementById("slider");
    const frame = document.getElementById("frame");
    const label = document.getElementById("label");
    function update() {
      const m = slider.value.padStart(2, "0");
      frame.src = "monthly_frames/no2_2020_" + m + ".png";
      label.textContent = names[Number(slider.value) - 1] + " 2020";
    }
    slider.addEventListener("input", update);
    update();
  </script>
</body>
</html>
'''

slider_path = OUT_DIR / "mumbai_2020_no2_timeslider.html"
slider_path.write_text(slider_html, encoding="utf-8")
print("Saved", slider_path)
"""
)

md(
    """## 13. WorldPop residents aged 65+ (2020)

We sum male and female age bands from age 65 upwards.  
This is **gridded residential population**, not individual personal exposure.
"""
)

code(
    """# 13. Load WorldPop 2020 age-sex structures and build population aged 65+
pop_age = (
    ee.ImageCollection("WorldPop/GP/100m/pop_age_sex_cons_unadj")
    .filter(ee.Filter.eq("year", 2020))
    .first()
    .clip(mumbai)
)

band_names = pop_age.bandNames().getInfo()
print("Example bands:", band_names[:12], "...")

# EE catalog uses M_65 / F_65 (and higher ages). Fall back to lowercase if needed.
def is_age65_plus(band):
    parts = band.split("_")
    if len(parts) != 2:
        return False
    sex, age = parts[0].lower(), parts[1]
    return sex in {"m", "f"} and age.isdigit() and int(age) >= 65


age65_bands = [b for b in band_names if is_age65_plus(b)]
if not age65_bands:
    raise ValueError("No age 65+ bands found in WorldPop image.")
print("65+ bands:", age65_bands)

pop65 = pop_age.select(age65_bands).reduce(ee.Reducer.sum()).rename("pop65")

POP_VIS = {
    "min": 0,
    "max": 50,
    "palette": cm.palettes.Blues,
}

Map_pop = geemap.Map()
Map_pop.centerObject(mumbai, 10)
Map_pop.addLayer(pop65, POP_VIS, "WorldPop 2020 population aged 65+")
Map_pop.addLayer(mumbai, {"color": "black"}, "Greater Mumbai boundary")
Map_pop
"""
)

md(
    """## 14. Highest-NO₂ quartile and 65+ exposure

**Rule used:** within Greater Mumbai, pixels at or above the city-wide **75th percentile** of 2020 mean tropospheric NO₂ are treated as the **highest-NO₂ quartile**.

We then estimate:
- total residents aged 65+ in the city;
- residents aged 65+ inside that high-NO₂ zone;
- the share (%).

Satellite NO₂ is a tropospheric column density. We report population living in areas with relatively high satellite-observed NO₂ — not personal or ground-level exposure.
"""
)

code(
    """# 14. Highest-NO2 quartile mask and 65+ exposure statistics
p75 = no2_annual.reduceRegion(
    reducer=ee.Reducer.percentile([75]),
    geometry=mumbai.geometry(),
    scale=1000,
    maxPixels=1e13,
    bestEffort=True,
).get(NO2_BAND)

p75_value = ee.Number(p75)
print("75th percentile NO2 (mol/m2):", p75_value.getInfo())

high_no2 = no2_annual.gte(p75_value).selfMask().rename("high_no2")

# Population aged 65+ inside / outside high NO2 zone
pop65_in_high = pop65.updateMask(high_no2)

scale_pop = 100

stats = ee.Dictionary({
    "pop65_total": pop65.reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=mumbai.geometry(),
        scale=scale_pop,
        maxPixels=1e13,
        bestEffort=True,
    ).get("pop65"),
    "pop65_high_no2": pop65_in_high.reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=mumbai.geometry(),
        scale=scale_pop,
        maxPixels=1e13,
        bestEffort=True,
    ).get("pop65"),
    "no2_mean": no2_annual.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=mumbai.geometry(),
        scale=1000,
        maxPixels=1e13,
        bestEffort=True,
    ).get(NO2_BAND),
    "no2_p75": p75_value,
})

stats_info = stats.getInfo()
pop65_total = float(stats_info["pop65_total"] or 0)
pop65_high = float(stats_info["pop65_high_no2"] or 0)
share = 100.0 * pop65_high / pop65_total if pop65_total else float("nan")

summary = {
    "city": "Greater Mumbai",
    "year": 2020,
    "no2_city_mean_mol_m2": stats_info["no2_mean"],
    "no2_p75_mol_m2": stats_info["no2_p75"],
    "pop65_total": pop65_total,
    "pop65_in_highest_no2_quartile": pop65_high,
    "share_pop65_in_highest_no2_quartile_percent": share,
    "high_no2_rule": "Pixels >= city-wide 75th percentile of 2020 mean tropospheric NO2",
    "boundary_source": "SBM Urban Local Bodies (GREATER MUMBAI) via ramSeraph indian_admin_boundaries urban release",
    "monthly_mean_no2": monthly_stats,
}

print(pd.Series({
    "City-wide mean NO2 (mol/m2)": summary["no2_city_mean_mol_m2"],
    "NO2 75th percentile (mol/m2)": summary["no2_p75_mol_m2"],
    "Population aged 65+ (total)": round(pop65_total),
    "Population aged 65+ in highest-NO2 quartile": round(pop65_high),
    "Share of 65+ in highest-NO2 quartile (%)": round(share, 2),
}))

summary_path = OUT_DIR / "mumbai_2020_no2_exposure_summary.json"
summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
print("Saved", summary_path)

summary_table = pd.DataFrame([
    {"Metric": "City-wide mean tropospheric NO2 (mol/m2)", "Value": summary["no2_city_mean_mol_m2"]},
    {"Metric": "Highest-quartile threshold (P75, mol/m2)", "Value": summary["no2_p75_mol_m2"]},
    {"Metric": "Residents aged 65+ (city total)", "Value": round(pop65_total)},
    {"Metric": "Residents aged 65+ in highest-NO2 quartile", "Value": round(pop65_high)},
    {"Metric": "Share of 65+ in highest-NO2 quartile (%)", "Value": round(share, 2)},
])
table_path = OUT_DIR / "mumbai_2020_no2_exposure_table.csv"
summary_table.to_csv(table_path, index=False)
print(summary_table.to_string(index=False))
print("Saved", table_path)
"""
)

code(
    """# 15. Exposure map: annual NO2 with highest-quartile overlay
Map_exp = geemap.Map()
Map_exp.centerObject(mumbai, 10)
Map_exp.addLayer(no2_annual, NO2_VIS, "2020 mean NO2")
Map_exp.addLayer(
    high_no2,
    {"palette": ["#6a00a8"]},
    "Highest-NO2 quartile (P75+)",
    True,
    0.45,
)
Map_exp.addLayer(pop65, POP_VIS, "Population aged 65+", False)
Map_exp.addLayer(mumbai, {"color": "black"}, "Greater Mumbai boundary")
Map_exp.add_colorbar(NO2_VIS, label="Tropospheric NO2 (mol/m2)")
Map_exp
"""
)

code(
    """# 16. Export exposure thumbnail for the webpage
# Combine annual NO2 visualisation with a binary high-quartile highlight
exposure_rgb = no2_annual.visualize(**NO2_VIS)
high_vis = high_no2.visualize(min=0, max=1, palette=["#6a00a8"])
exposure_map = ee.ImageCollection([exposure_rgb, high_vis]).mosaic().clip(mumbai)

thumb_exp = exposure_map.getThumbURL({
    "region": region,
    "dimensions": 800,
    "format": "png",
})
exposure_path = OUT_DIR / "mumbai_2020_no2_65plus_exposure.png"
exposure_path.write_bytes(requests.get(thumb_exp, timeout=120).content)
print("Saved", exposure_path)
"""
)

md(
    """## 17. Discussion notes (also summarised on the webpage)

After you run all cells, open `web/q2/index.html` (or the hosted `/q2/` page) for the maps, GIF/time slider, table, and written interpretation.

### What the analysis measures
- **Spatial pattern:** where 2020 mean tropospheric NO₂ is higher inside Greater Mumbai  
- **Temporal pattern:** month-to-month NO₂ through 2020 (same scale)  
- **Exposure summary:** share of WorldPop residents aged 65+ living in the highest-NO₂ quartile  

### Important limitations
- S5P NO₂ is a **tropospheric column** (~3.5–7 km pixels), not roadside or personal exposure  
- Cloud masking and monsoon months can reduce valid observations  
- WorldPop is a modelled 100 m residential surface for 2020; age bands are estimates  
- The P75 rule is a transparent city-specific definition of “relatively high”, not a health standard  
"""
)

code(
    """# 18. List webpage output files
print("Webpage outputs in", OUT_DIR)
for p in sorted(OUT_DIR.rglob("*")):
    if p.is_file():
        print("-", p.relative_to(OUT_DIR), f"({p.stat().st_size} bytes)")
"""
)

nb = new_notebook(
    cells=cells,
    metadata={
        "kernelspec": {
            "display_name": "Python 3 (ipykernel)",
            "language": "python",
            "name": "python3",
        },
        "language_info": {
            "name": "python",
            "pygments_lexer": "ipython3",
        },
    },
)
nbformat.write(nb, OUT)
print("Wrote", OUT)
