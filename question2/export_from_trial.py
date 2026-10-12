"""Run the Q2 analysis from trial.ipynb logic and write web/q2/outputs/."""
from pathlib import Path
import json

import ee
import geemap
import geopandas as gpd
import pandas as pd
import requests
from PIL import Image, ImageDraw

PROJECT_ID = "solar-grail-510708-p8"
ROOT = Path(__file__).resolve().parents[1]
BOUNDARY_PATH = ROOT / "dataset" / "Mumbai_boundary.geojson"
OUT_DIR = ROOT / "web" / "q2" / "outputs"
OUT_DIR.mkdir(parents=True, exist_ok=True)

NO2_BAND = "tropospheric_NO2_column_number_density"
CLOUD_BAND = "cloud_fraction"
# Warm teal → gold → coral palette (matches the dark webpage theme)
no2_vis = {
    "min": 0,
    "max": 0.0002,
    "palette": [
        "#071820",
        "#0b3d4a",
        "#147a7f",
        "#3dbb9a",
        "#f0c75e",
        "#f4a261",
        "#e76f51",
        "#c1121f",
    ],
}
HIGH_NO2_COLOR = "#ff6b6b"
month_names = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
]


def mask_clouds(img):
    return img.updateMask(img.select(CLOUD_BAND).lte(0.2))


def add_boundary_outline(rgb, mumbai_ee, width=3):
    """Dark fill outside the city + white ULB outline."""
    bg = (
        ee.Image.constant([7, 13, 20])
        .toByte()
        .rename(["vis-red", "vis-green", "vis-blue"])
    )
    base = bg.blend(rgb)
    outline = (
        ee.Image()
        .byte()
        .paint(mumbai_ee, 1, width)
        .selfMask()
        .visualize(palette=["ffffff"])
    )
    return base.blend(outline)


