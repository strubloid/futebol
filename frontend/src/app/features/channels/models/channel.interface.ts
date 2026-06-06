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
