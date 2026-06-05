import re
import time
from curl_cffi import requests as cf_requests
from bs4 import BeautifulSoup

# Set your model number here
model_number = "WDT780SAEM1"

# Mimics a real Chrome browser at the network level to bypass PartSelect's WAF.
session = cf_requests.Session(impersonate="chrome124")


def get_model_info(model_number: str) -> dict | None:
    url = f"https://www.partselect.com/Models/{model_number}/"
    r = session.get(url, timeout=15)
    if r.status_code != 200:
        return None

    soup = BeautifulSoup(r.text, "html.parser")

    # H1 is formatted as "WDT780SAEM1  Whirlpool Dishwasher - Overview"; strip the model number and suffix to get brand and appliance type.
    h1 = soup.find("h1")
    h1_text = h1.get_text(strip=True) if h1 else ""
    details = re.sub(re.escape(model_number), "", h1_text).replace("- Overview", "").strip()
    tokens = details.split(None, 1)
    brand          = tokens[0] if tokens else ""
    appliance_type = tokens[1] if len(tokens) > 1 else ""

    # Each <a class="symptoms"> links to a symptom page listing the parts that fix it.
    symptom_links = {}
    for a in soup.find_all("a", class_="symptoms"):
        name = re.sub(r"Fixed\s+by.*", "", a.get_text(strip=True), flags=re.IGNORECASE).strip()
        href = a.get("href", "")
        if name and href:
            symptom_links[name] = "https://www.partselect.com" + href # type: ignore

    # Fetch each symptom page and merge parts by part number so each part ends up tagged with every symptom it fixes.
    parts_map = {}
    for symptom, sym_url in symptom_links.items():
        sym_r = session.get(sym_url, timeout=15)
        if sym_r.status_code != 200:
            continue

        sym_soup = BeautifulSoup(sym_r.text, "html.parser")

        for entry in sym_soup.find_all("div", class_="symptoms"):
            name_div     = entry.find("div", class_="flex-grow-1")
            part_num_div = entry.find("div", class_="text-sm")
            pct_div      = entry.find("div", class_="symptoms__percent")

            if not (name_div and part_num_div):
                continue

            part_name   = re.split(r"Part Number:", name_div.get_text(strip=True))[0].strip()
            part_number = part_num_div.get_text(strip=True).replace("Part Number:", "").strip()
            pct_match   = re.search(r"(\d+)%", pct_div.get_text() if pct_div else "")
            fix_rate    = int(pct_match.group(1)) if pct_match else None

            if part_number not in parts_map:
                parts_map[part_number] = {"name": part_name, "fix_rates": {}}
            parts_map[part_number]["fix_rates"][symptom] = fix_rate

        time.sleep(0.3)

    compatible_parts = [
        {"part_number": pn, "name": data["name"], "fixes": data["fix_rates"]}
        for pn, data in parts_map.items()
    ]

    return {
        "model_number": model_number,
        "brand": brand,
        "appliance_type": appliance_type,
        "compatible_parts": compatible_parts,
    }


if __name__ == "__main__":
    info = get_model_info(model_number)
    if not info:
        print(f"Could not find model: {model_number}")
    else:
        print(f"Model     : {info['model_number']}")
        print(f"Brand     : {info['brand']}")
        print(f"Appliance : {info['appliance_type']}")
        print(f"\nCompatible parts ({len(info['compatible_parts'])}):")
        for part in info["compatible_parts"]:
            fixes = ", ".join(f"{s} ({p}%)" for s, p in part["fixes"].items())
            print(f"  [{part['part_number']}] {part['name']} — fixes: {fixes}")
