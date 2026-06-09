export interface ChannelFilters {
  searchTerm: string;
  playlistId: string;
  favoritesOnly: boolean;
  showNonWorking: boolean;

  // === Organization filters ===
  /** Filter by language code: 'all', 'pt', 'en', 'es', etc. */
  language: string;
  /** Filter by country code: 'all', 'BR', 'PT', 'US', etc. */
  country: string;
  /** Filter by Brazilian state: 'all', 'SP', 'RJ', 'MG', 'RS', etc. */
  state: string;
  /** Filter by access type: 'all', 'free', 'premium' */
  accessType: string;
  /** Filter by channel type: 'all', 'sports', 'news', 'entertainment', etc. */
  channelType: string;
}
