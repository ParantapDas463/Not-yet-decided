import json
from pathlib import Path

from parsers.ipindia_parser import IPIndiaParser


RAW_DIR = Path("data/raw/patents")
OUTPUT_DIR = Path("data/processed")
OUTPUT_FILE = OUTPUT_DIR / "ipindia_patents.json"


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    html_files = sorted(RAW_DIR.glob("*.html"))

    if not html_files:
        print("No raw patent HTML files found.")
        return

    print("=" * 70)
    print("IP INDIA RAW → JSON PROCESSOR")
    print("=" * 70)
    print(f"Raw files found: {len(html_files)}")
    print()

    patents = []
    failures = []

    for index, html_file in enumerate(html_files, start=1):

        print(
            f"[{index}/{len(html_files)}] "
            f"Parsing {html_file.name}"
        )

        try:
            html = html_file.read_text(
                encoding="utf-8",
                errors="replace"
            )

            parser = IPIndiaParser(html)
            patent = parser.get_patent()

            # Keep track of where this record came from.
            patent["source"] = "IP India"
            patent["raw_file"] = html_file.name

            patents.append(patent)

        except Exception as e:
            print(f"  ERROR: {e}")

            failures.append({
                "file": html_file.name,
                "error": str(e)
            })

    # ---------------------------------------------------------
    # Basic duplicate check
    # ---------------------------------------------------------

    seen = set()
    unique_patents = []

    for patent in patents:

        application_number = patent.get("application_number")

        if application_number:
            if application_number in seen:
                continue

            seen.add(application_number)

        unique_patents.append(patent)

    # ---------------------------------------------------------
    # Save JSON
    # ---------------------------------------------------------

    output = {
        "source": "IP India",
        "record_count": len(unique_patents),
        "failed_count": len(failures),
        "patents": unique_patents,
        "failures": failures
    }

    OUTPUT_FILE.write_text(
        json.dumps(
            output,
            indent=2,
            ensure_ascii=False
        ),
        encoding="utf-8"
    )

    # ---------------------------------------------------------
    # Summary
    # ---------------------------------------------------------

    print()
    print("=" * 70)
    print("PROCESSING COMPLETE")
    print("=" * 70)

    print(f"Raw HTML files : {len(html_files)}")
    print(f"Parsed patents : {len(patents)}")
    print(f"Unique patents : {len(unique_patents)}")
    print(f"Failures       : {len(failures)}")
    print()
    print(f"Output         : {OUTPUT_FILE}")
    print("=" * 70)


if __name__ == "__main__":
    main()