from fastapi import FastAPI, Query
from pydantic import BaseModel
import requests
import os

app = FastAPI()

ACCESS_TOKEN = os.getenv("ML_ACCESS_TOKEN")
USER_ID = os.getenv("ML_USER_ID")
ORIGIN_ZIP = os.getenv("ML_ORIGIN_ZIP", "C1001")  # CABA por defecto

headers = {
    "Authorization": f"Bearer {ACCESS_TOKEN}"
}

class ItemRequest(BaseModel):
    item_id: str
    price: float
    category_id: str
    listing_type_id: str
    currency_id: str = "ARS"
    weight: float = 0.5
    dimensions: str = "10x10x10"

@app.post("/get_fee_shipping")
def get_fee_shipping(data: ItemRequest):
    response_data = {
        "item_id": data.item_id,
        "price": data.price
    }

    # --- Comisión ---
    fee_url = "https://api.mercadolibre.com/items/fees"
    fee_payload = {
        "price": data.price,
        "category_id": data.category_id,
        "listing_type_id": data.listing_type_id,
        "currency_id": data.currency_id
    }
    fee_resp = requests.post(fee_url, headers=headers, json=fee_payload)
    if fee_resp.ok:
        fee_json = fee_resp.json()
        response_data["sale_fee"] = fee_json.get("sale_fee")
        response_data["fee_percent"] = fee_json.get("percentage")
    else:
        response_data["sale_fee"] = None
        response_data["fee_percent"] = None

    # --- Costo de envío ---
    shipping_url = f"https://api.mercadolibre.com/users/{USER_ID}/shipping_options"
    shipping_payload = {
        "zip_code": ORIGIN_ZIP,
        "dimensions": f"{data.dimensions},{int(data.weight * 1000)}",  # en gramos
        "item_price": data.price
    }
    ship_resp = requests.post(shipping_url, headers=headers, json=shipping_payload)
    if ship_resp.ok:
        shipping_json = ship_resp.json()
        options = shipping_json.get("options", [])
        if options:
            response_data["shipping_list_cost"] = options[0].get("list_cost")
            response_data["shipping_method"] = options[0].get("name")
        else:
            response_data["shipping_list_cost"] = None
            response_data["shipping_method"] = None
    else:
        response_data["shipping_list_cost"] = None
        response_data["shipping_method"] = None

    return response_data
