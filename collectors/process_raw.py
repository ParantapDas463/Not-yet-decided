import json
from datetime import datetime, timezone
from pathlib import Path

from parsers.ipindia_parser import IPIndiaParser


RAW_DIR = Path("data/raw/patents")
OUTPUT_DIR = Path("data/processed")
OUTPUT_FILE = OUTPUT_DIR / "ipindia_patents.json"


def normalize_ipc(ipc_value):
    """
    Convert the IPC field from a comma-separated string
    into a clean list of IPC codes.
    """

    if not ipc_value:
        return []

    if isinstance(ipc_value, list):
        return [
            item.strip()
            for item in ipc_value
            if item and item.strip()
        ]

    return [
        item.strip()
        for item in ipc_value.split(",")
        if item.strip()
    ]


def process_patent(html_file):
    """
    Read one raw HTML file and convert it into
    a structured patent dictionary.
    """

    html = html_file.read_text(
        encoding="utf-8",
        errors="replace"
    )

    parser = IPIndiaParser(html)
    patent = parser.get_patent()

    # ---------------------------------------------------------
    # Normalize IPC
    # ---------------------------------------------------------

    patent["ipc"] = normalize_ipc(
        patent.get("ipc")
    )

    # ---------------------------------------------------------
    # Source / provenance information
    # ---------------------------------------------------------

    patent["source"] = "IP India"
    patent["raw_file"] = html_file.name

    # This is the time we processed the downloaded HTML,
    # NOT necessarily the time IP India originally served it.
    patent["processed_at"] = datetime.now(
        timezone.utc
    ).isoformat()

    return patent


def main():

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    html_files = sorted(
        RAW_DIR.glob("*.html")
    )

    if not html_files:
        print("No raw patent HTML files found.")
        return

    print("=" * 70)
    print("IP INDIA RAW → NORMALIZED JSON")
    print("=" * 70)

    print(f"Raw files found: {len(html_files)}")
    print()

    patents = []
    failures = []

    # ---------------------------------------------------------
    # Parse every raw HTML file
    # ---------------------------------------------------------

    for index, html_file in enumerate(
        html_files,
        start=1
    ):

        print(
            f"[{index}/{len(html_files)}] "
            f"Parsing {html_file.name}"
        )

        try:

            patent = process_patent(
                html_file
            )

            patents.append(
                patent
            )

        except Exception as e:

            print(
                f"  ERROR: {e}"
            )

            failures.append({
                "file": html_file.name,
                "error": str(e)
            })

    # ---------------------------------------------------------
    # Remove duplicate application numbers
    # ---------------------------------------------------------

    seen = set()
    unique_patents = []

    for patent in patents:

        application_number = patent.get(
            "application_number"
        )

        # If application number is missing,
        # don't silently discard the record.
        if not application_number:

            unique_patents.append(
                patent
            )

            continue

        if application_number in seen:

            continue

        seen.add(
            application_number
        )

        unique_patents.append(
            patent
        )

    # ---------------------------------------------------------
    # Build final JSON document
    # ---------------------------------------------------------

    output = {
        "source": "IP India",
        "processed_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "record_count": len(
            unique_patents
        ),
        "failed_count": len(
            failures
        ),
        "patents": unique_patents,
        "failures": failures
    }

    # ---------------------------------------------------------
    # Save JSON
    # ---------------------------------------------------------

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

    print(
        f"Raw HTML files : {len(html_files)}"
    )

    print(
        f"Parsed patents : {len(patents)}"
    )

    print(
        f"Unique patents : {len(unique_patents)}"
    )

    print(
        f"Failures       : {len(failures)}"
    )

    print()
    print(
        f"Output         : {OUTPUT_FILE}"
    )

    print("=" * 70)


if __name__ == "__main__":
    main()