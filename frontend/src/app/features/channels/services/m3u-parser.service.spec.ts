import { M3uParserService } from './m3u-parser.service';
import { PlaylistFile } from '../models/playlist-file.interface';

describe('M3uParserService', () => {
  const playlist: PlaylistFile = {
    id: 'sports-m3u',
    name: 'sports',
    fileName: 'sports.m3u',
    url: '/m3u/sports.m3u',
    sizeBytes: 100,
    updatedAt: '2026-06-06T00:00:00.000Z',
  };

  it('parses channel metadata and stream urls from an M3U file', () => {
    const service = new M3uParserService();
    const channels = service.parse(
      '#EXTM3U\n' +
        '#EXTINF:-1 tvg-id="cazetv.br" tvg-logo="https://logo.test/caze.png" group-title="Sports",CazéTV\n' +
        'https://stream.test/caze.m3u8\n' +
        '#EXTINF:-1 group-title="Football",Futebol BR\n' +
        'https://stream.test/futebol.m3u8\n',
      playlist,
    );

    expect(channels).toHaveLength(2);
    expect(channels[0]).toEqual(
      expect.objectContaining({
        name: 'CazéTV',
        groupTitle: 'Sports',
        tvgId: 'cazetv.br',
        logoUrl: 'https://logo.test/caze.png',
        streamUrl: 'https://stream.test/caze.m3u8',
        sourcePlaylistName: 'sports',
      }),
    );
    expect(channels[1].groupTitle).toBe('Football');
  });
});
