import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { forkJoin, map, of, switchMap } from 'rxjs';

import { Channel } from '../models/channel.interface';
import { PlaylistFile, PlaylistManifest } from '../models/playlist-file.interface';
import { M3uParserService } from './m3u-parser.service';

@Injectable({ providedIn: 'root' })
export class PlaylistLoaderService {
  private readonly http = inject(HttpClient);
  private readonly parser = inject(M3uParserService);

  loadChannels() {
    return this.http.get<PlaylistManifest>('/m3u/manifest.json').pipe(
      switchMap((manifest) => {
        if (manifest.playlists.length === 0) {
          return of({ playlists: manifest.playlists, channels: [] as Channel[] });
        }

        return forkJoin(
          manifest.playlists.map((playlist) => this.loadPlaylist(playlist)),
        ).pipe(
          map((channelGroups) => ({
            playlists: manifest.playlists,
            channels: channelGroups.flat(),
          })),
        );
      }),
    );
  }

  private loadPlaylist(playlist: PlaylistFile) {
    return this.http
      .get(playlist.url, { responseType: 'text' })
      .pipe(map((content) => this.parser.parse(content, playlist)));
  }
}
