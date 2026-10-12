# Question 2 — Mumbai 2020 NO₂ and residents aged 65+

**Student:** Aditi Saha · HS25M101  
**Notebook to submit:** `trial.ipynb`

## Task
Map 2020 mean tropospheric NO₂ for Greater Mumbai; estimate number/share of residents aged 65+ in the city’s highest-NO₂ quartile (P75).

## Main files

| Path | Role |
|------|------|
| `trial.ipynb` | **Your Question 2 notebook** (run in Jupyter) |
| `export_from_trial.py` | Optional: re-export maps/GIF/JSON without Map widgets |
| `../dataset/Mumbai_boundary.geojson` | Greater Mumbai ULB boundary |
| `../web/q2/index.html` | Hosted results page |
| `../web/q2/outputs/` | Maps, GIF, time slider, summary JSON/CSV |

## Boundary source
Greater Mumbai ULB (**GREATER MUMBAI**, code **802794**) from the [Indian urban-boundary release](https://github.com/ramSeraph/indian_admin_boundaries/releases/tag/urban).

## How to run
1. Open `trial.ipynb` with the `uisa_2026` kernel.
2. Run all cells (`ee.Initialize` uses project `solar-grail-510708-p8`).
3. Exports go to `web/q2/outputs/` and the page `web/q2/index.html` reads them.

## Latest computed results (2020)
- City-wide mean NO₂ ≈ `8.61e-05` mol/m²  
- P75 threshold ≈ `1.04e-04` mol/m²  
- Residents aged 65+ ≈ **731,666**  
- 65+ in highest-NO₂ quartile ≈ **238,328**  
- Share ≈ **32.6%**

## Live page
https://interactive-waste-bin-mapping.vercel.app/q2/
