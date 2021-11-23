# playscrape

Crawl playstore pages for a given set of apps and scrape the reviews.

## Supported python versions and operating systems

Although the tests claim coverage of python 3.7 - 3.10, and both Ubuntu and MacOS, in practice
only `python==3.9` on MacOS have been tested in anger.

## Installation

Set up a fresh environment (e.g. with `conda` or `venv`) and then:

```
pip install -r requirements.txt
```

You will also need to [download and unzip Chromedriver](https://chromedriver.chromium.org/downloads), which will normally need to the be the latest version to match the version of `Chrome` on your laptop. This can be a little fiddly especially if you have multiple versions of `Chrome` hidden away on your laptop: and I can't provide concrete instructions for this. A little trial and error will go a long way!

## Usage

Do `python playscrape.py` for instructions:

```
Usage: playscrape.py [OPTIONS]

  Crawl playstore pages for a given set of apps and scrape the reviews.

Options:
  --driver-location TEXT  path/to/chromedriver  [required]
  --app-ids TEXT          Comma-seperated list of app ids.  [required]
  --max-scrolls INTEGER   The maximum number of times to scroll to the bottom
                          of the page to fetch new reviews.  [default: 10]
  --help                  Show this message and exit.
```

For example, for the previous NHSX project, the command was:

```
python playscrape.py --driver-location=~/Downloads/chromedriver --app-ids=com.nhs.online.nhsonline,px.app.systmonline,health.livi.android,air.com.sensely.asknhs,net.iplato.mygp,uk.co.patient.patientaccess,com.babylon,com.pushdr.application
```

to run a little test, I recommend setting `max-scrolls=1` and testing just on one app:

```
python playscrape.py --driver-location=~/Downloads/chromedriver --app-ids=com.nhs.online.nhsonline --max-scrolls=1
```

## Where can I find the App ID?

Find an app on the playstore and you can determine the ID from the URL:

`https://play.google.com/store/apps/details?id={==> app_id <==}&hl=en_GB&gl=US`

e.g.

https://play.google.com/store/apps/details?id=com.nhs.online.nhsonline&hl=en_GB&gl=US


# Known issues

* The following will lead to an inconsistent number of app reviews between runs:
   * A flaky internet connection
   * Interacting manually with the automated browser.
   * Bad luck.
* Even though running `--headless` might seem like a good idea, it seems to make the system *very* unreliable (it seems to massively truncate the number of reviews, reason unknown). This is a bit of a barrier to running this in production!
* Run time is way longer than it needs to be: the best way to reduce run time would be add explicit element waiting, however would require some serious investigation since element IDs can't be determined a priori because Google generates these on-the-fly. I'm sure there's something that could be done, and it would likely reduce run time by up to 90%.
* Tests are currently limited to the very functional stuff, and there is zero coverage of the bulk of the functionality here. Doing so will require setting up Selenium in GH actions, which is a body of work in and of itself.

# Legacy features

* A notebook for the original analysis can be found under `notebooks/`, although this isn't guaranteed to be compatible with the repo as-is. Please use it for illustrative purposes only.

# Useful extensions

Some nice extensions might be:

* Make this package installable, so that `playscrape` can be used as a command line executable.
* Make the data paths customisable.
* Make the verbosity a bit more interactive.
* Get the `--headless` mode working achieving the same number of reviews as non-headless mode (for some reasons early tests found that it truncates to the first 200 reviews. Probably the answer is to enable more options but it's a painfully slow development cycle with Selenium.)
