import requests
from typing import List, Dict, Optional, Tuple
import json
from dataclasses import dataclass, asdict
import datetime
import os
import smtplib
import pandas

# Check README.md for a guide to how to get an url for specified category, location and other filters that you need
URLS_TO_SCRAPE = {
    "Łódź mieszkania wynajem": "https://www.olx.pl/api/v1/offers/?offset=40&limit=40&category_id=15&sort_by=created_at%3Adesc&filter_refiners=spell_checker&sl=18ae25cfa80x3938008f",

}

# Email configuration
# Add env variables to AWS Lambda environment variables - guide in README.md
# This configuration is used for sending emails by using Gmail
smtp_server = "smtp.gmail.com"
smtp_port = 587
# smtp_username = os.environ["SMTP_USERNAME"]
# smtp_password = os.environ["SMTP_PASSWORD"]
# from_email = os.environ["FROM_EMAIL"]
# to_email = os.environ["TO_EMAIL"]

# The number of days from which offers are to come
DAY_DELAY: int = 1


@dataclass
class Params:
    name: str
    label: str


@dataclass
class Price:
    value: float
    currency: str


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
        # links = json_data.get("links")
        # if links:
        #     next_page = links.get("next")
        #     if next_page:
        #         return next_page.get("href")

        return None


def send_email(body: str, subject: str) -> None:
    message = f"Subject: {subject}\n\n{body}"
    message = message.encode("utf-8")
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
                created_time=offer["created_time"],
                city=offer.get("location", {}).get("city", {}).get("name"),
                district=offer.get("location", {}).get("district", {}).get("name"),
                region=offer.get("location", {}).get("region", {}).get("name"),
                price=price,
                params=params
            )
            objects.append(object_)

    return objects


def scrape() -> bool:
    for name, url_to_scrape in URLS_TO_SCRAPE.items():
        print(f"Start scraping {name}...")
        scraper = GetOlxContent(url_to_scrape)
        data = scraper.fetch_content()
        objects = parse_data(data)

        dicts = []
        for idx, object_ in enumerate(objects):
            params_dict = {}
            for param in object_.params:
                params_dict[param.name] = param.label

            dicts.append(
                {
                    "url": object_.url,
                    "title": object_.title,
                    "created_time": object_.created_time,
                    "city": object_.city,
                    "district": object_.district,
                    "region": object_.region,
                    "price_val": object_.price.value if object_.price else None,
                    "price_cur": object_.price.currency if object_.price else None,
                    **params_dict,
                }
            )

        df = pandas.DataFrame(dicts)
        df.to_excel("olx.xlsx", index=False)

        # send_email(body=body, subject=name)
    return True

def lambda_handler(event, context):
    return {
        'statusCode': 200,
        'body': json.dumps({"message": "Scraped", "status": scrape()})
    }


scrape()