from __future__ import annotations

import asyncio
import json
import logging
import queue
from collections import defaultdict
from typing import Any

import redis
import redis.asyncio as aioredis

from src.config import get_settings

logger = logging.getLogger("aegis.events")
settings = get_settings()


class EventBroadcaster:
    def __init__(self) -> None:
        self._use_memory = False
        self._queues: dict[str, queue.Queue[dict[str, Any]]] = defaultdict(queue.Queue)
        try:
            self._publisher = redis.from_url(settings.REDIS_URL, decode_responses=True)
            self._publisher.ping()
        except Exception as exc:
            logger.warning(
                "Redis unavailable for event broadcasting (%s); using in-memory fallback.",
                exc,
            )
            self._publisher = None
            self._use_memory = True

    def _channel(self, job_id: str) -> str:
        return f"aegis:job_events:{job_id}"

    def publish_sync(self, job_id: str, event: dict[str, Any]) -> None:
        payload = event.copy()
        payload["job_id"] = job_id
        if self._use_memory or self._publisher is None:
            self._queues[job_id].put_nowait(payload)
            return

        try:
            self._publisher.publish(self._channel(job_id), json.dumps(payload))
        except Exception as exc:
            logger.warning("Failed to publish event for job %s: %s", job_id, exc)
            self._use_memory = True
            self._queues[job_id].put_nowait(payload)

    async def stream(self, job_id: str) -> Any:
        if self._use_memory or self._publisher is None:
            while True:
                try:
                    event = await asyncio.to_thread(self._queues[job_id].get, timeout=5.0)
                    yield f"data: {json.dumps(event)}\n\n"
                except queue.Empty:
                    await asyncio.sleep(0.1)
                except Exception as exc:
                    logger.warning("In-memory streaming failed for job %s: %s", job_id, exc)
                    break
            return

        channel = self._channel(job_id)
        client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        pubsub = client.pubsub(ignore_subscribe_messages=True)
        await pubsub.subscribe(channel)

        try:
            while True:
                message = await pubsub.get_message(timeout=5.0)
                if message and message.get("type") == "message":
                    raw_data = message.get("data")
                    try:
                        event = json.loads(raw_data)
                    except (TypeError, ValueError):
                        logger.warning("Received malformed event payload for job %s", job_id)
                        continue
                    yield f"data: {json.dumps(event)}\n\n"
                else:
                    await asyncio.sleep(0.1)
        finally:
            try:
                await pubsub.unsubscribe(channel)
                await pubsub.close()
            except Exception:
                pass


broadcaster = EventBroadcaster()
