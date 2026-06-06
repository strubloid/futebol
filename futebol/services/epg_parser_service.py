import xml.etree.ElementTree as ET
from datetime import datetime

from futebol.domain.models.epg_program import EpgProgram


class EpgParserService:
    def parse(self, xmltv_content: str) -> list[EpgProgram]:
        root = ET.fromstring(xmltv_content)
        programs: list[EpgProgram] = []
        for programme in root.findall("programme"):
            title_element = programme.find("title")
            desc_element = programme.find("desc")
            programs.append(
                EpgProgram(
                    channel_id=programme.attrib.get("channel", ""),
                    title=title_element.text
                    if title_element is not None and title_element.text
                    else "",
                    start=self._parse_xmltv_datetime(programme.attrib.get("start")),
                    stop=self._parse_xmltv_datetime(programme.attrib.get("stop")),
                    description=desc_element.text if desc_element is not None else None,
                    language=title_element.attrib.get("lang")
                    if title_element is not None
                    else None,
                )
            )
        return programs

    def _parse_xmltv_datetime(self, value: str | None) -> datetime | None:
        if not value:
            return None
        compact = value.split()[0]
        try:
            return datetime.strptime(compact, "%Y%m%d%H%M%S")
        except ValueError:
            return None
