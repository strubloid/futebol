import { Component, input, output } from '@angular/core';
import { FormsModule } from '@angular/forms';

import { ChannelFilters } from '../../models/channel-filters.interface';
import { PlaylistFile } from '../../models/playlist-file.interface';

@Component({
  selector: 'app-channel-filters',
  imports: [FormsModule],
  templateUrl: './channel-filters.html',
  styleUrl: './channel-filters.scss',
})
export class ChannelFiltersComponent {
  readonly filters = input.required<ChannelFilters>();
  readonly groups = input.required<string[]>();
  readonly playlists = input.required<PlaylistFile[]>();
  readonly filtersChange = output<ChannelFilters>();

  protected updateSearchTerm(searchTerm: string): void {
    this.filtersChange.emit({ ...this.filters(), searchTerm });
  }

  protected updateGroup(groupTitle: string): void {
    this.filtersChange.emit({ ...this.filters(), groupTitle });
  }

  protected updatePlaylist(playlistId: string): void {
    this.filtersChange.emit({ ...this.filters(), playlistId });
  }
}
