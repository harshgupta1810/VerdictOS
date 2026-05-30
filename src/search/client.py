"""Elasticsearch client construction for local and managed deployments."""

from elasticsearch import Elasticsearch

from src.config import settings


def create_elasticsearch_client(*, url: str | None = None) -> Elasticsearch:
    """Create an Elasticsearch client using configured local defaults."""

    return Elasticsearch(url or settings.elasticsearch_url)
