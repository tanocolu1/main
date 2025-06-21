from fastapi import FastAPI
from pydantic import BaseModel
import httpx
import logging

app = FastAPI()

class UserAuth(BaseModel):
    access_token: str
    user_id: int

ML_API = "https://api.mercadolibre.com"

async def fetch_items_ids_scan(user_id: int, token: str) -> list:
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
    ids = await fetch_items_ids_scan(auth.user_id, auth.access_token)
    if not ids:
        return {"status": "error", "message": "No se encontraron publicaciones activas o token inválido", "items": []}

    details = await fetch_details(ids, auth.access_token)
    logging.info(f"📦 Total publicaciones detalladas: {len(details)}")
    return {"status": "ok", "items": details}
