import { Routes } from '@angular/router';

import { ChannelsPage } from './features/channels/pages/channels-page/channels-page';
import { GuidePage } from './features/channels/pages/guide-page/guide-page';

export const routes: Routes = [
  {
    path: '',
    component: ChannelsPage,
    title: 'Futebol IPTV Channels',
  },
  {
    path: 'guide',
    component: GuidePage,
    title: 'TV Guide — Futebol',
  },
];
