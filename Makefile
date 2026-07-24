.PHONY: dev test frontend-test backup-smoke version-check source-release-check check image-smoke release-gate release-build build build-amd64 build-arm build-vision-amd64 build-clip-amd64 build-transcribe-amd64 push-base-amd64 push-vision-amd64 push-clip-amd64 push-transcribe-amd64 save-amd64 save-vision-amd64 up down logs phase-audit

IMAGE ?= tg-media-manager
TAG ?= latest
DOCKERHUB_REPO ?= bsakuramiku/tg-media-manager
APP_SEMVER ?= $(shell tr -d '[:space:]' < VERSION)
APP_VERSION ?= $(shell git rev-parse --short HEAD 2>/dev/null || echo dev)
APP_BUILT_AT ?= $(shell date -u +%Y-%m-%dT%H:%M:%SZ)
APP_IMAGE ?= $(IMAGE):$(TAG)
PYTHON ?= $(shell if [ -x .venv/bin/python ]; then echo .venv/bin/python; else echo python3; fi)
BUILD_ARGS = --build-arg APP_SEMVER=$(APP_SEMVER) --build-arg APP_VERSION=$(APP_VERSION) --build-arg APP_IMAGE=$(APP_IMAGE) --build-arg APP_BUILT_AT=$(APP_BUILT_AT)
RELEASE_IMAGE ?= $(IMAGE):$(APP_SEMVER)-$(APP_VERSION)-amd64
CI_SMOKE_IMAGE ?= tg-media-manager:ci-smoke-$(APP_VERSION)
CI_SMOKE_CONTAINER ?= tgmm-ci-smoke-$(APP_VERSION)
CI_SMOKE_PASSWORD ?= ci-smoke-password

dev:
	docker compose up --build

test:
	$(PYTHON) -m unittest discover -s tests -p 'test_*.py' -v

frontend-test:
	npm --prefix frontend test

backup-smoke:
	$(PYTHON) scripts/sqlite_backup.py smoke-test

version-check:
	$(PYTHON) scripts/release_gate.py

source-release-check:
	$(PYTHON) scripts/release_gate.py --release

check: version-check test frontend-test backup-smoke
	$(PYTHON) -m compileall -q backend scripts
	npm --prefix frontend run build
	APP_PASSWORD=ci-check APP_SECRET=ci-check-secret docker compose -f docker-compose.nas.yml config --quiet
	TGMM_STAGING_IMAGE=$(IMAGE):staging-check STAGING_APP_PASSWORD=ci-check STAGING_APP_SECRET=ci-check-secret docker compose -f docker-compose.staging.yml config --quiet
	docker buildx build --check -f docker/Dockerfile .
	docker buildx build --check -f docker/Dockerfile.clip .

image-smoke: APP_IMAGE=$(CI_SMOKE_IMAGE)
image-smoke:
	docker build $(BUILD_ARGS) -t $(CI_SMOKE_IMAGE) -f docker/Dockerfile .
	@set -eu; \
	  trap 'code=$$?; if [ $$code -ne 0 ]; then docker logs $(CI_SMOKE_CONTAINER) 2>/dev/null || true; fi; docker rm -f $(CI_SMOKE_CONTAINER) >/dev/null 2>&1 || true; exit $$code' EXIT INT TERM; \
	  docker run -d --name $(CI_SMOKE_CONTAINER) -p 127.0.0.1:18787:8787 \
	    --tmpfs /data --tmpfs /media --tmpfs /models \
	    -e APP_DB=/data/tg_media_manager.sqlite3 \
	    -e MEDIA_ROOT=/media -e MEDIA_OUTPUT_ROOT=/media -e MODEL_ROOT=/models \
	    -e APP_PASSWORD=$(CI_SMOKE_PASSWORD) -e APP_SECRET=ci-smoke-session-secret -e APP_LOCAL_ONLY=true \
	    $(CI_SMOKE_IMAGE) >/dev/null; \
	  $(PYTHON) scripts/container_smoke.py --password $(CI_SMOKE_PASSWORD) \
	    --expected-version $(APP_SEMVER) --expected-commit $(APP_VERSION)

