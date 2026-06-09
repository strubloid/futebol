import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, forkJoin, of } from 'rxjs';
import { catchError, map, switchMap } from 'rxjs/operators';

import { Channel } from '../models/channel.interface';
import {
  EpgChannelGuide,
  EpgProgramme,
  GuideManifest,
  IptvOrgChannel,
  IptvOrgGuide,
} from '../models/epg.models';

/**
 * Fetches and caches TV guide (EPG) data for channels.
 *
 * Data sources (all public, no auth):
 * - iptv-org channels.json  – channel metadata + logos
 * - iptv-org guides.json   – per-channel guide source URLs
 * - Per-channel JSON guide  – e.g. https://worker-xxx.onrender.com/guide.json
 */
@Injectable({ providedIn: 'root' })
export class EpgService {
  private readonly http = inject(HttpClient);

  /** Cache of loaded channel guides, keyed by xmltv_id (without @SD/@HD suffix). */
  private guideCache = new Map<string, EpgChannelGuide>();

  private readonly IPTV_ORG_CHANNELS = 'https://iptv-org.github.io/api/channels.json';
  private readonly IPTV_ORG_GUIDES = 'https://iptv-org.github.io/api/guides.json';

  /** All channels that have guide data, loaded once. */
  private channelsWithGuide: string[] | null = null;

  /**
   * Strip feed qualifier from tvg-id.
   * e.g. "RedeGlobo.br@SD" → "RedeGlobo.br"
   */
  stripFeed(tvgId: string | null | undefined): string | null {
    if (!tvgId) return null;
    return tvgId.split('@')[0];
  }

  /**
   * Load guide data for a single channel.
   * Returns null if no guide source is known for this channel.
   */
  loadGuideForChannel(channel: Channel): Observable<EpgChannelGuide | null> {
    const xmltvId = this.stripFeed(channel.tvgId);
    if (!xmltvId) return of(null);

    return this.loadGuideForChannelId(xmltvId, channel.name);
  }

  /**
   * Load guide data for a channel by its xmltv_id.
   * Returns null if no guide source is known.
   */
  loadGuideForChannelId(
    xmltvId: string,
    fallbackName: string,
  ): Observable<EpgChannelGuide | null> {
    // Check cache
    if (this.guideCache.has(xmltvId)) {
      return of(this.guideCache.get(xmltvId)!);
    }

    return this.http.get<IptvOrgGuide[]>(this.IPTV_ORG_GUIDES).pipe(
      switchMap((guides) => {
        // Find all guide entries matching this channel
        const matches = guides.filter(
          (g) =>
            g.channel === xmltvId || g.channel?.split('@')[0] === xmltvId,
        );

        // Find a source with JSON format
        const jsonSource = matches
          .flatMap((g) => g.sources)
          .find((s) => s.format === 'JSON' && s.url);

        if (!jsonSource) return of(null);

        return this.fetchAndParseGuide(jsonSource.url, xmltvId, fallbackName);
      }),
      catchError(() => of(null)),
      map((result) => {
        if (result) {
          this.guideCache.set(xmltvId, result);
        }
        return result;
      }),
    );
  }

  /**
   * Load guides for multiple channels concurrently.
   * Only loads if a guide source exists (skips silently if not).
   * Returns a map of xmltvId → EpgChannelGuide (null entries are skipped).
   */
  loadGuidesForChannels(channels: Channel[]): Observable<Map<string, EpgChannelGuide>> {
    const requests: Observable<{ id: string; guide: EpgChannelGuide | null }>[] = [];

    for (const ch of channels) {
      const xmltvId = this.stripFeed(ch.tvgId);
      if (!xmltvId) continue;
      if (this.guideCache.has(xmltvId)) {
        requests.push(
          of({ id: xmltvId, guide: this.guideCache.get(xmltvId)! }),
        );
      } else {
        requests.push(
          this.loadGuideForChannel(ch).pipe(
            map((guide) => ({ id: xmltvId, guide })),
          ),
        );
      }
    }

    return forkJoin(requests).pipe(
      map((results) => {
        const map_ = new Map<string, EpgChannelGuide>();
        for (const { id, guide } of results) {
          if (guide) map_.set(id, guide);
        }
        return map_;
      }),
    );
  }

  /**
   * Get currently cached guides.
   */
  getCachedGuides(): Map<string, EpgChannelGuide> {
    return this.guideCache;
  }

  /** Load the guide manifest listing channels that have guide data. */
  loadChannelsWithGuide(): Observable<string[]> {
    if (this.channelsWithGuide) {
      return of(this.channelsWithGuide);
    }
    return this.http
      .get<GuideManifest>('/channels/guide-manifest.json')
      .pipe(
        map((m) => {
          this.channelsWithGuide = m.channelsWithGuide;
          return m.channelsWithGuide;
        }),
        catchError(() => {
          this.channelsWithGuide = [];
          return of([]);
        }),
      );
  }

  // ─── Private helpers ────────────────────────────────────────────────────────

  private fetchAndParseGuide(
    url: string,
    xmltvId: string,
    fallbackName: string,
  ) {
    return this.http.get<any>(url, { responseType: 'json' }).pipe(
      map((data) => {
        const today = new Date().toISOString().split('T')[0];
        const now = new Date();

        const chMap = new Map<string, { name: string; logo: string | null }>();
        for (const ch of data.channels ?? []) {
          chMap.set(ch.xmltv_id, {
            name: ch.name ?? fallbackName,
            logo: ch.logo ?? null,
          });
        }

        const name = chMap.get(xmltvId)?.name ?? fallbackName;
        const logo = chMap.get(xmltvId)?.logo ?? null;

        const todaySec = Date.parse(today) / 1000;
        const tomorrowSec = todaySec + 86400;

        const programmes: EpgProgramme[] = (data.programs ?? [])
          .filter(
            (p: any) =>
              p.channel === xmltvId &&
              p.start >= todaySec * 1000 &&
              p.start < tomorrowSec * 1000,
          )
          .map((p: any) => {
            const start = new Date(p.start);
            const stop = new Date(p.stop);
            return {
              channel: xmltvId,
              title: Array.isArray(p.titles) ? p.titles[0]?.value ?? '' : (p.titles?.value ?? ''),
              start: start.toISOString(),
              stop: stop.toISOString(),
              description: Array.isArray(p.descriptions)
                ? p.descriptions[0]?.value ?? undefined
                : p.descriptions?.value ?? undefined,
              category: Array.isArray(p.categories) ? p.categories[0] : undefined,
              isLive: start <= now && stop > now,
            };
          })
          .sort((a: EpgProgramme, b: EpgProgramme) =>
            a.start.localeCompare(b.start),
          );

        const nowPlaying = programmes.find((p) => p.isLive) ?? null;

        const guide: EpgChannelGuide = {
          channelId: xmltvId,
          name,
          logoUrl: logo,
          programmes,
          nowPlaying,
        };

        this.guideCache.set(xmltvId, guide);
        return guide;
      }),
      catchError(() => of(null)),
    );
  }
}