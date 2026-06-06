import { Injectable } from '@angular/core';

import { Channel } from '../models/channel.interface';
import { PlaylistFile } from '../models/playlist-file.interface';

@Injectable({ providedIn: 'root' })
export class M3uParserService {
  parse(content: string, playlist: PlaylistFile): Channel[] {
    const channels: Channel[] = [];
    const lines = content
      .split(/\r?\n/)
      .map((line) => line.trim())
      .filter(Boolean);

    let pendingMetadata: ParsedMetadata | null = null;

    for (const line of lines) {
      if (line.startsWith('#EXTINF')) {
        pendingMetadata = this.parseExtInf(line);
        continue;
      }

      if (line.startsWith('#')) {
        continue;
      }

      const name = pendingMetadata?.name || this.nameFromUrl(line);
      const id = `${playlist.id}-${channels.length}-${this.slug(name)}`;

      channels.push({
        id,
        name,
        streamUrl: line,
        groupTitle: pendingMetadata?.attributes['group-title'] || 'Ungrouped',
        logoUrl: pendingMetadata?.attributes['tvg-logo'] || null,
        tvgId: pendingMetadata?.attributes['tvg-id'] || null,
        sourcePlaylistId: playlist.id,
        sourcePlaylistName: playlist.name,
      });

      pendingMetadata = null;
    }

    return channels;
  }

  private parseExtInf(line: string): ParsedMetadata {
    const commaIndex = line.indexOf(',');
    const metadata = commaIndex >= 0 ? line.slice(0, commaIndex) : line;
    const name = commaIndex >= 0 ? line.slice(commaIndex + 1).trim() : 'Unnamed channel';
    const attributes: Record<string, string> = {};
    const attributeRegex = /([\w-]+)="([^"]*)"/g;
    let match: RegExpExecArray | null;

    while ((match = attributeRegex.exec(metadata)) !== null) {
      attributes[match[1]] = match[2];
    }

    return { name: name || 'Unnamed channel', attributes };
  }

  private nameFromUrl(url: string): string {
    try {
      const parsed = new URL(url);
      const lastPathPart = parsed.pathname.split('/').filter(Boolean).at(-1);
      return lastPathPart ? decodeURIComponent(lastPathPart) : parsed.hostname;
    } catch {
      return url;
    }
  }

  private slug(value: string): string {
    return value.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') || 'channel';
  }
}

interface ParsedMetadata {
  name: string;
  attributes: Record<string, string>;
}
