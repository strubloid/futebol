# AGENT.md

Instructions and project context for AI agents working on `futebol`.

## Project identity

`futebol` is a Python 3.12+ legal IPTV discovery and playlist-management app focused on football/soccer content, especially Brazilian Portuguese and World Cup coverage.

The project is currently a Python CLI/backend-style application. There is no separate web frontend or separate backend server folder yet.

## Legal rules are mandatory

Never add pirate IPTV links, stolen playlists, Xtream/Stalker panels, paywall bypasses, DRM bypasses, token bypasses, geo-block bypasses, or scraper logic for unauthorized streams.

Allowed source categories only:

- official broadcaster pages and metadata
- public/free/legal streams
- free-to-air streams with clear legitimacy
- user-provided M3U/M3U8 playlists
- verified public sources

Every source must have a clear legitimacy status:

- `official`
- `public/free/legal`
- `user-provided`
- `unknown`
- `blocked/rejected`

Unknown sources must be reported but must not be automatically included in exported playable playlists unless the user explicitly changes configuration with `FUTEBOL_ALLOW_UNKNOWN_SOURCES=true`.

Official broadcaster pages, including FIFA or CazéTV pages, are metadata/research sources. Do not scrape them for hidden stream URLs.

## Current verified broadcaster direction

FIFA has an official page confirming CazéTV media rights for Brazil coverage of FIFA World Cup 26:

https://www.fifa.com/en/tournaments/mens/worldcup/canadamexicousa2026/articles/caze-tv-brazil-media-rights

CazéTV official YouTube page:

https://www.youtube.com/@CazeTV

These are official metadata references, not hardcoded direct playable stream sources.

## Architecture rules

Follow clean architecture and SOLID principles.

Keep each class focused and in its own file when practical. Do not create huge mixed-responsibility modules.

Current package layout:

- `futebol/app`: CLI and application orchestration
- `futebol/config`: runtime settings
- `futebol/domain/models`: dataclass models/DTOs
- `futebol/domain/enums`: source/status/category enums
- `futebol/services`: parsing, loading, filtering, validation, EPG, reporting services
- `futebol/repositories`: persistence abstractions/backends
- `futebol/factories`: construction helpers
- `futebol/providers`: source providers
- `futebol/validators`: URL, stream, M3U, and legal validators
- `futebol/filters`: channel filters
- `futebol/infrastructure`: HTTP, storage, logging
- `futebol/output`: M3U, JSON, and console exporters/reporters
- `futebol/tests`: unit and integration tests

The `Application` class should only orchestrate. Do not put parsing, validation, filtering, HTTP probing, exporting, or storage details inside `Application`.

## Development style

Use:

- Python 3.12+
- type hints everywhere
- dataclasses or Pydantic for structured data
- `httpx` for HTTP
- `typer` for CLI
- `rich` for terminal output
- `pytest` for tests
- `ruff` for linting
- `mypy` for strict type checking

Do not add unrelated temp files or one-off scripts to the project root.

## Install and run

Install the project in editable mode:

```bash
pip install -e .
```

Run the CLI:

```bash
futebol --help
```

Add a local playlist:

```bash
futebol sources add-file ./playlist.m3u
```

Add a legal/user-provided playlist URL:

```bash
futebol sources add --url "https://example.org/legal-playlist.m3u"
```

Scan sources:

```bash
futebol scan
```

Filter football/Brazilian Portuguese channels:

```bash
futebol filter --category football --language pt-BR
```

Validate streams:

```bash
futebol validate-streams
```

Export a clean playlist:

```bash
futebol export --format m3u --output futebol-worldcup.m3u
```

Show the report:

```bash
futebol report
```

## Frontend and backend startup status

Current state:

- Frontend: not implemented yet.
- Backend server: not implemented yet as a separate HTTP API.
- Current backend/application layer: Python CLI package exposed by `futebol`.

So for now, start the app with:

```bash
futebol --help
```

If a future web frontend/backend is added, keep them separated:

```text
frontend/   # UI app, for example React/Vite or Angular
backend/    # API server, if different from the current Python package
```

Recommended future commands if implemented:

```bash
cd backend
pip install -e .
python3 -m futebol.app.api
```

```bash
cd frontend
npm install
npm run dev
```

Do not document those future commands as real until the folders and scripts exist.

## Verification before finishing code changes

Run:

```bash
python3 -m ruff check .
python3 -m mypy futebol
pytest futebol/tests -q
```

For CLI changes, also run:

```bash
futebol --help
```

If adding source scanning or exporting behavior, test with a small legal/local fixture playlist.

## Common pitfalls

- Do not treat unknown IPTV URLs as safe.
- Do not hardcode direct stream links from unofficial sources.
- Do not scrape official broadcaster pages to find hidden streams.
- Do not put many classes in one file.
- Do not add frontend/backend startup instructions unless those components actually exist.
- Keep reports explicit: included, rejected, broken, unknown.
