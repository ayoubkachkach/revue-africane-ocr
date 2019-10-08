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


PARSER = argparse.ArgumentParser(description='Make document dataset.')
PARSER.add_argument('--path', required=True)
PARSER.add_argument('--mode', required=True)
SUPPORTED_FORMATS = set(['jpg', 'jpeg', 'png', 'tiff'])

def to_xml(root, attribute_to_value):
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
    for attribute, value in attribute_to_value:
        node = ET.SubElement(root_node, attribute)
        node.text = value

    return root_node


def pdf_to_pil(filename, dpi=300):
    '''Converts PDF filename to PIL images.'''
    print("Converting pdf to images ...", end=' ')
    s = time.time()
    images = pdf2image.convert_from_path(filename, dpi=dpi, fmt='png')
    e = time.time()
    print("took %.2fs." % (e - s))
    return images


def tesseract_extract(images):
    """Extracts text stores in filename.
    Returns a list of text representing the text scraped from each page in the pdf.
    """
    texts = []
    for page, image in enumerate(images):
        print("OCRing page %s ..." % page, end=' ')
        s = time.time()
        text = pytesseract.image_to_string(image, lang='fra')
        texts.append(text)
        e = time.time()
        print("took %.2fs." % (e - s))

    return texts


def get_ext(filename):
    """Checks if the file with filename is supported."""
    _, file_ext = os.path.splitext(filename)
    return file_ext[1:]


def get_images_from_path(root_folder):
    for root, dirs, files in os.walk(root_folder):
        # Ignore hidden files and folders, and files with non-supported extensions
        images_filenames = sorted([f for f in files if not f[0] == '.' and get_ext(f) in SUPPORTED_FORMATS])
        dirs[:] = [d for d in dirs if not d[0] == '.']
        # Get all images in current root folder.
        images = [Image.open('%s/%s' % (root, filename)) for filename in images_filenames]
        folder_name = root.split('/')[-1]
        yield (folder_name, images)


def get_images_from_pdf(root_folder):
    for root, dirs, files in os.walk(root_folder):
        # Ignore hidden files and folders, and files with non-supported extensions
        pdf_filenames = sorted([f for f in files if not f[0] == '.' and get_ext(f) == 'pdf'])

        dirs[:] = [d for d in dirs if not d[0] == '.']
        # Get all PDFs in current folder.
        images = [image for filename in pdf_filenames for image in pdf2image.convert_from_path('%s/%s' % (root, filename))]
        folder_name = root.split('/')[-1]
        yield (folder_name, images)


def images_to_text(document_name, images, lang='fra'):
    return [pytesseract.image_to_string(image, lang=lang) for image in images]

get_images = {'pdf': get_images_from_pdf, 'img': get_images_from_path}

def scrape(path, mode):
    document_tags = []
    for document_id, (folder_name, images) in enumerate(get_images[args.mode](args.path)):
        print("Document %s --------------------------" % document_id)
        print("Running OCR ...", end=' ')
        s = time.time()
        texts = images_to_text(folder_name, images)  # extract text from pdf
        e = time.time()
        print("took %.2fs." % (e - s))
        body = ' '.join(texts)  # join text from pages
        print('Stripping text...')
        attribute_to_value = (('id', str(document_id)), ('title', clean_text(folder_name)), ('body', clean_text(body)))
        documents_tag.append(to_xml(root='document', attribute_to_value=attribute_to_value))
        break
    return documents_tag
    # tree = ET.ElementTree(documents_tag)
    # with open('output.xml', 'wb') as f:
    #     tree.write(f, encoding='utf-8', pretty_print=True)

if __name__ == '__main__':
    args = PARSER.parse_args()
    documents_tag = scrape(args.path, args.mode)
    tree = ET.ElementTree(documents_tag)
    with open('output.xml', 'wb') as f:
        tree.write(f, encoding='utf-8', pretty_print=True)
    