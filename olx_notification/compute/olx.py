import requests
from typing import List, Dict, Optional, Tuple, Generator
import json
from dataclasses import dataclass
import datetime
import os
import smtplib
import pandas
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

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
    """
    The `GetOlxContent` class is used to fetch content from the OLX website.

    Attributes:
        main_url (str): The main URL of the OLX website.

    Methods:
        fetch_content() -> List[Dict]: Fetches the content from the OLX website and returns it as a list of dictionaries.
        get_next_page_url(json_data) -> Optional[str]: Extracts the URL of the next page from the given JSON data.

    """

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

                    # Add scraped data to list
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


def send_email(filename: str, subject: str) -> None:
    """
    Sends an email with an attachment using the given parameters. The email is sent from the 'from_email' address to the 'to_email' address.
    """
    message = MIMEMultipart()
    message["From"] = from_email
    message["To"] = to_email
    message["Subject"] = subject

    with open(filename, "rb") as file:
        attachment = MIMEApplication(file.read())
        attachment.add_header("Content-Disposition", "attachment", filename=filename)
        message.attach(attachment)

    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(smtp_username, smtp_password)
        server.sendmail(from_email, to_email, message.as_string())


def parse_params(params) -> Tuple[List[Optional[Params]], Optional[Price]]:
    """
    Parse the given params to create a list of Params objects and extract the Price object.

    :param params: A list of dictionaries representing the params.
    :return: A tuple containing the list of Params objects and the Price object.
    """
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


def parse_data(data: List[Dict]) -> Generator[Object, None, None]:
    """
    This method `parse_data` takes a list of dictionaries as input and returns a generator object. Each dictionary in the input list represents an item, and within that item, there is a nested "data" key which contains a list of offers. Each offer is further processed using the `parse_params` function to extract parameters and price.

    :param data: A list of dictionaries representing items, with each item containing a "data" key which contains a list of offers.
    :return: A generator object that yields instances of the Object class.
    """
    for item in data:
        for offer in item["data"]:
            params, price = parse_params(offer["params"])

            yield Object(
                url=offer["url"],
                title=offer["title"],
                created_time=offer["created_time"],
                city=offer.get("location", {}).get("city", {}).get("name"),
                district=offer.get("location", {}).get("district", {}).get("name"),
                region=offer.get("location", {}).get("region", {}).get("name"),
                price=price,
                params=params
            )


def scrape(name, url_to_scrape) -> None:
    """
    Scrape data from a given URL and save it to an Excel file.

    :param name: The name of the scrape.
    :param url_to_scrape: The URL to scrape data from.
    :return: None
    """
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
                "city": object_.city if object_.city else None,
                "district": object_.district if object_.district else None,
                "region": object_.region if object_.region else None,
                "price_val": object_.price.value if object_.price else None,
                "price_cur": object_.price.currency if object_.price else None,
                **params_dict,
            }
        )

    df = pandas.DataFrame(dicts)
    df.to_excel("/tmp/olx.xlsx", index=False)

    send_email(filename="/tmp/olx.xlsx", subject=name)


def run() -> bool:
    """
    Executes the scraping process for each URL provided in the `URLS_TO_SCRAPE` dictionary.
    """
    for name, url_to_scrape in URLS_TO_SCRAPE.items():
        print(f"Start scraping {name}...")
        scrape(name, url_to_scrape)

    return True


def lambda_handler(event, context):
    return {
        'statusCode': 200,
        'body': json.dumps({"message": "Scraped", "status": run()})
    }
