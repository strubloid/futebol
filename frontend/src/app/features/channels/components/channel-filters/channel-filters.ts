import { Component, input, output, computed } from '@angular/core';
import { FormsModule } from '@angular/forms';

import { ChannelFilters } from '../../models/channel-filters.interface';
import { Channel } from '../../models/channel.interface';

@Component({
  selector: 'app-channel-filters',
  imports: [FormsModule],
  templateUrl: './channel-filters.html',
  styleUrl: './channel-filters.scss',
})
export class ChannelFiltersComponent {
  readonly filters = input.required<ChannelFilters>();
  readonly allChannels = input<Channel[]>([]);
  /** Deduplicated playlist list for the dropdown. */
  readonly playlists = input<{ id: string; name: string }[]>([]);
  readonly filtersChange = output<ChannelFilters>();

  /** Derive available filter options from the full channel set. */
  readonly options = computed(() => {
    const channels = this.allChannels();

    const languages = new Set<string>();
    const countries = new Set<string>();
    const states = new Set<string>();
    const channelTypes = new Set<string>();
    let hasFree = false;
    let hasPremium = false;

    for (const ch of channels) {
      if (ch.language) languages.add(ch.language);
      if (ch.country) countries.add(ch.country);
      if (ch.state) states.add(ch.state);
      if (ch.channelType) channelTypes.add(ch.channelType);
      if (ch.isFree) hasFree = true;
      else hasPremium = true;
    }

    return {
      languages: [...languages].sort(),
      countries: [...countries].sort(),
      states: [...states].sort(),
      channelTypes: [...channelTypes].sort(),
      hasFree,
      hasPremium,
    };
  });

  protected readonly LANGUAGE_LABELS: Record<string, string> = {
    pt: 'Português',
    en: 'English',
    es: 'Español',
    fr: 'Français',
    de: 'Deutsch',
    it: 'Italiano',
    ru: 'Русский',
    ar: 'العربية',
    zh: '中文',
    ja: '日本語',
    ko: '한국어',
    nl: 'Nederlands',
    pl: 'Polski',
    cs: 'Čeština',
    ro: 'Română',
    el: 'Ελληνικά',
    tr: 'Türkçe',
    no: 'Norsk',
    fi: 'Suomi',
    da: 'Dansk',
    sv: 'Svenska',
    hi: 'हिन्दी',
    th: 'ไทย',
    vi: 'Tiếng Việt',
    id: 'Bahasa Indonesia',
    ms: 'Bahasa Melayu',
    fil: 'Filipino',
    ur: 'اردو',
    bn: 'বাংলা',
    si: 'සිංහල',
    he: 'עברית',
    hr: 'Hrvatski',
    hu: 'Magyar',
    bg: 'Български',
    sk: 'Slovenčina',
    lt: 'Lietuvių',
    lv: 'Latviešu',
    et: 'Eesti',
    ka: 'ქართული',
    az: 'Azərbaycan',
    hy: 'Հայերեն',
    is: 'Íslenska',
  };

  protected readonly COUNTRY_NAMES: Record<string, string> = {
    BR: 'Brasil', PT: 'Portugal', US: 'Estados Unidos',
    GB: 'Reino Unido', FR: 'França', DE: 'Alemanha',
    ES: 'Espanha', IT: 'Itália', AR: 'Argentina',
    MX: 'México', CO: 'Colômbia', CL: 'Chile',
    PE: 'Peru', UY: 'Uruguai', QA: 'Qatar',
    TR: 'Turquia', GR: 'Grécia', RU: 'Rússia',
    CN: 'China', JP: 'Japão', KR: 'Coreia do Sul',
    IN: 'Índia', AU: 'Austrália', CA: 'Canadá',
    MA: 'Marrocos', ZA: 'África do Sul',
  };

  protected readonly TYPE_LABELS: Record<string, string> = {
    sports: 'Esportes',
    news: 'Notícias',
    entertainment: 'Entretenimento',
    religious: 'Religioso',
    kids: 'Infantil',
    education: 'Educativo',
    music: 'Música',
    movies: 'Filmes',
    general: 'Geral',
    travel: 'Viajem',
    comedy: 'Comédia',
    culture: 'Cultura',
  };

  protected readonly STATE_NAMES: Record<string, string> = {
    AC: 'Acre', AL: 'Alagoas', AP: 'Amapá', AM: 'Amazonas',
    BA: 'Bahia', CE: 'Ceará', DF: 'Distrito Federal',
    ES: 'Espírito Santo', GO: 'Goiás', MA: 'Maranhão',
    MT: 'Mato Grosso', MS: 'Mato Grosso do Sul',
    MG: 'Minas Gerais', PA: 'Pará', PB: 'Paraíba',
    PR: 'Paraná', PE: 'Pernambuco', PI: 'Piauí',
    RJ: 'Rio de Janeiro', RN: 'Rio Grande do Norte',
    RS: 'Rio Grande do Sul', RO: 'Rondônia', RR: 'Roraima',
    SC: 'Santa Catarina', SP: 'São Paulo', SE: 'Sergipe',
    TO: 'Tocantins',
  };

  protected updateField<K extends keyof ChannelFilters>(
    field: K,
    value: ChannelFilters[K],
  ): void {
    this.filtersChange.emit({ ...this.filters(), [field]: value });
  }
}
