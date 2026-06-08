import { Component, computed, inject, signal } from '@angular/core';
import { take } from 'rxjs';

import { Channel } from '../../models/channel.interface';
import { ChannelFilters } from '../../models/channel-filters.interface';
import { PlaylistFile } from '../../models/playlist-file.interface';
import { ChannelsLoaderService } from '../../services/channels-loader.service';
import { FavoriteChannelsService } from '../../services/favorite-channels.service';
import { ChannelFiltersComponent } from '../../components/channel-filters/channel-filters';
import { ChannelListComponent } from '../../components/channel-list/channel-list';
import { ChannelPlayerComponent } from '../../components/channel-player/channel-player';

@Component({
  selector: 'app-channels-page',
  imports: [ChannelFiltersComponent, ChannelListComponent, ChannelPlayerComponent],
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
  protected readonly filters = signal<ChannelFilters>({
    searchTerm: '',
    playlistId: 'all',
    favoritesOnly: false,
    showNonWorking: false,
  });
  protected readonly favoriteIds = this.favoriteChannels.favoriteIds;

  /** True while the player overlay is open. */
  protected readonly playerOpen = computed(() => this.selectedChannel() !== null);

  protected readonly filteredChannels = computed(() => {
    const filters = this.filters();
    const searchTerm = filters.searchTerm.trim().toLowerCase();

    return this.channels().filter((channel) => {
      // Working status filter
      if (!channel.working && !filters.showNonWorking) {
        return false;
      }

      const matchesText =
        searchTerm.length === 0 ||
        channel.name.toLowerCase().includes(searchTerm) ||
        channel.sourcePlaylistName.toLowerCase().includes(searchTerm);
      const matchesPlaylist =
        filters.playlistId === 'all' || channel.sourcePlaylistId === filters.playlistId;
      const matchesFavorite = !filters.favoritesOnly || this.favoriteChannels.isFavorite(channel.id);

      return matchesText && matchesPlaylist && matchesFavorite;
    });
  });

  protected readonly stats = computed(() => ({
    totalChannels: this.channels().length,
    totalPlaylists: this.playlists().length,
    visibleChannels: this.filteredChannels().length,
    favoriteChannels: this.favoriteIds().length,
  }));

  constructor() {
    this.loadChannels();
  }

  protected loadChannels(): void {
    this.isLoading.set(true);
    this.error.set(null);

    this.channelsLoader
      .loadFromIndex()
      .pipe(take(1))
      .subscribe({
        next: ({ channels }) => {
          this.channels.set(channels);
          this.playlists.set(this.extractPlaylists(channels));
          this.isLoading.set(false);
        },
        error: () => {
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

  protected toggleFavorite(channel: Channel): void {
    this.favoriteChannels.toggleFavorite(channel.id);
  }

  private extractPlaylists(channels: Channel[]): PlaylistFile[] {
    const seen = new Map<string, PlaylistFile>();
    for (const ch of channels) {
      const key = ch.sourcePlaylistId;
      if (!seen.has(key)) {
        seen.set(key, {
          id: key,
          name: ch.sourcePlaylistName,
          fileName: '',
          url: '',
          sizeBytes: 0,
          updatedAt: '',
        });
      }
    }
    return [...seen.values()].sort((a, b) => a.name.localeCompare(b.name));
  }
}
