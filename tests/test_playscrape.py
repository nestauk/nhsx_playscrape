from playscrape import is_date, validate_app_id, validating_echo
from playscrape import requests

import pytest


@pytest.mark.parametrize(
    "date,result",
    [
        ("August 23, 2021", True),
        ("January 21, 1341", True),
        ("June 1, 1997", True),
        ("foo bar, baz", False),
        ("Nov 23, 1234", False),
        ("January 21, abcd", False),
    ],
)
def test_is_date(date, result):
    assert is_date(date) is result


def test_validating_echo(capsys):
    validating_echo("foo", "bar")
    captured = capsys.readouterr()
    assert captured.out == "Validating foo ... bar\n"


def test_validate_app_id_good(capsys):
    validate_app_id("com.nhs.online.nhsonline")
    captured = capsys.readouterr()
    assert (
        captured.out
        == "Validating com.nhs.online.nhsonline ... \rValidating com.nhs.online.nhsonline ... ✅\n"
    )


def test_validate_app_id_bad(capsys):
    with pytest.raises(requests.exceptions.HTTPError):
        validate_app_id("foo.bar.baz")
    captured = capsys.readouterr()
    assert captured.out == "Validating foo.bar.baz ... \rValidating foo.bar.baz ... ❌\n"
