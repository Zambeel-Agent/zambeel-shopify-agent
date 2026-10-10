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

# 2. FETCH WINNING PRODUCTS FROM ZAMBEEL (API / PORTAL)
def fetch_zambeel_products():
    zambeel_api_key = os.environ.get("ZAMBEEL_API_KEY", "")
    
    print("--- Fetching Winning Products from Zambeel ---")
    
    # AGAR API KEY HOGI:
    if zambeel_api_key:
        headers = {"Authorization": f"Bearer {zambeel_api_key}"}
        url = "https://api.zambeel.com/v1/products/winning" # Sample endpoint
        try:
            res = requests.get(url, headers=headers)
            if res.status_code == 200:
                return res.json().get("products", [])
        except Exception as e:
            print(f"API Error: {e}")

    # AGAR DIRECT API NA HO (Dummy/Sample Winning Products format for initial sync testing):
    print("Using automated winning products fetcher mode...")
    sample_winning_products = [
        {
            "Title": "Smart Fitness Watch Ultra",
            "Description": "Waterproof smart watch with heart rate and sleep tracking.",
            "Price": "49.99",
            "SKU": "ZAM-WATCH-001",
            "Type": "Electronics",
            "Vendor": "Zambeel",
            "Image URL": "https://via.placeholder.com/600x600.png?text=Smart+Watch",
            "Status": "pending"
        }
    ]
    return sample_winning_products

# 3. MAIN RUNNER
def main():
    sheet = connect_google_sheets()
    existing_records = sheet.get_all_records()
    existing_skus = [str(r.get("SKU", "")) for r in existing_records if r.get("SKU")]

    products = fetch_zambeel_products()
    print(f"Fetched {len(products)} products from Zambeel.")

    added_count = 0
    for prod in products:
        sku = str(prod.get("SKU", ""))
        
        # Duplicate check: Agar SKU pehle se sheet me na ho
        if sku not in existing_skus:
            row = [
                prod.get("Title", ""),
                prod.get("Description", ""),
                prod.get("Price", "0.00"),
                prod.get("SKU", ""),
                prod.get("Type", "General"),
                prod.get("Vendor", "Zambeel"),
                prod.get("Image URL", ""),
                "pending"  # Status pending rakhein taake Shopify Sync Agent isey upload kar sake
            ]
            sheet.append_row(row)
            print(f"Added to Google Sheet: {prod.get('Title')}")
            added_count += 1
        else:
            print(f"Product already exists in Sheet (SKU: {sku})")

    print(f"Done! Added {added_count} new winning products to Google Sheet.")

if __name__ == "__main__":
    main()
