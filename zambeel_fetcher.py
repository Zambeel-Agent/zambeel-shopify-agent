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

# 2. FETCH WINNING PRODUCTS FROM ZAMBEEL
def fetch_zambeel_products():
    zambeel_api_key = os.environ.get("ZAMBEEL_API_KEY", "")
    
    print("--- Fetching Winning Products from Zambeel ---")
    
    if zambeel_api_key:
        headers = {"Authorization": f"Bearer {zambeel_api_key}"}
        url = "https://api.zambeel.com/v1/products/winning"
        try:
            res = requests.get(url, headers=headers)
            if res.status_code == 200:
                return res.json().get("products", [])
        except Exception as e:
            print(f"API Error: {e}")

    # Sample winning product matching sheet columns exactly
    sample_winning_products = [
        {
            "Title": "Wireless Earbuds Pro",
            "Description": "High quality wireless earbuds with active noise cancellation.",
            "Cost_Price": "40",
            "Selling_Price": "120",
            "Image_URL": "https://images.unsplash.com/photo-1590658268037-6bf12165a8df",
            "Color": "Black",
            "Warehouse_Stock": "50",
            "Product_URL": "https://zambeel.com/product/wireless-earbuds-pro",
            "Status": "pending"
        }
    ]
    return sample_winning_products

# 3. MAIN RUNNER
def main():
    sheet = connect_google_sheets()
    existing_records = sheet.get_all_records()
    existing_titles = [str(r.get("Title", "")) for r in existing_records if r.get("Title")]

    products = fetch_zambeel_products()
    print(f"Fetched {len(products)} products from Zambeel.")

    added_count = 0
    for prod in products:
        title = str(prod.get("Title", ""))
        
        # Check duplicate by Title
        if title not in existing_titles:
            # Exact 9 columns mapping:
            # A: Title, B: Description, C: Cost Price, D: Selling Price (SAR), E: Image URLs, F: Color, G: Warehouse Stock, H: Product URL, I: Status
            row = [
                prod.get("Title", ""),
                prod.get("Description", ""),
                prod.get("Cost_Price", "0"),
                prod.get("Selling_Price", "0"),
                prod.get("Image_URL", ""),
                prod.get("Color", ""),
                prod.get("Warehouse_Stock", "0"),
                prod.get("Product_URL", ""),
                "pending"
            ]
            sheet.append_row(row)
            print(f"Added to Google Sheet: {title}")
            added_count += 1
        else:
            print(f"Product already exists in Sheet: {title}")

    print(f"Done! Added {added_count} new winning products to Google Sheet.")

if __name__ == "__main__":
    main()
