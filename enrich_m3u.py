#!/usr/bin/env python3
"""
Enrich M3U files with language/country/state/is-free/channel-type metadata.
Reads existing M3U files and re-writes them with enriched EXTINF attributes.

Usage: python enrich_m3u.py <m3u_dir>
"""

import re
import sys
from pathlib import Path

# ── Channel metadata mapping ──────────────────────────────────────────
# Based on tvg-id suffix (country), channel name patterns, and group-title

COUNTRY_TLD: dict[str, str] = {
    'br': 'BR', 'pt': 'PT', 'us': 'US', 'uk': 'GB', 'fr': 'FR',
    'de': 'DE', 'es': 'ES', 'it': 'IT', 'jp': 'JP', 'cn': 'CN',
    'ru': 'RU', 'in': 'IN', 'au': 'AU', 'ca': 'CA', 'mx': 'MX',
    'ar': 'AR', 'co': 'CO', 'cl': 'CL', 'pe': 'PE', 'uy': 'UY',
    've': 'VE', 'ec': 'EC', 'bo': 'BO', 'py': 'PY', 'do': 'DO',
    'hn': 'HN', 'sv': 'SV', 'ni': 'NI', 'cr': 'CR', 'pa': 'PA',
    'gt': 'GT', 'cu': 'CU', 'pr': 'PR', 'qa': 'QA', 'ma': 'MA',
    'dz': 'DZ', 'tn': 'TN', 'eg': 'EG', 'sa': 'SA', 'ae': 'AE',
    'ir': 'IR', 'iq': 'IQ', 'jo': 'JO', 'lb': 'LB', 'sy': 'SY',
    'tr': 'TR', 'gr': 'GR', 'cy': 'CY', 'il': 'IL', 'pk': 'PK',
    'bd': 'BD', 'lk': 'LK', 'th': 'TH', 'vn': 'VN', 'ph': 'PH',
    'id': 'ID', 'my': 'MY', 'sg': 'SG', 'hk': 'HK', 'tw': 'TW',
    'kr': 'KR', 'za': 'ZA', 'ng': 'NG', 'ke': 'KE', 'gh': 'GH',
    'tz': 'TZ', 'ug': 'UG', 'bj': 'BJ', 'ci': 'CI', 'sn': 'SN',
    'cm': 'CM', 'ao': 'AO', 'mz': 'MZ', 'cv': 'CV', 'ge': 'GE',
    'az': 'AZ', 'am': 'AM', 'by': 'BY', 'ua': 'UA', 'ro': 'RO',
    'bg': 'BG', 'rs': 'RS', 'hr': 'HR', 'si': 'SI', 'cz': 'CZ',
    'sk': 'SK', 'hu': 'HU', 'pl': 'PL', 'lt': 'LT', 'lv': 'LV',
    'ee': 'EE', 'is': 'IS', 'no': 'NO', 'se': 'SE', 'fi': 'FI',
    'dk': 'DK', 'nl': 'NL', 'be': 'BE', 'ch': 'CH', 'at': 'AT',
    'ie': 'IE', 'mt': 'MT', 'al': 'AL', 'mk': 'MK', 'ba': 'BA',
    'me': 'ME', 'tj': 'TJ', 'kz': 'KZ',
}

# tvg-id → country mapping for special cases or when tvg-id is clean
def extract_country_from_tvg_id(tvg_id: str) -> str | None:
    """Extract country code from tvg-id like 'RedeGlobo.br' or 'ESPNDeportes.us'."""
    if not tvg_id:
        return None
    # Match the last 2-letter country TLD before @ or end
    m = re.search(r'\.([a-z]{2})(?:@|$)', tvg_id)
    if m and m.group(1) in COUNTRY_TLD:
        return COUNTRY_TLD[m.group(1)]
    return None

# ── Channel type inference ────────────────────────────────────────────
SPORTS_KEYWORDS = [
    'espn', 'sport', 'sportv', 'football', 'futebol', 'soccer',
    'fifa', 'gol', 'sporttv', 'combate', 'premiere', 'racing',
    'racing', 'fight', 'boxing', 'mma', 'ufc', 'wwe', 'nba',
    'nfl', 'nhl', 'mlb', 'nascar', 'f1', 'moto', 'golf',
    'tennis', 'cricket', 'baseball', 'basketball', 'hockey',
    'olympic', 'deportes', 'esporte', 'canal do inter',
    'cazetv', 'caze', 'ge fast', 'red bull tv',
    'billiard', 'cornhole', 'draftkings', 'fanduel',
    'flosport', 'floracing', 'flohockey', 'fuel tv',
    'fubosports', 'game+', 'gemsport', 'gem fit',
    'alkass', 'arryadia', 'bahrain sport', 'erocanaltv',
    'ert sport', 'ct sport', 'dsport', 'cbc sport',
    'cbs sports', 'fox sport', 'adjarasport',
    'bein sport', 'barca tv', 'atalanta',
    'sportklub',
]

