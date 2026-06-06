# Project: futebol

## Summary

`futebol` is a legal IPTV discovery and playlist-management application for football/soccer content. It is designed for users who want to manage legitimate IPTV playlists, identify football-related channels/events, prioritize Brazilian Portuguese coverage, and export clean playlists and reports.

The project is especially oriented toward World Cup coverage research for Brazil, while staying inside legal boundaries.

## What problem it solves

IPTV playlists can contain many channels, broken URLs, unclear metadata, mixed languages, and unknown source legitimacy. `futebol` helps by:

1. Loading legal/user-provided playlists.
2. Validating playlist and stream URLs.
3. Parsing M3U/M3U8 channel metadata.
4. Detecting football, World Cup, and Brazilian Portuguese signals.
5. Separating included channels from unknown, rejected, or broken entries.
6. Exporting a clean M3U playlist.
7. Producing JSON and console reports explaining decisions.

## What it is not

`futebol` is not a pirate IPTV finder. It does not include pirate links, stolen channel packs, paid-channel bypasses, DRM bypasses, geo-block bypasses, or scraping of hidden broadcaster streams.

The application is intended for legal IPTV organization and official broadcaster metadata discovery.

## Current product state

Current implementation:

- Python CLI application
- Clean architecture package under `futebol/`
- JSON-backed local persistence
- M3U parser
- stream URL validator/prober
- football/Brazil/World Cup filters
- M3U and JSON exporters
- Rich console reports
- unit tests, linting, and strict typing

Not implemented yet:

- Web frontend
- HTTP backend/API server
- Authentication
- Scheduled scanning
- Full EPG/channel matching workflow
- Browser-based playlist management UI

## User-facing workflow

A normal user flow is:

1. Install the app.
2. Add one or more legal sources.
3. Scan sources.
4. Filter by football and language.
5. Validate streams.
6. Export a clean playlist.
7. Read the report to see why channels were included or rejected.

Example:

```bash
pip install -e .
futebol sources add-folder ./m3u
futebol scan
futebol filter --category football --language pt-BR
futebol validate-streams
futebol export --format m3u --output futebol-worldcup.m3u
futebol report
```

## How to start the project

### Current CLI/backend-style app

There is no web frontend yet and no separate backend server yet. The current executable app is the Python CLI.

From the project root:

```bash
pip install -e .
futebol
```

Use `futebol --help` only when you want command reference for automation.

Bulk-add all playlist files from a folder:

```bash
futebol sources add-folder ./m3u
```

Download legal/user-provided playlist URLs from a text file and add them automatically:

```bash
futebol sources download-list ./m3u-urls.txt --output-dir ./m3u
```

Run a command:

```bash
futebol scan
```

### Backend

Current backend/application layer:

```text
futebol/
  app/
  services/
  repositories/
  validators/
  filters/
  domain/
```

Start it through the CLI:

```bash
futebol --help
```

There is currently no command like `npm run backend`, `uvicorn`, `fastapi`, or `python app.py`, because no HTTP API server exists yet.

If a real backend API is added later, recommended structure:

```text
backend/
  pyproject.toml
  backend/
    api.py
    routes/
```

Potential future startup command:

```bash
cd backend
pip install -e .
python3 -m backend.api
```

Only use/document that once it actually exists.

### Frontend

There is currently no frontend folder and no UI app to start.

If a frontend is added later, recommended structure:

```text
frontend/
  package.json
  src/
```

Potential future startup command:

```bash
cd frontend
npm install
npm run dev
```

Only use/document that once `frontend/package.json` exists.

## Main modules

### `futebol/app`

Application entrypoints.

- `cli.py`: Typer CLI commands.
- `application.py`: orchestration only.

### `futebol/domain`

Business objects and enums.

Models:

- `Channel`
- `Playlist`
- `Stream`
- `EpgProgram`
- `SearchResult`

Enums:

- `ChannelCategory`
- `StreamStatus`
- `SourceType`

### `futebol/services`

Business services:

- `PlaylistLoaderService`: loads local or remote playlist content.
- `PlaylistParserService`: parses M3U/M3U8 playlists.
- `StreamValidatorService`: probes stream availability.
- `ChannelFilterService`: applies filters and inclusion rules.
- `FootballDetectorService`: detects football terms.
- `BroadcasterSearchService`: stores official broadcaster metadata references.
- `EpgParserService`: parses XMLTV EPG content.
- `ReportService`: summarizes channel decisions.

### `futebol/validators`

Focused validators:

- `UrlValidator`
- `StreamUrlValidator`
- `LegalSourceValidator`
- `M3uFormatValidator`

### `futebol/filters`

Focused channel filters:

- `FootballFilter`
- `BrazilianPortugueseFilter`
- `WorldCupFilter`
- `LiveChannelFilter`

### `futebol/output`

Export and reporting:

- `M3uExporter`
- `JsonExporter`
- `ConsoleReporter`

## Data and persistence

By default, runtime data is stored in:

```text
.futebol/
  sources.json
  channels.json
```

Configure with:

```bash
FUTEBOL_DATA_DIR=.futebol
```

## Configuration

Environment variables:

```bash
FUTEBOL_DATA_DIR=.futebol
FUTEBOL_STREAM_TIMEOUT_SECONDS=8
FUTEBOL_ALLOW_UNKNOWN_SOURCES=false
```

Safe default:

```bash
FUTEBOL_ALLOW_UNKNOWN_SOURCES=false
```

## Legal source handling

Source handling is intentionally conservative.

- `official`: can be included if it points to valid playable content or metadata.
- `public/free/legal`: can be included.
- `user-provided`: can be included, but the user is responsible for having rights.
- `unknown`: reported but excluded from final playable playlist by default.
- `blocked/rejected`: always excluded.

## Football and Brazil detection

Football keywords include:

- futebol
- football
- soccer
- copa
- copa do mundo
- mundial
- brasil
- seleção brasileira
- sportv
- ge
- cazétv
- globo
- esporte
- fifa
- world cup

Brazilian Portuguese indicators include:

- pt-BR
- Portuguese/Português
- Brasil/Brazil
- Globo
- ge
- CazéTV
- SporTV

## Quality gates

Run before finishing development work:

```bash
python3 -m ruff check .
python3 -m mypy futebol
pytest futebol/tests -q
```

CLI smoke check:

```bash
futebol --help
```

## Suggested next project milestones

1. Add integration tests for full scan/filter/export with a local fixture playlist.
2. Add an HTTP API backend if a web UI is needed.
3. Add a frontend dashboard for sources, channels, validation status, and exports.
4. Add EPG matching to identify football events by schedule.
5. Add official broadcaster metadata refresh without scraping unauthorized streams.
6. Add clearer reports for legal status, stream status, and filter-match reasons.

## Product principles

- Legal-first.
- Explain every inclusion/rejection decision.
- Prefer official and Brazilian Portuguese sources.
- Keep architecture modular and testable.
- Keep the CLI useful even before a web frontend exists.
