"""
Execute the Question 2 notebook and write maps/GIF/JSON into web/q2/outputs/.

From the repo root (uisa_2026 env recommended):

  python question2/run_q2_exports.py

If Earth Engine auth is expired, authenticate once first:

  python -c "import ee; ee.Authenticate(); ee.Initialize(project='solar-grail-510708-p8')"
"""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
NB = Path(__file__).resolve().parent / "HS25M101_Q2_TEST_2.ipynb"
PROJECT_ID = "solar-grail-510708-p8"


def main():
    try:
        import ee

        ee.Initialize(project=PROJECT_ID)
        print("Earth Engine initialized:", PROJECT_ID)
    except Exception as exc:
        print("Earth Engine Initialize failed:", exc)
        print(
            'Authenticate once, then retry:\n'
            '  python -c "import ee; ee.Authenticate(); '
            f'ee.Initialize(project=\'{PROJECT_ID}\')"'
        )
        sys.exit(1)

    cmd = [
        sys.executable,
        "-m",
        "jupyter",
        "nbconvert",
        "--to",
        "notebook",
        "--execute",
        "--inplace",
        str(NB),
        "--ExecutePreprocessor.timeout=3600",
        "--ExecutePreprocessor.kernel_name=python3",
    ]
    print("Executing:", NB.name)
    print("(cwd =", ROOT, ")")
    result = subprocess.run(cmd, cwd=str(ROOT))
    if result.returncode != 0:
        sys.exit(result.returncode)

    out = ROOT / "web" / "q2" / "outputs"
    print("Done. Check exports in", out)


if __name__ == "__main__":
    main()
