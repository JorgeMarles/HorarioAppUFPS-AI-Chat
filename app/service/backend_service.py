from app.config import get_settings
from typing import Dict, Any
import httpx


class BackendService:
    def __init__(self):
        settings = get_settings()
        self.backend_url = settings.backend_url

    async def _get(self, endpoint: str, jwt: str) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            url = f"{self.backend_url}{endpoint}"
            print(f"GET {url}")
            response = await client.get(
                url,
                headers={
                    "Authorization": f"Bearer {jwt}"
                },
            )
            response.raise_for_status()
            return response.json()
    
    async def _post(self, endpoint: str, jwt: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            url = f"{self.backend_url}{endpoint}"
            print(f"POST {url}")
            response = await client.post(
                url,
                headers={
                    "Authorization": f"Bearer {jwt}"
                },
                json=data
            )
            response.raise_for_status()
            return response.json()
        
    async def _put(self, endpoint: str, jwt: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            url = f"{self.backend_url}{endpoint}"
            print(f"PUT {url}")
            response = await client.put(
                url,
                headers={
                    "Authorization": f"Bearer {jwt}"
                },
                json=data
            )
            response.raise_for_status()
            return response.json()
    
    async def _delete(self, endpoint: str, jwt: str) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            url = f"{self.backend_url}{endpoint}"
            print(f"DELETE {url}")
            response = await client.delete(
                url,
                headers={
                    "Authorization": f"Bearer {jwt}"
                }
            )
            response.raise_for_status()
            return response.json()

    async def get_pensum(self, jwt: str, **kwargs) -> Dict[str, Any]:
        return await self._get("pensum", jwt)
    
    async def get_schedule(self, jwt: str, schedule_id: int, **kwargs) -> Dict[str, Any]:
        return await self._get(f"schedule/{schedule_id}", jwt)

    async def add_group(self,  jwt: str, schedule_id: int, group_code: str, **kwargs) -> Dict[str, Any]:
        return await self._post(f"schedule/{schedule_id}/group/{group_code}", jwt)

    async def delete_group(self, jwt: str, schedule_id: int, group_code: str, **kwargs) -> Dict[str, Any]:
        return await self._delete(f"schedule/{schedule_id}/group/{group_code}", jwt)

    async def change_group(self, jwt: str, schedule_id: int, old_group_code: str, new_group_code: str, **kwargs) -> Dict[str, Any]:
        return await self._put(f"schedule/{schedule_id}/group/{old_group_code}", jwt, {
            "newCode": new_group_code
        })

backend_service = BackendService()