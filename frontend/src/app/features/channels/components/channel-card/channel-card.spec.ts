import { ComponentFixture, TestBed } from '@angular/core/testing';

import { Channel } from '../../models/channel.interface';
import { ChannelCardComponent } from './channel-card';

const CHANNEL: Channel = {
  id: 'playlist-one::cazetv',
  name: 'CazéTV Futebol',
  streamUrl: 'https://example.org/live.m3u8',
  groupTitle: 'Esporte',
  logoUrl: null,
  tvgId: null,
  sourcePlaylistId: 'playlist-one',
  sourcePlaylistName: 'sports.m3u',
  working: true,
};

describe('ChannelCardComponent', () => {
  let fixture: ComponentFixture<ChannelCardComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ChannelCardComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(ChannelCardComponent);
    fixture.componentRef.setInput('channel', CHANNEL);
  });

  it('shows a heart favorite button and emits favorite toggles without selecting the card', () => {
    const component = fixture.componentInstance;
    const selectedSpy = vi.fn();
    const favoriteSpy = vi.fn();
    component.channelSelected.subscribe(selectedSpy);
    component.favoriteToggled.subscribe(favoriteSpy);
    fixture.componentRef.setInput('isFavorite', false);
    fixture.detectChanges();

    const favoriteButton = (fixture.nativeElement as HTMLElement).querySelector(
      '.favorite-button',
    ) as HTMLButtonElement | null;
    favoriteButton?.click();

    expect(favoriteButton?.getAttribute('aria-label')).toBe('Add CazéTV Futebol to favorites');
    expect(favoriteSpy).toHaveBeenCalledWith(CHANNEL);
    expect(selectedSpy).not.toHaveBeenCalled();
  });
});