NEWS_KEYWORDS = [
    'news', 'noticia', 'cnn', 'bbc', 'globo news',
    'record news', 'jovem pan', 'times brasil',
    'cnbc', 'bloomberg', 'reuters', 'africa24',
    'franceinfo', 'euronews', 'sky news',
]

RELIGIOUS_KEYWORDS = [
    'gospel', 'novo tempo', 'rit tv', 'tv aparecida',
    'tv universal', 'tv evangelizar', 'angel tv',
    'kuriakos', 'despertar tv', 'fonte tv',
    'tv padre', 'tv terceiro anjo', 'tv gideoes',
    'tv mana', 'rede gospel', 'boas novas',
]

ENTERTAINMENT_KEYWORDS = [
    'movie', 'filme', 'series', 'loading', 'ngt',
    'rede ngt', 'awsome', 'funny', 'comedy',
    'fora tedio', 'um tv', 'vrt channel',
    'elemental channel', 'ely tv', 'conecta',
    'ghost tv', 'ghost', 'bdc tv',
]

KIDS_KEYWORDS = [
    'nick', 'cartoon', 'gloob', 'disney', 'kids',
    'infantil', 'boomerang',
]

MUSIC_KEYWORDS = [
    'music', 'mtv', 'kpop', 'tik tok', 'trace',
    'tiktok radio',
]

EDUCATION_KEYWORDS = [
    'educa', 'cultura', 'ufg', 'ufop', 'uni tv',
    'tv escola', 'tv cultura', 'tv uf',
    'tv mackenzie', 'universidade',
]

FREE_CHANNEL_KEYWORDS = [
    'rede globo', 'sbt', 'record tv', 'record news',
    'tv cultura', 'tv brasil', 'tv camara',
    'tv educacao', 'tv gov', 'fifa+',
    'ge fast', 'cazetv', 'caze tv',
    'canal do inter', 'tv liberal',
    'tv evangelizar', 'tv aparecida',
    'novo tempo', 'tv universal',
    'tv cancao nova', 'rit tv',
    'jovem pan', 'times brasil',
    'record', 'tv bahia',
    'tv itu', 'tv thathi', 'tv brusque',
    'tv cidad', 'tv comunitaria',
    'rede minas', 'tv educativa',
    'amazon sat', 'boas novas',
    'canal rural', 'canal do criador',
    'cwb tv', 'demais tv',
    'tv aldeia', 'tv alternativ',
    'tv arapuan', 'tv aratu',
    'tv birigui', 'tv brasil',
    'tv brusque', 'tv camara',
    'tv cidade', 'tv clube',
    'tv da s', 'tv das artes',
    'tv destak', 'tv difusora',
    'tv digital', 'tv do povo',
    'tv empire', 'tv fronteira',
    'tv futuro', 'tv grao',
    'tv guar', 'tv interlagos',
    'tv liberdade', 'tv mais',
    'tv marajoara', 'tv max',
    'tv metropole', 'tv modelo',
    'tv natal', 'tv pampa',
    'tv pantanal', 'tv paraense',
    'tv passo fundo', 'tv sandegi',
    'tv sao raimundo', 'tv series',
    'tv sim', 'tv sol',
    'tv sul', 'tv universitaria',
    'tv vila real', 'tv zoom',
    'tv vicos', 'tvedio',
    'tv itape', 'tvnbn',
    'tvcom', 'channel', 'tvi',
    'catve', 'conexao',
    'prime tv', 'primer tv',
    'rbatv', 'tvc',
    'tvcomunitaria', 'tvcomm',
    'vv8 tv', 'sertaoo tv',
    'tv futuro', 'tv grao',
    'tv mais', 'tv maric',
    'alfa channel', 'alpha channel',
    'awtv', 'cabo frio',
    'canal 38', 'canal 25',
    'chroma tv', 'classique tv',
    'conecta', 'conectv',
    'cultura para', 'eu tv',
    'fala litoral', 'geekdot',
    'istv', 'loading tv',
    'mkk web tv', 'mytime movie',
    'nick', 'nicktoons',
    'nova era tv', 'play tv',
    'plena tv', 'santa cecilia',
    'sesc tv', 'sic tv',
    'stz tv', 'tcm 10',
    'tv acritica', 'tv a folha',
    'tv alianca', 'tv assembleia',
    'tv brics', 'tv brusque',
]

PREMIUM_CHANNEL_KEYWORDS = [
    'espn', 'sportv', 'premiere fc', 'combate',
    'fox sport', 'cbs sport', 'bein sport',
    'dazn', 'fight network', 'fite',
]

