from fastapi import FastAPI, Query
from pydantic import BaseModel
import httpx
import logging
from typing import Optional

app = FastAPI()

class UserAuth(BaseModel):
    access_token: str
    user_id: int

ML_API = "https://api.mercadolibre.com"

async def fetch_items_ids_scan(user_id: int, token: str, scroll_limit: int = 5000) -> list:
    ids = []
    headers = {"Authorization": f"Bearer {token}"}
    scroll_id = None

    while True:
        url = f"{ML_API}/users/{user_id}/items/search?status=active&search_type=scan"
        if scroll_id:
            url += f"&scroll_id={scroll_id}"
        logging.info(f"📤 Solicitando: {url}")

        async with httpx.AsyncClient() as client:
            r = await client.get(url, headers=headers)
            logging.info(f"🔄 Respuesta {r.status_code}: {r.text[:500]}")

            if r.status_code != 200:
                logging.error(f"❌ Error al obtener items: {r.status_code} {r.text}")
                return []

            data = r.json()
            batch_ids = data.get("results", [])
            if not batch_ids:
                break

            scroll_id = data.get("scroll_id")
            ids += batch_ids
            logging.info(f"🔹 Batch recibido: {len(batch_ids)} (Total acumulado: {len(ids)})")

            if len(ids) >= scroll_limit:
                break

    return ids

async def fetch_details(ids: list, token: str) -> list:
    batched = [ids[i:i+20] for i in range(0, len(ids), 20)]
    results = []
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient() as client:
        for group in batched:
            id_str = ",".join(group)
            url = f"{ML_API}/items?ids={id_str}"
            r = await client.get(url, headers=headers)
            if r.status_code != 200:
                logging.error(f"❌ Error al obtener detalles: {r.status_code} {r.text}")
                continue
            batch = r.json()
            for item in batch:
                body = item.get("body", {})
                body["commission_fee"] = await fetch_commission(body.get("id"), body.get("price"), token)
                body["shipping_info"] = await fetch_shipping_cost(body.get("id"), body.get("price"), token)
                body["stats"] = await fetch_sales_data(body.get("id"), token)
                results.append(body)
    return results

async def fetch_commission(item_id, price, token):
    try:
        url = f"https://api.mercadolibre.com/items/{item_id}/fees?price={price}"
        headers = {"Authorization": f"Bearer {token}"}
        async with httpx.AsyncClient() as client:
            r = await client.get(url, headers=headers)
            if r.status_code == 200:
                data = r.json()
                return {
                    "sale_fee": data.get("sale_fee"),
                    "fee_percent": data.get("sale_fee") / price if price else None
                }
    except:
        return None

async def fetch_shipping_cost(item_id, price, token):
    try:
        url = f"https://api.mercadolibre.com/items/{item_id}/shipping_options?quantity=1&price={price}"
        headers = {"Authorization": f"Bearer {token}"}
        async with httpx.AsyncClient() as client:
            r = await client.get(url, headers=headers)
            if r.status_code == 200:
                data = r.json()
                options = data.get("options", [])
                if options:
                    return {
                        "list_cost": options[0].get("list_cost"),
                        "shipping_method": options[0].get("name")
                    }
    except:
        return None

async def fetch_sales_data(item_id, token):
    try:
        url = f"https://api.mercadolibre.com/items/{item_id}/visits/time_window?last=60"
        headers = {"Authorization": f"Bearer {token}"}
        async with httpx.AsyncClient() as client:
            r = await client.get(url, headers=headers)
            if r.status_code == 200:
                return r.json()
    except:
        return None

@app.post("/get_full_items_report")
async def get_full_items_report(
    auth: UserAuth,
    limit: int = Query(200, ge=1, le=500),
    page: int = Query(1, ge=1)
):
    logging.info(f"📥 Solicitando publicaciones para user_id {auth.user_id}, página {page}, límite {limit}")
    all_ids = await fetch_items_ids_scan(auth.user_id, auth.access_token)
    if not all_ids:
        return {"status": "error", "message": "No se encontraron publicaciones activas o token inválido", "items": []}

    start = (page - 1) * limit
    end = start + limit
    page_ids = all_ids[start:end]

    details = await fetch_details(page_ids, auth.access_token)
    logging.info(f"📦 Publicaciones detalladas: {len(details)}")
    return {
        "status": "ok",
        "items": details,
        "page": page,
        "limit": limit,
        "total_items": len(all_ids)
    }
