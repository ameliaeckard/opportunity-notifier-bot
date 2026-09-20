from __future__ import annotations

from abc import ABC, abstractmethod

import aiohttp

from bot.models import Opportunity


class OpportunitySource(ABC):
    name: str

    @abstractmethod
    async def fetch(self, session: aiohttp.ClientSession) -> list[Opportunity]:
        raise NotImplementedError
