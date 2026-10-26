HA_VERSION ?= 2026.6.4
RUFF_VERSION ?= 0.15.21
DOMAIN := garmin_connect_personal

.PHONY: dev lint test

# Start Home Assistant on http://localhost:8123 with the integration mounted.
# Uses config/ as the configuration directory. Stop with Ctrl+C.
dev:
	docker run --rm --name ha-garmin-connect-personal-dev \
		-p 8123:8123 \
		-v "$(CURDIR)/config:/config" \
		-v "$(CURDIR)/custom_components/$(DOMAIN):/config/custom_components/$(DOMAIN):ro" \
		ghcr.io/home-assistant/home-assistant:$(HA_VERSION)

lint:
	uvx ruff@$(RUFF_VERSION) format .
	uvx ruff@$(RUFF_VERSION) check . --fix

test:
	uv run pytest