# ── Brazilian state mapping ───────────────────────────────────────────
STATE_BY_CITY: dict[str, str] = {
    # São Paulo
    'são paulo': 'SP', 'sao paulo': 'SP', 'jundiaí': 'SP',
    'birigui': 'SP', 'ribeirão': 'SP', 'ribeirao': 'SP',
    'campinas': 'SP', 'santos': 'SP', 'sorocaba': 'SP',
    'biritiba': 'SP', 'mogi': 'SP', 'guarulhos': 'SP',
    'sbc': 'SP', 'são bernardo': 'SP', 'sao bernardo': 'SP',
    'são josé dos campos': 'SP', 'sao jose dos campos': 'SP',
    'interior sp': 'SP',
    # Rio de Janeiro
    'rio de janeiro': 'RJ', 'rio': 'RJ', 'niterói': 'RJ',
    'niteroi': 'RJ', 'petrópolis': 'RJ', 'petropolis': 'RJ',
    'angra': 'RJ', 'macae': 'RJ', 'campos': 'RJ',
    'nova friburgo': 'RJ', 'cabo frio': 'RJ',
    # Minas Gerais
    'belo horizonte': 'MG', 'bh': 'MG', 'juiz de fora': 'MG',
    'uberlândia': 'MG', 'uberlandia': 'MG', 'montes claros': 'MG',
    'governador valadares': 'MG', 'sul de minas': 'MG',
    'poços de caldas': 'MG', 'pocos de caldas': 'MG',
    # Bahia
    'salvador': 'BA', 'bahia': 'BA', 'feira de santana': 'BA',
    'ilhéus': 'BA', 'ilheus': 'BA', 'vitoria da conquista': 'BA',
    'sul bahia': 'BA',
    # Rio Grande do Sul
    'porto alegre': 'RS', 'poa': 'RS', 'passo fundo': 'RS',
    'caxias do sul': 'RS', 'santa maria': 'RS',
    # Paraná
    'curitiba': 'PR', 'cwb': 'PR', 'londrina': 'PR',
    'maringá': 'PR', 'maringa': 'PR', 'parana': 'PR',
    'catarinense': 'SC',
    # Santa Catarina
    'florianópolis': 'SC', 'florianopolis': 'SC',
    'joinville': 'SC', 'blumenau': 'SC', 'brusque': 'SC',
    'criciúma': 'SC', 'criciuma': 'SC', 'itajaí': 'SC', 'itajai': 'SC',
    'catarinense': 'SC',
    # Pernambuco
    'recife': 'PE', 'olinda': 'PE', 'caruaru': 'PE',
    # Ceará
    'fortaleza': 'CE', 'ceara': 'CE', 'juazeiro do norte': 'CE',
    # Goiás
    'goiânia': 'GO', 'goiania': 'GO', 'goias': 'GO',
    # Distrito Federal
    'brasília': 'DF', 'brasilia': 'DF', 'df': 'DF',
    # Amazonas
    'manaus': 'AM', 'amazonas': 'AM', 'amazon sat': 'AM',
    # Pará
    'belém': 'PA', 'belem': 'PA', 'paraense': 'PA', 'pará': 'PA',
    'marajoara': 'PA',
    # Maranhão
    'são luís': 'MA', 'sao luis': 'MA',
    # Rio Grande do Norte
    'natal': 'RN', 'rn': 'RN', 'potiguar': 'RN',
    # Mato Grosso
    'cuiabá': 'MT', 'cuiaba': 'MT', 'matogrosso': 'MT',
    'rondonópolis': 'MT', 'rondonopolis': 'MT',
    'nova mutum': 'MT', 'sinop': 'MT',
    # Mato Grosso do Sul
    'campo grande': 'MS', 'pantanal': 'MS', 'ms': 'MS',
    # Espírito Santo
    'vitória': 'ES', 'vitoria': 'ES', 'es': 'ES',
    'cachoeiro': 'ES', 'colatina': 'ES',
    'são mateus': 'ES', 'sao mateus': 'ES',
    'vila velha': 'ES',
    # Alagoas
    'maceió': 'AL', 'maceio': 'AL',
    # Paraíba
    'joão pessoa': 'PB', 'joao pessoa': 'PB',
    # Amazonas
    'manaus': 'AM',
    # Piauí
    'teresina': 'PI',
    # Sergipe
    'aracaju': 'SE',
    # Rondônia
    'porto velho': 'RO',
    # Acre
    'rio branco': 'AC',
    # Amapá
    'macapá': 'AP', 'macapa': 'AP',
    # Tocantins
    'palmas': 'TO',
    # Roraima
    'boa vista': 'RR',
}


