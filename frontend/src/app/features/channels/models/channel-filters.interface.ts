export interface ChannelFilters {
  searchTerm: string;
  groupTitle: string;
  playlistId: string;
  favoritesOnly: boolean;
  /** When true, also shows channels marked as not working */
  showNonWorking: boolean;
}
