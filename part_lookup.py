import json
import re
from curl_cffi import requests as cf_requests
from bs4 import BeautifulSoup

# Set your part number here
part_number = "PS16218028"

# Mimics a real Chrome browser at the network level to bypass PartSelect's WAF.
session = cf_requests.Session(impersonate="chrome124")


def get_part_info(part_number: str) -> dict | None:
    """Returns {"name": str, "price": str | None} for a part, or None if not found."""
    search_url = (
        f"https://www.partselect.com/api/search/"
        f"?searchterm={part_number}&siteId=1"
    )
    redirect = session.get(search_url, timeout=15, allow_redirects=False)
    product_url = redirect.headers.get("Location")

    if not product_url:
        return None

    if product_url.startswith("/"):
        product_url = "https://www.partselect.com" + product_url

    product_page = session.get(product_url, timeout=15)
    if product_page.status_code != 200:
        return None

    soup = BeautifulSoup(product_page.text, "html.parser")
    is_search_results = "/partsearchresult/" in product_url

    # --- Name ---
    name = None
    if is_search_results:
        # First listing title on the search results page
        title_div = soup.find("div", class_="table-row__info__part-title")
        if title_div:
            raw = title_div.get_text(strip=True)
            name = re.split(r"Part Number", raw, flags=re.IGNORECASE)[0].strip()
    else:
        for script in soup.find_all("script", {"type": "application/ld+json"}):
            try:
                data = json.loads(script.string or "")
                for item in (data if isinstance(data, list) else [data]):
                    if isinstance(item, dict) and item.get("@type") == "Product":
                        name = item.get("name")
                        break
            except Exception:
                continue
        if not name:
            h1 = soup.find("h1")
            name = h1.get_text(strip=True) if h1 else None

    if not name:
        return None

    # --- Price ---
    # Product page uses span.js-partPrice; search results page uses div.bold.info-item.price
    price_tag = soup.find("span", class_="js-partPrice") or \
                soup.find("div", class_=lambda c: c and "bold" in c and "price" in c and "info-item" in c) # type: ignore
    raw_price = price_tag.get_text(strip=True).lstrip("$") if price_tag else None
    price = f"${raw_price}" if raw_price else None

    # --- Image --- (same CDN pattern on both page types)
    CDN = "partselectcom-gtcdcddbene3cpes.z01.azurefd.net"
    image_url = None
    for img in soup.find_all("img", src=True):
        src = img["src"]
        if CDN in src and "-1-M-" in src:
            image_url = src
            break

    return {"name": name, "price": price, "image_url": image_url}


def get_part_name(part_number: str) -> str | None:
    info = get_part_info(part_number)
    return info["name"] if info else None


if __name__ == "__main__":
    info = get_part_info(part_number)
    if info:
        print(f"Part number : {part_number}")
        print(f"Part name   : {info['name']}")
        print(f"Price       : {info['price'] or 'N/A'}")
        print(f"Image URL   : {info['image_url'] or 'N/A'}")
    else:
        print(f"Could not find part: {part_number}")
