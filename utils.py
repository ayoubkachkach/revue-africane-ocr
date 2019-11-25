import re
import unicodedata
import PyPDF2


class PdfParser(PyPDF2.PdfFileReader):
    def getDestinationPageNumbers(self):
        def _setup_outline_page_ids(outline, _result=None):
            if _result is None:
                _result = {}
            for obj in outline:
                if isinstance(obj, PyPDF2.pdf.Destination):
                    _result[(id(obj), obj.title)] = obj.page.idnum
                elif isinstance(obj, list):
                    _setup_outline_page_ids(obj, _result)
            return _result

        def _setup_page_id_to_num(pages=None, _result=None, _num_pages=None):
            if _result is None:
                _result = {}
            if pages is None:
                _num_pages = []
                pages = self.trailer["/Root"].getObject()["/Pages"].getObject()
            t = pages["/Type"]
            if t == "/Pages":
                for page in pages["/Kids"]:
                    _result[page.idnum] = len(_num_pages)
                    _setup_page_id_to_num(page.getObject(), _result, _num_pages)
            elif t == "/Page":
                _num_pages.append(1)
            return _result

        outline_page_ids = _setup_outline_page_ids(self.getOutlines())
        page_id_to_page_numbers = _setup_page_id_to_num()

        result = {}
        for (_, title), page_idnum in outline_page_ids.items():
            page = page_id_to_page_numbers.get(page_idnum, '???')
            result[title] = page
        return result


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
        # "œ":'oe',
    }
    # remove control characters not supported by XML.
    text = strip_chars(text)
    text = unicodedata.normalize('NFC', text.strip())
    text = re.sub(r'(\n\n )+', ' ', text)
    text = re.sub(r'([a-zA-Zàâçéèêëîïôûùüÿñæœ,;-])(\n)+([^\s])', r'\1 \3', text)
    return text.translate(str.maketrans(translation_dict))