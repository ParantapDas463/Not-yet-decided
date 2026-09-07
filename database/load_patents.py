import json
from datetime import datetime

from database.connection import engine
from sqlalchemy import text


JSON_FILE = "data/processed/ipindia_patents.json"


def parse_date(value):
    """Convert a date string into a Python date."""

    if not value:
        return None

    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            pass

    return None


def load_patents():

    with open(
        JSON_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        data = json.load(file)

    patents = data["patents"]

    print(f"Found {len(patents)} patents in JSON.")

    inserted = 0
    skipped = 0

    with engine.begin() as connection:

        for patent in patents:

            application_number = patent.get(
                "application_number"
            )

            if not application_number:
                skipped += 1
                continue

            # Check whether this patent already exists
            result = connection.execute(
                text(
                    """
                    SELECT id
                    FROM patents
                    WHERE application_number = :application_number
                    """
                ),
                {
                    "application_number":
                        application_number
                }
            )

            if result.fetchone():
                skipped += 1
                continue

            ipc = patent.get("ipc")

            # Handle both the old string format
            # and the newer list format.
            if isinstance(ipc, list):
                ipc = ", ".join(ipc)

            connection.execute(
                text(
                    """
                    INSERT INTO patents (
                        application_number,
                        title,
                        publication_number,
                        publication_date,
                        filing_date,
                        field_of_invention,
                        ipc,
                        abstract,
                        complete_specification,
                        source
                    )
                    VALUES (
                        :application_number,
                        :title,
                        :publication_number,
                        :publication_date,
                        :filing_date,
                        :field_of_invention,
                        :ipc,
                        :abstract,
                        :complete_specification,
                        :source
                    )
                    """
                ),
                {
                    "application_number":
                        application_number,

                    "title":
                        patent.get("title"),

                    "publication_number":
                        patent.get("publication_number"),

                    "publication_date":
                        parse_date(
                            patent.get(
                                "publication_date"
                            )
                        ),

                    "filing_date":
                        parse_date(
                            patent.get(
                                "filing_date"
                            )
                        ),

                    "field_of_invention":
                        patent.get(
                            "field_of_invention"
                        ),

                    "ipc":
                        ipc,

                    "abstract":
                        patent.get("abstract"),

                    "complete_specification":
                        patent.get(
                            "complete_specification"
                        ),

                    "source":
                        patent.get(
                            "source",
                            "IP India"
                        )
                }
            )

            inserted += 1

    print()
    print("=" * 50)
    print("PATENT LOADING COMPLETE")
    print("=" * 50)
    print(f"Inserted : {inserted}")
    print(f"Skipped  : {skipped}")
    print("=" * 50)


if __name__ == "__main__":
    load_patents()