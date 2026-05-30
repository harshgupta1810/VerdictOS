"""Download and verify the spaCy en_core_web_lg model.

Run this script once during local development setup to ensure the
NER pipeline in GraphRAG has the required language model available.

Usage:
    python scripts/setup_spacy.py
"""

import subprocess
import sys


MODEL_NAME = "en_core_web_lg"


def main() -> int:
    print(f"Downloading spaCy model: {MODEL_NAME}")
    result = subprocess.run(
        [sys.executable, "-m", "spacy", "download", MODEL_NAME],
        capture_output=False,
    )
    if result.returncode != 0:
        print(f"ERROR: Failed to download {MODEL_NAME} (exit code {result.returncode})")
        return 1

    # Verify the model loads correctly
    try:
        import spacy
        nlp = spacy.load(MODEL_NAME)
        doc = nlp("Acme Corporation acquired Widget Inc. in 2024.")
        entities = [(ent.text, ent.label_) for ent in doc.ents]
        print(f"Model verified successfully. Sample entities: {entities}")
    except Exception as exc:
        print(f"ERROR: Model downloaded but failed to load: {exc}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
