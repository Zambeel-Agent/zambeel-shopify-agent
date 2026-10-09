import os
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import requests

# 1. SHOPIFY AUTHENTICATION & ACCESS TOKEN LOGIC
def get_shopify_access_token():
    direct_token = os.environ.get("SHOPIFY_ACCESS_TOKEN", "").strip()
    if direct_token and direct_token.startswith("shpat_"):
        print(" Using direct SHOPIFY_ACCESS_TOKEN.")
        return direct_token

    client_id = os.environ.get("SHOPIFY_CLIENT_ID", "").strip()
    client_secret = os.environ.get("SHOPIFY_CLIENT_SECRET", "").strip()
    shop_url = os.environ.get("SHOPIFY_SHOP_URL", "").strip()

    if not client_id or not client_secret:
        if direct_token:
            return direct_token
        raise ValueError("Missing SHOPIFY_CLIENT_ID or SHOPIFY_CLIENT_SECRET in GitHub Secrets.")

    url = f"https://{shop_url}/admin/oauth/access_token"
    payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "client_credentials"
    }
    
    print(" Requesting access token from Shopify OAuth server...")
    response = requests.post(url, json=payload)
    
    if response.status_code == 200:
        token = response.json().get("access_token")
        print(" Token successfully generated from Shopify OAuth!")
        return token
    else:
        raise Exception(f"OAuth Token Error ({response.status_code}): {response.text}")

# 2. GOOGLE SHEETS CONNECTIVITY
def connect_google_sheets():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    
    creds_json_str = os.environ.get("GCP_SERVICE_ACCOUNT_KEY")
    if not creds_json_str:
        raise ValueError("GCP_SERVICE_ACCOUNT_KEY environment variable missing!")
        
    creds_dict = json.loads(creds_json_str)
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    
    sheet_name = os.environ.get("GOOGLE_SHEET_NAME", "Zambeel Products")
    sheet = client.open(sheet_name).sheet1
    return sheet

# 3. SHOPIFY PRODUCT CREATION
def create_shopify_product(shop_url, access_token, product_data):
    endpoint = f"https://{shop_url}/admin/api/2024-01/products.json"
    
    headers = {
        "X-Shopify-Access-Token": access_token,
        "Content-Type": "application/json"
    }
    
    payload = {
        "product": {
            "title": product_data.get("Title"),
            "body_html": product_data.get("Description", ""),
            "vendor": product_data.get("Vendor", "Zambeel"),
            "product_type": product_data.get("Type", "General"),
            "variants": [
                {
                    "price": str(product_data.get("Price", "0.00")),
                    "sku": str(product_data.get("SKU", ""))
                }
            ]
        }
    }
    
    image_url = product_data.get("Image URL")
    if image_url:
        payload["product"]["images"] = [{"src": image_url}]
        
    response = requests.post(endpoint, json=payload, headers=headers)
    return response

# 4. MAIN AGENT RUNNER
def main():
    shop_url = os.environ.get("SHOPIFY_SHOP_URL", "").strip()
    if not shop_url:
        raise ValueError("SHOPIFY_SHOP_URL secret is missing!")

    print("--- Starting Zambeel to Shopify Sync Agent ---")
    
    access_token = get_shopify_access_token()
    sheet = connect_google_sheets()
    records = sheet.get_all_records()
    
    print(f" Found {len(records)} products in Google Sheet.")
    
    for idx, row in enumerate(records, start=2):
        status = str(row.get("Status", "")).strip().lower()
        title = row.get("Title", "Untitled Product")
        
        if status in ["", "pending", "new"]:
            print(f" Uploading product: '{title}'...")
            
            res = create_shopify_product(shop_url, access_token, row)
            
            if res.status_code == 201:
                print(f" Successfully created '{title}' on Shopify!")
                status_col_idx = list(row.keys()).index("Status") + 1
                sheet.update_cell(idx, status_col_idx, "Uploaded")
            else:
                print(f" Failed to create product '{title}': {res.text}")

if __name__ == "__main__":
    main()
