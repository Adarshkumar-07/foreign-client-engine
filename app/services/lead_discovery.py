import asyncio
import httpx


NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"

OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]


async def get_coordinates(
    client: httpx.AsyncClient,
    city: str,
    country: str
):
    response = await client.get(
        NOMINATIM_URL,
        params={
            "q": f"{city}, {country}",
            "format": "json",
            "limit": 1
        }
    )

    response.raise_for_status()

    locations = response.json()

    if not locations:
        return None, None

    return (
        float(locations[0]["lat"]),
        float(locations[0]["lon"])
    )


async def query_overpass(
    client: httpx.AsyncClient,
    query: str
):
    last_error = None

    for endpoint in OVERPASS_ENDPOINTS:

        try:
            response = await client.post(
                endpoint,
                content=query,
                headers={
                    "Content-Type": "text/plain"
                },
                timeout=30
            )

            response.raise_for_status()

            data = response.json()

            return data.get("elements", [])

        except (
            httpx.ConnectError,
            httpx.ConnectTimeout,
            httpx.ReadTimeout,
            httpx.HTTPStatusError,
            httpx.RequestError
        ) as error:

            last_error = error

            await asyncio.sleep(1)

    raise RuntimeError(
        f"Overpass service unavailable: {last_error}"
    )


async def discover_leads(
    city: str,
    category: str,
    country: str,
    limit: int = 10
):
    """
    Discover businesses using OpenStreetMap.

    Zero-cost MVP provider.
    Uses Nominatim for geocoding and
    multiple Overpass servers for resilience.
    """

    try:

        headers = {
            "User-Agent": (
                "ForeignClientEngine/0.5 "
                "(business research application)"
            )
        }

        timeout = httpx.Timeout(
            connect=10,
            read=35,
            write=35,
            pool=10
        )

        async with httpx.AsyncClient(
            timeout=timeout,
            headers=headers,
            follow_redirects=True
        ) as client:

            # ------------------------------------------------
            # GEOCODE CITY
            # ------------------------------------------------

            lat, lon = await get_coordinates(
                client,
                city,
                country
            )

            if lat is None or lon is None:

                return {
                    "error": (
                        f"Could not locate {city}, {country}."
                    ),
                    "leads": []
                }

            # ------------------------------------------------
            # CATEGORY FILTER
            # ------------------------------------------------

            category_lower = category.lower().strip()

            category_map = {

                "dentist": [
                    '["amenity"="dentist"]',
                    '["healthcare"="dentist"]'
                ],

                "doctor": [
                    '["amenity"="doctors"]',
                    '["healthcare"="doctor"]'
                ],

                "restaurant": [
                    '["amenity"="restaurant"]'
                ],

                "cafe": [
                    '["amenity"="cafe"]'
                ],

                "hotel": [
                    '["tourism"="hotel"]'
                ],

                "pharmacy": [
                    '["amenity"="pharmacy"]'
                ],

                "gym": [
                    '["leisure"="fitness_centre"]',
                    '["sport"="fitness"]'
                ]
            }

            filters = category_map.get(
                category_lower
            )

            if filters is None:

                # Generic fallback for unknown categories.
                filters = [
                    '["name"]'
                ]

            radius = 10000

            query_parts = []

            for item_filter in filters:

                query_parts.append(
                    f"""
                    node
                        {item_filter}
                        (around:{radius},{lat},{lon});

                    way
                        {item_filter}
                        (around:{radius},{lat},{lon});

                    relation
                        {item_filter}
                        (around:{radius},{lat},{lon});
                    """
                )

            overpass_query = f"""
            [out:json][timeout:30];

            (
                {"".join(query_parts)}
            );

            out center tags;
            """

            # ------------------------------------------------
            # QUERY OVERPASS
            # ------------------------------------------------

            elements = await query_overpass(
                client,
                overpass_query
            )

            # ------------------------------------------------
            # CONVERT TO LEADS
            # ------------------------------------------------

            leads = []

            seen_names = set()

            for item in elements:

                tags = item.get(
                    "tags",
                    {}
                )

                name = tags.get("name")

                if not name:
                    continue

                normalized_name = (
                    name.strip().lower()
                )

                if normalized_name in seen_names:
                    continue

                seen_names.add(
                    normalized_name
                )

                website = (
                    tags.get("website")
                    or tags.get("contact:website")
                    or ""
                )

                phone = (
                    tags.get("phone")
                    or tags.get("contact:phone")
                    or ""
                )

                email = (
                    tags.get("email")
                    or tags.get("contact:email")
                    or ""
                )

                leads.append(
                    {
                        "business_name": name.strip(),
                        "country": country,
                        "city": city,
                        "category": category,
                        "website": website,
                        "phone": phone,
                        "email": email,
                        "source": "OPENSTREETMAP"
                    }
                )

                if len(leads) >= limit:
                    break

            return leads

    except Exception as error:

        return {
            "error": (
                "Business discovery service is "
                "temporarily unavailable."
            ),
            "details": str(error),
            "leads": []
        }