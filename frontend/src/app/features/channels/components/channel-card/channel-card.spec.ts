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

  it('emits channelSelected when the card button is clicked', () => {
    const component = fixture.componentInstance;
    const selectedSpy = vi.fn();
    component.channelSelected.subscribe(selectedSpy);
    fixture.detectChanges();

    const card = (fixture.nativeElement as HTMLElement).querySelector(
      '.channel-card',
    ) as HTMLButtonElement | null;
    card?.click();

    expect(selectedSpy).toHaveBeenCalledWith(CHANNEL);
  });

  it('emits favoriteToggled without triggering channelSelected', () => {
    const component = fixture.componentInstance;
    const selectedSpy = vi.fn();
    const favoriteSpy = vi.fn();
    component.channelSelected.subscribe(selectedSpy);
    component.favoriteToggled.subscribe(favoriteSpy);
    fixture.componentRef.setInput('isFavorite', false);
    fixture.detectChanges();

    const faveBtn = (fixture.nativeElement as HTMLElement).querySelector(
      '.fave-btn',
    ) as HTMLButtonElement | null;
    faveBtn?.click();

    expect(favoriteSpy).toHaveBeenCalledWith(CHANNEL);
    expect(selectedSpy).not.toHaveBeenCalled();
  });
});
