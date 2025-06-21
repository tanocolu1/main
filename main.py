from fastapi import FastAPI, Query
from pydantic import BaseModel
import requests
import os

app = FastAPI()

ACCESS_TOKEN = os.getenv("ML_ACCESS_TOKEN")
USER_ID = os.getenv("ML_USER_ID")
ORIGIN_ZIP = os.getenv("ML_ORIGIN_ZIP", "C1001")

HEADERS = {"Authorization": f"Bearer {ACCESS_TOKEN}"}

class SummaryRequest(BaseModel):
    item_id: str
    price: float
    category_id: str = None
    listing_type_id: str = None
    currency_id: str = "ARS"
    dimensions: str = "20x20x20"
    weight: float = 0.6

@app.post("/get_summary")
def get_summary(data: SummaryRequest):
    result = {
        "item_id": data.item_id,
        "price": data.price
    }

    # Obtener info de ítem para completar datos faltantes
    item_resp = requests.get(f"https://api.mercadolibre.com/items/{data.item_id}", headers=HEADERS)
    if item_resp.ok:
        item_json = item_resp.json()
        category_id = data.category_id or item_json.get("category_id")
        listing_type_id = data.listing_type_id or item_json.get("listing_type_id")
    else:
        category_id = data.category_id
        listing_type_id = data.listing_type_id

    # Comisión real
    fee_url = "https://api.mercadolibre.com/items/fees"
    fee_payload = {
        "price": data.price,
        "category_id": category_id,
        "listing_type_id": listing_type_id,
        "currency_id": data.currency_id
    }
    fee_resp = requests.post(fee_url, headers=HEADERS, json=fee_payload)
    if fee_resp.ok:
        fee_data = fee_resp.json()
        result["sale_fee"] = fee_data.get("sale_fee")
        result["fee_percent"] = fee_data.get("percentage")
    else:
        result["sale_fee"] = None
        result["fee_percent"] = None

    # Costo de envío real
    shipping_url = f"https://api.mercadolibre.com/users/{USER_ID}/shipping_options"
    shipping_payload = {
        "zip_code": ORIGIN_ZIP,
        "dimensions": f"{data.dimensions},{int(data.weight * 1000)}",
        "item_price": data.price
    }
    shipping_resp = requests.post(shipping_url, headers=HEADERS, json=shipping_payload)
    if shipping_resp.ok:
        shipping_data = shipping_resp.json()
        option = shipping_data.get("options", [{}])[0]
        result["shipping_list_cost"] = option.get("list_cost")
        result["shipping_method"] = option.get("name")
    else:
        result["shipping_list_cost"] = None
        result["shipping_method"] = None

    return result
