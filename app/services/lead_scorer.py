def calculate_lead_score(
    website_data: dict,
    rating: float | None = None,
    reviews: int | None = None
):

    score = 0
    reasons = []

    # No website
    if website_data["status"] == "NO_WEBSITE":
        score += 40
        reasons.append("No official website")

    # Website unreachable
    elif website_data["status"] == "UNREACHABLE":
        score += 30
        reasons.append("Website is unreachable")

    # Existing website problems
    else:

        problems = website_data.get("problems", [])

        if "Missing mobile viewport tag" in problems:
            score += 15
            reasons.append("Potential mobile optimization issue")

        if "No clear call-to-action detected" in problems:
            score += 10
            reasons.append("Weak conversion call-to-action")

        if "No contact form detected" in problems:
            score += 10
            reasons.append("No contact form")

        if "Missing page title" in problems:
            score += 5
            reasons.append("Missing SEO page title")

        if "Missing meta description" in problems:
            score += 5
            reasons.append("Missing meta description")

    # Strong business profile means more potential value
    if rating and rating >= 4.5:
        score += 10
        reasons.append("Strong customer rating")

    if reviews and reviews >= 20:
        score += 10
        reasons.append("Established customer review presence")

    # Limit score
    score = min(score, 100)

    if score >= 80:
        priority = "VERY_HIGH"
    elif score >= 60:
        priority = "HIGH"
    elif score >= 40:
        priority = "MEDIUM"
    else:
        priority = "LOW"

    if website_data["status"] == "NO_WEBSITE":
        recommended_service = "NEW_BUSINESS_WEBSITE"

    elif score >= 60:
        recommended_service = "WEBSITE_REDESIGN_OR_IMPROVEMENT"

    else:
        recommended_service = "MANUAL_REVIEW"

    return {
        "lead_score": score,
        "priority": priority,
        "recommended_service": recommended_service,
        "reasons": reasons
    }