"""Utils for scraping the Google play store."""
import json
import time
from contextlib import contextmanager
from datetime import datetime as dt
from pathlib import Path
from typing import Any, List

from bs4 import BeautifulSoup
from bs4 import element as bs4_element

from cachetools import cached

import click

import requests

from selenium import webdriver
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    ElementNotInteractableException,
)
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote import webelement


PLAY_URL = "https://play.google.com/store/apps/details?id={app_id}&showAllReviews=true"
SLEEP_TIME = 2
TENACITY = 10
_PATH_TO_HERE = Path(__file__).parent
HTML_PATH = _PATH_TO_HERE / "html_cache"
DATA_PATH = _PATH_TO_HERE / "data"
CACHE = {}


def is_date(text: str, date_format: str = "%B %d, %Y") -> bool:
    """Determines whether the given text conforms to the expected date format."""
    try:
        dt.strptime(text, date_format)
    except ValueError:
        return False
    return True


@cached(cache=CACHE, key=str)  # Don't click elements that you've already clicked!
def _click_element(element: webelement.WebElement) -> bool:
    """Click this element and wait if it worked."""
    try:
        element.click()
    except (ElementNotInteractableException, ElementClickInterceptedException):
        return False
    time.sleep(SLEEP_TIME)  # Give the javascript and I/O time to load
    return True


def click_elements(driver: webdriver.Chrome, element_type: str, text: str) -> None:
    """Click on every element of type `element_type` with text value `text`."""
    for element in driver.find_elements(By.XPATH, f'//{element_type}[text()="{text}"]'):
        success = _click_element(element)
        # Delete the element from the cache if no success, to offer the chance to
        # succeed again in the future!
        if not success:
            del CACHE[str(element)]


@contextmanager
def open_browser(driver_location: str, url: str) -> webdriver.Chrome:
    """Open up a new browser at the provided URL."""
    driver = webdriver.Chrome(service=Service(driver_location))
    driver.get(url)
    time.sleep(3 * SLEEP_TIME)
    yield driver
    driver.close()


def expand_reviews(driver: webdriver.Chrome, max_scrolls: int) -> None:
    """Scroll 'pages' of the current website into memory, and expand reviews."""
    html = driver.find_element(By.TAG_NAME, "html")
    # Iterate until end of the page is reached, or max_scrolls exceeded
    found_the_end = False
    for ipage in range(max_scrolls):
        click.secho(f"\tOn review 'page' number {ipage}.")
        html_length = len(driver.page_source)
        # Note that this is done TENACITY times
        # since scraping with Selenium is highly non-deterministic. This doesn't
        # particularly add much run time since _click_element is cached, but
        # it does give a more reliable yield of reviews.
        for _ in range(TENACITY):
            # Step 1: Expand all reviews
            click_elements(driver, "button", "Full Review")
            # Step 2: Expand any long reviews.
            click_elements(driver, "span", "Show More")
        # Step 3: Move the cursor to the end of the page and allow some grace for the
        # IO and javascript to get their heads together whilst the page expands.
        html.send_keys(Keys.END)
        time.sleep(SLEEP_TIME)
        # If the page has stopped expanding
        if len(driver.page_source) == html_length:
            found_the_end = True
            break
    if not found_the_end:
        click.secho(
            (
                "\tIf you would like to find more reviews you "
                "should increase max-scrolls."
            ),
            fg="red",
        )


def get_rating(element: bs4_element.Tag) -> str:
    """Get the app rating for this review"""
    rating = element.get("aria-label")
    if (
        rating is not None
        and rating.endswith("stars out of five stars")
        and len(rating) == 31
    ):
        return rating[6]
    return None


def get_element_text(element: bs4_element.Tag) -> str:
    """Get the text from this element only if it is not a parent."""
    if len(element.findChildren()) > 0:
        return None
    return element.text


def extract_review(review_container: bs4_element.Tag) -> dict:
    """Parse the review from this element."""
    container_elements = review_container.findChildren()
    # Get the only rating in the element
    for _rating in filter(bool, map(get_rating, container_elements)):
        break
    # Get all parts of the review (reviewer, date, review text)
    review_parts = list(filter(bool, map(get_element_text, container_elements)))
    # Ignore reviews without any details at all
    if len(review_parts) == 0:
        return None
    # Truncate reply fields, which end with a date
    if is_date(review_parts[-1]):
        review_parts = review_parts[0:-2]
    # Ignore reviews without any details at all
    if len(review_parts) == 0:
        return None
    # Unpack the reviewer and review date, and enforce some integrity
    reviewer = review_parts.pop(0)
    review_date = review_parts.pop(0)
    if not is_date(review_date):
        return None
    # Unpack the review text
    review_text = ""
    if review_parts:
        review_text = review_parts[-1]  # Everything else in the container is junk
    return dict(reviewer=reviewer, date=review_date, rating=_rating, review=review_text)


