import random
import requests

def fetch_with_random_query(url):
    random_value = random.randint(1, 100000)
    modified_url = f"{url}?t={random_value}"  # Add random query parameter to bypass cache

    headers = {
        'User-Agent': 'Mozilla/5.0'
    }

    response = requests.get(modified_url, headers=headers)

    print(f"Requested URL: {response.url}")  # Verify the URL
    print(f"Cache-Control in response: {response.headers.get('Cache-Control')}")

    return response.content

# Test function
url = "https://www.olx.pl/moda/ubrania-meskie/bluzy/?search%5Border%5D=created_at:desc"
page_content = fetch_with_random_query(url)
