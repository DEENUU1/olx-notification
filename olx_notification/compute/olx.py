import requests
from typing import List, Dict, Optional, Tuple
import json
from dataclasses import dataclass
import datetime
import os
import smtplib

# Check README.md for a guide to how to get an url for specified category, location and other filters that you need
URLS_TO_SCRAPE = {
    "Łódź mieszkania wynajem": "https://www.olx.pl/api/v1/offers/?offset=40&limit=40&category_id=15&sort_by=created_at%3Adesc&filter_refiners=spell_checker&sl=18ae25cfa80x3938008f",

}

# Email configuration
# Add env variables to AWS Lambda environment variables - guide in README.md
# This configuration is used for sending emails by using Gmail
smtp_server = "smtp.gmail.com"
smtp_port = 587
smtp_username = os.environ["SMTP_USERNAME"]
smtp_password = os.environ["SMTP_PASSWORD"]
from_email = os.environ["FROM_EMAIL"]
to_email = os.environ["TO_EMAIL"]


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
    price: Optional[Price] = None
    params: Optional[List[Params]] = None


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


def send_email(body: str, subject: str) -> None:
    message = f"Subject: {subject}\n\n{body}"

    with smtplib.SMTP(smtp_server, smtp_port) as smtp:
        smtp.starttls()
        smtp.login(smtp_username, smtp_password)
        smtp.sendmail(from_email, to_email, message)


def parse_params(params) -> Tuple[List[Optional[Params]], Optional[Price]]:
    params_list = []
    price = None

    for param in params:
        key, label = param["key"], param["value"]["label"]
        if key == "price":
            price = Price(
                value=param.get("value", {}).get("value"),
                currency=param.get("value", {}).get("currency"),
                negotiable=param.get("value", {}).get("negotiable")
            )

        params_list.append(
            Params(
                name=key,
                label=label
            )
        )

    return params_list, price


def parse_data(data: List[Dict]) -> List[Object]:
    objects = []
    for item in data:
        for offer in item["data"]:
            params, price = parse_params(offer["params"])

            object_ = Object(
                url=offer["url"],
                title=offer["title"],
                created_time=convert_time(offer["created_time"]),
                city=offer.get("location", {}).get("city", {}).get("name"),
                district=offer.get("location", {}).get("district", {}).get("name"),
                region=offer.get("location", {}).get("region", {}).get("name"),
                price=price,
                params=params
            )
            objects.append(object_)

    return objects


def convert_time(time: str) -> datetime.datetime:
    return datetime.datetime.strptime(time, "%Y-%m-%dT%H:%M:%S%z")


def scrape():
    for name, url_to_scrape in URLS_TO_SCRAPE.items():
        print(f"Start scraping {name}...")
        scraper = GetOlxContent(url_to_scrape)
        data = scraper.fetch_content()
        objects = parse_data(data)

        body = ""
        for idx, object_ in enumerate(objects):
            body += f"{idx}. {object_.title} - {object_.url} - {object_.created_time} \n"
            body += f"Localization: {object_.city}, {object_.region}, {object_.district} \n"
            body += f"Price: {object_.price.value} {object_.price.currency} \n"
            params = "\n".join([f"{param.name}: {param.label}" for param in object_.params])
            body += f"Params: {params} \n"
            body += "\n\n\n"

        send_email(body=body, subject=name)
