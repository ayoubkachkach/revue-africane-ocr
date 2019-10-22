import requests
import bs4
import re
import zipfile
import io
import os
from scraper import to_xml, scrape

missing_vols = [str(i) for i in range(67, 107)]
missing_vols += ['61', '55', '54', '51']

################################################################
print("Getting PDFs from links ...")
url = 'http://www.algerie-ancienne.com/livres/Revue/'
html = requests.get(url).content
soup = bs4.BeautifulSoup(html, 'lxml')
# Get all links to folders
for link in soup.findAll('a', attrs={'href': re.compile("[0-9]*_([0-9]*|fin)/")}):
    if int(link.get('href').split('_')[0]) < 51:
        continue

    absolute_url = url + link.get('href')
    zip_page = requests.get(absolute_url).content
    soup = bs4.BeautifulSoup(zip_page, 'lxml')
    # Get all zip files in folder
    for link in soup.findAll('a', attrs={'href': re.compile(r".*_(\d\d)\.zip")}):
        zip_link = link.get('href')
        vol = re.compile(r".*_\d{2,3}\.zip").match(zip_link).group(1).replace('.', '_')
        if vol not in missing_vols:
            print('Skipping vol %s' % vol)
            continue

        #Download zip file
        r = requests.get(absolute_url + '/' + link.get('href'))
        z = zipfile.ZipFile(io.BytesIO(r.content))
        z.extractall(path='docs/')