release-gate: source-release-check check

release-build: release-gate
	docker buildx build --platform linux/amd64 \
	  --build-arg APP_SEMVER=$(APP_SEMVER) \
	  --build-arg APP_VERSION=$(APP_VERSION) \
	  --build-arg APP_IMAGE=$(RELEASE_IMAGE) \
	  --build-arg APP_BUILT_AT=$(APP_BUILT_AT) \
	  -t $(RELEASE_IMAGE) -f docker/Dockerfile.clip --load .

build:
	docker compose build

build-arm: APP_IMAGE=$(IMAGE):arm64
build-arm:
	docker buildx build --platform linux/arm64 $(BUILD_ARGS) -t $(IMAGE):arm64 -f docker/Dockerfile .

build-amd64: APP_IMAGE=$(IMAGE):amd64
build-amd64:
	docker buildx build --platform linux/amd64 $(BUILD_ARGS) -t $(IMAGE):amd64 -f docker/Dockerfile .

build-vision-amd64: APP_IMAGE=$(IMAGE):vision-amd64
build-vision-amd64:
	docker buildx build --platform linux/amd64 $(BUILD_ARGS) -t $(IMAGE):vision-amd64 -f docker/Dockerfile.vision .

build-clip-amd64: APP_IMAGE=$(IMAGE):clip-amd64
build-clip-amd64:
	docker buildx build --platform linux/amd64 $(BUILD_ARGS) -t $(IMAGE):clip-amd64 -f docker/Dockerfile.clip .

build-transcribe-amd64: APP_IMAGE=$(IMAGE):transcribe-amd64
build-transcribe-amd64:
	docker buildx build --platform linux/amd64 $(BUILD_ARGS) -t $(IMAGE):transcribe-amd64 -f docker/Dockerfile.transcribe .

push-base-amd64: APP_IMAGE=$(DOCKERHUB_REPO):base-amd64
push-base-amd64:
	docker buildx build --platform linux/amd64 $(BUILD_ARGS) -t $(DOCKERHUB_REPO):base-amd64 -f docker/Dockerfile --push .

push-vision-amd64: APP_IMAGE=$(DOCKERHUB_REPO):vision-amd64
push-vision-amd64:
	docker buildx build --platform linux/amd64 $(BUILD_ARGS) -t $(DOCKERHUB_REPO):vision-amd64 -f docker/Dockerfile.vision --push .

push-clip-amd64: APP_IMAGE=$(DOCKERHUB_REPO):clip-amd64
push-clip-amd64:
	docker buildx build --platform linux/amd64 $(BUILD_ARGS) -t $(DOCKERHUB_REPO):clip-amd64 -t $(DOCKERHUB_REPO):latest -f docker/Dockerfile.clip --push .

push-transcribe-amd64: APP_IMAGE=$(DOCKERHUB_REPO):transcribe-amd64
push-transcribe-amd64:
	docker buildx build --platform linux/amd64 $(BUILD_ARGS) -t $(DOCKERHUB_REPO):transcribe-amd64 -f docker/Dockerfile.transcribe --push .

save-amd64: APP_IMAGE=$(IMAGE):amd64
save-amd64:
	docker buildx build --platform linux/amd64 $(BUILD_ARGS) -t $(IMAGE):amd64 -f docker/Dockerfile --load .
	docker save $(IMAGE):amd64 -o $(IMAGE)-amd64.tar

save-vision-amd64: APP_IMAGE=$(IMAGE):vision-amd64
save-vision-amd64:
	docker buildx build --platform linux/amd64 $(BUILD_ARGS) -t $(IMAGE):vision-amd64 -f docker/Dockerfile.vision --load .
	docker save $(IMAGE):vision-amd64 -o $(IMAGE)-vision-amd64.tar

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f --tail=200

phase-audit:
	$(PYTHON) scripts/phase_audit.py
