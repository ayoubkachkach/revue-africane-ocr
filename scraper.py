"""Extract text from PDF files and organize in XML."""
import argparse
import glob
import os
import re
import textract
from lxml import etree as ET
import unicodedata
from pdf2image import convert_from_path
import pytesseract
import time

PARSER = argparse.ArgumentParser(description='Make article dataset.')
PARSER.add_argument('--path', required=True)

def strip_ext(filename):
    """ Strips extension from filename.
    e.g.
    >> strip_ext('example.pdf')
    >> 'example'
    """
    return re.sub(r'((.*/)*)?(.+)\..+', r'\3', filename)


def strip_chars(text, extra=u''):
    """Strip text from control characters not supported by XML."""
    remove_re = re.compile(u'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F%s]'
                           % extra)
    return remove_re.sub('', text)


def clean_text(text):
    """Normalize quotes, apostrophes and diacritics (by using combined
    characters) used in text
    """
    translation_dict = {
        '’':"'",
        '‘':"'",
        "œ":'oe',
        "_":"'",
    }
    # remove control characters not supported by XML.
    text = strip_chars(text)

    text = unicodedata.normalize('NFC', text.strip())
    text = re.sub(r'(\n\n )+', ' ', text)
    text = re.sub(r'([a-zA-Zàâçéèêëîïôûùüÿñæœ,;-])(\n)+([^\s])', r'\1 \3', text)
    return text.translate(str.maketrans(translation_dict))


def to_xml(article_id, filename, body):
    """Create xml of doc from its components.

    Args:
        id: (int)
        filename: (str) name of file.
        body: (str) content of the file.

    Returns:
        ET.Element object representing the XML node of the article.
    """
    if not body:
        print("No content for %s" % filename)

    article_node = ET.Element('article')

    id_node = ET.SubElement(article_node, 'id')
    id_node.text = str(article_id)

    filename_node = ET.SubElement(article_node, 'filename')
    filename_node.text = clean_text(filename)

    body_node = ET.SubElement(article_node, 'body')
    body_node.text = clean_text(body)

    return article_node


def tesseract_extract(filename):
    """Extracts text stores in filename.
    Returns a list of text representing the text scraped from each page in the pdf.
    """
    # Convert pdf to images

    print("Converting pdf to images ...", end=' ')
    s = time.time()
    images = convert_from_path(filename)
    e = time.time()
    print("took %.2fs." % (e - s))
    texts = []
    for page, image in enumerate(images):
        print("OCRing page %s ..." % page, end=' ')
        s = time.time()
        texts.append(pytesseract.image_to_string(image, lang='fra'))
        e = time.time()
        print("took %.2fs." % (e - s))

    return texts


if __name__ == '__main__':
    args = PARSER.parse_args()
    path = os.path.expanduser(args.path)
    print('Got %s' % path)

    filenames = glob.glob(path + "*pdf")
    print('Found %s filenames' % filenames)
    articles_tag = ET.Element('articles')
    results = []
    for article_id, filename in enumerate(filenames):
        print("Document %s --------------------------" % article_id)
        print("Running OCR ...", end=' ')
        s = time.time()
        texts = tesseract_extract(filename)  # extract text from pdf
        e = time.time()
        print("took %.2fs." % (e - s))
        body = ' '.join(texts)  # join text from pages
        print('Stripping text...')
        title = strip_ext(filename)  # keep only filename as title
        articles_tag.append(to_xml(article_id, title, body))


    tree = ET.ElementTree(articles_tag)
    with open('textract_output.xml', 'wb') as f:
        tree.write(f, encoding='utf-8', pretty_print=True)
