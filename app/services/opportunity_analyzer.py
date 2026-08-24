def analyze_opportunity(lead, website_data, scoring):

    rating = lead.rating or 0
    reviews = lead.reviews or 0

    if website_data.get("status") == "NO_WEBSITE":

        opportunity = "VERY_HIGH"

        current_situation = (
            "No official website was detected for this business."
        )

        website_opportunity = (
            f"Create a professional website for the {lead.category} "
            "business with clear service information, contact options, "
            "mobile-friendly design, and conversion-focused calls to action."
        )

        sales_angle = (
            f"The business already has a {rating} customer rating and "
            f"{reviews} reviews, showing existing customer trust. "
            "A dedicated website could strengthen its online presence "
            "and make it easier for potential customers to learn about "
            "services and contact the business."
        )

        recommended_offer = "NEW_BUSINESS_WEBSITE"
        target_price = "$299"

    elif website_data.get("status") == "UNREACHABLE":

        opportunity = "HIGH"

        current_situation = (
            "The existing website could not be reached."
        )

        website_opportunity = (
            "Build a reliable modern website with clear business "
            "information and contact options."
        )

        sales_angle = (
            "The business may be losing potential customers because "
            "its online presence appears inaccessible."
        )

        recommended_offer = "WEBSITE_REPLACEMENT"
        target_price = "$299"

    else:

        problems = website_data.get("problems", [])

        if scoring.get("lead_score", 0) >= 60:
            opportunity = "HIGH"
        elif scoring.get("lead_score", 0) >= 40:
            opportunity = "MEDIUM"
        else:
            opportunity = "LOW"

        current_situation = (
            "The business has an existing website, but improvement "
            "opportunities were detected."
        )

        website_opportunity = (
            "Improve the existing website to provide a clearer "
            "customer journey, stronger calls to action, and better "
            "lead generation."
        )

        sales_angle = (
            "The current website may have opportunities for improvement, "
            "particularly in areas that affect customer engagement and "
            "conversion."
        )

        recommended_offer = "WEBSITE_REDESIGN"
        target_price = "$299"

    return {
        "opportunity_level": opportunity,
        "current_situation": current_situation,
        "business_strength": {
            "rating": rating,
            "reviews": reviews
        },
        "website_opportunity": website_opportunity,
        "recommended_offer": recommended_offer,
        "target_price": target_price,
        "sales_angle": sales_angle
    }