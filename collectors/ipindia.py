from pathlib import Path
import json
import time
import traceback

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright


# ============================================================
# URLS
# ============================================================

SEARCH_PAGE_URL = (
    "https://iprsearch.ipindia.gov.in/publicsearch"
)

SEARCH_RESULT_URL = (
    "https://iprsearch.ipindia.gov.in/"
    "PublicSearch/PublicationSearch/PatentSearchResult"
)

DETAIL_URL = (
    "https://iprsearch.ipindia.gov.in/"
    "PublicSearch/PublicationSearch/PatentDetails"
)


# ============================================================
# DIRECTORIES
# ============================================================

RAW_SEARCH_DIR = Path("data/raw/search")
RAW_PATENT_DIR = Path("data/raw/patents")
PROCESSED_DIR = Path("data/processed")

RAW_SEARCH_DIR.mkdir(
    parents=True,
    exist_ok=True
)

RAW_PATENT_DIR.mkdir(
    parents=True,
    exist_ok=True
)

PROCESSED_DIR.mkdir(
    parents=True,
    exist_ok=True
)


class IPIndiaCollector:

    def __init__(self, headless=False):

        self.headless = headless

        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None

    # ========================================================
    # START BROWSER
    # ========================================================

    def start_browser(self):

        print("\nStarting Chromium...")

        self.playwright = sync_playwright().start()

        self.browser = self.playwright.chromium.launch(
            headless=self.headless
        )

        self.context = self.browser.new_context(
            viewport={
                "width": 1400,
                "height": 900
            },
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/142.0.0.0 Safari/537.36"
            )
        )

        self.page = self.context.new_page()

        print("Chromium started.")

    # ========================================================
    # CLOSE BROWSER
    # ========================================================

    def close(self):

        print("\nClosing browser...")

        try:
            if self.context:
                self.context.close()
        except Exception:
            pass

        try:
            if self.browser:
                self.browser.close()
        except Exception:
            pass

        try:
            if self.playwright:
                self.playwright.stop()
        except Exception:
            pass

    # ========================================================
    # OPEN SEARCH PAGE
    # ========================================================

    def open_search_page(self):

        print("\nOpening IP India Public Search...")

        self.page.goto(
            SEARCH_PAGE_URL,
            wait_until="domcontentloaded",
            timeout=60000
        )

        self.page.wait_for_timeout(2000)

        print("Search page loaded.")
        print("URL:", self.page.url)

    # ========================================================
    # GET HIDDEN INPUT VALUE
    # ========================================================

    def get_hidden_value(
        self,
        soup,
        name
    ):

        element = soup.find(
            "input",
            attrs={
                "name": name
            }
        )

        if element:
            return element.get("value")

        element = soup.find(
            "input",
            attrs={
                "id": name
            }
        )

        if element:
            return element.get("value")

        return None

    # ========================================================
    # RESULT PAGE DETECTION
    # ========================================================

    def looks_like_results_page(
        self,
        html
    ):

        if not html:
            return False

        soup = BeautifulSoup(
            html,
            "lxml"
        )

        # ----------------------------------------------------
        # IMPORTANT
        #
        # Do NOT detect results using generic words such as
        # "Application Number" or "Publication Number".
        #
        # Those can also occur on the search page.
        #
        # Instead, look for the hidden fields that are actually
        # populated on the PatentSearchResult page.
        # ----------------------------------------------------

        query_string = self.get_hidden_value(
            soup,
            "QueryString"
        )

        total_pages = self.get_hidden_value(
            soup,
            "TotalPages"
        )

        total_result = self.get_hidden_value(
            soup,
            "TotalResult"
        )

        # All three must exist and be populated.
        if (
            query_string
            and total_pages
            and total_result
        ):
            return True

        return False

    # ========================================================
    # WAIT FOR MANUAL SEARCH
    # ========================================================

    def wait_for_manual_search(self):

        print("\n")
        print("=" * 70)
        print("WAITING FOR YOUR SEARCH")
        print("=" * 70)

        print("""
Chromium is now open.

Inside Chromium:

    1. Select Title (TI)
    2. Enter: lithium
    3. Solve the CAPTCHA
    4. Click Search

You can take as long as you need.

There is NO timeout for this step.

The browser will remain open until the actual search
results are detected.
""")

        print("=" * 70)
        print()

        last_url = self.page.url

        while True:

            try:

                # ------------------------------------------------
                # Check all open tabs/pages.
                # ------------------------------------------------

                pages = self.context.pages

                for candidate in pages:

                    try:

                        html = candidate.content()

                        if self.looks_like_results_page(
                            html
                        ):

                            self.page = candidate

                            print("\n")
                            print("=" * 70)
                            print("✓ RESULTS PAGE DETECTED")
                            print("=" * 70)

                            print(
                                "URL:",
                                self.page.url
                            )

                            return html

                    except Exception:
                        continue

                # ------------------------------------------------
                # Detect URL changes.
                # ------------------------------------------------

                current_url = self.page.url

                if current_url != last_url:

                    print(
                        "Browser URL changed:"
                    )

                    print(
                        current_url
                    )

                    last_url = current_url

                # ------------------------------------------------
                # Check current page.
                # ------------------------------------------------

                html = self.page.content()

                if self.looks_like_results_page(
                    html
                ):

                    print("\n")
                    print("=" * 70)
                    print("✓ RESULTS PAGE DETECTED")
                    print("=" * 70)

                    print(
                        "URL:",
                        self.page.url
                    )

                    return html

            except Exception as error:

                print(
                    "\n[Waiting] Browser check error:",
                    repr(error)
                )

            # No overall timeout.
            time.sleep(1)

    # ========================================================
    # PARSE RESULT METADATA
    # ========================================================

    def parse_result_metadata(
        self,
        html
    ):

        soup = BeautifulSoup(
            html,
            "lxml"
        )

        metadata = {

            "current_page":
                self.get_hidden_value(
                    soup,
                    "CurrentPage"
                ),

            "total_pages":
                self.get_hidden_value(
                    soup,
                    "TotalPages"
                ),

            "connection_name":
                self.get_hidden_value(
                    soup,
                    "ConnectionName"
                ),

            "query_string":
                self.get_hidden_value(
                    soup,
                    "QueryString"
                ),

            "total_result":
                self.get_hidden_value(
                    soup,
                    "TotalResult"
                ),

            "title":
                self.get_hidden_value(
                    soup,
                    "Title"
                ),

            "page":
                self.get_hidden_value(
                    soup,
                    "page"
                )
        }

        # Convert numeric fields.
        for key in [
            "current_page",
            "total_pages",
            "total_result",
            "page"
        ]:

            if metadata[key] is not None:

                try:

                    metadata[key] = int(
                        metadata[key]
                    )

                except ValueError:
                    pass

        return metadata

    # ========================================================
    # EXTRACT APPLICATION NUMBERS
    # ========================================================

    def extract_application_numbers(
        self,
        html
    ):

        soup = BeautifulSoup(
            html,
            "lxml"
        )

        applications = []

        # ----------------------------------------------------
        # Look through all text nodes.
        # ----------------------------------------------------

        for element in soup.find_all(
            string=True
        ):

            text = element.strip()

            if not text:
                continue

            tokens = (
                text
                .replace(",", " ")
                .replace(";", " ")
                .split()
            )

            for token in tokens:

                cleaned = "".join(
                    c
                    for c in token
                    if c.isdigit()
                )

                # Indian patent application numbers observed
                # in the IP India database begin with 20.
                if (
                    cleaned.startswith("20")
                    and 10 <= len(cleaned) <= 15
                ):

                    if cleaned not in applications:

                        applications.append(
                            cleaned
                        )

        return applications

    # ========================================================
    # SAVE SEARCH PAGE
    # ========================================================

    def save_search_page(
        self,
        html,
        page_number
    ):

        path = (
            RAW_SEARCH_DIR
            / f"page_{page_number}.html"
        )

        path.write_text(
            html,
            encoding="utf-8"
        )

        return path

    # ========================================================
    # LOAD SPECIFIC RESULT PAGE
    # ========================================================

    def search_page(
        self,
        page_number,
        metadata
    ):

        payload = {

            "CurrentPage":
                str(
                    metadata.get(
                        "current_page",
                        1
                    )
                ),

            "TotalPages":
                str(
                    metadata.get(
                        "total_pages",
                        ""
                    )
                ),

            "ConnectionName":
                metadata.get(
                    "connection_name",
                    "PublicationConnection"
                ),

            "QueryString":
                metadata.get(
                    "query_string",
                    ""
                ),

            "TotalResult":
                str(
                    metadata.get(
                        "total_result",
                        ""
                    )
                ),

            "Title":
                metadata.get(
                    "title",
                    ""
                ),

            # IMPORTANT:
            # This is the actual pagination parameter.
            "page":
                str(page_number)
        }

        print(
            f"\nLoading result page {page_number}..."
        )

        response = self.context.request.post(
            SEARCH_RESULT_URL,
            form=payload,
            timeout=60000
        )

        if not response.ok:

            raise RuntimeError(
                "Pagination request failed: "
                f"{response.status} "
                f"{response.status_text}"
            )

        html = response.text()

        if not self.looks_like_results_page(
            html
        ):

            # Save failed response for debugging.
            debug_path = (
                RAW_SEARCH_DIR
                / f"debug_page_{page_number}.html"
            )

            debug_path.write_text(
                html,
                encoding="utf-8"
            )

            raise RuntimeError(
                f"Page {page_number} did not "
                "return a valid result page. "
                f"Saved response to {debug_path}"
            )

        print(
            f"✓ Page {page_number} loaded."
        )

        return html

    # ========================================================
    # FETCH PATENT DETAILS
    # ========================================================

    def get_patent_details(
        self,
        application_number
    ):

        payload = {

            "ConnectionName":
                "PublicationConnection",

            "ApplicationNumber":
                application_number
        }

        response = self.context.request.post(
            DETAIL_URL,
            form=payload,
            timeout=60000
        )

        if not response.ok:

            raise RuntimeError(
                f"PatentDetails failed for "
                f"{application_number}: "
                f"{response.status} "
                f"{response.status_text}"
            )

        return response.text()

    # ========================================================
    # SAVE PATENT DETAILS
    # ========================================================

    def save_patent_html(
        self,
        application_number,
        html
    ):

        path = (
            RAW_PATENT_DIR
            / f"{application_number}.html"
        )

        path.write_text(
            html,
            encoding="utf-8"
        )

        return path

    # ========================================================
    # MAIN COLLECTION
    # ========================================================

    def collect_all(
        self,
        start_page=1,
        max_pages=1,
        fetch_details=True
    ):

        # ----------------------------------------------------
        # Start browser.
        # ----------------------------------------------------

        self.start_browser()

        try:

            # ------------------------------------------------
            # Open actual search form.
            # ------------------------------------------------

            self.open_search_page()

            # ------------------------------------------------
            # Wait indefinitely for manual search.
            # ------------------------------------------------

            html = self.wait_for_manual_search()

            # ------------------------------------------------
            # Parse metadata.
            # ------------------------------------------------

            metadata = self.parse_result_metadata(
                html
            )

            print("\n")
            print("=" * 70)
            print("SEARCH INFORMATION")
            print("=" * 70)

            print(
                "Total results :",
                metadata.get(
                    "total_result"
                )
            )

            print(
                "Total pages   :",
                metadata.get(
                    "total_pages"
                )
            )

            print(
                "QueryString   :",
                metadata.get(
                    "query_string"
                )
            )

            print(
                "Title         :",
                metadata.get(
                    "title"
                )
            )

            print("=" * 70)

            # ------------------------------------------------
            # Validate QueryString.
            # ------------------------------------------------

            if not metadata.get(
                "query_string"
            ):

                print(
                    "\nERROR: QueryString was not found."
                )

                debug_path = (
                    RAW_SEARCH_DIR
                    / "debug_result.html"
                )

                debug_path.write_text(
                    html,
                    encoding="utf-8"
                )

                print(
                    "Saved result HTML to:",
                    debug_path
                )

                input(
                    "\nPress ENTER to close Chromium..."
                )

                return

            # ------------------------------------------------
            # Validate TotalPages.
            # ------------------------------------------------

            total_pages = metadata.get(
                "total_pages"
            )

            if not total_pages:

                raise RuntimeError(
                    "TotalPages was not found."
                )

            # ------------------------------------------------
            # Determine final page.
            # ------------------------------------------------

            if max_pages is None:

                final_page = total_pages

            else:

                final_page = min(
                    total_pages,
                    start_page + max_pages - 1
                )

            all_applications = []
            all_pages = []

            # ------------------------------------------------
            # PROCESS PAGES
            # ------------------------------------------------

            for page_number in range(
                start_page,
                final_page + 1
            ):

                # Page 1 was already obtained from the
                # manual browser search.
                if page_number == 1:

                    page_html = html

                else:

                    page_html = self.search_page(
                        page_number,
                        metadata
                    )

                # Save raw search result.
                self.save_search_page(
                    page_html,
                    page_number
                )

                # Extract applications.
                applications = (
                    self.extract_application_numbers(
                        page_html
                    )
                )

                print(
                    f"\nPage {page_number}: "
                    f"{len(applications)} "
                    f"applications found."
                )

                # Display them.
                for application in applications:

                    print(
                        "   ",
                        application
                    )

                # Add unique applications.
                for application in applications:

                    if application not in (
                        all_applications
                    ):

                        all_applications.append(
                            application
                        )

                all_pages.append({

                    "page":
                        page_number,

                    "applications":
                        applications
                })

                # ------------------------------------------------
                # FETCH DETAILS
                # ------------------------------------------------

                if fetch_details:

                    for index, application in enumerate(
                        applications,
                        start=1
                    ):

                        print(
                            f"\n  [{index}/"
                            f"{len(applications)}] "
                            f"Fetching {application}..."
                        )

                        try:

                            patent_html = (
                                self.get_patent_details(
                                    application
                                )
                            )

                            path = (
                                self.save_patent_html(
                                    application,
                                    patent_html
                                )
                            )

                            print(
                                "      ✓ saved:",
                                path
                            )

                        except Exception as error:

                            print(
                                "      ✗ ERROR:",
                                repr(error)
                            )

                        # Small delay between requests.
                        time.sleep(0.3)

            # ------------------------------------------------
            # SAVE MANIFEST
            # ------------------------------------------------

            manifest = {

                "search_metadata":
                    metadata,

                "pages_collected":
                    all_pages,

                "application_numbers":
                    all_applications,

                "application_count":
                    len(
                        all_applications
                    ),

                "start_page":
                    start_page,

                "end_page":
                    final_page
            }

            manifest_path = (
                PROCESSED_DIR
                / "ipindia_collection.json"
            )

            manifest_path.write_text(
                json.dumps(
                    manifest,
                    indent=2,
                    ensure_ascii=False
                ),
                encoding="utf-8"
            )

            # ------------------------------------------------
            # COMPLETE
            # ------------------------------------------------

            print("\n")
            print("=" * 70)
            print("COLLECTION COMPLETE")
            print("=" * 70)

            print(
                "Pages collected:",
                start_page,
                "→",
                final_page
            )

            print(
                "Unique applications:",
                len(
                    all_applications
                )
            )

            print(
                "Manifest:",
                manifest_path
            )

            print("=" * 70)

            input(
                "\nPress ENTER to close Chromium..."
            )

        except Exception as error:

            # ------------------------------------------------
            # IMPORTANT:
            # Keep browser open if something fails.
            # ------------------------------------------------

            print("\n")
            print("=" * 70)
            print("COLLECTOR ERROR")
            print("=" * 70)

            print(
                repr(error)
            )

            print("\nFull traceback:")
            traceback.print_exc()

            print("\n")
            print(
                "Chromium will remain open so you can "
                "inspect the page."
            )

            input(
                "\nPress ENTER to close Chromium..."
            )

        finally:

            self.close()


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    collector = IPIndiaCollector(
        headless=False
    )

    # --------------------------------------------------------
    # TEST RUN
    #
    # Only collect page 1 for now.
    #
    # Once this works, change:
    #
    #     max_pages=1
    #
    # to:
    #
    #     max_pages=None
    #
    # to collect all pages.
    # --------------------------------------------------------

    collector.collect_all(
        start_page=1,
        max_pages=None,
        fetch_details=True
    )