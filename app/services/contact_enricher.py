import re
import httpx
from bs4 import BeautifulSoup


async def enrich_contact(website: str | None):
    """
    Extract publicly available business contact information
    from the business's official website.
    """

    result = {
        "email": None,
        "phone": None,
        "contact_pages_checked": [],
        "status": "NOT_FOUND"
    }

    if not website:
        result["status"] = "NO_WEBSITE"
        return result

    if not website.startswith(("http://", "https://")):
        website = f"https://{website}"

    headers = {
        "User-Agent": (
            "Mozilla/5.0 "
            "(compatible; ForeignClientEngine/0.3)"
        )
    }

    try:
        async with httpx.AsyncClient(
            timeout=15,
            follow_redirects=True,
            headers=headers
        ) as client:

            response = await client.get(website)
            response.raise_for_status()

            base_url = response.url
            pages_to_check = [str(base_url)]

            soup = BeautifulSoup(
                response.text,
                "html.parser"
            )

            for link in soup.find_all("a", href=True):

                href = link["href"]

                link_text = link.get_text(
                    " ",
                    strip=True
                ).lower()

                href_lower = href.lower()

                keywords = [
                    "contact",
                    "about",
                    "get-in-touch",
                    "get_in_touch"
                ]

                if any(
                    keyword in link_text
                    or keyword in href_lower
                    for keyword in keywords
                ):

                    try:
                        full_url = str(
                            base_url.join(href)
                        )

                        if full_url not in pages_to_check:
                            pages_to_check.append(
                                full_url
                            )

                    except Exception:
                        continue

            # Check maximum 5 pages
            pages_to_check = pages_to_check[:5]

            for page_url in pages_to_check:

                try:
                    page_response = await client.get(
                        page_url
                    )

                    if page_response.status_code != 200:
                        continue

                    result[
                        "contact_pages_checked"
                    ].append(page_url)

                    soup = BeautifulSoup(
                        page_response.text,
                        "html.parser"
                    )

                    # ------------------------------------------------
                    # FIND EMAIL
                    # ------------------------------------------------

                    if not result["email"]:

                        # First check mailto links
                        mailto_link = soup.find(
                            "a",
                            href=re.compile(
                                r"^mailto:",
                                re.IGNORECASE
                            )
                        )

                        if mailto_link:

                            email = mailto_link.get(
                                "href"
                            ).replace(
                                "mailto:",
                                ""
                            ).split("?")[0]

                            if email:
                                result["email"] = email

                        # Otherwise search page text
                        if not result["email"]:

                            text = soup.get_text(
                                " ",
                                strip=True
                            )

                            emails = re.findall(
                                r"[A-Za-z0-9._%+-]+"
                                r"@"
                                r"[A-Za-z0-9.-]+"
                                r"\.[A-Za-z]{2,}",
                                text
                            )

                            filtered_emails = [
                                email
                                for email in emails
                                if not any(
                                    bad in email.lower()
                                    for bad in [
                                        "example.com",
                                        "email.com",
                                        "wixpress.com",
                                        "sentry.io"
                                    ]
                                )
                            ]

                            if filtered_emails:
                                result["email"] = (
                                    filtered_emails[0]
                                )

                    # ------------------------------------------------
                    # FIND PHONE
                    # ------------------------------------------------

                    if not result["phone"]:

                        # First check tel links
                        tel_link = soup.find(
                            "a",
                            href=re.compile(
                                r"^tel:",
                                re.IGNORECASE
                            )
                        )

                        if tel_link:

                            phone = tel_link.get(
                                "href"
                            ).replace(
                                "tel:",
                                ""
                            )

                            if phone:
                                result["phone"] = phone

                        # Otherwise search page text
                        if not result["phone"]:

                            text = soup.get_text(
                                " ",
                                strip=True
                            )

                            phones = re.findall(
                                r"(?:\+?\d{1,3}[\s.-]?)?"
                                r"(?:\(?\d{2,4}\)?[\s.-]?)"
                                r"\d{3,4}[\s.-]?\d{3,4}",
                                text
                            )

                            if phones:
                                result["phone"] = (
                                    phones[0].strip()
                                )

                    # Stop if both were found
                    if (
                        result["email"]
                        and result["phone"]
                    ):
                        break

                except Exception:
                    continue

        # ------------------------------------------------
        # FINAL STATUS
        # ------------------------------------------------

        if result["email"] or result["phone"]:
            result["status"] = "FOUND"

        return result

    except Exception as error:

        result["status"] = "ERROR"
        result["error"] = str(error)

        return result