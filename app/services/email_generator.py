def generate_outreach_email(lead, opportunity):

    business_name = lead.business_name
    city = lead.city
    category = lead.category.lower()

    if opportunity["recommended_offer"] == "NEW_BUSINESS_WEBSITE":

        subject = f"A website idea for {business_name}"

        body = f"""Hi,

I came across {business_name} while looking at {category} businesses in {city}.

I noticed that your business has a strong customer presence, but I couldn't find an official website for the business.

I build modern, mobile-friendly websites that help local businesses clearly showcase their services and make it easier for potential customers to contact them.

I had an idea for how a website for {business_name} could be structured around your services, customer trust, and contact or appointment requests.

If you're interested, I'd be happy to share the idea with you.

Best,
Adarsh
"""

    elif opportunity["recommended_offer"] == "WEBSITE_REPLACEMENT":

        subject = f"A website idea for {business_name}"

        body = f"""Hi,

I came across {business_name} while looking at businesses in {city}.

I noticed that there may be an issue with the current website's availability.

I build modern, mobile-friendly websites designed to clearly present services and make it easier for customers to contact a business.

I had a few ideas that could help improve the online presence of {business_name}.

Would you be open to seeing a quick website concept?

Best,
Adarsh
"""

    else:

        subject = f"A website improvement idea for {business_name}"

        body = f"""Hi,

I came across {business_name} while looking at businesses in {city}.

I took a quick look at the current online presence and noticed a few potential opportunities to improve the website experience.

I build modern, mobile-friendly websites focused on clear information, stronger calls to action, and making it easier for customers to contact the business.

I have a few ideas specifically for {business_name}.

Would you be open to seeing them?

Best,
Adarsh
"""

    return {
        "subject": subject,
        "body": body
    }