def main():
    ee.Initialize(project=PROJECT_ID)
    print("EE OK")

    mumbai_gdf = gpd.read_file(BOUNDARY_PATH)
    if mumbai_gdf.crs is None or mumbai_gdf.crs.to_epsg() != 4326:
        mumbai_gdf = mumbai_gdf.to_crs(epsg=4326)
    print(mumbai_gdf[["ulbnm", "ulbcode"]].to_string(index=False))
    mumbai_ee = geemap.geopandas_to_ee(mumbai_gdf)
    region = mumbai_ee.geometry().bounds()

    no2_2020 = (
        ee.ImageCollection("COPERNICUS/S5P/OFFL/L3_NO2")
        .filterBounds(mumbai_ee.geometry())
        .filterDate("2020-01-01", "2021-01-01")
    )
    print("NO2 images:", no2_2020.size().getInfo())

    annual_no2 = (
        no2_2020.map(mask_clouds).select(NO2_BAND).mean().clip(mumbai_ee.geometry())
    )

    annual_rgb = add_boundary_outline(annual_no2.visualize(**no2_vis), mumbai_ee)
    annual_path = OUT_DIR / "mumbai_2020_mean_no2.png"
    annual_path.write_bytes(
        requests.get(
            annual_rgb.getThumbURL(
                {
                    "region": region,
                    "dimensions": 800,
                    "format": "png",
                }
            ),
            timeout=180,
        ).content
    )
    print("Saved", annual_path)

    monthly_stats = []
    frames_dir = OUT_DIR / "monthly_frames"
    frames_dir.mkdir(exist_ok=True)
    frame_paths = []

    for m in range(1, 13):
        start = ee.Date.fromYMD(2020, m, 1)
        end = start.advance(1, "month")
        month_img = (
            no2_2020.filterDate(start, end)
            .map(mask_clouds)
            .select(NO2_BAND)
            .mean()
            .clip(mumbai_ee.geometry())
        )
        mean_val = month_img.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=mumbai_ee.geometry(),
            scale=1000,
            maxPixels=1e13,
            bestEffort=True,
        ).get(NO2_BAND)
        monthly_stats.append(
            {
                "month": m,
                "label": month_names[m - 1],
                "mean_no2_mol_m2": mean_val.getInfo(),
            }
        )

        month_rgb = add_boundary_outline(month_img.visualize(**no2_vis), mumbai_ee)
        raw_path = frames_dir / f"no2_2020_{m:02d}.png"
        raw_path.write_bytes(
            requests.get(
                month_rgb.getThumbURL(
                    {
                        "region": region,
                        "dimensions": 700,
                        "format": "png",
                    }
                ),
                timeout=180,
            ).content
        )
        im = Image.open(raw_path).convert("RGBA")
        bar = Image.new("RGBA", (im.width, 36), (7, 24, 32, 235))
        labeled = Image.new("RGBA", (im.width, im.height + 36), (255, 255, 255, 255))
        labeled.paste(bar, (0, 0))
        labeled.paste(im, (0, 36))
        draw = ImageDraw.Draw(labeled)
        draw.text(
            (12, 8),
            f"Greater Mumbai — {month_names[m - 1]} 2020 tropospheric NO2",
            fill=(255, 255, 255),
        )
        labeled_path = frames_dir / f"labeled_{m:02d}.png"
        labeled.convert("RGB").save(labeled_path)
        frame_paths.append(labeled_path)
        print("Frame", m, monthly_stats[-1]["mean_no2_mol_m2"])

    gif_path = OUT_DIR / "mumbai_2020_monthly_no2.gif"
    frames = [Image.open(p).convert("RGB") for p in frame_paths]
    frames[0].save(
        gif_path, save_all=True, append_images=frames[1:], duration=700, loop=0
    )
    print("Saved", gif_path)

    (OUT_DIR / "mumbai_2020_no2_timeslider.html").write_text(
        """<!DOCTYPE html>
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
      const m = String(slider.value).padStart(2, "0");
      frame.src = "monthly_frames/no2_2020_" + m + ".png";
      label.textContent = names[Number(slider.value) - 1] + " 2020";
    }
    slider.addEventListener("input", update);
    update();
  </script>
</body>
</html>
""",
        encoding="utf-8",
    )

    print(pd.DataFrame(monthly_stats).to_string(index=False))

    p75 = annual_no2.reduceRegion(
        reducer=ee.Reducer.percentile([75]),
        geometry=mumbai_ee.geometry(),
        scale=1000,
        maxPixels=1e13,
        bestEffort=True,
    )
    threshold = ee.Number(p75.get(NO2_BAND))
    p75_value = threshold.getInfo()
    print("P75:", p75_value)
    high_no2 = annual_no2.gte(threshold).selfMask()

    pop_image = ee.Image(
        ee.ImageCollection("WorldPop/GP/100m/pop_age_sex_cons_unadj")
        .filter(ee.Filter.eq("country", "IND"))
        .filter(ee.Filter.eq("year", 2020))
        .first()
    )
    band_names = pop_image.bandNames().getInfo()
    age65_bands = [
        b
        for b in band_names
        if "_" in b
        and b.split("_")[0] in ("M", "F", "m", "f")
        and b.split("_")[1].isdigit()
        and int(b.split("_")[1]) >= 65
    ]
    print("65+ bands:", age65_bands)
    pop65 = (
        pop_image.select(age65_bands)
        .reduce(ee.Reducer.sum())
        .rename("population_65_plus")
        .clip(mumbai_ee.geometry())
    )
    exposed_65 = pop65.updateMask(high_no2)

    exposed_population = float(
        exposed_65.reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=mumbai_ee.geometry(),
            scale=100,
            maxPixels=1e13,
            bestEffort=True,
        ).getInfo()["population_65_plus"]
        or 0
    )
    total_population = float(
        pop65.reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=mumbai_ee.geometry(),
            scale=100,
            maxPixels=1e13,
            bestEffort=True,
        ).getInfo()["population_65_plus"]
        or 0
    )
    mean_no2_value = (
        annual_no2.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=mumbai_ee.geometry(),
            scale=1000,
            maxPixels=1e13,
            bestEffort=True,
        )
        .get(NO2_BAND)
        .getInfo()
    )
    exposure_share = (
        exposed_population / total_population * 100 if total_population else float("nan")
    )

    summary = {
        "city": "Greater Mumbai",
        "year": 2020,
        "no2_city_mean_mol_m2": mean_no2_value,
        "no2_p75_mol_m2": p75_value,
        "pop65_total": total_population,
        "pop65_in_highest_no2_quartile": exposed_population,
        "share_pop65_in_highest_no2_quartile_percent": exposure_share,
        "high_no2_rule": "Pixels >= city-wide 75th percentile of 2020 mean tropospheric NO2",
        "boundary_source": "dataset/Mumbai_boundary.geojson (GREATER MUMBAI ULB; SBM / ramSeraph urban release)",
        "monthly_mean_no2": monthly_stats,
    }
    (OUT_DIR / "mumbai_2020_no2_exposure_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    pd.DataFrame(
        [
            {"Metric": "City-wide mean tropospheric NO2 (mol/m2)", "Value": mean_no2_value},
            {"Metric": "Highest-quartile threshold (P75, mol/m2)", "Value": p75_value},
            {"Metric": "Residents aged 65+ (city total)", "Value": round(total_population)},
            {
                "Metric": "Residents aged 65+ in highest-NO2 quartile",
                "Value": round(exposed_population),
            },
            {
                "Metric": "Share of 65+ in highest-NO2 quartile (%)",
                "Value": round(exposure_share, 2),
            },
        ]
    ).to_csv(OUT_DIR / "mumbai_2020_no2_exposure_table.csv", index=False)

    exposure_rgb = annual_no2.visualize(**no2_vis)
    high_vis = high_no2.visualize(min=0, max=1, palette=[HIGH_NO2_COLOR])
    exposure_map = add_boundary_outline(
        ee.ImageCollection([exposure_rgb, high_vis]).mosaic(),
        mumbai_ee,
    )
    (OUT_DIR / "mumbai_2020_no2_65plus_exposure.png").write_bytes(
        requests.get(
            exposure_map.getThumbURL(
                {"region": region, "dimensions": 800, "format": "png"}
            ),
            timeout=180,
        ).content
    )

    print("SUMMARY")
    print("mean NO2:", mean_no2_value)
    print("P75:", p75_value)
    print("pop65 total:", round(total_population))
    print("pop65 high NO2:", round(exposed_population))
    print("share %:", round(exposure_share, 2))
    print("Done ->", OUT_DIR)


if __name__ == "__main__":
    main()
