import {
  Component,
  OnInit,
  computed,
  inject,
  signal,
} from '@angular/core';
import { DatePipe, SlicePipe } from '@angular/common';
import { RouterLink } from '@angular/router';

import { Channel } from '../../models/channel.interface';
import { ChannelsLoaderService } from '../../services/channels-loader.service';
import { EpgService } from '../../services/epg.service';
import { EpgChannelGuide, EpgProgramme } from '../../models/epg.models';
import { ChannelFilters } from '../../models/channel-filters.interface';
import { ChannelFiltersComponent } from '../../components/channel-filters/channel-filters';
import { ChannelPlayerComponent } from '../../components/channel-player/channel-player';

type TimeView = 'now' | 'later' | 'all';
type SortBy = 'name' | 'now';

@Component({
  selector: 'app-guide-page',
  imports: [DatePipe, RouterLink, ChannelFiltersComponent, SlicePipe, ChannelPlayerComponent],
  templateUrl: './guide-page.html',
  styleUrl: './guide-page.scss',
})
export class GuidePage implements OnInit {
  private readonly channelsLoader = inject(ChannelsLoaderService);
  private readonly epgService = inject(EpgService);

  protected readonly channels = signal<Channel[]>([]);
  protected readonly guideMap = signal<Map<string, EpgChannelGuide>>(new Map());
  protected readonly isLoading = signal(true);
  protected readonly loadingMessage = signal('scanning guides…');
  protected readonly error = signal<string | null>(null);
  protected readonly loadedCount = signal(0);
  protected readonly totalToLoad = signal(0);
  protected readonly selectedChannel = signal<EpgChannelGuide | null>(null);
  protected readonly guideOpen = signal(false);

  /** Channel selected for playing (opens player overlay). */
  protected readonly playerChannel = signal<Channel | null>(null);
  protected readonly playerOpen = computed(() => this.playerChannel() !== null);
  protected readonly filters = signal<ChannelFilters>({
    searchTerm: '',
    playlistId: 'all',
    favoritesOnly: false,
    showNonWorking: false,
    language: 'all',
    country: 'all',
    state: 'all',
    accessType: 'all',
    channelType: 'all',
  });
  protected readonly timeView = signal<TimeView>('now');
  protected readonly sortBy = signal<SortBy>('name');

  /** Channels that have guide data loaded */
  protected readonly channelsWithGuide = computed(() =>
    this.channels().filter((ch) => {
      const id = this.epgService.stripFeed(ch.tvgId);
      return id && this.guideMap().has(id!);
    }),
  );

  /** Channels without guide data */
  protected readonly channelsWithoutGuide = computed(() =>
    this.channels().filter((ch) => {
      const id = this.epgService.stripFeed(ch.tvgId);
      return id && !this.guideMap().has(id!);
    }),
  );

  /** Channels filtered + enriched with guide data */
  protected readonly enrichedChannels = computed(() => {
    const map = this.guideMap();
    const f = this.filters();
    const search = f.searchTerm.trim().toLowerCase();

    return this.channelsWithGuide()
      .filter((ch) => {
        if (search) {
          const id = this.epgService.stripFeed(ch.tvgId)!;
          const guide = map.get(id);
          const matchesText =
            ch.name.toLowerCase().includes(search) ||
            ch.sourcePlaylistName.toLowerCase().includes(search) ||
            (guide?.nowPlaying?.title ?? '').toLowerCase().includes(search);
          if (!matchesText) return false;
        }
        if (f.playlistId !== 'all' && ch.sourcePlaylistId !== f.playlistId)
          return false;
        if (f.language !== 'all' && ch.language !== f.language) return false;
        if (f.country !== 'all' && ch.country !== f.country) return false;
        return true;
      })
      .map((ch) => {
        const id = this.epgService.stripFeed(ch.tvgId)!;
        return { channel: ch, guide: map.get(id)! };
      });
  });

  /** Channels sorted for display */
  protected readonly sortedChannels = computed(() => {
    const list = [...this.enrichedChannels()];
    if (this.sortBy() === 'now') {
      list.sort((a, b) =>
        (a.guide.nowPlaying?.title ?? 'zzz').localeCompare(
          b.guide.nowPlaying?.title ?? 'zzz',
        ),
      );
    } else {
      list.sort((a, b) => a.channel.name.localeCompare(b.channel.name));
    }
    return list;
  });

  /** Playlist names for filter dropdown */
  protected readonly playlistNames = computed(() => {
    const seen = new Map<string, { id: string; name: string }>();
    for (const ch of this.channels()) {
      if (!seen.has(ch.sourcePlaylistId)) {
        seen.set(ch.sourcePlaylistId, {
          id: ch.sourcePlaylistId,
          name: ch.sourcePlaylistName,
        });
      }
    }
    return [...seen.values()].sort((a, b) => a.name.localeCompare(b.name));
  });

  /** Channels with live right now */
  protected readonly liveChannels = computed(() =>
    this.sortedChannels().filter(
      (item) =>
        item.guide.nowPlaying &&
        item.guide.nowPlaying.isLive,
    ),
  );

  ngOnInit(): void {
    this.loadChannelsAndGuides();
  }

  private loadChannelsAndGuides(): void {
    this.isLoading.set(true);
    this.channelsLoader.loadFromIndex().subscribe({
      next: ({ channels }) => {
        this.channels.set(channels);
        this.totalToLoad.set(channels.length);
        this.loadGuides(channels);
      },
      error: () => {
        this.error.set('Could not load channels. Run "futebol load-servers" first.');
        this.isLoading.set(false);
      },
    });
  }

  private loadGuides(channels: Channel[]): void {
    // Subscribe to start loading and track progress
    this.epgService.loadGuidesForChannels(channels).subscribe({
      next: (map) => {
        this.guideMap.set(map);
        this.loadedCount.set(map.size);
        this.isLoading.set(false);
      },
      error: () => {
        this.error.set('Could not load guide data.');
        this.isLoading.set(false);
      },
    });
  }

  protected openGuide(ch: EpgChannelGuide): void {
    this.selectedChannel.set(ch);
    this.guideOpen.set(true);
  }

  protected openPlayer(channel: Channel): void {
    this.playerChannel.set(channel);
  }

  protected closePlayer(): void {
    this.playerChannel.set(null);
  }

  protected closeGuide(): void {
    this.guideOpen.set(false);
    this.selectedChannel.set(null);
  }

  protected updateFilters(filters: ChannelFilters): void {
    this.filters.set(filters);
  }

  protected resetFilters(): void {
    this.filters.set({
      searchTerm: '',
      playlistId: 'all',
      favoritesOnly: false,
      showNonWorking: false,
      language: 'all',
      country: 'all',
      state: 'all',
      accessType: 'all',
      channelType: 'all',
    });
  }

  protected setTimeView(view: TimeView): void {
    this.timeView.set(view);
  }

  protected setSortBy(sort: SortBy): void {
    this.sortBy.set(sort);
  }

  protected formatTime(isoStr: string): string {
    const d = new Date(isoStr);
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }

  protected durationMinutes(start: string, stop: string): number {
    return Math.round(
      (new Date(stop).getTime() - new Date(start).getTime()) / 60000,
    );
  }

  protected isPastProgramme(prog: EpgProgramme): boolean {
    return !prog.isLive && new Date(prog.stop) < new Date();
  }

  protected trackByChannelId(
    _index: number,
    item: { channel: Channel; guide: EpgChannelGuide },
  ): string {
    return item.channel.id;
  }

  protected trackByProgramme(_index: number, prog: EpgProgramme): string {
    return `${prog.title}-${prog.start}`;
  }
}