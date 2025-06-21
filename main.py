from fastapi import FastAPI
from pydantic import BaseModel
import httpx
import logging

app = FastAPI()

class UserAuth(BaseModel):
    user_id: str
    access_token: str

ML_API = "https://api.mercadolibre.com"

async def fetch_items_ids(user_id: str, token: str) -> list:
    ids = []
    offset = 0
    total = 1
    headers = {"Authorization": f"Bearer {token}"}

    while offset < total:
        url = f"{ML_API}/users/{user_id}/items/search?status=active&offset={offset}&limit=50"
        async with httpx.AsyncClient() as client:
            r = await client.get(url, headers=headers)
            if r.status_code != 200:
                logging.error(f"❌ Error al obtener items: {r.status_code} {r.text}")
                return []
            data = r.json()
            batch_ids = data.get("results", [])
            total = data.get("paging", {}).get("total", 0)
            logging.info(f"🔹 Offset {offset} → {len(batch_ids)} IDs (de {total})")
            ids += batch_ids
            if len(batch_ids) < 50:
                break
            offset += 50
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
            results += [x["body"] for x in batch if "body" in x]
    return results

@app.post("/get_full_items_report")
async def get_full_items_report(auth: UserAuth):
    logging.info(f"📥 Solicitando publicaciones para user_id {auth.user_id}")
    ids = await fetch_items_ids(auth.user_id, auth.access_token)
    if not ids:
        return {"status": "error", "message": "No se encontraron publicaciones activas o token inválido", "items": []}

    details = await fetch_details(ids, auth.access_token)
    logging.info(f"📦 Total publicaciones detalladas: {len(details)}")
    return {"status": "ok", "items": details}
