import os

import httpx
from fastapi import APIRouter, Request, Response

router = APIRouter()
POCKETBASE_URL = os.getenv("POCKETBASE_URL")
assert POCKETBASE_URL is not None, "Pocketbase URL not specified by env"


async def proxy_to_pocketbase(path: str, request: Request) -> Response:
    """Shared proxy logic"""
    async with httpx.AsyncClient() as client:
        response = await client.request(
            method=request.method,
            url=f"{POCKETBASE_URL}/{path}",
            headers={k: v for k, v in request.headers.items() if k.lower() != "host"},
            content=await request.body(),
            params=request.query_params,
        )
        return Response(
            content=response.content,
            status_code=response.status_code,
            headers=dict(response.headers),
        )


@router.get("/pb/{path:path}")
async def proxy_get(path: str, request: Request):
    return await proxy_to_pocketbase(path, request)


@router.post("/pb/{path:path}")
async def proxy_post(path: str, request: Request):
    return await proxy_to_pocketbase(path, request)


@router.put("/pb/{path:path}")
async def proxy_put(path: str, request: Request):
    return await proxy_to_pocketbase(path, request)


@router.delete("/pb/{path:path}")
async def proxy_delete(path: str, request: Request):
    return await proxy_to_pocketbase(path, request)


@router.patch("/pb/{path:path}")
async def proxy_patch(path: str, request: Request):
    return await proxy_to_pocketbase(path, request)
