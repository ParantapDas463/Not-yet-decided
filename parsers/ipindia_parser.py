from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
import warnings

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)


class IPIndiaParser:

    def __init__(self, html):
        self.soup = BeautifulSoup(html, "lxml")

    def _clean(self, text):
        if not text:
            return None
    
        text = " ".join(text.split()).strip()
    
        # Fix spacing introduced by nested HTML spans
        text = text.replace(" - ", "-")
        text = text.replace("- ", "-")
        text = text.replace(" -", "-")
    
        return text

    def _get_field(self, label):
        """
        Extract value from rows like:

        <tr>
            <td>Invention Title</td>
            <td>...</td>
        </tr>
        """

        for row in self.soup.find_all("tr"):
            cells = row.find_all("td", recursive=False)

            if len(cells) >= 2:
                key = self._clean(cells[0].get_text(" ", strip=True))

                if key == label:
                    return self._clean(
                        cells[1].get_text(" ", strip=True)
                    )

        return None

    def _get_people(self, section_name):
        """
        Extract Inventor or Applicant table.
        """

        people = []

        # Find the row containing "Inventor" / "Applicant"
        section_row = None

        for row in self.soup.find_all("tr"):
            text = self._clean(row.get_text(" ", strip=True))

            if text == section_name:
                section_row = row
                break

        if not section_row:
            return people

        # The next row contains the nested table
        next_row = section_row.find_next_sibling("tr")

        if not next_row:
            return people

        table = next_row.find("table")

        if not table:
            return people

        rows = table.find_all("tr")

        # Skip header
        for row in rows[1:]:
            cells = row.find_all("td")

            if len(cells) < 4:
                continue

            people.append({
                "name": self._clean(cells[0].get_text(" ", strip=True)),
                "address": self._clean(cells[1].get_text(" ", strip=True)),
                "country": self._clean(cells[2].get_text(" ", strip=True)),
                "nationality": self._clean(cells[3].get_text(" ", strip=True))
            })

        return people

    def get_patent(self):

        patent = {
            "title": self._get_field("Invention Title"),

            "publication_number":
                self._get_field("Publication Number"),

            "publication_date":
                self._get_field("Publication Date"),

            "publication_type":
                self._get_field("Publication Type"),

            "application_number":
                self._get_field("Application Number"),

            "filing_date":
                self._get_field("Application Filing Date"),

            "priority_number":
                self._get_field("Priority Number"),

            "priority_country":
                self._get_field("Priority Country"),

            "priority_date":
                self._get_field("Priority Date"),

            "field_of_invention":
                self._get_field("Field Of Invention"),

            "ipc":
                self._get_field("Classification (IPC)"),

            "inventors":
                self._get_people("Inventor"),

            "applicants":
                self._get_people("Applicant")
        }

        # Abstract
        abstract = None

        for td in self.soup.find_all("td"):
            text = self._clean(td.get_text(" ", strip=True))

            if text and text.startswith("Abstract:"):
                abstract = text
                break

        if abstract:
            abstract = abstract.replace("Abstract:", "", 1)
            abstract = self._clean(abstract)

            if abstract.upper().startswith("ABSTRACT:"):
                abstract = abstract[9:].strip()

        patent["abstract"] = abstract

        # Complete specification
        specification = self.soup.find(
            "textarea",
            {"id": "COMPLETE_SPECIFICATION"}
        )

        if specification:
            patent["complete_specification"] = self._clean(
                specification.get_text()
            )
        else:
            patent["complete_specification"] = None

        return patent