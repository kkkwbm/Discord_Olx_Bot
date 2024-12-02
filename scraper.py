import hikari
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import re
import random
from loguru import logger as log  # Ensure 'loguru' logger is properly imported

# Timezone offset for your location (e.g., UTC+2 for Central European Summer Time)
TIMEZONE_OFFSET = 2  # Adjust according to your local timezone

# Function to scrape OLX offers for a given subscription
# Updated function to handle image extraction better and price parsing with decimal values
def scrape(db, params):
    random_query = f"?t={random.randint(1000, 9999)}"
    url = params["url"] + random_query

    headers = {
        'Cache-Control': 'no-cache'
    }

    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.content, 'html.parser')

    listings = soup.find_all('div', class_='css-1sw7q4x', limit=20)
    new_offers = []

    now = datetime.now() - timedelta(hours=TIMEZONE_OFFSET)
    excluded_words = params.get('excluded_words', "").split()

    for listing in listings:
        link_tag = listing.find('a', class_='css-z3gu2d')
        if not link_tag:
            continue

        offer_url = "https://www.olx.pl" + link_tag.get('href').strip().replace('\n', '')
        log.debug(f"Processing offer URL: {offer_url}")

        if listing.find('div', class_='css-1dyfc0k'):
            print(f"Skipping promoted offer: {offer_url}")
            continue

        title_tag = listing.find('h6', class_='css-1wxaaza')
        title = title_tag.text.strip().replace('\n', '') if title_tag else "Unknown Title"

        log.debug(f"Processing offer title: {title}")

        if any(word.lower() in title.lower() for word in excluded_words):
            print(f"Offer contains excluded word: {offer_url} - {title}")
            continue

        price_tag = listing.find('p', class_='css-13afqrm')
        price_text = price_tag.text.strip() if price_tag else "Unknown Price"
        log.debug(f"Raw price text: {price_text}")

        try:
            # Replace comma with period and remove non-numeric characters (except the period)
            price_value = float(re.sub(r'[^\d,]', '', price_text).replace(',', '.'))
            log.debug(f"Parsed price value: {price_value}")
        except ValueError:
            log.warning(f"Failed to parse price: {price_text}")
            price_value = None

        # Extract the image (if available)
        image_tag = listing.find('img', class_='css-8wsg1m')
        image_url = None

        if image_tag:
            log.debug("Image tag found.")
            if image_tag.get('srcset'):
                log.debug(f"Image 'srcset' found: {image_tag['srcset']}")
            elif image_tag.get('src'):
                log.debug(f"Image 'src' found: {image_tag['src']}")
        else:
            log.debug("Image tag not found.")

        if image_tag:
            # Extracting from 'srcset' if available
            if image_tag.get('srcset'):
                srcset = image_tag['srcset'].split(',')
                # Take the full image URL, which often includes a longer suffix
                highest_res_url = srcset[-1].strip().split(' ')[0]
                image_url = highest_res_url
            # Fallback if 'srcset' is not available
            elif image_tag.get('src'):
                image_url = image_tag.get('src')

            # If the image URL contains a placeholder or 'no_thumbnail', set it to None
            if image_url and 'no_thumbnail' in image_url:
                image_url = None

        log.debug(f"Image URL: {image_url}")

        time_element = listing.find('p', class_='css-1mwdrlh')
        if time_element:
            time_text = time_element.text.strip()
            offer_time = parse_time(time_text, now)
            if offer_time is None or offer_time < now - timedelta(minutes=10):
                print(f"Skipping old offer posted at {offer_time}, URL: {offer_url}")
                continue
        else:
            offer_time = now

        offers_table = db["offers"]
        existing_offer = offers_table.find_one(url=offer_url)
        if existing_offer:
            print(f"Offer already in the database: {offer_url}")
            continue

        offer = {
            'url': offer_url,
            'title': title,
            'price': price_text,  # Store the raw price text as it's displayed
            'image_url': image_url,
            'posted_at': offer_time
        }
        offers_table.insert(offer)
        new_offers.append(offer)
        print(f"New offer found: {offer_url} - {title} ({price_text}) at {offer_time}")

    return new_offers



# Function to parse the time text from the listing (e.g., "Dzisiaj o 16:56")
def parse_time(time_text, current_time):
    """
    Parses the time from OLX listings and adjusts for timezone offset.

    Args:
        time_text (str): Text that includes the time (e.g., "Dzisiaj o 16:56")
        current_time (datetime): The current date to calculate the proper datetime

    Returns:
        datetime: Parsed and adjusted offer time
    """
    if "Dzisiaj" in time_text:
        match = re.search(r'Dzisiaj o (\d{2}:\d{2})', time_text)
        if match:
            time_part = match.group(1)
            offer_time = datetime.strptime(time_part, "%H:%M")
            return datetime.combine(current_time.date(), offer_time.time())
    elif "Wczoraj" in time_text:
        match = re.search(r'Wczoraj o (\d{2}:\d{2})', time_text)
        if match:
            time_part = match.group(1)
            offer_time = datetime.strptime(time_part, "%H:%M")
            return datetime.combine(current_time.date() - timedelta(days=1), offer_time.time())
    return None


# Function to generate a Discord embed for a new offer
def generate_embed(item, sub_id):
    """
    Generate an embed with item details for Discord.

    Args:
        item (dict): Scraped item
        sub_id (int): Subscription ID

    Returns:
        hikari.Embed: Generated embed
    """
    embed = hikari.Embed(
        title=item['title'].strip(),
        description=f"Price: {item['price']}\nPosted at: {item['posted_at']}".strip(),
        url=item['url'].strip(),
        color=hikari.Color(0x09B1BA)
    )

    if item['image_url']:
        embed.set_thumbnail(item['image_url'].strip())

    embed.set_footer(f'Subscription #{str(sub_id)}')
    return embed
