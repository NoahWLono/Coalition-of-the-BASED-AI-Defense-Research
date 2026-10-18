"""Build the portable results viewer from the saved experiment evidence."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = (
    "results/comparison.csv", "results/distributions.csv",
    "results/artifact-audit.json", "results/capacity_certificate.json",
)


def build():
    with (ROOT / SOURCES[0]).open(newline="") as stream:
        comparison = list(csv.DictReader(stream))
    with (ROOT / SOURCES[1]).open(newline="") as stream:
        distributions = [row for row in csv.DictReader(stream) if row["case"] == "baseline"]
    data = {
        "baseline": [row for row in comparison if row["case"] == "baseline"],
        "sensitivity": [row for row in comparison if row["information"] == "offline"],
        "distributions": distributions,
        "audit": json.loads((ROOT / SOURCES[2]).read_text()),
        "capacity": json.loads((ROOT / SOURCES[3]).read_text()),
        "sources": {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in SOURCES},
    }
    # Do not render malformed evidence as a successful experiment.
    assert data["audit"]["valid"] is True
    assert len(data["baseline"]) == 6
    for row in comparison:
        assert int(row["served"]) + int(row["rejected"]) == int(row["eligible"])
        assert int(row["on_time"]) + int(row["late_requests"]) == int(row["served"])
    payload = json.dumps(data, ensure_ascii=True, separators=(",", ":")).replace("<", "\\u003c")
    return (ROOT / "viewer/index.template.html").read_text().replace("__EVIDENCE_JSON__", payload)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Fail if index.html differs from the source evidence or template")
    args = parser.parse_args()
    expected = build()
    target = ROOT / "index.html"
    if args.check:
        if not target.is_file() or target.read_text() != expected:
            parser.exit(1, "Viewer is stale; run python3 scripts/build_viewer.py\n")
        print("Viewer matches all four evidence sources and the HTML template.")
    else:
        target.write_text(expected)
        print(f"Wrote {target.name} from saved experiment evidence.")


if __name__ == "__main__":
    main()
