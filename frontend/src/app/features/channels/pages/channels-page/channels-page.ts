import { Component, computed, inject, signal } from '@angular/core';
import { take } from 'rxjs';
import { RouterLink } from '@angular/router';

import { Channel } from '../../models/channel.interface';
import { ChannelFilters } from '../../models/channel-filters.interface';
import { PlaylistFile } from '../../models/playlist-file.interface';
import { ChannelsLoaderService } from '../../services/channels-loader.service';
import { FavoriteChannelsService } from '../../services/favorite-channels.service';
import { ChannelFiltersComponent } from '../../components/channel-filters/channel-filters';
import { ChannelListComponent } from '../../components/channel-list/channel-list';
import { ChannelPlayerComponent } from '../../components/channel-player/channel-player';
import { EpgPanelComponent } from '../../components/epg-panel/epg-panel';

@Component({
  selector: 'app-channels-page',
  imports: [
    ChannelFiltersComponent,
    ChannelListComponent,
    ChannelPlayerComponent,
    EpgPanelComponent,
    RouterLink,
  ],
  templateUrl: './channels-page.html',
  styleUrl: './channels-page.scss',
})
export class ChannelsPage {
  private readonly channelsLoader = inject(ChannelsLoaderService);
  private readonly favoriteChannels = inject(FavoriteChannelsService);

  protected readonly channels = signal<Channel[]>([]);
  protected readonly playlists = signal<PlaylistFile[]>([]);
  protected readonly selectedChannel = signal<Channel | null>(null);
  protected readonly isLoading = signal(true);
  protected readonly error = signal<string | null>(null);
  protected readonly loadingPhase = signal(0);
  protected readonly favoriteIds = this.favoriteChannels.favoriteIds;

  /** EPG panel state */
  protected readonly epgChannel = signal<Channel | null>(null);
  protected readonly epgOpen = computed(() => this.epgChannel() !== null);

  /** True while the player overlay is open. */
  protected readonly playerOpen = computed(() => this.selectedChannel() !== null);

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

  /** Deduplicated playlist names for the filter dropdown */
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

  /** Apply all filters */
  protected readonly filteredChannels = computed(() => {
    const filters = this.filters();
    const searchTerm = filters.searchTerm.trim().toLowerCase();

    return this.channels().filter((channel) => {
      // Working status filter
      if (!channel.working && !filters.showNonWorking) {
        return false;
      }

      // Text search
      if (searchTerm.length > 0) {
        const matchesText =
          channel.name.toLowerCase().includes(searchTerm) ||
          channel.sourcePlaylistName.toLowerCase().includes(searchTerm) ||
          (channel.country || '').toLowerCase().includes(searchTerm) ||
          (channel.state || '').toLowerCase().includes(searchTerm) ||
          (channel.channelType || '').toLowerCase().includes(searchTerm);
        if (!matchesText) return false;
      }

      // Playlist filter
      if (filters.playlistId !== 'all' && channel.sourcePlaylistId !== filters.playlistId) {
        return false;
      }

      // Favorites only
      if (filters.favoritesOnly && !this.favoriteChannels.isFavorite(channel.id)) {
        return false;
      }

      // Language
      if (filters.language !== 'all' && channel.language !== filters.language) {
        return false;
      }

      // Country
      if (filters.country !== 'all' && channel.country !== filters.country) {
        return false;
      }

      // State (Brazil)
      if (filters.state !== 'all' && channel.state !== filters.state) {
        return false;
      }

      // Access type
      if (filters.accessType === 'free' && !channel.isFree) return false;
      if (filters.accessType === 'premium' && channel.isFree) return false;

      // Channel type
      if (filters.channelType !== 'all' && channel.channelType !== filters.channelType) {
        return false;
      }

      return true;
    });
  });

  protected readonly stats = computed(() => ({
    totalChannels: this.channels().length,
    totalPlaylists: this.playlistNames().length,
    visibleChannels: this.filteredChannels().length,
    favoriteChannels: this.favoriteIds().length,
    workingChannels: this.channels().filter((c) => c.working).length,
    freeChannels: this.channels().filter((c) => c.isFree).length,
    premiumChannels: this.channels().filter((c) => !c.isFree).length,
    languages: new Set(this.channels().map((c) => c.language).filter(Boolean)).size,
    countries: new Set(this.channels().map((c) => c.country).filter(Boolean)).size,
  }));

  constructor() {
    this.loadChannels();
  }

  protected loadChannels(): void {
    this.isLoading.set(true);
    this.error.set(null);
    this.loadingPhase.set(0);

    // Animate loading phases
    const phaseInterval = setInterval(() => {
      this.loadingPhase.update((p) => Math.min(p + 1, 4));
    }, 600);

    this.channelsLoader
      .loadFromIndex()
      .pipe(take(1))
      .subscribe({
        next: ({ channels }) => {
          clearInterval(phaseInterval);
          this.loadingPhase.set(4);
          this.channels.set(channels);
          this.isLoading.set(false);
        },
        error: () => {
          clearInterval(phaseInterval);
          this.error.set(
            'Could not load channels. Run "futebol load-servers" then restart the frontend.',
          );
          this.isLoading.set(false);
        },
      });
  }

  protected updateFilters(filters: ChannelFilters): void {
    this.filters.set(filters);
  }

  protected openPlayer(channel: Channel): void {
    this.selectedChannel.set(channel);
  }

  protected closePlayer(): void {
    this.selectedChannel.set(null);
  }

  protected openEpg(channel: Channel): void {
    this.epgChannel.set(channel);
  }

  protected closeEpg(): void {
    this.epgChannel.set(null);
  }

  protected toggleFavorite(channel: Channel): void {
    this.favoriteChannels.toggleFavorite(channel.id);
  }

  /** Reset all filters to defaults */
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
}
