import { Injectable, signal } from '@angular/core';

const FAVORITES_STORAGE_KEY = 'futebol.favoriteChannelIds';

@Injectable({ providedIn: 'root' })
export class FavoriteChannelsService {
  private readonly ids = signal<string[]>(this.loadFavoriteIds());

  readonly favoriteIds = this.ids.asReadonly();

  isFavorite(channelId: string): boolean {
    return this.ids().includes(channelId);
  }

  toggleFavorite(channelId: string): void {
    const current = this.ids();
    const next = current.includes(channelId)
      ? current.filter((id) => id !== channelId)
      : [...current, channelId];

    this.ids.set(next);
    this.saveFavoriteIds(next);
  }

  private loadFavoriteIds(): string[] {
    try {
      const raw = window.localStorage.getItem(FAVORITES_STORAGE_KEY);
      const parsed: unknown = raw ? JSON.parse(raw) : [];
      return Array.isArray(parsed) ? parsed.filter((id): id is string => typeof id === 'string') : [];
    } catch {
      return [];
    }
  }

  private saveFavoriteIds(ids: string[]): void {
    window.localStorage.setItem(FAVORITES_STORAGE_KEY, JSON.stringify(ids));
  }
}
