"""Extract text from PDF files and organize in XML."""
import argparse
import glob
import os
import re
from lxml import etree as ET
import unicodedata
import pdf2image
import pytesseract
import time
from PIL import Image
from utils import clean_text, PdfParser
import logging
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from collections import namedtuple


PARSER = argparse.ArgumentParser(description='Make document dataset.')
PARSER.add_argument('--path', required=True)
PARSER.add_argument('--threads', type=int, default=4)
PARSER.add_argument('--lang', default='fra')

logging.basicConfig(level=logging.DEBUG, filename='scraper.log', format='%(asctime)s %(levelname)s:%(message)s')

# Set max threads to be used by tesseract on one page to 1
os.environ['OMP_THREAD_LIMIT'] = '1'

XMLTag = namedtuple('XMLTag', ('tag_name', 'text'))

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

def read_pdfs(path):
    for path2pdf in path.glob('*pdf'):
        with open(path2pdf, 'rb') as pdf:
            filename, _ = os.path.splitext(path2pdf.name)
            yield filename, pdf, pdf.read()


def pdf_to_pil(pdf, dpi=300):
    """Converts pdf in pdf_path to a list of PIL images.
    
    Args:
        pdf: Bytes of PDF to convert.
        dpi: (int) Desired DPI of converted images.
    Returns:
        List of PIL images, each holding a page of the pdf.
    """
    logging.log(logging.INFO, "Converting pdf to images ...")
    s = time.time()
    images = pdf2image.convert_from_bytes(pdf, dpi=dpi, fmt='jpg', thread_count=4)
    e = time.time()
    logging.log(logging.INFO, "took %.2fs." % (e - s))
    return images


def add_pages(texts):
    return [f'\n[p.{page_num+1}]\n{text}' for page_num, text in enumerate(texts)]


def join_hyphenated_words(texts):
    return [re.sub(r'-\n(\w+ *)', r'\1\n', text) for text in texts]


def extract_volume_info(tag_to_value):
    vol, year = None, None
    for tag, value in tag_to_value:
        if tag != 'title':
            continue
        
        m = re.match('Volume_(.*)_(.*)', value)
        if not m:
            return tag_to_value
        vol = m.group(1)
        year = m.group(2)

    return tag_to_value + (XMLTag('vol', vol), XMLTag('year', year),)

def get_table_of_contents(pdf):
    """ Returns table of contents as string."""
    parsed_pdf = PdfParser(pdf)
    output_format = '%-5s  %s'
    toc_items = []
    if not parsed_pdf.getDestinationPageNumbers():
        return 'N/A'

    page_to_title = sorted([(v,str(k)) for k,v in parsed_pdf.getDestinationPageNumbers().items()])
    for page, title in page_to_title:
        toc_items.append(output_format % (page + 1, title))
    
    return '\n'.join(toc_items)


def scrape(path, text_processors, xml_constructors, lang='fra', threads=10):
    """Scrapes text from all pdfs in path. The text scraped is then given to functions in text_processors successively.
    args:
        path: pathlib.Path object holding path to folder containing pdfs to scrape.
        text_processors: list of functions taking 1 argument (list of texts scraped from pdf) and returning
            a list of processed texts.
        lang: string containing ISO 639-1 representation of language of the pdf to be scraped.
    returns:
        List of XML 'document' tags.
        Each document tag has 3 children: an artificial id, a title (filename) and the content
        of the pdf. Each text scraped is separated by an indicator of the page number the text was scraped from.
        The indicator is in the form "[p.X]" where x is the page number. This indicator appears at the end of
        the text from said page.
    """
    try:
        logging.log(logging.INFO, 'Reading PDFs ...')
        for document_id, (filename, pdf, pdf_bytes) in enumerate(read_pdfs(path)):
            if os.path.isfile(Path(f'{filename}.xml')):
                logging.log(logging.INFO, f'Skipping {filename} as it already exists.')
                continue

            logging.log(logging.INFO, f'Reading PDF {filename}')
            table_of_contents = get_table_of_contents(pdf)
            # Convert pdf to images
            images = pdf_to_pil(pdf_bytes)

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
            filename = clean_text(filename)
            tag_to_value = (
                XMLTag(tag_name='id', text=str(document_id)), 
                XMLTag(tag_name='title', text=filename),
                XMLTag(tag_name='body', text=clean_text(body)),
                XMLTag(tag_name='toc', text=clean_text(table_of_contents))
            )
            for xml_constructor in xml_constructors:
                tag_to_value = xml_constructor(tag_to_value)

            document_tag = to_xml(root='document', tag_to_value=tag_to_value)
            tree = ET.ElementTree(document_tag)        
            with open(f'{filename}.xml', 'wb') as f:
                tree.write(f, encoding='utf-8', pretty_print=True)

            logging.log(logging.INFO, f'Document {document_id + 1} done.')

    except KeyboardInterrupt:
        logging.log(logging.INFO, 'Program stopped by user ... returning XMLs created so far to file')
    except Exception as e:
        print(e)
    finally:
        return []


if __name__ == '__main__':
    args = PARSER.parse_args()

    input_path = Path(args.path)

    document_tags = scrape(
        input_path,
        text_processors=[add_pages, join_hyphenated_words],
        xml_constructors=[extract_volume_info],
        lang=args.lang,
        threads=args.threads)