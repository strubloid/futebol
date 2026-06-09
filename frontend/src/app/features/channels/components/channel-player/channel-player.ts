import {
  AfterViewInit,
  Component,
  ElementRef,
  OnDestroy,
  ViewChild,
  computed,
  effect,
  inject,
  input,
  output,
  signal,
} from '@angular/core';
import { DatePipe } from '@angular/common';
import type Hls from 'hls.js';

import { Channel } from '../../models/channel.interface';
import { EpgChannelGuide, EpgProgramme } from '../../models/epg.models';
import { EpgService } from '../../services/epg.service';

@Component({
  selector: 'app-channel-player',
  templateUrl: './channel-player.html',
  styleUrl: './channel-player.scss',
  imports: [DatePipe],
})
export class ChannelPlayerComponent implements AfterViewInit, OnDestroy {
  readonly channel = input<Channel | null>(null);
  readonly close = output<void>();

  @ViewChild('videoElement') private videoElement?: ElementRef<HTMLVideoElement>;

  protected isFullscreen = false;
  protected readonly ready = signal(false);
  /** Whether the EPG programme panel is open. */
  protected readonly guideOpen = signal(false);
  /** Current wall-clock time, refreshed every 30 s. */
  protected readonly currentTime = signal<Date>(new Date());

  /** Guide data for the currently playing channel. */
  private readonly channelGuide = signal<EpgChannelGuide | null>(null);

  /** Programme that is airing right now. */
  protected readonly nowPlaying = computed<EpgProgramme | null>(() => {
    const guide = this.channelGuide();
    const now = this.currentTime();
    if (!guide) return null;
    return (
      guide.programmes.find((p) => {
        const start = new Date(p.start);
        const stop = new Date(p.stop);
        return start <= now && stop > now;
      }) ?? null
    );
  });

  /** Upcoming programmes (after the currently playing one). */
  protected readonly upcoming = computed<EpgProgramme[]>(() => {
    const guide = this.channelGuide();
    const now = this.currentTime();
    if (!guide) return [];
    return guide.programmes.filter((p) => new Date(p.start) > now).slice(0, 6);
  });

  /** Current wall-clock time formatted as HH:MM. */
  protected readonly timeString = computed(() => {
    const d = this.currentTime();
    return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
  });

  private readonly epg = inject(EpgService);
  private hls: Hls | null = null;
  private viewReady = false;
  private clockTimer: ReturnType<typeof setInterval> | null = null;

  constructor() {
    effect(() => {
      const channel = this.channel();
      if (this.viewReady && channel) {
        this.loadChannel(channel);
        this.loadGuide(channel);
      }
    });
  }

  ngAfterViewInit(): void {
    this.viewReady = true;
    this.startClock();
    const channel = this.channel();
    if (channel) {
      this.loadChannel(channel);
      this.loadGuide(channel);
    }
  }

  ngOnDestroy(): void {
    this.destroyHls();
    this.stopClock();
  }

  protected toggleGuide(): void {
    this.guideOpen.update((v) => !v);
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
    this.stopClock();
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
    this.guideOpen.set(false);
    this.close.emit();
  }

  /** Compute programme duration in minutes. */
  protected progDuration(p: EpgProgramme): number {
    const start = new Date(p.start).getTime();
    const stop = new Date(p.stop).getTime();
    return Math.round((stop - start) / 60000);
  }

  /** Compute progress of the current programme as a percentage. */
  protected progProgress(p: EpgProgramme): number {
    const now = this.currentTime().getTime();
    const start = new Date(p.start).getTime();
    const stop = new Date(p.stop).getTime();
    if (stop <= start) return 0;
    return Math.min(100, Math.max(0, ((now - start) / (stop - start)) * 100));
  }

  // ─── Private ──────────────────────────────────────────────────────────

  private startClock(): void {
    this.clockTimer = setInterval(() => this.currentTime.set(new Date()), 30_000);
  }

  private stopClock(): void {
    if (this.clockTimer) {
      clearInterval(this.clockTimer);
      this.clockTimer = null;
    }
  }

  private loadGuide(channel: Channel): void {
    this.channelGuide.set(null);
    const xmltvId = this.epg.stripFeed(channel.tvgId);
    if (!xmltvId) return;

    this.epg.loadGuideForChannelId(xmltvId, channel.name).subscribe((guide) => {
      this.channelGuide.set(guide);
    });
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
      this.ready.set(true);
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

  private tryPlay(video: HTMLVideoElement): void {
    video
      .play()
      .then(() => {
        this.unmuteAfterInteraction(video);
      })
      .catch(() => {});
  }

  private async attachHls(video: HTMLVideoElement, streamUrl: string): Promise<boolean> {
    const hlsModule = await import('hls.js');
    const HlsConstructor = hlsModule.default;

    if (!HlsConstructor.isSupported()) return false;

    this.hls = new HlsConstructor({
      lowLatencyMode: false,
      liveDurationInfinity: true,
      maxBufferLength: 60,
      maxMaxBufferLength: 120,
      maxBufferSize: 120 * 1000 * 1000,
      backBufferLength: 15,
      maxBufferHole: 3,
      maxStarvationDelay: 10,
      maxLoadingDelay: 8,
      startFragPrefetch: true,
      testBandwidth: true,
      xhrSetup: (xhr) => {
        xhr.setRequestHeader(
          'User-Agent',
          'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36',
        );
      },
    });
    this.hls.loadSource(streamUrl);
    this.hls.attachMedia(video);

    this.hls.on(HlsConstructor.Events.MANIFEST_PARSED, () => {
      this.ready.set(true);
      this.tryPlay(video);
    });

    this.hls.on(HlsConstructor.Events.ERROR, (_event, data) => {
      if (data.fatal) {
        this.ready.set(true);
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
