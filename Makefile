TF := terraform -chdir=infra/terraform

.PHONY: install lint test build plan deploy sync-docs

install:
	python -m pip install -r requirements-dev.txt

lint:
	ruff check .
	ruff format --check .
	$(TF) fmt -check -recursive

test:
	pytest -q

build:
	bash scripts/build.sh

plan: build
	$(TF) init
	$(TF) plan -out=tfplan

deploy:
	$(TF) apply tfplan

# Usage: make sync-docs BUCKET=rag-datasets KB_ID=... DS_ID=...
sync-docs:
	aws s3 sync data/ s3://$(BUCKET)/docs/ --delete
	aws bedrock-agent start-ingestion-job --knowledge-base-id $(KB_ID) --data-source-id $(DS_ID)
