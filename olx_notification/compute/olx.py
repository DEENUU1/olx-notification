import requests
from typing import List, Dict, Optional
import json
from dataclasses import dataclass
import datetime

# Check README.md for a guide to how to get a url for specified category, location and other filters that you need
URLS_TO_SCRAPE = {
    "Łódź mieszkania wynajem": "https://www.olx.pl/api/v1/offers/?offset=40&limit=40&category_id=15&sort_by=created_at%3Adesc&filter_refiners=spell_checker&sl=18ae25cfa80x3938008f",

}


@dataclass
class Params:
    name: str
    label: str


@dataclass
class Price:
    value: float
    currency: str
    negotiable: bool


@dataclass
class Object:
    url: str
    title: str
    created_time: datetime.datetime
    city: Optional[str] = None
    district: Optional[str] = None
    region: Optional[str] = None


class GetOlxContent:

    def __init__(self, url: str):
        self.main_url = url

    def fetch_content(self) -> List[Dict]:
        result = []

        while self.main_url:
            try:
                response = requests.get(self.main_url)
                if response.status_code == 200:
                    json_data = json.loads(response.content)
                    if not json_data:
                        break

                    # Save scraped data to JSON file
                    result.append(json_data)

                    self.main_url = self.get_next_page_url(json_data)

            except Exception as e:
                print(e)

        return result

    @staticmethod
    def get_next_page_url(json_data) -> Optional[str]:
        links = json_data.get("links")
        if links:
            next_page = links.get("next")
            if next_page:
                return next_page.get("href")

        return None

# def parse_data(data: List[Dict]) -> List[]
