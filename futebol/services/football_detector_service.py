import unicodedata


class FootballDetectorService:
    KEYWORDS: tuple[str, ...] = (
        "futebol",
        "football",
        "soccer",
        "copa",
        "copa do mundo",
        "mundial",
        "brasil",
        "seleção brasileira",
        "selecao brasileira",
        "sportv",
        "ge",
        "cazétv",
        "cazetv",
        "globo",
        "esporte",
        "fifa",
        "world cup",
    )

    def normalize(self, text: str) -> str:
        decomposed = unicodedata.normalize("NFD", text.lower())
        return "".join(char for char in decomposed if unicodedata.category(char) != "Mn")

    def is_football_related(self, text: str) -> bool:
        normalized = self.normalize(text)
        return any(self.normalize(keyword) in normalized for keyword in self.KEYWORDS)