def infer_language(name: str, tvg_id: str | None, group_title: str | None,
                   playlist_name: str) -> str:
    """Infer language code from channel info."""
    name_lower = name.lower()
    tvg_id_lower = (tvg_id or '').lower()
    group_lower = (group_title or '').lower()

    # Brazilian Portuguese indicators
    br_indicators = ['.br@', '.br', 'portuguese', 'português',
                     'globo', 'record', 'sbt', 'band',
                     'caze', 'combate', 'esporte',
                     'globoplay', 'premiere', 'fifa+ portuguese',
                     'canal do inter', 'ge fast', 'jovem pan',
                     'novo tempo', 'tv cultura', 'rede globo',
                     'tv brasil', 'tv bahia', 'tv aparecida',
                     'canais-brasil', 'br.m3u',
                     'times brasil', 'record news',
                     'tvcamara', 'tv camara',
                     'playplus', 'cantadas',
                     'tvaovivo', 'aovivo',
                     'cwb tv', 'cx tv',
                     # Brazilian channels in the sports file
                     'sportv', 'canal do inter',
                     ]
    # Portuguese (Portugal) indicators
    pt_indicators = ['portugal', '.pt@', '.pt', 'sic', 'tvi',
                     'rtp', 'portugal']

    # Spanish indicators
    es_indicators = ['espanol', 'español', 'deportes', '.es@', '.mx@',
                     '.ar@', '.co@', '.cl@', '.pe@', '.uy@',
                     'latino', 'hispanic',
                     'fox deportes', 'bein sports xtra en espanol',
                     'cdn deportes', 'deportes tvc',
                     'diresports', 'dsport',
                     'ftv', 'awapa', 'colimdo',
                     'tvc deportes',
                     'alfa sport cy', 'antena sport']
    # English indicators
    en_indicators = [
        'english', '.uk@', '.us@', '.au@', '.ca@',
        'cbs sports', 'espn', 'nfl', 'nba', 'mlb', 'nascar',
        'fight network', 'fite', 'flosport', 'draftkings',
        'fanduel', 'golf kingdom', '30a golf',
        'acc digital', 'acl cornhole', 'billiard tv',
        'bein sports xtra', 'bek tv',
        'cricket gold', 'dazn combat',
        'f1 channel', 'fifa+ united states',
        'fifa+ women', 'fifa+ english',
        'floracing', 'flohockey',
        'fox sports', 'fubosports', 'fuel tv',
        'game+', 'red bull tv',
        'fast&funbox',
    ]
    # French indicators
    fr_indicators = ['french', '.fr@', '.fr', 'canal+', 'equidia',
                     'africa 24 sport', 'franceinfo',
                     'fifa+ french']

    language = 'pt'  # Default for br.m3u / canais-brasil.m3u playlists

    # Check playlist name first (strong signal)
    if 'br' in playlist_name.lower():
        language = 'pt'
    elif 'sports' in playlist_name.lower():
        language = 'en'  # default for sports, will override below

    # Check tvg-id country suffix
    country = extract_country_from_tvg_id(tvg_id or '')
    if country == 'BR':
        language = 'pt'
    elif country in ('PT',):
        language = 'pt'
    elif country in ('ES', 'MX', 'AR', 'CO', 'CL', 'PE', 'UY', 'BO', 'EC',
                     'VE', 'CR', 'DO', 'PA', 'SV', 'HN', 'NI', 'GT', 'CU',
                     'PR', 'PY'):
        language = 'es'
    elif country in ('FR',):
        language = 'fr'
    elif country in ('DE', 'AT', 'CH'):
        language = 'de'
    elif country in ('IT',):
        language = 'it'
    elif country in ('JP',):
        language = 'jp'
    elif country in ('CN',):
        language = 'zh'
    elif country in ('RU',):
        language = 'ru'
    elif country in ('QA', 'AE', 'SA', 'IQ', 'JO', 'LB', 'SY', 'YE', 'OM', 'KW', 'BH', 'EG',
                     'MA', 'DZ', 'TN', 'LY', 'SD'):
        language = 'ar'
    elif country in ('TR',):
        language = 'tr'
    elif country in ('NL', 'BE'):
        language = 'nl'
    elif country in ('PL',):
        language = 'pl'
    elif country in ('SE', 'NO', 'DK', 'IS'):
        language = 'no'
    elif country in ('FI',):
        language = 'fi'
    elif country in ('CZ', 'SK'):
        language = 'cs'
    elif country in ('HU',):
        language = 'hu'
    elif country in ('RO',):
        language = 'ro'
    elif country in ('BG',):
        language = 'bg'
    elif country in ('RS', 'HR', 'BA', 'ME', 'AL', 'MK', 'SI'):
        language = 'hr'
    elif country in ('GR', 'CY'):
        language = 'el'
    elif country in ('IL',):
        language = 'he'
    elif country in ('TH',):
        language = 'th'
    elif country in ('VN',):
        language = 'vi'
    elif country in ('ID',):
        language = 'id'
    elif country in ('KR',):
        language = 'ko'
    elif country in ('TW', 'HK'):
        language = 'zh'
    elif country in ('IN',):
        language = 'hi'
    elif country in ('PK',):
        language = 'ur'
    elif country in ('BD',):
        language = 'bn'
    elif country in ('LK',):
        language = 'si'
    elif country in ('PH',):
        language = 'fil'
    elif country in ('MY',):
        language = 'ms'
    elif country in ('SG',):
        language = 'en'
    elif country in ('NZ',):
        language = 'en'
    elif country in ('ZA',):
        language = 'en'
    elif country in ('NG', 'GH', 'KE', 'TZ', 'UG', 'ZA', 'BJ', 'CI', 'SN', 'CM', 'AO', 'MZ',
                     'CV'):
        language = 'fr' if country in ('BJ', 'CI', 'SN', 'CM', 'MZ') else 'pt' if country in ('AO', 'MZ', 'CV') else 'en'
    elif country in ('TJ', 'KZ', 'AZ', 'AM', 'GE', 'BY', 'UA', 'EE', 'LV', 'LT'):
        language = 'ru'
    elif country in ('MA',):
        language = 'ar'

    # Check by content name patterns
    for en_kw in en_indicators:
        if en_kw.lower() in name_lower or en_kw.lower() in tvg_id_lower:
            if language == 'pt' or language == 'es':
                # Only override if it's clearly English
                if any(x in name_lower for x in ['cbs sports hq',
                                                   'cbs sports golazo',
                                                   'fox sports',
                                                   'fifa+ united states',
                                                   'fifa+ women',
                                                   'fifa+ english',
                                                   'fifa+ (720p)',
                                                   'golf kingdom',
                                                   'draftkings',
                                                   'fanduel',
                                                   'fight network',
                                                   'floracing',
                                                   'flohockey',
                                                   'fite 24/7',
                                                   'fubosports',
                                                   'red bull tv us',
                                                   'beIN SPORTS XTRA',
                                                   ]):
                    language = 'en'
            elif country is None or country in ('US', 'GB', 'AU', 'CA', 'IE', 'NZ', 'ZA'):
                language = 'en'

    for es_kw in es_indicators:
        if es_kw.lower() in name_lower or es_kw.lower() in tvg_id_lower:
            if country in (None, 'US') or any(c in (tvg_id or '') for c in ['.es', '.mx', '.ar', '.co', '.cl']):
                language = 'es'

    for fr_kw in fr_indicators:
        if fr_kw.lower() in name_lower or fr_kw.lower() in tvg_id_lower:
            language = 'fr'

    for br_kw in br_indicators:
        if br_kw.lower() in name_lower or br_kw.lower() in tvg_id_lower:
            language = 'pt'

    for pt_kw in pt_indicators:
        if pt_kw.lower() in name_lower or pt_kw.lower() in tvg_id_lower:
            language = 'pt'
            break

    return language


