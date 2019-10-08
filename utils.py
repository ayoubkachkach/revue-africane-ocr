import re
import unicodedata

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
        # "œ":'oe',
    }
    # remove control characters not supported by XML.
    text = strip_chars(text)
    text = unicodedata.normalize('NFC', text.strip())
    text = re.sub(r'(\n\n )+', ' ', text)
    text = re.sub(r'([a-zA-Zàâçéèêëîïôûùüÿñæœ,;-])(\n)+([^\s])', r'\1 \3', text)
    return text.translate(str.maketrans(translation_dict))