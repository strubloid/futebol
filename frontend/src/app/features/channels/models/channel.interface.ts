export interface Channel {
  id: string;
  name: string;
  streamUrl: string;
  groupTitle: string;
  logoUrl: string | null;
  tvgId: string | null;
  sourcePlaylistId: string;
  sourcePlaylistName: string;
}

export interface ChannelStats {
  totalChannels: number;
  totalPlaylists: number;
  visibleChannels: number;
  groups: string[];
}
