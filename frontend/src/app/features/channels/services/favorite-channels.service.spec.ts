import { TestBed } from '@angular/core/testing';

import { FavoriteChannelsService } from './favorite-channels.service';

describe('FavoriteChannelsService', () => {
  beforeEach(() => {
    window.localStorage.clear();
    TestBed.configureTestingModule({});
  });

  it('toggles favorite channel ids and persists them', () => {
    const service = TestBed.inject(FavoriteChannelsService);

    service.toggleFavorite('playlist-one::cazetv');

    expect(service.isFavorite('playlist-one::cazetv')).toBe(true);
    expect(service.favoriteIds()).toEqual(['playlist-one::cazetv']);
    expect(JSON.parse(window.localStorage.getItem('futebol.favoriteChannelIds') ?? '[]')).toEqual([
      'playlist-one::cazetv',
    ]);

    service.toggleFavorite('playlist-one::cazetv');

    expect(service.isFavorite('playlist-one::cazetv')).toBe(false);
    expect(service.favoriteIds()).toEqual([]);
  });

  it('loads previously saved favorites', () => {
    window.localStorage.setItem(
      'futebol.favoriteChannelIds',
      JSON.stringify(['playlist-one::cazetv', 'playlist-two::sportv']),
    );

    const service = TestBed.inject(FavoriteChannelsService);

    expect(service.favoriteIds()).toEqual(['playlist-one::cazetv', 'playlist-two::sportv']);
    expect(service.isFavorite('playlist-two::sportv')).toBe(true);
  });
});
