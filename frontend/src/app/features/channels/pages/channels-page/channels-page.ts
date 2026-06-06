import { Component, computed, inject, signal } from '@angular/core';
import { take } from 'rxjs';

import { Channel } from '../../models/channel.interface';
import { ChannelFilters } from '../../models/channel-filters.interface';
import { PlaylistFile } from '../../models/playlist-file.interface';
import { PlaylistLoaderService } from '../../services/playlist-loader.service';
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
  private readonly playlistLoader = inject(PlaylistLoaderService);

  protected readonly channels = signal<Channel[]>([]);
  protected readonly playlists = signal<PlaylistFile[]>([]);
  protected readonly selectedChannel = signal<Channel | null>(null);
  protected readonly isLoading = signal(true);
  protected readonly error = signal<string | null>(null);
  protected readonly filters = signal<ChannelFilters>({
    searchTerm: '',
    groupTitle: 'all',
    playlistId: 'all',
  });

  protected readonly groups = computed(() =>
    [...new Set(this.channels().map((channel) => channel.groupTitle))].sort((left, right) =>
      left.localeCompare(right),
    ),
  );

  protected readonly filteredChannels = computed(() => {
    const filters = this.filters();
    const searchTerm = filters.searchTerm.trim().toLowerCase();

    return this.channels().filter((channel) => {
      const matchesText =
        searchTerm.length === 0 ||
        channel.name.toLowerCase().includes(searchTerm) ||
        channel.groupTitle.toLowerCase().includes(searchTerm) ||
        channel.sourcePlaylistName.toLowerCase().includes(searchTerm);
      const matchesGroup = filters.groupTitle === 'all' || channel.groupTitle === filters.groupTitle;
      const matchesPlaylist =
        filters.playlistId === 'all' || channel.sourcePlaylistId === filters.playlistId;

      return matchesText && matchesGroup && matchesPlaylist;
    });
  });

  protected readonly stats = computed(() => ({
    totalChannels: this.channels().length,
    totalPlaylists: this.playlists().length,
    visibleChannels: this.filteredChannels().length,
    groups: this.groups(),
  }));

  constructor() {
    this.loadChannels();
  }

  protected loadChannels(): void {
    this.isLoading.set(true);
    this.error.set(null);

    this.playlistLoader
      .loadChannels()
      .pipe(take(1))
      .subscribe({
        next: ({ playlists, channels }) => {
          this.playlists.set(playlists);
          this.channels.set(channels);
          this.selectedChannel.set(channels[0] ?? null);
          this.isLoading.set(false);
        },
        error: () => {
          this.error.set('Could not load M3U files. Run npm run sync:m3u inside frontend/ and try again.');
          this.isLoading.set(false);
        },
      });
  }

  protected updateFilters(filters: ChannelFilters): void {
    this.filters.set(filters);
    const visibleChannels = this.filteredChannels();
    const selected = this.selectedChannel();

    if (visibleChannels.length > 0 && !visibleChannels.some((channel) => channel.id === selected?.id)) {
      this.selectedChannel.set(visibleChannels[0]);
    }
  }

  protected selectChannel(channel: Channel): void {
    this.selectedChannel.set(channel);
  }
}
