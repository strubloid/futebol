export interface Channel {
  id: string;
  name: string;
  streamUrl: string;
  groupTitle: string;
  logoUrl: string | null;
  tvgId: string | null;
  sourcePlaylistId: string;
  sourcePlaylistName: string;
  /** Whether the channel is marked as working (visible in UI). Default true. */
  working: boolean;

  // === Organization fields ===
  /** Language code: 'pt' (Portuguese), 'en' (English), 'es' (Spanish), etc. */
  language: string | null;
  /** Country code: 'BR' (Brazil), 'PT' (Portugal), 'US' (United States), etc. */
  country: string | null;
  /** Brazilian state: 'SP', 'RJ', 'MG', 'RS', 'BA', etc. (for BR channels only). */
  state: string | null;
  /** True = free-to-air / open channel, False = premium / subscription. */
  isFree: boolean;
  /** 'sports', 'news', 'entertainment', 'movies', 'religious', 'general', etc. */
  channelType: string | null;
}

export interface ChannelStats {
  totalChannels: number;
  totalPlaylists: number;
  visibleChannels: number;
  favoriteChannels: number;
  groups: string[];
}

/** Schema for a channel entry from the channels/index.json file */
export interface ChannelIndexEntry {
  tvgId: string;
  name: string;
  streamUrl: string;
  groupTitle: string;
  logoUrl: string | null;
  sourcePlaylist: string;
  sourcePlaylistId: string;
  working: boolean;
  tags: string[];
  language: string | null;
  country: string | null;
  state: string | null;
  isFree: boolean;
  channelType: string | null;
}

/** Schema for the aggregate channels/index.json file */
export interface ChannelIndexFile {
  generatedAt: string;
  channels: ChannelIndexEntry[];
}

/** Schema for channels/manifest.json */
export interface ChannelManifest {
  generatedAt: string;
  totalChannels: number;
  workingChannels: number;
  playlists: { id: string; name: string }[];
}
