# futebol

Legal IPTV discovery and playlist management focused on football/soccer content, with a special bias toward Brazilian Portuguese World Cup coverage.

This project does not include pirate IPTV URLs and does not discover or scrape unauthorized IPTV services. It manages only:

- official broadcaster pages and metadata,
- public/free/legal streams,
- free-to-air streams where the source is clearly legitimate,
- user-provided M3U/M3U8 playlists,
- verified public sources.

Unknown sources are marked as `unknown` and are not automatically included in the exported playable playlist.

## Legal boundaries

Do not use this app to bypass authentication, paywalls, DRM, geo-blocks, token checks, or private broadcaster apps. Do not add stolen IPTV playlists, Xtream/Stalker panels, pirate portals, or links advertised as premium channel packs.

Every source has one legitimacy status:

- `official`
- `public/free/legal`
- `user-provided`
- `unknown`
- `blocked/rejected`

Only `official`, `public/free/legal`, and `user-provided` sources are eligible for automatic inclusion. `unknown` sources are kept in reports but excluded from final M3U exports unless explicitly allowed by configuration.

## IPTV basics

IPTV means television/video delivered over IP networks instead of cable, satellite, or terrestrial broadcast. In practice, legal IPTV apps commonly use playlist files, HTTP streaming protocols, and optional programme metadata.

### M3U and M3U8

M3U is a plain-text playlist format. IPTV M3U files usually contain:

```m3u
#EXTM3U
#EXTINF:-1 tvg-id="channel-id" tvg-name="Channel" group-title="Sports",Channel
https://example.org/live/channel.m3u8
```

M3U8 is the UTF-8 variant and is also commonly used for HLS manifests. A playlist may point to channel streams, and an HLS manifest may point to individual video segments.

### HLS streams

HLS, HTTP Live Streaming, is Apple's adaptive streaming protocol. A player downloads a `.m3u8` manifest, then downloads small media segments listed in that manifest. Some HLS manifests include multiple quality variants so players can switch quality according to bandwidth.

This app validates stream URLs by probing them over HTTP. It does not decrypt DRM, bypass token systems, or attempt to access private media.

### EPG/XMLTV metadata

EPG means Electronic Programme Guide. XMLTV is a common XML format for channel schedules. It maps channel IDs to programme entries with titles, descriptions, start times, stop times, and optional languages.

The app includes an XMLTV parser service so future workflows can identify events such as World Cup matches by programme title and description.

### How IPTV players organize channels

IPTV players normally group channels using M3U metadata:

- `group-title` for categories such as Sports, News, Football,
- `tvg-id` to match channels with EPG entries,
- `tvg-name` for display names,
- `tvg-logo` for channel icons.

`futebol` normalizes each parsed entry into a `Channel` model and then applies football, World Cup, live, and Brazilian Portuguese filters.

## World Cup and Brazil focus

The project stores official broadcaster metadata, not direct unauthorized stream links. A verified direction is FIFA's official article confirming CazéTV media rights for Brazil coverage of FIFA World Cup 26:

https://www.fifa.com/en/tournaments/mens/worldcup/canadamexicousa2026/articles/caze-tv-brazil-media-rights

CazéTV's official YouTube page is represented as official broadcaster metadata:

https://www.youtube.com/@CazeTV

The app must not scrape those pages for hidden stream URLs. If an official public live URL exists, add it only as a legal source or user-provided playlist entry.

## Architecture

The code follows clean architecture and SOLID-oriented separation:

- `domain/models`: dataclass DTOs/entities such as Channel, Stream, Playlist, EpgProgram.
- `domain/enums`: source, stream, and channel classification enums.
- `services`: parsing, loading, validation, filtering orchestration, reporting, EPG parsing.
- `validators`: URL, stream URL, M3U, and legal source checks.
- `filters`: focused channel filters.
- `providers`: source providers for local files, URLs, official metadata, and user playlists.
- `repositories`: JSON-backed persistence for sources/channels.
- `factories`: construction helpers.
- `output`: M3U, JSON, and console reporting.
- `app`: CLI and Application orchestration.

The `Application` class only orchestrates the flow. Parsing, validation, filtering, storage, and exporting live in separate classes.

## Install

Python 3.12+ is required.

```bash
pip install -e .
```

## Configuration

Copy `.env.example` if desired or set environment variables directly:

```bash
FUTEBOL_DATA_DIR=.futebol
FUTEBOL_STREAM_TIMEOUT_SECONDS=8
FUTEBOL_ALLOW_UNKNOWN_SOURCES=false
```

`FUTEBOL_ALLOW_UNKNOWN_SOURCES=false` is the safe default.

## CLI usage

Start the interactive menu:

```bash
futebol
```

Pick `1. Load M3U playlists` to open a load submenu with choices for a single file, a folder, one internet URL, or `Search sports playlists for me` which automatically downloads curated sports/Brazil public playlists into `m3u/`. The scriptable commands below remain available for automation.

Add a legal/user-provided playlist URL:

```bash
futebol sources add --url "https://example.org/legal-playlist.m3u"
```

Add a local user-provided playlist file:

```bash
futebol sources add-file ./playlist.m3u
```

Add every `.m3u`/`.m3u8` file from a folder recursively:

```bash
futebol sources add-folder ./m3u
```

Download legal/user-provided playlist URLs from a text file into `./m3u` and add them automatically:

```bash
futebol sources download-list ./m3u-urls.txt --output-dir ./m3u
```

Download one legal/user-provided playlist URL into `./m3u` and add it automatically:

```bash
futebol sources download-url "https://example.org/legal-playlist.m3u" --output-dir ./m3u
```

Download curated public M3U playlists into `./m3u` and add them automatically:

```bash
futebol sources download-public --output-dir ./m3u
```

Search a folder recursively for existing `.m3u`/`.m3u8` files, copy them into `./m3u`, and add them automatically:

```bash
futebol sources search-local . --output-dir ./m3u
```

The URL list file should contain one playlist URL per line. Blank lines and `#` comments are ignored. URLs matching blocked IPTV panel/piracy terms are skipped.

Scan configured sources:

```bash
futebol scan
```

Filter football channels with Brazilian Portuguese preference:

```bash
futebol filter --category football --language pt-BR
```

Validate stream availability:

```bash
futebol validate-streams
```

Export an M3U playlist containing only included legal/allowed channels:

```bash
futebol export --format m3u --output futebol-worldcup.m3u
```

Generate a console report:

```bash
futebol report
```

## Source validation rules

The app validates:

1. URL format: only HTTP/HTTPS URLs are accepted as remote sources.
2. Legal status: blocked terms such as pirate panel patterns are rejected.
3. M3U format: playlists must start with `#EXTM3U` and include `#EXTINF` entries.
4. Stream availability: HTTP HEAD/GET probes classify streams as alive, broken, or unreachable.
5. Unknown legitimacy: unknown sources are reported but not auto-exported.

## Football/Brazilian/World Cup detection

Football detection uses keywords including:

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

Brazilian Portuguese detection prioritizes terms such as:

- pt-BR
- Portuguese/Português
- Brasil/Brazil
- Globo
- ge
- CazéTV
- SporTV

## Development checks

```bash
python3 -m ruff check .
python3 -m mypy futebol
pytest futebol/tests -q
```

## Important note

This is a legal playlist-management and discovery-support tool, not a pirate IPTV finder. It helps users manage playlists they are legally allowed to use and documents official broadcaster metadata for research. It intentionally avoids unauthorized scraping, hardcoded illegal URLs, and paywall/DRM/authentication bypasses.
