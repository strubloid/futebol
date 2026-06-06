export interface PlaylistFile {
  id: string;
  name: string;
  fileName: string;
  url: string;
  sizeBytes: number;
  updatedAt: string;
}

export interface PlaylistManifest {
  generatedAt: string;
  playlists: PlaylistFile[];
}