def parse_reviews(html_source: str) -> List[str]:
    """Write the HTML source to disk, and then parse reviews from the source."""
    soup = BeautifulSoup(html_source, features="html.parser")

    # Any element which has a rating is a review, and so we first find *any* element
    # which has a rating, and then use this to find the parent container class
    # for each review. Note that the parent container class changes dynamically
    # from page to page, and so has to be determined dynamically in this way.
    for _element in filter(get_rating, soup.find_all("div")):
        break
    parent_class = _element.parent.parent.parent.parent.parent.parent["class"]
    review_containers = soup.find_all("div", {"class": parent_class})
    return list(filter(bool, map(extract_review, review_containers)))


def expand_and_parse_reviews(
    driver_location: str, app_id: str, max_scrolls: int = 5
) -> List[str]:
    """Crawl the playstore page for the given app and scrape reviews from the source.

    Args:
        driver_location: The Chromedriver location on your local filesystem.
        app_id: The Google playstore ID of an app.
        max_scrolls: Maximum number of 'pages' of reviews to scroll back through.

    Returns:
        A list of reviews.
    """
    source_filename = HTML_PATH / f"{app_id}-source.html"
    title_filename = HTML_PATH / f"{app_id}-title"
    url = PLAY_URL.format(app_id=app_id)
    with open_browser(driver_location, url) as driver:
        expand_reviews(driver=driver, max_scrolls=max_scrolls)
        html_source = driver.page_source
        title = driver.title
    # Write to disk
    with open(source_filename, "w") as f:
        f.write(html_source)
    with open(title_filename, "w") as f:
        f.write(title.split(" - Apps on Google Play")[0])
    # Parse and return
    reviews = parse_reviews(html_source=html_source)
    return reviews


def validating_echo(app_id: str, end: str, **kwargs: Any) -> None:
    """Print a comforting message regarding the validation status of app id."""
    click.secho("Validating ", nl=False)
    click.secho(app_id, fg="blue", bold=True, nl=False)
    click.secho(f" ... {end}", **kwargs)


def validate_app_id(app_id: str) -> str:
    """Validate the app id with the playstore, raising an error if required."""
    validating_echo(app_id, "\r", nl=False)
    response = requests.get(PLAY_URL.format(app_id=app_id))
    if response.status_code != 200:
        validating_echo(app_id, "❌")
        response.raise_for_status()
    validating_echo(app_id, "✅")
    return app_id


@click.command(no_args_is_help=True)
@click.option("--driver-location", required=True, help="path/to/chromedriver")
@click.option("--app-ids", required=True, help="Comma-seperated list of app ids.")
@click.option(
    "--max-scrolls",
    default=10,
    show_default=True,
    help=(
        "The maximum number of times "
        "to scroll to the bottom of the "
        "page to fetch new reviews."
    ),
)
def playscrape(
    driver_location: str,
    app_ids: str,
    max_scrolls: int,
) -> None:
    """Crawl playstore pages for a given set of apps and scrape the reviews."""
    # Prepare arguments
    driver_location = str(Path(driver_location).expanduser())
    app_ids = app_ids.split(",")
    if app_ids == [""]:
        raise ValueError("No app-ids provided")

    # Apply validation and process each app's reviews
    for app_id in list(map(validate_app_id, app_ids)):
        click.secho("Processing ", nl=False)
        click.secho(app_id, fg="blue", bold=True)
        start = time.time()
        reviews = expand_and_parse_reviews(
            driver_location=driver_location,
            app_id=app_id,
            max_scrolls=max_scrolls,
        )
        click.secho("\tFound ", nl=False)
        click.secho(str(len(reviews)), fg="blue", nl=False)
        click.secho(" reviews")
        with open(HTML_PATH / f"{app_id}-title") as f:
            title = f.read()
        data = {"title": title, "reviews": reviews}
        with open(DATA_PATH / f"{app_id}.json", "w") as f:
            f.write(json.dumps(data))
        click.secho("\t%.2f seconds to process %s" % ((time.time() - start), app_id))
    click.secho("Raw html written to ", nl=False)
    click.secho(str(HTML_PATH), fg="blue")
    click.secho("Processed data written to ", nl=False)
    click.secho(str(DATA_PATH), fg="blue")


if __name__ == "__main__":
    playscrape()
