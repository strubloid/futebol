import { AfterViewInit, Component, ElementRef, OnDestroy, ViewChild, effect, input } from '@angular/core';
import type Hls from 'hls.js';

import { Channel } from '../../models/channel.interface';

@Component({
  selector: 'app-channel-player',
  templateUrl: './channel-player.html',
  styleUrl: './channel-player.scss',
})
export class ChannelPlayerComponent implements AfterViewInit, OnDestroy {
  readonly channel = input<Channel | null>(null);

  @ViewChild('videoElement') private videoElement?: ElementRef<HTMLVideoElement>;

  protected playbackMessage = 'Pick a channel to start previewing the stream.';
  private hls: Hls | null = null;
  private viewReady = false;

  constructor() {
    effect(() => {
      const channel = this.channel();
      if (this.viewReady) {
        this.loadChannel(channel);
      }
    });
  }

  ngAfterViewInit(): void {
    this.viewReady = true;
    this.loadChannel(this.channel());
  }

  ngOnDestroy(): void {
    this.destroyHls();
  }

  private async loadChannel(channel: Channel | null): Promise<void> {
    const video = this.videoElement?.nativeElement;
    if (!video) {
      return;
    }

    this.destroyHls();
    video.pause();
    video.removeAttribute('src');
    video.load();

    if (!channel) {
      this.playbackMessage = 'Pick a channel to start previewing the stream.';
      return;
    }

    this.playbackMessage = 'Loading preview...';

    if (video.canPlayType('application/vnd.apple.mpegurl')) {
      video.src = channel.streamUrl;
      this.playbackMessage = 'Native HLS preview ready. Press play.';
      return;
    }

    if (await this.attachHls(video, channel.streamUrl)) {
      return;
    }

    this.playbackMessage = 'This browser does not support HLS preview. Open the stream URL directly.';
  }

  private async attachHls(video: HTMLVideoElement, streamUrl: string): Promise<boolean> {
    const hlsModule = await import('hls.js');
    const HlsConstructor = hlsModule.default;

    if (!HlsConstructor.isSupported()) {
      return false;
    }

    this.hls = new HlsConstructor({ lowLatencyMode: true });
    this.hls.loadSource(streamUrl);
    this.hls.attachMedia(video);
    this.hls.on(HlsConstructor.Events.MANIFEST_PARSED, () => {
      this.playbackMessage = 'Preview ready. Press play.';
    });
    this.hls.on(HlsConstructor.Events.ERROR, (_event, data) => {
      if (data.fatal) {
        this.playbackMessage = 'The browser could not play this stream. Try opening the stream URL directly.';
      }
    });

    return true;
  }

  private destroyHls(): void {
    this.hls?.destroy();
    this.hls = null;
  }
}
