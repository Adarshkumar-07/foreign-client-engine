import httpx


async def discover_leads(
    city: str,
    category: str,
    country: str,
    limit: int = 10
):
    """
    Discover businesses from OpenStreetMap data.

    This is the zero-cost MVP provider.
    Later, additional providers can be added without
    changing the rest of the application.
    """

    search_query = f"{category}, {city}, {country}"

    headers = {
        "User-Agent": "ForeignClientEngine/0.1"
    }

    try:
        async with httpx.AsyncClient(
            timeout=20,
            headers=headers
        ) as client:

            geocode_response = await client.get(
                "https://nominatim.openstreetmap.org/search",
                params={
                    "q": search_query,
                    "format": "json",
                    "limit": 1
                }
            )

            geocode_response.raise_for_status()

            locations = geocode_response.json()

            if not locations:
                return []

            location = locations[0]

            lat = float(location["lat"])
            lon = float(location["lon"])

            radius = 10000

            overpass_query = f"""
            [out:json][timeout:25];

            (
                node
                  ["name"]
                  ["amenity"]
                  (around:{radius},{lat},{lon});

                way
                  ["name"]
                  ["amenity"]
                  (around:{radius},{lat},{lon});

                relation
                  ["name"]
                  ["amenity"]
                  (around:{radius},{lat},{lon});
            );

            out center tags;
            """

            overpass_response = await client.post(
                "https://overpass-api.de/api/interpreter",
                data=overpass_query
            )

            overpass_response.raise_for_status()

            elements = overpass_response.json().get(
                "elements",
                []
            )

            leads = []

            category_lower = category.lower()

            for item in elements:

                tags = item.get("tags", {})

                name = tags.get("name")

                if not name:
                    continue

                amenity = tags.get(
                    "amenity",
                    ""
                ).lower()

                healthcare = tags.get(
                    "healthcare",
                    ""
                ).lower()

                shop = tags.get(
                    "shop",
                    ""
                ).lower()

                combined_type = (
                    f"{amenity} "
                    f"{healthcare} "
                    f"{shop}"
                )

                if category_lower not in combined_type:

                    category_map = {
                        "dentist": "dentist",
                        "doctor": "doctor",
                        "restaurant": "restaurant",
                        "cafe": "cafe",
                        "hotel": "hotel",
                        "pharmacy": "pharmacy",
                        "gym": "fitness"
                    }

                    expected = category_map.get(
                        category_lower,
                        category_lower
                    )

                    if expected not in combined_type:
                        continue

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
                        "business_name": name,
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

    except Exception as e:
        return {
            "error": str(e),
            "leads": []
        }