import os
import time
import pytest
from dataload.import_to_elasticsearch import import_to_elasticsearch
from selenium import webdriver

prefix = 'https://raw.githubusercontent.com/OpenDataServices/grantnav-sampledata/c555725bf1aa1e2d22fb69dd99c1831feff7ecbd/'


@pytest.fixture(scope="module")
def browser(request):
    browser = webdriver.Firefox()
    browser.implicitly_wait(3)
    request.addfinalizer(lambda: browser.quit())
    return browser


@pytest.fixture(scope="module")
def server_url(request, live_server):
    if 'CUSTOM_SERVER_URL' in os.environ:
        return os.environ['CUSTOM_SERVER_URL']
    else:
        return live_server.url


@pytest.fixture(scope="module")
def dataload():
    import_to_elasticsearch([prefix + 'wolfson.json',
                             prefix + '360_giving_LBFEW_2010_2015.xlsx',
                             prefix + 'IndigoTrust_360giving.csv'], clean=True)
    #elastic search needs some time to commit its data
    time.sleep(2)


def test_home(dataload, server_url, browser):
    browser.get(server_url)
    assert 'GrantNav' in browser.find_element_by_tag_name('body').text


def test_search(dataload, server_url, browser):
    browser.get(server_url)
    browser.find_element_by_class_name("large-search-icon").click()
    assert 'Total: 4,764' in browser.find_element_by_tag_name('body').text
    assert 'Lloyds Bank Foundation for England and Wales (4,116)' in browser.find_element_by_tag_name('body').text
    assert 'Wolfson Foundation (379)' in browser.find_element_by_tag_name('body').text


def test_bad_search(dataload, server_url, browser):
    browser.get(server_url)
    browser.find_element_by_name("text_query").send_keys(" £s:::::afdsfas")
    browser.find_element_by_class_name("large-search-icon").click()
    assert 'Search input is not valid' in browser.find_element_by_tag_name('body').text
