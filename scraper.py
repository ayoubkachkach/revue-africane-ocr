"""Extract text from PDF files and organize in XML."""
import argparse
import glob
import os
import re
import textract
from lxml import etree as ET
import unicodedata
import pdf2image
import pytesseract
import time
from PIL import Image
from utils import clean_text
import logging
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor


PARSER = argparse.ArgumentParser(description='Make document dataset.')
PARSER.add_argument('--path', required=True)
PARSER.add_argument('--threads', type=int, default=4)
PARSER.add_argument('--lang', default='fra')

logging.basicConfig(level=logging.DEBUG, filename='scraper.log', format='%(asctime)s %(levelname)s:%(message)s')

# Set max threads to be used by tesseract on one page to 1
os.environ['OMP_THREAD_LIMIT'] = '1'

def to_xml(root, tag_to_value):
    """Create xml of doc from its components.

    Args:
        root: (str) name of root tag in xml tree
        attribute_to_value: list of tuples of the form (tag, value).
    Returns:
        ET.Element object representing the XML node of the document.
    Usage:
        to_xml('doc', [('title', 'This is a title.'), ('body', 'This is a body.')])
    """
    root_node = ET.Element(root)
    for tag, value in tag_to_value:
        node = ET.SubElement(root_node, tag)
        node.text = value

    return root_node


def pdf_to_pil(pdf_path, dpi=300):
    """Converts pdf in pdf_path to a list of PIL images.
    
    Args:
        pdf_path: pathlib.Path object holding path to PDF to convert.
        dpi: (int) Desired DPI of converted images.
    Returns:
        List of PIL images, each holding a page of the pdf.
    """
    logging.log(logging.INFO, "Converting pdf to images ...")
    s = time.time()
    images = pdf2image.convert_from_path(pdf_path, dpi=dpi, fmt='png')
    e = time.time()
    logging.log(logging.INFO, "took %.2fs." % (e - s))
    return images


def get_images_from_pdfs(path):
    """Generator that converts all PDFs in path to images.
    args:
        path: pathlib.Path object holding path to folder containing pdfs to convert.
    returns:
        Generator that yields list of images of pdf to convert in every call.
    """
    for path2pdf in path.glob('*pdf'):
        print('hey')
        images = pdf_to_pil(path2pdf)
        filename, _ = os.path.splitext(path2pdf.name)
        yield (filename, images)


def add_pages(texts):
    print('here')
    return [f'\n[p.{page_num+1}]\n{text}' for page_num, text in enumerate(texts)]


def join_hyphenated_words(texts):
    print('here')
    return [re.sub(r'-\n(\w+ *)', r'\1\n', text) for text in texts]


def scrape(path, text_processors, lang='fra', threads=10):
    """Scrapes text from all pdfs in path. The text scraped is then given to functions in text_processors successively.
    args:
        path: pathlib.Path object holding path to folder containing pdfs to scrape.
        text_processors: list of functions taking 1 argument (list of texts scraped from pdf) and returning
            a list of processed texts.
        lang: string containing ISO 639-1 representation of language of the pdf to be scraped.
    returns:
        XML root whose children ('document' tags) are the pdfs found in path. 
        Each document tag has 3 children: an artificial id, a title (filename) and the content
        of the pdf. Each text scraped is separated by an indicator of the page number the text was scraped from.
        The indicator is in the form "[p.X]" where x is the page number. This indicator appears at the end of
        the text from said page.
    """
    document_tags = ET.Element('documents')
    try:
        for document_id, (folder_name, images) in enumerate(get_images_from_pdfs(path)):
            logging.log(logging.INFO, "Running OCR on document %s " % document_id)
            s = time.time()
            with ThreadPoolExecutor(threads) as executor:
                images_texts = list(executor.map(lambda x: pytesseract.image_to_string(x, lang=lang), images))

            for processor in text_processors:
                images_texts = processor(images_texts)

            # Glue text from pages together and separate
            body = ' '.join(images_texts)
            e = time.time()
            logging.log(logging.INFO, "took %.2fs." % (e - s))

            # Construct XML from scraped documents.
            tag_to_value = (('id', str(document_id)), ('title', clean_text(folder_name)), ('body', clean_text(body)))
            document_tags.append(to_xml(root='document', tag_to_value=tag_to_value))

    except KeyboardInterrupt:
        logging.log(logging.INFO, 'Program stopped by user ... returning XMLs created so far to file')
    finally:
        return document_tags


if __name__ == '__main__':
    args = PARSER.parse_args()

    input_path = Path(args.path)
    print(list(input_path.glob('*pdf')))
    documents_tag = scrape(
        input_path,
        text_processors=[add_pages, join_hyphenated_words],
        lang=args.lang,
        threads=args.threads)

    tree = ET.ElementTree(documents_tag)
    with open('output.xml', 'wb') as f:
        tree.write(f, encoding='utf-8', pretty_print=True)
    