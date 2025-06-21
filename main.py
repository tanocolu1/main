from fastapi import FastAPI, Query
import requests

app = FastAPI()

@app.get("/get_fee")
def get_fee(item_id: str, price: float, token: str):
    url = f"https://api.mercadolibre.com/items/{item_id}/fees"
    params = {
        "price": price,
        "quantity": 1,
        "currency_id": "ARS"
    }
    headers = {
        "Authorization": f"Bearer {token}"
    }

    response = requests.get(url, headers=headers, params=params)

    if response.status_code != 200:
        return {"error": response.text, "status": response.status_code}

    data = response.json()
    sale_fee = data.get("sale_fee")
    if sale_fee:
        porcentaje = round((sale_fee / price) * 100, 2)
        return {
            "sale_fee": sale_fee,
            "percent": f"{porcentaje}%",
            "item_id": item_id,
            "price": price
        }
    return {"error": "No se encontró 'sale_fee'"}
