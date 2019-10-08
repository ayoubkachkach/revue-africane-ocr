import requests, zipfile, io
from selenium import webdriver
from scrapy.http import TextResponse
import pandas as pd
import numpy as np
import re
import time
import bs4
from lxml import etree as ET
from utils import clean_text
from scraper import to_xml, scrape

if __name__ == '__main__':
    root_node = ET.Element('documents')

    print("Getting RAW txt from links ...")
    df = pd.read_csv('revue_africaine_links.csv', sep=' ', index_col='volume')
    df = df[df['link'].str.startswith('https')]
    # Initialize HTML ids for selenium
    BUTTON_ID = 'icon-download'
    TXT_CHECKBOX_ID = 'texteBrut'
    TERMS_CHECKBOX_ID = 'checkboxes-0'
    # Initialize HTML IDs to scrape with
    DATE_REGEX = re.compile(r"(Date d'édition|Publication date) : (.*)")
    PUBLISHER_REGEX = re.compile(r'(Éditeur|Publisher) : (.*)')
    PAGE_REGEX = re.compile(r'(Nombre de pages|Number of pages): (.*)')
    SPLIT_REGEX = re.compile(r"((The text displayed may contain some errors)|(Le texte affiché peut comporter un certain nombre d'erreurs))")
    field_to_regex = {
        'date': DATE_REGEX,
        'publisher': PUBLISHER_REGEX,
        'pages': PAGE_REGEX}
    zzz = 2  # Sleeping time between accessing HTML components
    driver = webdriver.Firefox('/home/ayoub/projects/revue-africane-ocr/')
    for vol, row in df.iterrows():
        link = row['link']
        driver.get(link)
        time.sleep(zzz)
        # Get download icon and click
        download_icon = driver.find_element_by_id(BUTTON_ID)
        download_icon.click()
        time.sleep(zzz)
        # Select text checkbox and click
        txt_button = driver.find_element_by_id(TXT_CHECKBOX_ID)
        txt_button.click()
        # Select accept terms checkbox and click
        terms_checkbox = driver.find_element_by_id(TERMS_CHECKBOX_ID)
        terms_checkbox.click()
        # Select download button and click 
        download_button = driver.find_element_by_xpath("//button[contains(.,'Download')]")
        download_button.click()
        time.sleep(zzz)
        # Switch to newly opened window containing text to scrape
        driver.switch_to.window(driver.window_handles[1])
        time.sleep(zzz*1.5)
        # Get HTML of current window
        html = driver.page_source
        soup = bs4.BeautifulSoup(html, "lxml")
        paragraphs = soup.find_all('p')
        article_content = None
        field_to_value = []
        for i, p in enumerate(paragraphs):
            article = {}
            paragraph = p.text
            # Reached end of header
            if SPLIT_REGEX.match(paragraph):
                article_content = ' '.join([p.text for p in paragraphs[i+1:]])
                field_to_value.append(('body', article_content))
                break

            for field, regex in field_to_regex.items():
                match_result = regex.match(paragraph)
                if match_result:
                    field_to_value.append((field, match_result.group(1)))
                    break

        doc_node = to_xml('document', field_to_value)
        root_node.append(doc_node)
        driver.close()
        driver.switch_to.window(driver.window_handles[0])
    ################################################################
    print("Getting PDFs from links ...")
    url = 'http://www.algerie-ancienne.com/livres/Revue/'
    soup = bs4.BeautifulSoup(url)
    for link in soup.findAll('a', attrs={'href': re.compile("[0-9]{2,}_[0-9]{2,}/")}):
        link = requests.get(url + link.get('href'))
        for link in soup.findAll('a', attrs={'href': re.compile(r".*_(\d\d)\.zip")}):
            zip_link = link.get('href')
            vol = re.compile(r".*_(\d\d)zip").match(zip_link).group(1)
            r = requests.get(link.get('href'))
            z = zipfile.ZipFile(io.BytesIO(r.content))
            z.extractall(path='docs/volume_%s.pdf' % vol)

    ################################################################
    print("Scraping PDFs ...")
    document_tags = scrape('docs/', 'pdf')
    for tag in document_tags:
        root_node.append(tag)

    tree = ET.ElementTree(root_node)
    with open('output.xml', 'wb') as f:
        tree.write(f, encoding='utf-8', pretty_print=True)