def infer_country(name: str, tvg_id: str | None, group_title: str | None,
                  playlist_name: str) -> str | None:
    """Infer country code from channel info."""
    name_lower = name.lower()
    tvg_id_lower = (tvg_id or '').lower()
    group_lower = (group_title or '').lower()

    # From tvg-id
    country = extract_country_from_tvg_id(tvg_id or '')
    if country:
        return country

    # From playlist name
    if 'br' in playlist_name.lower() or 'canais-brasil' in playlist_name.lower():
        return 'BR'

    # From channel name patterns
    if any(kw in name_lower for kw in ['globo', 'record', 'sbt', 'band',
                                         'caze tv', 'combate', 'sportv', 'premiere fc',
                                         'tv cultura', 'tv brasil', 'jovem pan',
                                         'canal do inter', 'novo tempo',
                                         'tv aparecida', 'tv camara', 'times brasil',
                                         'playplus', 'tv bahia', 'tv itu',
                                         'gloob', 'nicktoons brasil', 'nickweb',
                                         'nick online', 'rede ng', 'redetv',
                                         'tvc', 'tvcom', 'tv modelo',
                                         'tv natal', 'tv paraense', 'tv pampa',
                                         'tv sul de minas', 'tvitape',
                                         'tv brusque', 'tv cidade',
                                         'tv curuca', 'tv das art',
                                         'tv destino', 'tv difusora',
                                         'tv digital', 'tv do povo',
                                         'tv empire', 'tv encontro',
                                         'tv evangelizar', 'tv fronteira',
                                         'tv futuro', 'tv gideoes',
                                         'tv grao', 'tv guar',
                                         'tv interlagos', 'tv liberdade',
                                         'tv mackenzie', 'tv mais',
                                         'tv mana brasil', 'tv marajoara',
                                         'tv max', 'tv metropole',
                                         'tv padre', 'tv pantanal',
                                         'tv passo fundo', 'tv sandegi',
                                         'tv sao raimundo', 'tv series',
                                         'tv sim', 'tv sol',
                                         'tv thathi', 'tv ufg',
                                         'tv ufop', 'tv universal',
                                         'tv vicosa', 'tv vila real',
                                         'tv zoom', 'tv a critica',
                                         'tv a folha', 'tv aldeia',
                                         'tv alianca', 'tv alternativ',
                                         'tv arapuan', 'tv aratu',
                                         'tv birigui', 'tv brics',
                                         'tvedio', 'tvnbn',
                                         'ge fast', 'cwb tv',
                                         'awtv', 'mytime movie',
                                         'kpop', 'trace brasil',
                                         'tcm 10', 'vv8 tv',
                                         'sertaoo tv', 'tvcomunitaria',
                                         'tvcomm', 'tv cultura',
                                         'radio', 'mais',
                                         'canal educa', 'canal gov',
                                         'canal libras', 'canal rural',
                                         'canal do criador',
                                         'canal saude', 'canal 38',
                                         'canal 25', 'canal ricos',
                                         'santa cecilia', 'sesc tv',
                                         'stz tv', 'tv acritica',
                                         'tv a folha', 'tv agu',
                                         'tv alcance', 'tv all',
                                         'tv ame', 'tv amor',
                                         'tv andradas', 'tv angeloni',
                                         'tv anima', 'tv antena',
                                         'tv ara', 'tv arara',
                                         'tv aruj', 'tv atalaia',
                                         'tv b', 'tv bam',
                                         'tv bate', 'tv ben',
                                         'tv boa', 'tv brasi',
                                         'tv brasi', 'tv cab',
                                         'tv cam', 'tv camp',
                                         'tv cancao', 'tv capitao',
                                         'tv cascavel', 'tv cent',
                                         'tv centro', 'tv cidad',
                                         'tv cid', 'tv cnh',
                                         'tv coletiv', 'tv comunitaria',
                                         'tv conexao', 'tv conq',
                                         'tv cont', 'tv corrida',
                                         'tv cost', 'tv crista',
                                         'tv cru', 'tv cuiaba',
                                         'tv curit', 'tv curu',
                                         'tv delta', 'tv des',
                                         'tv destino', 'tv dic',
                                         'tv difu', 'tv digital',
                                         'tv dil', 'tv di',
                                         'tv do', 'tv dos',
                                         'tv dru', 'tv eco',
                                         'tv eden', 'tv educ',
                                         'tv ef', 'tv ema',
                                         'tv emis', 'tv enc',
                                         'tv entr', 'tv entrev',
                                         'tv esco', 'tv espa',
                                         'tv espe', 'tv esp',
                                         'tv est', 'tv f',
                                         'tv fala', 'tv fam',
                                         'tv far', 'tv faz',
                                         'tv feed', 'tv feli',
                                         'tv fen', 'tv fil',
                                         'tv flor', 'tv fon',
                                         'tv for', 'tv foz',
                                         'tv fr', 'tv fron',
                                         'tv ftec', 'tv fun',
                                         'tv gente', 'tv global',
                                         'tv goi', 'tv gran',
                                         'tv gre', 'tv gru',
                                         'tv gua', 'tv gua',
                                         'tv guar', 'tv gui',
                                         'tv ha', 'tv hel',
                                         'tv hor', 'tv hum',
                                         'tv id', 'tv im',
                                         'tv imp', 'tv inf',
                                         'tv ins', 'tv int',
                                         'tv ip', 'tv it',
                                         'tv itu', 'tv iv',
                                         'tv jar', 'tv jo',
                                         'tv jov', 'tv ju',
                                         'tv jus', 'tv k',
                                         'tv lac', 'tv lar',
                                         'tv le', 'tv let',
                                         'tv lh', 'tv li',
                                         'tv liv', 'tv lo',
                                         'tv lut', 'tv m',
                                         'tv mac', 'tv mag',
                                         'tv mam', 'tv man',
                                         'tv mar', 'tv mat',
                                         'tv may', 'tv mc',
                                         'tv med', 'tv meg',
                                         'tv men', 'tv mer',
                                         'tv mes', 'tv met',
                                         'tv mg', 'tv mi',
                                         'tv mil', 'tv min',
                                         'tv mir', 'tv mis',
                                         'tv mod', 'tv mon',
                                         'tv mor', 'tv mos',
                                         'tv mov', 'tv msg',
                                         'tv muc', 'tv mul',
                                         'tv mun', 'tv mur',
                                         'tv mus', 'tv mz',
                                         'tv n', 'tv nac',
                                         'tv nas', 'tv nav',
                                         'tv nd', 'tv net',
                                         'tv ni', 'tv no',
                                         'tv nome', 'tv nos',
                                         'tv not', 'tv nova',
                                         'tv ntv', 'tv nu',
                                         'tv ob', 'tv od',
                                         'tv olh', 'tv on',
                                         'tv opi', 'tv or',
                                         'tv ou', 'tv p',
                                         'tv pac', 'tv pad',
                                         'tv pal', 'tv pam',
                                         'tv pan', 'tv paz',
                                         'tv pe', 'tv ped',
                                         'tv pen', 'tv pequ',
                                         'tv per', 'tv pet',
                                         'tv pi', 'tv pia',
                                         'tv pit', 'tv pl',
                                         'tv pla', 'tv pla',
                                         'tv po', 'tv pon',
                                         'tv pop', 'tv por',
                                         'tv pos', 'tv pr',
                                         'tv pra', 'tv pre',
                                         'tv pri', 'tv pro',
                                         'tv pv', 'tv q',
                                         'tv qua', 'tv que',
                                         'tv ra', 'tv rad',
                                         'tv ram', 'tv re',
                                         'tv rec', 'tv reg',
                                         'tv rei', 'tv rel',
                                         'tv rev', 'tv ri',
                                         'tv rob', 'tv rot',
                                         'tv rs', 'tv s',
                                         'tv sa', 'tv sal',
                                         'tv san', 'tv sao',
                                         'tv sc', 'tv seg',
                                         'tv sem', 'tv sen',
                                         'tv sep', 'tv ser',
                                         'tv ses', 'tv sho',
                                         'tv sie', 'tv sil',
                                         'tv sis', 'tv sm',
                                         'tv soc', 'tv sol',
                                         'tv son', 'tv sou',
                                         'tv sp', 'tv ss',
                                         'tv st', 'tv sta',
                                         'tv ste', 'tv sto',
                                         'tv suc', 'tv sul',
                                         'tv sun', 'tv sup',
                                         'tv sur', 'tv sus',
                                         'tv t', 'tv ta',
                                         'tv tar', 'tv te',
                                         'tv tel', 'tv tem',
                                         'tv ter', 'tv ti',
                                         'tv tig', 'tv tin',
                                         'tv tol', 'tv top',
                                         'tv tor', 'tv tot',
                                         'tv tr', 'tv tra',
                                         'tv tri', 'tv tro',
                                         'tv tu', 'tv tv',
                                         'tv u', 'tv ult',
                                         'tv une', 'tv uni',
                                         'tv urban', 'tv v',
                                         'tv va', 'tv val',
                                         'tv van', 'tv vec',
                                         'tv vel', 'tv vem',
                                         'tv ver', 'tv via',
                                         'tv vib', 'tv vid',
                                         'tv vig', 'tv vir',
                                         'tv vis', 'tv vit',
                                         'tv viv', 'tv vo',
                                         'tv vol', 'tv vos',
                                         'tv we', 'tv web',
                                         'tv word', 'tv x',
                                         'tv y', 'tv z',
                                         'tv zoom',
                                         'tvmais', 'tv video', 'tv res',
                                         'tv teste', 'tv top',
                                         'alfa tv', 'alfa tv ',
                                         'alpha channel']):
        return 'BR'

    if 'portugal' in name_lower:
        return 'PT'

    return None


