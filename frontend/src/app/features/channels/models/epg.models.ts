/**
 * EPG / TV Guide data structures and helpers.
 * Data sourced from iptv-org guide API (public, no API key needed).
 */

/** A single TV programme entry. */
export interface EpgProgramme {
  /** Channel xmltv_id this programme belongs to, e.g. "RedeGlobo.br" */
  channel: string;
  /** Programme title, e.g. "Jornal Nacional" */
  title: string;
  /** ISO date string: start time, e.g. "2026-06-08T19:00:00Z" */
  start: string;
  /** ISO date string: end time */
  stop: string;
  /** Short description (may be empty) */
  description?: string;
  /** Category like "sports", "news", "movie" (from guide categories) */
  category?: string;
  /** Whether this programme is currently airing (computed client-side) */
  isLive?: boolean;
}

/** A guide entry for one channel (one day's programmes). */
export interface EpgChannelGuide {
  /** Channel xmltv_id, e.g. "RedeGlobo.br" */
  channelId: string;
  /** Channel display name */
  name: string;
  /** URL to channel logo (from iptv-org channels API) */
  logoUrl: string | null;
  /** Today's programmes */
  programmes: EpgProgramme[];
  /** The programme currently airing (first where isLive=true) */
  nowPlaying: EpgProgramme | null;
}

/** Raw channel entry from iptv-org channels.json */
export interface IptvOrgChannel {
  id: string;
  name: string;
  alt_names: string[];
  country: string;
  categories: string[];
  website: string | null;
}

/** Raw guide entry from iptv-org guides.json */
export interface IptvOrgGuide {
  channel: string | null;
  feed: string | null;
  site: string;
  site_id: string;
  site_name: string;
  lang: string;
  sources: {
    host: string;
    url: string;
    format: string;
  }[];
}

/** Cached guide manifest stored at /channels/guide-manifest.json */
export interface GuideManifest {
  generatedAt: string;
  /** List of channel ids that have guide data available */
  channelsWithGuide: string[];
}