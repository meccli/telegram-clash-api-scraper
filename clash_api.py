import aiohttp
import asyncio
import json
import logging
from typing import AsyncGenerator, Dict, Any, List

logger = logging.getLogger(__name__)

class ClashAPI:
    def __init__(self, base_url: str, secret: str = None):
        self.base_url = base_url.rstrip('/')
        self.headers = {}
        if secret:
            self.headers['Authorization'] = f"Bearer {secret}"

    async def _get(self, endpoint: str) -> Dict[str, Any]:
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with session.get(f"{self.base_url}{endpoint}") as response:
                response.raise_for_status()
                # Force content_type=None to ignore mimetype and parse as JSON
                return await response.json(content_type=None)

    async def get_version(self) -> Dict[str, Any]:
        return await self._get('/version')

    async def get_configs(self) -> Dict[str, Any]:
        return await self._get('/configs')

    async def get_proxies(self) -> Dict[str, Any]:
        return await self._get('/proxies')

    async def get_connections(self) -> Dict[str, Any]:
        return await self._get('/connections')

    async def get_rules(self) -> Dict[str, Any]:
        return await self._get('/rules')

    async def reload_config(self, force: bool = True) -> bool:
        """Trigger a configuration reload."""
        # Get current config
        config = await self.get_configs()
        logger.info(f"Current config data: {config}")
        path = config.get('path')
        
        # If path is missing, try to send an empty JSON or just the force param
        # Standard Clash API allows PUT /configs with just a URL or path
        payload = {}
        if path:
            payload["path"] = path
        
        url = f"{self.base_url}/configs?force={'true' if force else 'false'}"
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with session.put(url, json=payload) as response:
                response.raise_for_status()
                return True

    async def stream_traffic(self) -> AsyncGenerator[Dict[str, int], None]:
        url = f"{self.base_url}/traffic".replace('http://', 'ws://').replace('https://', 'wss://')
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with session.ws_connect(url) as ws:
                async for msg in ws:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        yield json.loads(msg.data)
                    elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                        break

    async def stream_logs(self, level: str = 'info') -> AsyncGenerator[Dict[str, Any], None]:
        url = f"{self.base_url}/logs?level={level}".replace('http://', 'ws://').replace('https://', 'wss://')
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with session.ws_connect(url) as ws:
                async for msg in ws:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        yield json.loads(msg.data)
                    elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                        break
