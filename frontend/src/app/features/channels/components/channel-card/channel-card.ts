import { Component, input, output } from '@angular/core';

import { Channel } from '../../models/channel.interface';

@Component({
  selector: 'app-channel-card',
  templateUrl: './channel-card.html',
  styleUrl: './channel-card.scss',
})
export class ChannelCardComponent {
  readonly channel = input.required<Channel>();
  readonly isFavorite = input(false);
  readonly channelSelected = output<Channel>();
  readonly favoriteToggled = output<Channel>();
}
