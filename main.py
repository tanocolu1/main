from fastapi import FastAPI, Request
from pydantic import BaseModel
import httpx
import asyncio

app = FastAPI()

class UserAuth(BaseModel):
    user_id: str
    access_token: str

ML_API = "https://api.mercadolibre.com"

async def fetch_items_ids(user_id: str, token: str) -> list:
    ids = []
    offset = 0
    while True:
        url = f"{ML_API}/users/{user_id}/items/search?status=active&offset={offset}&limit=50"
        headers = {"Authorization": f"Bearer {token}"}
        async with httpx.AsyncClient() as client:
            r = await client.get(url, headers=headers)
            data = r.json()
            ids += data.get("results", [])
            if len(data.get("results", [])) < 50:
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
            results += [x["body"] for x in r.json() if "body" in x]
    return results

@app.post("/get_full_items_report")
async def get_full_items_report(auth: UserAuth):
    ids = await fetch_items_ids(auth.user_id, auth.access_token)
    details = await fetch_details(ids, auth.access_token)
    return details
