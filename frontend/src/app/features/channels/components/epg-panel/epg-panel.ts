import { Component, input, output, signal } from '@angular/core';
import { DatePipe } from '@angular/common';

export interface EpgProgram {
  time: string;       // e.g. "06:00"
  title: string;
  description?: string;
  category?: string;  // 'sports', 'news', 'movie', etc.
}

export interface EpgData {
  channelName: string;
  channelLogo?: string;
  date: string;       // ISO date
  programs: EpgProgram[];
}

/**
 * A curated EPG dataset for popular Brazilian sports channels.
 * In production this would come from an XMLTV feed.
 */
const MOCK_EPG: Record<string, EpgProgram[]> = {
  'SporTV': [
    { time: '06:00', title: 'SportsCenter', category: 'news', description: 'Notícias do esporte nacional e internacional ao vivo' },
    { time: '07:00', title: 'Abre o Jogo', category: 'talk', description: 'Mesa-redonda sobre os principais temas do esporte brasileiro' },
    { time: '08:00', title: 'SporTV News', category: 'news', description: 'Noticiário esportivo com highlights dos jogos' },
    { time: '09:00', title: 'Corrida de Rua: SP Half Marathon', category: 'sports', description: 'Cobertura ao vivo da meia maratona internacional' },
    { time: '11:00', title: 'Além do Lance', category: 'talk', description: 'Entrevistas especiais com personalidades do esporte' },
    { time: '12:00', title: 'SporTV News', category: 'news', description: 'Edição do meio-dia com as principais notícias' },
    { time: '13:00', title: 'Futebol ao Vivo: Pré-jogo', category: 'sports', description: 'Aquecimento e análise tática antes da partida' },
    { time: '14:00', title: 'Campeonato Brasileiro Série A: Flamengo x Palmeiras', category: 'sports', description: 'AO VIVO: Jogo válido pela 12ª rodada do Brasileirão' },
    { time: '16:30', title: 'Intervalo — Gols da Rodada', category: 'sports', description: 'Melhores momentos dos jogos do dia' },
    { time: '17:00', title: 'Seleção SporTV', category: 'talk', description: 'Debate sobre os melhores momentos da rodada' },
    { time: '18:00', title: 'Jogo Aberto', category: 'talk', description: 'Programa de debate esportivo' },
    { time: '19:00', title: 'SporTV News — Edição Noturna', category: 'news', description: 'Notícias da noite no mundo esportivo' },
    { time: '20:00', title: 'Futebol Internacional: Champions League', category: 'sports', description: 'AO VIVO: Partida da Liga dos Campeões' },
    { time: '22:30', title: 'Resumo da Rodada', category: 'sports', description: 'Compacto com todos os gols do dia' },
    { time: '23:30', title: 'SportsCenter — Edição da Madrugada', category: 'news', description: 'Últimas notícias e encerramento' },
  ],
  'SporTV 2': [
    { time: '06:30', title: 'SporTV News', category: 'news', description: 'Primeira edição do noticiário esportivo' },
    { time: '08:00', title: 'Vôlei: Superliga Feminina', category: 'sports', description: 'AO VIVO: Sesi Vôlei Bauru x Osasco' },
    { time: '10:00', title: 'Tênis: ATP 500', category: 'sports', description: 'AO VIVO: Quartas de final com tenistas do top 20' },
    { time: '12:00', title: 'SporTV News', category: 'news', description: 'Notícias do esporte' },
    { time: '13:00', title: 'Futebol Europeu: Premier League', category: 'sports', description: 'Melhores momentos da rodada' },
    { time: '14:00', title: 'Basquete: NBB', category: 'sports', description: 'AO VIVO: Jogo do Novo Basquete Brasil' },
    { time: '16:00', title: 'MMA: Grandes Lutas', category: 'sports', description: 'Reapresentação dos melhores combates' },
    { time: '18:00', title: 'Futebol ao Vivo: Série B', category: 'sports', description: 'AO VIVO: Partida da Série B do Brasileirão' },
    { time: '20:00', title: 'Campeonato Italiano', category: 'sports', description: 'AO VIVO: Jogo da Serie A italiana' },
    { time: '22:00', title: 'Gol: O Grande Momento', category: 'sports', description: 'Os gols mais bonitos da rodada' },
    { time: '23:30', title: 'SporTV News', category: 'news', description: 'Encerramento com notícias da madrugada' },
  ],
  'SporTV 3': [
    { time: '07:00', title: 'Vôlei de Praia: Circuito Mundial', category: 'sports', description: 'Melhores momentos da etapa' },
    { time: '09:00', title: 'Natação: Troféu Brasil', category: 'sports', description: 'Finais do campeonato nacional' },
    { time: '11:00', title: 'Futebol Feminino', category: 'sports', description: 'AO VIVO: Jogo do Campeonato Brasileiro Feminino' },
    { time: '13:00', title: 'Atletismo: Diamond League', category: 'sports', description: 'Cobertura da etapa sul-americana' },
    { time: '15:00', title: 'Rúgbi: Super Rugby', category: 'sports', description: 'Partida do campeonato de rúgbi' },
    { time: '17:00', title: 'Esportes a Motor', category: 'sports', description: 'Resumo da semana no automobilismo' },
    { time: '19:00', title: 'Futebol ao Vivo: Libertadores', category: 'sports', description: 'AO VIVO: Partida da Copa Libertadores' },
    { time: '21:30', title: 'Debate Libertadores', category: 'talk', description: 'Mesa-redonda pós-jogo' },
    { time: '23:00', title: 'SporTV News', category: 'news', description: 'Notícias da noite' },
  ],
  'Combate': [
    { time: '08:00', title: 'Combate News', category: 'news', description: 'Notícias do mundo das lutas' },
    { time: '10:00', title: 'UFC: Grandes Lutas — Spider x Belfort', category: 'sports', description: 'Reapresentação de lenda do MMA' },
    { time: '12:00', title: 'Pesagem AO VIVO', category: 'sports', description: 'Pesagem oficial do UFC Fight Night' },
    { time: '14:00', title: 'Pré-luta: Card Completo', category: 'sports', description: 'Análise de todas as lutas do evento' },
    { time: '16:00', title: 'UFC Fight Night: Lutas Preliminares', category: 'sports', description: 'AO VIVO: Primeiras lutas do evento' },
    { time: '19:00', title: 'UFC Fight Night: Card Principal', category: 'sports', description: 'AO VIVO: Lutas principais da noite' },
    { time: '22:00', title: 'Pós-luta: Análise e Entrevistas', category: 'talk', description: 'Reação dos lutadores e análise' },
    { time: '23:30', title: 'Combate News — Edição Extra', category: 'news', description: 'Resumo do evento' },
  ],
  'Premiere FC': [
    { time: '10:00', title: 'Premiere: Gols da Rodada', category: 'sports', description: 'Todos os gols do Brasileirão Série A' },
    { time: '12:00', title: 'Pré-jogo: Aquecimento', category: 'sports', description: 'Escalações e análise tática' },
    { time: '13:00', title: 'Futebol ao Vivo: Brasileirão Série A', category: 'sports', description: 'AO VIVO: Jogo do Campeonato Brasileiro' },
    { time: '15:30', title: 'Intervalo: Mesa Redonda', category: 'talk', description: 'Análise do primeiro tempo' },
    { time: '16:00', title: 'Futebol ao Vivo: Segundo Tempo', category: 'sports', description: 'AO VIVO: Continuação da partida' },
    { time: '18:00', title: 'Pós-jogo: Debate', category: 'talk', description: 'Análise completa da partida' },
    { time: '19:00', title: 'Futebol ao Vivo: Jogo da Noite', category: 'sports', description: 'AO VIVO: Segunda partida da rodada' },
    { time: '21:30', title: 'Premiere: Mesa Redonda', category: 'talk', description: 'Debate sobre os jogos do dia' },
    { time: '23:00', title: 'Gols da Noite', category: 'sports', description: 'Compacto dos melhores momentos' },
  ],
  'CazéTV': [
    { time: '08:00', title: 'Cazé News', category: 'news', description: 'Informações do esporte' },
    { time: '10:00', title: 'Cortes do Cazé', category: 'entertainment', description: 'Melhores momentos da semana' },
    { time: '12:00', title: 'Pré-jogo: CazéTV ao Vivo', category: 'sports', description: 'Aquecimento com convidados especiais' },
    { time: '13:30', title: 'Futebol ao Vivo', category: 'sports', description: 'AO VIVO: Transmissão com narração diferenciada' },
    { time: '16:00', title: 'Pós-jogo: Reação & Memes', category: 'entertainment', description: 'Reações e melhores momentos' },
    { time: '18:00', title: 'Gameplay com Cazé', category: 'entertainment', description: 'Live de jogos e interação' },
    { time: '20:00', title: 'Live: Debate Esportivo', category: 'talk', description: 'Mesa-redonda com convidados especiais' },
    { time: '22:00', title: 'Cortes da Noite', category: 'entertainment', description: 'Melhores momentos do dia' },
  ],
  'ge Fast': [
    { time: '06:00', title: 'ge Manhã', category: 'news', description: 'Notícias rápidas do esporte' },
    { time: '08:00', title: 'Gols do Dia', category: 'sports', description: 'Todos os gols em 30 minutos' },
    { time: '10:00', title: 'Mercado da Bola', category: 'news', description: 'Notícias de transferências' },
    { time: '12:00', title: 'ge ao Vivo', category: 'sports', description: 'Programa ao vivo com notícias' },
    { time: '14:00', title: 'Melhores Momentos: Rodada', category: 'sports', description: 'Compacto da rodada' },
    { time: '16:00', title: 'ge Fast News', category: 'news', description: 'Edição da tarde' },
    { time: '18:00', title: 'Pré-jogo Rápido', category: 'sports', description: 'O que esperar dos jogos da noite' },
    { time: '20:00', title: 'Gols da Noite', category: 'sports', description: 'Todos os gols em tempo real' },
    { time: '22:00', title: 'ge Encerramento', category: 'news', description: 'Últimas notícias' },
  ],
  'ESPN': [
    { time: '06:00', title: 'SportsCenter AM', category: 'news', description: 'Morning sports news with highlights' },
    { time: '08:00', title: 'First Take', category: 'talk', description: 'Debate about the biggest stories in sports' },
    { time: '10:00', title: 'NBA Today', category: 'sports', description: 'NBA analysis, highlights and updates' },
    { time: '12:00', title: 'SportsCenter', category: 'news', description: 'Noon edition of SportsCenter' },
    { time: '13:00', title: 'NFL Live', category: 'sports', description: 'NFL news, analysis and predictions' },
    { time: '14:00', title: 'College Football Live', category: 'sports', description: 'College football coverage' },
    { time: '16:00', title: 'Pardon The Interruption', category: 'talk', description: 'Sports debate show' },
    { time: '17:00', title: 'SportsCenter PM', category: 'news', description: 'Evening sports news' },
    { time: '18:00', title: 'NBA Basketball', category: 'sports', description: 'LIVE: NBA regular season game' },
    { time: '20:30', title: 'NFL Monday Night Football', category: 'sports', description: 'LIVE: Monday Night Football' },
    { time: '23:30', title: 'SportsCenter Late', category: 'news', description: 'Late night sports news' },
  ],
  'Fox Sports': [
    { time: '07:00', title: 'Fox Sports News', category: 'news', description: 'Morning sports news' },
    { time: '09:00', title: 'Undisputed', category: 'talk', description: 'Skip Shannon and Keyshawn debate' },
    { time: '11:00', title: 'MLB Central', category: 'sports', description: 'Major League Baseball coverage' },
    { time: '13:00', title: 'Fox Sports Live', category: 'news', description: 'Live sports news updates' },
    { time: '14:00', title: 'MLB Baseball', category: 'sports', description: 'LIVE: MLB regular season' },
    { time: '17:00', title: 'NASCAR Race Hub', category: 'sports', description: 'NASCAR news and analysis' },
    { time: '18:00', title: 'College Football', category: 'sports', description: 'LIVE: College football game' },
    { time: '21:00', title: 'MLB Postgame', category: 'sports', description: 'Post-game analysis' },
    { time: '22:00', title: 'Fox Sports Tonight', category: 'talk', description: 'Evening sports debate' },
    { time: '23:30', title: 'Fox Sports News Late', category: 'news', description: 'Late night news' },
  ],
  'Canal do Inter': [
    { time: '08:00', title: 'Notícias do Inter', category: 'news', description: 'Informações atualizadas do Clube do Povo' },
    { time: '10:00', title: 'Memória Colorado', category: 'sports', description: 'Grandes momentos da história do Inter' },
    { time: '12:00', title: 'Sala de Imprensa', category: 'news', description: 'Coletiva e notícias do dia' },
    { time: '14:00', title: 'Jogos Históricos', category: 'sports', description: 'Reapresentação de jogos clássicos' },
    { time: '16:00', title: 'Base Colorado', category: 'sports', description: 'Notícias das categorias de base' },
    { time: '18:00', title: 'Pré-jogo: Preparação', category: 'sports', description: 'Aquecimento para a partida' },
    { time: '19:30', title: 'AO VIVO: Jogo do Inter', category: 'sports', description: 'Transmissão ao vivo com narração' },
    { time: '22:00', title: 'Pós-jogo: Análise', category: 'talk', description: 'Debate sobre a partida' },
    { time: '23:00', title: 'Encerramento', category: 'news', description: 'Últimas notícias do Inter' },
  ],
};

