import os
import json
import requests
import gspread
from google.oauth2.service_account import Credentials

# 1. GOOGLE SHEETS CONNECTIVITY
def connect_google_sheets():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds_json_str = os.environ.get("GCP_SERVICE_ACCOUNT_KEY")
    if not creds_json_str:
        raise ValueError("GCP_SERVICE_ACCOUNT_KEY environment variable missing!")

    creds_dict = json.loads(creds_json_str)
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)

    sheet_name = os.environ.get("GOOGLE_SHEET_NAME", "Zambeel Products")
    sheet = client.open(sheet_name).sheet1
    return sheet

# 2. SHOPIFY ACCESS TOKEN GENERATOR VIA CLIENT CREDENTIALS
def get_shopify_token():
    shop_url = os.environ.get("SHOPIFY_SHOP_URL")
    client_id = os.environ.get("SHOPIFY_CLIENT_ID")
    client_secret = os.environ.get("SHOPIFY_CLIENT_SECRET")

    url = f"https://{shop_url}/admin/oauth/access_token"
    payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "client_credentials"
    }
    
    print("Requesting access token from Shopify OAuth server...")
    response = requests.post(url, json=payload)
    
    if response.status_code == 200:
        data = response.json()
        print("Token successfully retrieved from Shopify!")
        return data.get("access_token")
    else:
        raise Exception(f"Failed to get Shopify token: {response.text}")

# 3. MAIN SYNC LOGIC
def main():
    sheet = connect_google_sheets()
    rows = sheet.get_all_records()
    print(f"Found {len(rows)} total rows in Google Sheet.")

    token = get_shopify_token()
    shop_url = os.environ.get("SHOPIFY_SHOP_URL")
    api_url = f"https://{shop_url}/admin/api/2024-10/products.json"
    headers = {
        "X-Shopify-Access-Token": token,
        "Content-Type": "application/json"
    }

    success_count = 0
    for idx, row in enumerate(rows, start=2):
        status = str(row.get("Status", "")).strip().lower()
        
        if status == "pending":
            title = row.get("Title", "")
            description = row.get("Description", "")
            selling_price = str(row.get("Selling Price (SAR)", "0"))
            image_url = row.get("Image URLs", "")

            print(f"Uploading product: '{title}' with Price: {selling_price} SAR...")

            product_data = {
                "product": {
                    "title": title,
                    "body_html": description,
                    "vendor": "Zambeel",
                    "product_type": "Dropshipping",
                    "variants": [
                        {
                            "price": selling_price,
                            "sku": str(row.get("SKU", "ZAM-SKU-001")),
                            "inventory_management": "shopify",
                            "inventory_quantity": int(row.get("Warehouse Stock", 10))
                        }
                    ],
                    "images": [
                        {
                            "src": image_url
                        }
                    ] if image_url else []
                }
            }

            res = requests.post(api_url, headers=headers, json=product_data)
            
            if res.status_code == 201:
                print(f"Successfully created '{title}' on Shopify!")
                sheet.update_cell(idx, 9, "Uploaded")
                success_count += 1
            else:
                print(f"Failed to create product '{title}': {res.text}")

    print(f"Sync complete. Successfully uploaded {success_count} products.")

if __name__ == "__main__":
    main()
