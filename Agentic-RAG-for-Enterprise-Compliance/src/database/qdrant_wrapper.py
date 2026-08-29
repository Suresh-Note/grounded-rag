import logging

from qdrant_client import QdrantClient
from qdrant_client.http import models

from src.config import get_settings

logger = logging.getLogger("aegis.qdrant")
settings = get_settings()


def get_db_client() -> QdrantClient:
    """Initializes and returns a Qdrant connection instance."""
    return QdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT)


def initialize_compliance_collection() -> None:
    """
    Allocates the vector collection using `settings.EMBEDDING_DIM`, which must
    match the real output dimension of `settings.LOCAL_EMBED_MODEL`. The
    original code hardcoded 384 here while nomic-embed-text (the default
    model) actually outputs 768 dims — every vector written was then silently
    truncated in half elsewhere in the codebase. Collection size is immutable
    in Qdrant once created; if you change the embedding model, drop and
    recreate the collection rather than trying to reconcile the mismatch.
    """
    client = get_db_client()
    collection_name = settings.COMPLIANCE_COLLECTION_NAME

    if client.collection_exists(collection_name=collection_name):
        logger.info("Collection '%s' already exists. Skipping initialization.", collection_name)
        return

    client.create_collection(
        collection_name=collection_name,
        vectors_config=models.VectorParams(
            size=settings.EMBEDDING_DIM,
            distance=models.Distance.COSINE,
            on_disk=True,
        ),
        quantization_config=models.ScalarQuantization(
            scalar=models.ScalarQuantizationConfig(type=models.ScalarType.INT8, always_ram=False)
        ),
    )
    logger.info("Collection '%s' initialized (dim=%s, INT8 quantization).", collection_name, settings.EMBEDDING_DIM)
