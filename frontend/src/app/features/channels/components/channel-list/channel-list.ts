import { Component, input, output } from '@angular/core';

import { Channel } from '../../models/channel.interface';
import { ChannelCardComponent } from '../channel-card/channel-card';

@Component({
  selector: 'app-channel-list',
  imports: [ChannelCardComponent],
  templateUrl: './channel-list.html',
  styleUrl: './channel-list.scss',
})
export class ChannelListComponent {
  readonly channels = input.required<Channel[]>();
  readonly favoriteIds = input<string[]>([]);
  readonly channelSelected = output<Channel>();
  readonly favoriteToggled = output<Channel>();

  isFavorite(channel: Channel): boolean {
    return this.favoriteIds().includes(channel.id);
  }
}
