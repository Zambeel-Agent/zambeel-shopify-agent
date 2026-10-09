import os
import json
import requests
import gspread
from google.oauth2.service_account import Credentials

SHOPIFY_SHOP_URL = os.environ.get("SHOPIFY_SHOP_URL")
SHOPIFY_ACCESS_TOKEN = os.environ.get("SHOPIFY_ACCESS_TOKEN")
GOOGLE_SHEET_ID = os.environ.get("GOOGLE_SHEET_ID")
GOOGLE_CREDENTIALS_JSON = os.environ.get("GOOGLE_CREDENTIALS")

scopes = ["https://www.googleapis.com/auth/spreadsheets"]
creds_dict = json.loads(GOOGLE_CREDENTIALS_JSON)
creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
client = gspread.authorize(creds)

sheet = client.open_by_key(GOOGLE_SHEET_ID).sheet1

def add_product_to_shopify(row, row_idx):
    title = row.get("Title")
    description = row.get("Description", "")
    cost_price = row.get("Cost Price", "0")
    selling_price = row.get("Selling Price (SAR)", "0")
    image_url = row.get("Image URLs", "").split(",")[0].strip()
    status = row.get("Status", "").strip()

    if status.lower() == "uploaded" or not title:
        return

    url = f"https://{SHOPIFY_SHOP_URL}/admin/api/2024-01/products.json"
    headers = {
        "X-Shopify-Access-Token": SHOPIFY_ACCESS_TOKEN,
        "Content-Type": "application/json"
    }

    product_data = {
        "product": {
            "title": title,
            "body_html": description,
            "variants": [
                {
                    "price": selling_price,
                    "cost": cost_price
                }
            ]
        }
    }

    if image_url:
        product_data["product"]["images"] = [{"src": image_url}]

    response = requests.post(url, headers=headers, json=product_data)

    if response.status_code == 201:
        print(f"✅ Successfully created product: {title}")
        sheet.update_cell(row_idx, 9, "Uploaded")
    else:
        print(f"❌ Failed to create product {title}: {response.text}")

def main():
    records = sheet.get_all_records()
    print(f"Found {len(records)} products in Google Sheet.")
    for idx, row in enumerate(records, start=2):
        add_product_to_shopify(row, idx)

if __name__ == "__main__":
    main()
