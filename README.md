# interactive-waste-bin-mapping

Coursework for Aditi Saha (HS25M101).

Question 1 is the interactive waste-bin map:

- `HS25M101_Q1_Interactive_Map.ipynb` — notebook that builds the map
- `HS25M101_Q1_Interactive_Map.py` — the same code, for the `uisa_2026` environment
- `web/index.html` — portfolio page
- `web/waste-bins.html` — Folium map

Run it from this folder with the `uisa_2026` environment:

```
python HS25M101_Q1_Interactive_Map.py
```

Copy the QField `DCIM` folder to `HS25M101/DCIM` and run that command again before deploying. The notebook publishes the photographs into `web/photos`, and the popups load them from that folder.

On Vercel, import this repository and set the project root directory to `web`.