def infer_state(name: str, tvg_id: str | None, group_title: str | None,
                country: str | None) -> str | None:
    """Infer Brazilian state from channel name/city."""
    if country != 'BR':
        return None

    name_lower = name.lower()
    tvg_id_lower = (tvg_id or '').lower()
    group_lower = (group_title or '').lower()

    combined = f'{name_lower} {tvg_id_lower} {group_lower}'.lower()

    for keyword, state in STATE_BY_CITY.items():
        if keyword in combined:
            return state

    return None


def infer_channel_type(name: str, group_title: str | None, playlist_name: str) -> str | None:
    """Infer channel type category."""
    name_lower = name.lower()
    group_lower = (group_title or '').lower()
    combined = f'{name_lower} {group_lower}'

    # Strong sports signals
    if any(kw in combined for kw in SPORTS_KEYWORDS):
        return 'sports'
    # Strong news signals
    if any(kw in combined for kw in NEWS_KEYWORDS):
        return 'news'
    # Religious
    if any(kw in combined for kw in RELIGIOUS_KEYWORDS):
        return 'religious'
    # Kids
    if any(kw in combined for kw in KIDS_KEYWORDS):
        return 'kids'
    # Education
    if any(kw in combined for kw in EDUCATION_KEYWORDS):
        return 'education'
    # Music
    if any(kw in combined for kw in MUSIC_KEYWORDS):
        return 'music'
    # Entertainment
    if any(kw in combined for kw in ENTERTAINMENT_KEYWORDS):
        return 'entertainment'

    # From group_title
    if group_title:
        gt = group_lower
        if 'sport' in gt or 'esporte' in gt:
            return 'sports'
        if 'news' in gt or 'notícia' in gt or 'noticia' in gt:
            return 'news'
        if 'religi' in gt:
            return 'religious'
        if 'kid' in gt or 'infantil' in gt or 'cartoon' in gt:
            return 'kids'
        if 'music' in gt or 'música' in gt:
            return 'music'
        if 'movie' in gt or 'filme' in gt or 'movie' in gt:
            return 'movies'
        if 'entertain' in gt:
            return 'entertainment'
        if 'educa' in gt:
            return 'education'
        if 'travel' in gt or 'turismo' in gt:
            return 'travel'

    return None


