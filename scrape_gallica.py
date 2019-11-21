import requests
import zipfile
import io
from selenium import webdriver
from scrapy.http import TextResponse
import pandas as pd
import re
import time
import bs4
from lxml import etree as ET
from utils import clean_text
from scraper import to_xml, scrape
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
import os
import time

def try_getting_element(driver, element, by):
    try:
        button = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((by, element))
        ).click()
        # button.click()
    except Exception as e:
        print(e)
        print('Found nothing!')
        driver.save_screenshot('screenshot_%s.png' % time.time())
        return None        

    return button


def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False

if __name__ == '__main__':
    driver = webdriver.PhantomJS('./phantomjs')
    root_node = ET.Element('documents')
    driver.set_window_size(1900,1800)

    print("Getting RAW txt from links ...")
    df = pd.read_csv('revue_africaine_links.csv', sep=' ', index_col='volume')
    # Remove missing entries with missing links
    df = df[df['link'].str.startswith('https')]
    # Initialize HTML ids for selenium
    BUTTON_ID = 'icon-download'
    TXT_CHECKBOX_ID = 'texteBrut'
    TERMS_CHECKBOX_ID = 'checkboxes-0'
    # Initialize HTML IDs to scrape with
    DATE_REGEX = re.compile(r"(Date d'édition|Publication date) : (.*)")
    PUBLISHER_REGEX = re.compile(r'(Éditeur|Publisher) : (.*)')
    PAGE_REGEX = re.compile(r'(Nombre de pages|Number of pages): (.*)')
    SPLIT_REGEX = re.compile(
        r"((The text displayed may contain some errors)|(Le texte affiché peut comporter un certain nombre d'erreurs))")
    field_to_regex = {
        'date': DATE_REGEX,
        'publisher': PUBLISHER_REGEX,
        'pages': PAGE_REGEX}
    zzz = 2  # Sleeping time between accessing HTML components
    for vol, row in df.iterrows():
        vol = str(vol).replace('.', '_')
        PATH = 'xmls/volume_%s' % (vol)
        print('Getting volume %s' % vol)
        link = row['link']
        driver.get(link)

        # Get download icon and click
        download_icon = try_getting_element(driver, BUTTON_ID, By.ID)

        # Select text checkbox and click
        txt_button = try_getting_element(driver, TXT_CHECKBOX_ID, By.ID)

        # Select accept terms checkbox and click
        terms_checkbox = try_getting_element(driver, TERMS_CHECKBOX_ID, By.ID)

        # Select download button and click
        download_button = try_getting_element(driver, "//button[contains(.,'Download')]", By.XPATH)

        # Switch to newly opened window containing text to scrape
        driver.switch_to.window(driver.window_handles[1])
        time.sleep(zzz * 4)
        # Get HTML of current window
        soup = bs4.BeautifulSoup(driver.page_source, "lxml")
        paragraphs = soup.find_all('p')
        article_content = None
        field_to_value = []
        for i, p in enumerate(paragraphs):
            article = {}
            paragraph = p.text
            # Reached end of header
            if SPLIT_REGEX.match(paragraph):
                article_content = ' '.join(
                    [paragraph.text for paragraph in paragraphs[i + 1:]])
                field_to_value.append(('body', article_content))
                break

            for field, regex in field_to_regex.items():
                match_result = regex.match(paragraph)
                if match_result:
                    field_to_value.append((field, match_result.group(2)))
                    break

        doc_node = to_xml('document', field_to_value)
        root_node.append(doc_node)
        tree = ET.ElementTree(doc_node)
        with open(PATH, 'wb') as f:
            tree.write(f, encoding='utf-8', pretty_print=True)
        driver.close()
        driver.switch_to.window(driver.window_handles[0])

    driver.close()
