.PHONY: dev build build-amd64 build-arm build-vision-amd64 build-clip-amd64 build-transcribe-amd64 push-base-amd64 push-vision-amd64 push-clip-amd64 push-transcribe-amd64 save-amd64 save-vision-amd64 up down logs phase-audit

IMAGE ?= tg-media-manager
TAG ?= latest
DOCKERHUB_REPO ?= bsakuramiku/tg-media-manager
APP_SEMVER ?= 1.0.10
APP_VERSION ?= $(shell git rev-parse --short HEAD 2>/dev/null || echo dev)
APP_BUILT_AT ?= $(shell date -u +%Y-%m-%dT%H:%M:%SZ)
BUILD_ARGS = --build-arg APP_SEMVER=$(APP_SEMVER) --build-arg APP_VERSION=$(APP_VERSION) --build-arg APP_BUILT_AT=$(APP_BUILT_AT)

dev:
	docker compose up --build

build:
	docker compose build

build-arm:
	docker buildx build --platform linux/arm64 $(BUILD_ARGS) -t $(IMAGE):arm64 -f docker/Dockerfile .

build-amd64:
	docker buildx build --platform linux/amd64 $(BUILD_ARGS) -t $(IMAGE):amd64 -f docker/Dockerfile .

build-vision-amd64:
	docker buildx build --platform linux/amd64 $(BUILD_ARGS) -t $(IMAGE):vision-amd64 -f docker/Dockerfile.vision .

build-clip-amd64:
	docker buildx build --platform linux/amd64 $(BUILD_ARGS) -t $(IMAGE):clip-amd64 -f docker/Dockerfile.clip .

build-transcribe-amd64:
	docker buildx build --platform linux/amd64 $(BUILD_ARGS) -t $(IMAGE):transcribe-amd64 -f docker/Dockerfile.transcribe .

push-base-amd64:
	docker buildx build --platform linux/amd64 $(BUILD_ARGS) -t $(DOCKERHUB_REPO):base-amd64 -f docker/Dockerfile --push .

push-vision-amd64:
	docker buildx build --platform linux/amd64 $(BUILD_ARGS) -t $(DOCKERHUB_REPO):vision-amd64 -f docker/Dockerfile.vision --push .

push-clip-amd64:
	docker buildx build --platform linux/amd64 $(BUILD_ARGS) -t $(DOCKERHUB_REPO):clip-amd64 -t $(DOCKERHUB_REPO):latest -f docker/Dockerfile.clip --push .

push-transcribe-amd64:
	docker buildx build --platform linux/amd64 $(BUILD_ARGS) -t $(DOCKERHUB_REPO):transcribe-amd64 -f docker/Dockerfile.transcribe --push .

save-amd64:
	docker buildx build --platform linux/amd64 $(BUILD_ARGS) -t $(IMAGE):amd64 -f docker/Dockerfile --load .
	docker save $(IMAGE):amd64 -o $(IMAGE)-amd64.tar

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
	python3 scripts/phase_audit.py
