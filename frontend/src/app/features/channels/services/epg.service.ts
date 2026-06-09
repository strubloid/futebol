import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, of } from 'rxjs';
import { catchError, map, shareReplay } from 'rxjs/operators';

import { Channel } from '../models/channel.interface';
import { EpgChannelGuide, EpgProgramme } from '../models/epg.models';

/**
 * EPG data source:
 * Loads the single static guide.json produced by the Python scraper
 * (``futebol epg-scrape`` → frontend/public/epg/guide.json).
 *
 * No per-channel API calls — one fetch, all programmes.
 */
@Injectable({ providedIn: 'root' })
export class EpgService {
  private readonly http = inject(HttpClient);

  /** Cache of loaded channel guides, keyed by xmltv_id (without @SD/@HD). */
  private guideCache = new Map<string, EpgChannelGuide>();

  /** Single-source guide — loaded once, shared across subscribers. */
  private localGuide$: Observable<Map<string, EpgChannelGuide>> | null = null;

  /**
   * Strip feed qualifier from tvg-id.
   * e.g. "RedeGlobo.br@SD" → "RedeGlobo.br"
   */
  stripFeed(tvgId: string | null | undefined): string | null {
    if (!tvgId) return null;
    return tvgId.split('@')[0];
  }

  /**
   * Load guide data for a single channel from the local guide.json.
   */
  loadGuideForChannel(channel: Channel): Observable<EpgChannelGuide | null> {
    const xmltvId = this.stripFeed(channel.tvgId);
    if (!xmltvId) return of(null);
    return this.loadGuideForChannelId(xmltvId, channel.name);
  }

  /**
   * Load guide data for a channel by its xmltv_id from the local guide.
   */
  loadGuideForChannelId(
    xmltvId: string,
    _fallbackName?: string,
  ): Observable<EpgChannelGuide | null> {
    if (this.guideCache.has(xmltvId)) {
      return of(this.guideCache.get(xmltvId)!);
    }
    return this.loadLocalGuide().pipe(
      map((map) => map.get(xmltvId) ?? null),
    );
  }

  /**
   * Load guides for multiple channels from the local guide.json.
   * One HTTP request for all data.
   */
  loadGuidesForChannels(_channels?: Channel[]): Observable<Map<string, EpgChannelGuide>> {
    return this.loadLocalGuide();
  }

  /** Get currently cached guides. */
  getCachedGuides(): Map<string, EpgChannelGuide> {
    return this.guideCache;
  }

  /**
   * Fetch the full guide.json once and share it with all subscribers.
   */
  loadLocalGuide(): Observable<Map<string, EpgChannelGuide>> {
    if (this.localGuide$) {
      return this.localGuide$;
    }

    this.localGuide$ = this.http.get<any>('/epg/guide.json').pipe(
      map((data) => this.parseGuide(data)),
      catchError(() => of(new Map())),
      shareReplay(1),
    );

    return this.localGuide$;
  }

  // ─── Private helpers ────────────────────────────────────────────────────────

  private parseGuide(data: any): Map<string, EpgChannelGuide> {
    const now = new Date();
    const map = new Map<string, EpgChannelGuide>();

    // Build a quick lookup of logo per channel id
    const logoMap = new Map<string, string | null>();
    for (const ch of data.channels ?? []) {
      logoMap.set(ch.id, ch.logo || null);
    }

    // Group programmes by channel
    const programmeMap = new Map<string, EpgProgramme[]>();
    for (const prog of data.programs ?? []) {
      const channelId = prog.channel;
      if (!channelId) continue;

      const entry: EpgProgramme = {
        channel: channelId,
        title: prog.title ?? 'Unknown',
        start: prog.start,
        stop: prog.stop,
        description: prog.description || undefined,
        category: prog.category || undefined,
        isLive: prog.isLive ?? (new Date(prog.start) <= now && new Date(prog.stop) > now),
      };

      const list = programmeMap.get(channelId);
      if (list) {
        list.push(entry);
      } else {
        programmeMap.set(channelId, [entry]);
      }
    }

    // Sort programmes by start time
    for (const [, list] of programmeMap) {
      list.sort((a, b) => a.start.localeCompare(b.start));
    }

    // Build EpgChannelGuide for each channel that has programmes
    for (const ch of data.channels ?? []) {
      const id = ch.id;
      const programmes = programmeMap.get(id) ?? [];
      const nowPlaying = programmes.find((p) => p.isLive) ?? null;

      const guide: EpgChannelGuide = {
        channelId: id,
        name: ch.name || id,
        logoUrl: logoMap.get(id) ?? null,
        programmes,
        nowPlaying,
      };

      map.set(id, guide);
      this.guideCache.set(id, guide);
    }

    return map;
  }
}