def infer_is_free(name: str, tvg_id: str | None, group_title: str | None,
                  playlist_name: str) -> bool:
    """Infer if a channel is free-to-air."""
    name_lower = name.lower()
    tvg_id_lower = (tvg_id or '').lower()
    group_lower = (group_title or '').lower()
    combined = f'{name_lower} {tvg_id_lower} {group_lower}'

    # Premium indicators
    if any(kw in combined for kw in PREMIUM_CHANNEL_KEYWORDS):
        return False

    # Check group-title for premium signal
    if group_lower in ('esportes', 'sports'):
        # In sports playlist, most channels are available as free streams
        # unless they are known premium brands
        premium_brands = ['espn', 'sportv', 'premiere fc', 'combate',
                          'fox sports 1', 'fox sports 2',
                          'cbs sports', 'bein sport']
        if any(b in combined for b in premium_brands):
            return False
        return True

    # Free channel indicators
    if any(kw in combined for kw in FREE_CHANNEL_KEYWORDS):
        return True

    # Default to free for Brazilian channels
    if any(kw in combined for kw in ['tv', 'canal']):
        return True

    # For sports channels from the sports playlist, default to free
    # (many are free FAST channels or free-to-air streams)
    if 'sports' in playlist_name.lower():
        return True

    return True


