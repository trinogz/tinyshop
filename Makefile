# Local Postgres on 5433, so it can sit beside another server on 5432.
PG_BIN := $(shell if command -v initdb >/dev/null 2>&1; then dirname $$(command -v initdb); else echo /usr/lib/postgresql/14/bin; fi)
PGDATA := $(HOME)/.local/share/tinyshop/pg
PGPORT := 5433
DATABASE_URL := postgresql+psycopg://tinyshop:tinyshop@127.0.0.1:$(PGPORT)/tinyshop

.PHONY: start install db api web test stop docker docker-stop diagram

start: install db
	$(MAKE) -j2 api web

install:
	uv sync --group dev
	npm --prefix web install

db:
	mkdir -p $(dir $(PGDATA))
	@if [ ! -f $(PGDATA)/PG_VERSION ]; then \
		$(PG_BIN)/initdb -D $(PGDATA) --username=tinyshop --auth=trust; \
	fi
	@if ! $(PG_BIN)/pg_ctl -D $(PGDATA) status >/dev/null 2>&1; then \
		$(PG_BIN)/pg_ctl -D $(PGDATA) -l $(PGDATA)/server.log \
			-o "-p $(PGPORT) -k $(PGDATA) -c listen_addresses=127.0.0.1" start; \
	fi
	@$(PG_BIN)/psql -h 127.0.0.1 -p $(PGPORT) -U tinyshop -d postgres -tAc \
		"SELECT 1 FROM pg_database WHERE datname = 'tinyshop'" | grep -q 1 \
		|| $(PG_BIN)/createdb -h 127.0.0.1 -p $(PGPORT) -U tinyshop tinyshop

api: db
	DATABASE_URL="$(DATABASE_URL)" uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

web:
	npm --prefix web run dev -- --host 127.0.0.1 --port 5173

test:
	uv run pytest

stop:
	-$(PG_BIN)/pg_ctl -D $(PGDATA) stop

docker:
	docker compose up --build

docker-stop:
	docker compose down

diagram:
	@tmp=$$(mktemp -d); \
	awk '/^```mermaid$$/{f=1;next} /^```$$/{if(f) exit} f' docs/er.md > $$tmp/er.mmd; \
	printf '%s\n' '{"args":["--no-sandbox","--disable-gpu"]}' > $$tmp/puppeteer.json; \
	PUPPETEER_EXECUTABLE_PATH="$${CHROME:-/usr/bin/google-chrome}" \
		npx -y @mermaid-js/mermaid-cli -i $$tmp/er.mmd -o docs/er.png -b "#f6f3ee" -p $$tmp/puppeteer.json; \
	rm -rf $$tmp
