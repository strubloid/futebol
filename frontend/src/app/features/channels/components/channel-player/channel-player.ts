import {
  AfterViewInit,
  Component,
  ElementRef,
  OnDestroy,
  ViewChild,
  effect,
  input,
  output,
  signal,
} from '@angular/core';
import type Hls from 'hls.js';

import { Channel } from '../../models/channel.interface';

@Component({
  selector: 'app-channel-player',
  templateUrl: './channel-player.html',
  styleUrl: './channel-player.scss',
})
export class ChannelPlayerComponent implements AfterViewInit, OnDestroy {
  readonly channel = input<Channel | null>(null);
  readonly close = output<void>();

  @ViewChild('videoElement') private videoElement?: ElementRef<HTMLVideoElement>;

  protected isFullscreen = false;
  protected readonly ready = signal(false);
  private hls: Hls | null = null;
  private viewReady = false;

  constructor() {
    effect(() => {
      const channel = this.channel();
      if (this.viewReady && channel) {
        this.loadChannel(channel);
      }
    });
  }

  ngAfterViewInit(): void {
    this.viewReady = true;
    const channel = this.channel();
    if (channel) {
      this.loadChannel(channel);
    }
  }

  ngOnDestroy(): void {
    this.destroyHls();
  }

  protected toggleFullscreen(): void {
    if (!this.isFullscreen) {
      document.documentElement.requestFullscreen().catch(() => {});
    } else {
      document.exitFullscreen().catch(() => {});
    }
    this.isFullscreen = !this.isFullscreen;
  }

  protected closePlayer(): void {
    this.destroyHls();
    const video = this.videoElement?.nativeElement;
    if (video) {
      video.pause();
      video.removeAttribute('src');
      video.load();
    }
    if (document.fullscreenElement) {
      document.exitFullscreen().catch(() => {});
    }
    this.isFullscreen = false;
    this.ready.set(false);
    this.close.emit();
  }

  private async loadChannel(channel: Channel): Promise<void> {
    const video = this.videoElement?.nativeElement;
    if (!video) return;

    this.destroyHls();
    video.pause();
    video.removeAttribute('src');
    video.load();
    this.ready.set(false);

    video.muted = true;
    video.playsInline = true;

    // Native HLS (Safari)
    if (video.canPlayType('application/vnd.apple.mpegurl')) {
      video.src = channel.streamUrl;
      this.ready.set(true); // show player — source is loaded regardless of play()
      this.tryPlay(video);
      return;
    }

    // hls.js for others
    if (await this.attachHls(video, channel.streamUrl)) {
      return;
    }

    // Fallback: load as regular mp4/ts
    video.src = channel.streamUrl;
    this.ready.set(true);
    this.tryPlay(video);
  }

  /**
   * Try to autoplay the video.  Browsers may block this (autoplay policy)
   * or the stream may not be playable in a plain <video> tag.  That's OK —
   * the player is already visible, and a user click anywhere on the page
   * will unmute + resume the stream.
   */
  private tryPlay(video: HTMLVideoElement): void {
    video.play().then(() => {
      this.unmuteAfterInteraction(video);
    }).catch(() => {
      // Autoplay blocked or stream not playable in <video> tag.
      // Player is already visible (ready=true) — user click will unblock.
    });
  }

  private async attachHls(video: HTMLVideoElement, streamUrl: string): Promise<boolean> {
    const hlsModule = await import('hls.js');
    const HlsConstructor = hlsModule.default;

    if (!HlsConstructor.isSupported()) return false;

    this.hls = new HlsConstructor({ lowLatencyMode: true });
    this.hls.loadSource(streamUrl);
    this.hls.attachMedia(video);

    this.hls.on(HlsConstructor.Events.MANIFEST_PARSED, () => {
      // Source is loaded and the hls segment pipeline is ready
      this.ready.set(true);
      this.tryPlay(video);
    });

    this.hls.on(HlsConstructor.Events.ERROR, (_event, data) => {
      if (data.fatal) {
        // hls.js failed — try native fallback
        this.ready.set(true); // show player before fallback attempt
        video.src = streamUrl;
        this.tryPlay(video);
      }
    });

    return true;
  }

  private unmuteAfterInteraction(video: HTMLVideoElement): void {
    const handler = () => {
      video.muted = false;
      document.removeEventListener('click', handler);
      document.removeEventListener('keydown', handler);
    };
    document.addEventListener('click', handler, { once: true });
    document.addEventListener('keydown', handler, { once: true });
  }

  private destroyHls(): void {
    this.hls?.destroy();
    this.hls = null;
  }
}