def enrich_m3u_line(line: str, playlist_name: str) -> str:
    """Add language/country/state/is-free/channel-type attributes to EXTINF lines."""
    if not line.startswith('#EXTINF'):
        return line

    # Extract tvg-id
    tvg_id_match = re.search(r'tvg-id="([^"]*)"', line)
    tvg_id = tvg_id_match.group(1) if tvg_id_match else None

    # Extract channel name
    name_match = re.search(r',(.+)$', line)
    name = name_match.group(1).strip() if name_match else ''

    # Extract group-title
    group_match = re.search(r'group-title="([^"]*)"', line)
    group_title = group_match.group(1) if group_match else None

    # Infer metadata
    language = infer_language(name, tvg_id, group_title, playlist_name)
    country = infer_country(name, tvg_id, group_title, playlist_name)
    state = infer_state(name, tvg_id, group_title, country)
    channel_type = infer_channel_type(name, group_title, playlist_name)
    is_free = infer_is_free(name, tvg_id, group_title, playlist_name)

    # Insert attributes into the EXTINF line (before the comma)
    # Find the last attribute and insert before it, or before the comma
    comma_pos = line.rindex(',')
    header = line[:comma_pos]

    # Remove existing attributes if any (we'll re-add)
    attrs = {}

    # Parse existing attributes
    attr_pattern = re.compile(r'([\w-]+)="([^"]*)"')
    for m in attr_pattern.finditer(header):
        key = m.group(1)
        value = m.group(2)
        if key not in ('language', 'country', 'state', 'is-free', 'channel-type'):
            attrs[key] = value

    # Build the new header with new attrs
    attr_parts = []
    for key, value in attrs.items():
        attr_parts.append(f'{key}="{value}"')

    # Add new attrs (always, for consistency)
    attr_parts.append(f'language="{language}"')
    if country:
        attr_parts.append(f'country="{country}"')
    if state:
        attr_parts.append(f'state="{state}"')
    attr_parts.append(f'is-free={"false" if not is_free else "true"}')
    if channel_type:
        attr_parts.append(f'channel-type="{channel_type}"')

    rest = line[comma_pos:]  # includes the comma and channel name

    return f'#EXTINF:-1 {" ".join(attr_parts)}{rest}'


def main(m3u_dir: str):
    path = Path(m3u_dir)
    m3u_files = sorted(path.glob('*.m3u')) + sorted(path.glob('*.m3u8'))

    if not m3u_files:
        print(f'No M3U files found in {path}')
        return

    for m3u_path in m3u_files:
        print(f'Processing {m3u_path.name}...')
        content = m3u_path.read_text(encoding='utf-8', errors='replace')
        lines = content.splitlines(keepends=True)

        enriched_lines = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('#EXTINF'):
                enriched = enrich_m3u_line(stripped, m3u_path.stem)
                enriched_lines.append(enriched + line[len(stripped):] if line.endswith('\n') else enriched + '\n')
            else:
                enriched_lines.append(line)

        # Write backup
        backup = m3u_path.with_suffix(m3u_path.suffix + '.bak')
        backup.write_text(content, encoding='utf-8')

        # Write enriched
        m3u_path.write_text(''.join(enriched_lines), encoding='utf-8')
        print(f'  ✓ Enriched {m3u_path.name} ({sum(1 for l in enriched_lines if "#EXTINF" in l)} channels)')
        print(f'  ✓ Backup saved to {backup.name}')


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python enrich_m3u.py <m3u_dir>')
        sys.exit(1)
    main(sys.argv[1])
