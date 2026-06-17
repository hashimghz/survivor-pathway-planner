.PHONY: update-schema-hash check-schema-hash

update-schema-hash:
	uv run python -c "import hashlib; from pathlib import Path; p = Path('models/__init__.py'); print(hashlib.sha256(p.read_bytes()).hexdigest())" > models/.schema-hash

check-schema-hash:
	uv run python scripts/check_schema_hash.py
