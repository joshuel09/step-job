"""Handing work to the background worker.

The dependency runs one way: the worker depends on the API for its models and
business rules, never the reverse. So this enqueues a message by actor name
rather than importing the actor, which would invert that and make the API
unimportable without the worker installed.

The cost is that the actor name is a string shared between two packages. That is
covered by a test asserting the worker really does define an actor with this
name, so a rename breaks the suite rather than production.
"""

import logging

from app.core.settings import get_settings

logger = logging.getLogger(__name__)

# Must match the actor defined in apps/worker/worker/extraction.py.
EXTRACTION_ACTOR = "extract_import"
QUEUE = "default"


def enqueue_extraction(profile_id: str, import_id: str, source: str) -> None:
    """Queue an import for the worker.

    The source text travels with the message rather than being stored. Keeping
    it would mean a copy of someone's resume sitting in a table, which is what
    the rest of this feature exists to avoid.
    """
    import dramatiq
    from dramatiq.brokers.redis import RedisBroker

    broker = dramatiq.get_broker()
    if not isinstance(broker, RedisBroker):
        broker = RedisBroker(url=get_settings().redis_url)
        dramatiq.set_broker(broker)

    broker.enqueue(
        dramatiq.Message(
            queue_name=QUEUE,
            actor_name=EXTRACTION_ACTOR,
            args=(profile_id, import_id, source),
            kwargs={},
            options={},
        )
    )
    logger.info("extraction queued", extra={"profile_id": profile_id, "outcome": "queued"})
