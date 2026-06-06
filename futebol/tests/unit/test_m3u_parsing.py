from futebol.services.playlist_parser_service import PlaylistParserService


def test_parses_m3u_channels_with_metadata() -> None:
    content = """#EXTM3U
#EXTINF:-1 tvg-id="caze" tvg-name="CazéTV" group-title="Esporte",CazéTV Copa do Mundo
https://example.org/live/caze.m3u8
#EXTINF:-1 group-title="News",Not Sports
https://example.org/news.m3u8
"""

    playlist = PlaylistParserService().parse(content, source_url="user://test")

    assert len(playlist.channels) == 2
    assert playlist.channels[0].name == "CazéTV Copa do Mundo"
    assert playlist.channels[0].tvg_id == "caze"
    assert playlist.channels[0].group_title == "Esporte"
    assert playlist.channels[0].stream.url == "https://example.org/live/caze.m3u8"
