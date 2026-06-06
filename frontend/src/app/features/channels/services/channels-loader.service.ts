import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { map, of, catchError } from 'rxjs';

import {
  Channel,
  ChannelIndexEntry,
  ChannelIndexFile,
  ChannelManifest,
} from '../models/channel.interface';

@Injectable({ providedIn: 'root' })
export class ChannelsLoaderService {
  private readonly http = inject(HttpClient);

  /**
   * Load channels from channels/index.json.
   * Returns parsed channels with `working` status preserved.
   * Falls back to empty array if the index file doesn't exist.
   */
  loadFromIndex() {
    return this.http.get<ChannelIndexFile>('/channels/index.json').pipe(
      map((indexFile) => ({
        channels: indexFile.channels.map((entry) => this.entryToChannel(entry)),
        manifest: null as ChannelManifest | null,
      })),
      catchError(() => {
        // channels/ index not available — return empty, caller can fall back
        return of({ channels: [] as Channel[], manifest: null as ChannelManifest | null });
      }),
    );
  }

  /**
   * Load channel manifest from channels/manifest.json (summary data for stats).
   */
  loadManifest() {
    return this.http.get<ChannelManifest>('/channels/manifest.json').pipe(
      catchError(() => of(null as ChannelManifest | null)),
    );
  }

  /**
   * Convert a ChannelIndexEntry (from channels/index.json) to the app's Channel model.
   * Only includes channels marked as working.
   */
  private entryToChannel(entry: ChannelIndexEntry): Channel {
    return {
      id: entry.tvgId || this.fallbackId(entry.streamUrl),
      name: entry.name,
      streamUrl: entry.streamUrl,
      groupTitle: entry.groupTitle || 'Ungrouped',
      logoUrl: entry.logoUrl ?? null,
      tvgId: entry.tvgId || null,
      sourcePlaylistId: entry.sourcePlaylistId,
      sourcePlaylistName: entry.sourcePlaylist,
      working: entry.working !== false, // default to true
    };
  }

  private fallbackId(streamUrl: string): string {
    // Simple hash from URL for channels without tvgId
    let hash = 0;
    for (let i = 0; i < streamUrl.length; i++) {
      const chr = streamUrl.charCodeAt(i);
      hash = (hash << 5) - hash + chr;
      hash |= 0;
    }
    return 'ch-' + Math.abs(hash).toString(16);
  }
}