@Component({
  selector: 'app-epg-panel',
  imports: [DatePipe],
  templateUrl: './epg-panel.html',
  styleUrl: './epg-panel.scss',
})
export class EpgPanelComponent {
  readonly open = input<boolean>(false);
  readonly channelName = input<string>('');
  readonly channelLogo = input<string | null | undefined>(undefined);
  readonly closePanel = output<void>();

  protected readonly today = new Date();
  protected readonly weekDayNames = [
    'Domingo', 'Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado',
  ];

  /** Current programs for the selected channel */
  protected get programs(): EpgProgram[] {
    const name = this.channelName();
    // Try exact match first, then prefix match
    for (const [key, progs] of Object.entries(MOCK_EPG)) {
      if (name.includes(key) || key.includes(name)) {
        return progs;
      }
    }
    // Try partial match
    for (const [key, progs] of Object.entries(MOCK_EPG)) {
      if (name.toLowerCase().includes(key.toLowerCase()) ||
          key.toLowerCase().includes(name.toLowerCase())) {
        return progs;
      }
    }
    // Fallback: return generic schedule
    return this.buildGenericSchedule();
  }

  /** Find the currently-airing program index */
  protected get nowIndex(): number {
    const now = new Date();
    const currentMinutes = now.getHours() * 60 + now.getMinutes();
    const progs = this.programs;
    for (let i = progs.length - 1; i >= 0; i--) {
      const [h, m] = progs[i].time.split(':').map(Number);
      if (h * 60 + m <= currentMinutes) return i;
    }
    return 0;
  }

