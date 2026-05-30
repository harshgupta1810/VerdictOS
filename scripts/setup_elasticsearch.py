"""Elasticsearch Index Bootstrap Script.

Creates and configures Elasticsearch indices with proper
mappings for document chunks and metadata.

Usage:
    python scripts/setup_elasticsearch.py [--force]

    --force  Drop and recreate the index if it already exists.
"""

from __future__ import annotations

import argparse
import sys

from elasticsearch import Elasticsearch

sys.path.insert(0, ".")

from src.config import settings
from src.search.indexer import DOCUMENT_INDEX_MAPPING


def bootstrap(*, force: bool = False) -> None:
    client = Elasticsearch(settings.elasticsearch_url)

    if not client.ping():
        print(f"ERROR: Cannot reach Elasticsearch at {settings.elasticsearch_url}", file=sys.stderr)
        sys.exit(1)

    index = settings.elasticsearch_index

    if client.indices.exists(index=index):
        if not force:
            print(f"Index '{index}' already exists. Use --force to recreate it.")
            return
        client.indices.delete(index=index)
        print(f"Deleted existing index '{index}'.")

    client.indices.create(index=index, mappings=DOCUMENT_INDEX_MAPPING)
    print(f"Created index '{index}' with clause-type BM25 mappings.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bootstrap Elasticsearch index for VerdictOS.")
    parser.add_argument("--force", action="store_true", help="Drop and recreate index if it exists.")
    args = parser.parse_args()
    bootstrap(force=args.force)
