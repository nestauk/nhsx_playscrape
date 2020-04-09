import time
import json
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import ElementNotInteractableException, ElementClickInterceptedException
from bs4 import BeautifulSoup
from datetime import datetime as dt


def is_date(text):
    try:
        date = dt.strptime(text, '%B %d, %Y')
    except ValueError:
        return False
    return True


def click_live(driver, element_type, text):
    for e in driver.find_elements_by_xpath(f'//{element_type}[text()="{text}"]'):
        try:
            e.click()
        except (ElementNotInteractableException,
                ElementClickInterceptedException):
            continue
        time.sleep(1.5)


def open_browser(driver_location, url):
    driver = webdriver.Chrome(driver_location)
    driver.get(url)
    time.sleep(5)
    return driver


def crawl(driver, n_pages, sleep):
    html = driver.find_element_by_tag_name('html')
    for n in range(0, n_pages):
        # Iterate until end of the page is reached
        source_length = len(driver.page_source)
        new_length = source_length + 1
        while new_length > source_length:
            source_length = new_length
            click_live(driver, 'button', 'Full Review')
            html.send_keys(Keys.END)
            time.sleep(sleep)
            new_length = len(driver.page_source)
        click_live(driver, 'span', 'Show More')


def scrape(source):
    soup = BeautifulSoup(source, features="html.parser")
    for element in soup.find_all('div'):
        _rating = element.get('aria-label')
        if (_rating is not None and
            _rating.endswith('stars out of five stars') and
            len(_rating) == 31):
            break
    _class = element.parent.parent.parent.parent.parent.parent['class']
    parents = soup.find_all('div', {'class': _class})
    print('--> Found', len(parents)/2, 'reviews')
    reviews = []
    for parent in parents:
        _review = []
        rating = None
        for child in parent.findChildren():
            _rating = child.get('aria-label')
            if _rating is not None and _rating.endswith('stars out of five stars'):
                rating = _rating[6]
            if len(child.findChildren()) > 0 or child.text == '':
                continue
            _review.append(child.text)
        if len(_review) == 0:
            continue
        if is_date(_review[-1]):  # delete reply fields
            _review = _review[0:-2]
            if len(_review) == 0:
                continue
        if not is_date(_review[1]):
            continue
        data = dict(reviewer=_review[0], date=_review[1], rating=rating, review='')
        if len(_review) > 2:
            data['review'] = _review[-1]
        reviews.append(data)
    return [r for i, r in enumerate(reviews) if i % 2 == 0]


def crawl_and_scrape(driver_location, app_id, n_pages=5, sleep=2):
    driver = open_browser(driver_location,
                          url=('https://play.google.com/store/apps/'
                               f'details?id={app_id}&showAllReviews=true'))
    crawl(driver, n_pages, sleep)
    source = driver.page_source
    title = driver.title
    driver.close()
    #service.stop()
    reviews = scrape(source)
    return reviews, title


if __name__ == "__main__":
    driver_location = '/Users/jklinger/Downloads/chromedriver81'
    #driver_location = '/Users/jklinger/Downloads/msedgedriver'
    for app_id in (#'com.nhs.online.nhsonline',
                   #'px.app.systmonline',
                   #'health.livi.android',
                   #'air.com.sensely.asknhs',
                   #'net.iplato.mygp',
                   #'uk.co.patient.patientaccess',
                   'com.babylon',):
                   #'com.pushdr.application'):
        print(app_id)
        reviews, title = crawl_and_scrape(driver_location, app_id, n_pages=20)
        title = title.split(' - Apps on Google Play')[0]
        data = {'title': title, 'reviews': reviews}
        with open(f'{app_id}.json', 'w') as f:
            f.write(json.dumps(data))