  private buildGenericSchedule(): EpgProgram[] {
    const base = [
      { time: '06:00', title: 'Programação Matinal', category: 'general' },
      { time: '08:00', title: 'Sessão da Manhã', category: 'general' },
      { time: '10:00', title: 'Programa Variedades', category: 'general' },
      { time: '12:00', title: 'Jornal do Meio-dia', category: 'news' },
      { time: '13:00', title: 'Sessão da Tarde', category: 'entertainment' },
      { time: '15:00', title: 'Esporte ao Vivo', category: 'sports' },
      { time: '17:00', title: 'Infantil', category: 'kids' },
      { time: '18:00', title: 'Jornal da Noite', category: 'news' },
      { time: '19:00', title: 'Novela / Série', category: 'entertainment' },
      { time: '20:00', title: 'Programa de Auditório', category: 'entertainment' },
      { time: '22:00', title: 'Jornal da Madrugada', category: 'news' },
      { time: '23:00', title: 'Sessão de Filmes', category: 'movies' },
    ];
    return base.map(p => ({ ...p, description: undefined }));
  }

  protected close(): void {
    this.closePanel.emit();
  }

  protected nowBarTop(programs: EpgProgram[], nowIndex: number, panelEl: HTMLElement): number {
    /* The "now" bar position is computed via CSS based on the scrolling container */
    return 0;
  }
}
