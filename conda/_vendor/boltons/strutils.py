# -*- coding: utf-8 -*-
"""So much practical programming involves string manipulation, which
Python readily accomodates. Still, there are dozens of basic and
common capabilities missing from the standard library, several of them
provided by ``strutils``.
"""

from __future__ import print_function

import re
import sys
import uuid
import zlib
import string
import unicodedata
import collections

try:
    unicode, str, bytes, basestring = unicode, str, str, basestring
    from HTMLParser import HTMLParser
    import htmlentitydefs
except NameError:  # basestring not defined in Python 3
    unicode, str, bytes, basestring = str, bytes, bytes, (str, bytes)
    unichr = chr
    from html.parser import HTMLParser
    from html import entities as htmlentitydefs


__all__ = ['camel2under', 'under2camel', 'slugify', 'split_punct_ws',
           'unit_len', 'ordinalize', 'cardinalize', 'pluralize', 'singularize',
           'asciify', 'is_ascii', 'is_uuid', 'html2text', 'strip_ansi',
           'bytes2human', 'find_hashtags', 'a10n', 'gunzip_bytes',
           'iter_splitlines', 'indent', 'escape_shell_args',
           'args2cmd', 'args2sh', 'parse_int_list', 'format_int_list']


_punct_ws_str = string.punctuation + string.whitespace
_punct_re = re.compile('[' + _punct_ws_str + ']+')
_camel2under_re = re.compile('((?<=[a-z0-9])[A-Z]|(?!^)[A-Z](?=[a-z]))')


def camel2under(camel_string):
    """Converts a camelcased string to underscores. Useful for turning a
    class name into a function name.

    >>> camel2under('BasicParseTest')
    'basic_parse_test'
    """
    return _camel2under_re.sub(r'_\1', camel_string).lower()


def under2camel(under_string):
    """Converts an underscored string to camelcased. Useful for turning a
    function name into a class name.

    >>> under2camel('complex_tokenizer')
    'ComplexTokenizer'
    """
    return ''.join(w.capitalize() or '_' for w in under_string.split('_'))


def slugify(text, delim='_', lower=True, ascii=False):
    """
    A basic function that turns text full of scary characters
    (i.e., punctuation and whitespace), into a relatively safe
    lowercased string separated only by the delimiter specified
    by *delim*, which defaults to ``_``.

    The *ascii* convenience flag will :func:`asciify` the slug if
    you require ascii-only slugs.

    >>> slugify('First post! Hi!!!!~1    ')
    'first_post_hi_1'

    >>> slugify("Kurt Gödel's pretty cool.", ascii=True) == \
        b'kurt_goedel_s_pretty_cool'
    True

    """
    ret = delim.join(split_punct_ws(text))
    if ascii:
        ret = asciify(ret)
    if lower:
        ret = ret.lower()
    return ret


def split_punct_ws(text):
    """While :meth:`str.split` will split on whitespace,
    :func:`split_punct_ws` will split on punctuation and
    whitespace. This used internally by :func:`slugify`, above.

    >>> split_punct_ws('First post! Hi!!!!~1    ')
    ['First', 'post', 'Hi', '1']
    """
    return [w for w in _punct_re.split(text) if w]


def unit_len(sized_iterable, unit_noun='item'):  # TODO: len_units()/unitize()?
    """Returns a plain-English description of an iterable's
    :func:`len()`, conditionally pluralized with :func:`cardinalize`,
    detailed below.

    >>> print(unit_len(range(10), 'number'))
    10 numbers
    >>> print(unit_len('aeiou', 'vowel'))
    5 vowels
    >>> print(unit_len([], 'worry'))
    No worries
    """
    count = len(sized_iterable)
    units = cardinalize(unit_noun, count)
    if count:
        return u'%s %s' % (count, units)
    return u'No %s' % (units,)


_ORDINAL_MAP = {'1': 'st',
                '2': 'nd',
                '3': 'rd'}  # 'th' is the default


def ordinalize(number, ext_only=False):
    """Turns *number* into its cardinal form, i.e., 1st, 2nd,
    3rd, 4th, etc. If the last character isn't a digit, it returns the
    string value unchanged.

    Args:
        number (int or str): Number to be cardinalized.
        ext_only (bool): Whether to return only the suffix. Default ``False``.

    >>> print(ordinalize(1))
    1st
    >>> print(ordinalize(3694839230))
    3694839230th
    >>> print(ordinalize('hi'))
    hi
    >>> print(ordinalize(1515))
    1515th
    """
    numstr, ext = unicode(number), ''
    if numstr and numstr[-1] in string.digits:
        try:
            # first check for teens
            if numstr[-2] == '1':
                ext = 'th'
            else:
                # all other cases
                ext = _ORDINAL_MAP.get(numstr[-1], 'th')
        except IndexError:
            # single digit numbers (will reach here based on [-2] above)
            ext = _ORDINAL_MAP.get(numstr[-1], 'th')
    if ext_only:
        return ext
    else:
        return numstr + ext


def cardinalize(unit_noun, count):
    """Conditionally pluralizes a singular word *unit_noun* if
    *count* is not one, preserving case when possible.

    >>> vowels = 'aeiou'
    >>> print(len(vowels), cardinalize('vowel', len(vowels)))
    5 vowels
    >>> print(3, cardinalize('Wish', 3))
    3 Wishes
    """
    if count == 1:
        return unit_noun
    return pluralize(unit_noun)


def singularize(word):
    """Semi-intelligently converts an English plural *word* to its
    singular form, preserving case pattern.

    >>> singularize('records')
    'record'
    >>> singularize('FEET')
    'FOOT'

    """
    orig_word, word = word, word.strip().lower()
    if not word or word in _IRR_S2P:
        return orig_word

    irr_singular = _IRR_P2S.get(word)
    if irr_singular:
        singular = irr_singular
    elif not word.endswith('s'):
        return orig_word
    elif len(word) == 2:
        singular = word[:-1]  # or just return word?
    elif word.endswith('ies') and word[-5:-4] not in 'aeiou':
        singular = word[:-3] + 'y'
    elif word.endswith('es'):
        singular = word[:-2]
    else:
        singular = word[:-1]
    return _match_case(orig_word, singular)


def pluralize(word):
    """Semi-intelligently converts an English *word* from singular form to
    plural, preserving case pattern.

    >>> pluralize('friend')
    'friends'
    >>> pluralize('enemy')
    'enemies'
    >>> pluralize('Sheep')
    'Sheep'
    """
    orig_word, word = word, word.strip().lower()
    if not word or word in _IRR_P2S:
        return orig_word
    irr_plural = _IRR_S2P.get(word)
    if irr_plural:
        plural = irr_plural
    elif word.endswith('y') and word[-2:-1] not in 'aeiou':
        plural = word[:-1] + 'ies'
    elif word[-1] == 's' or word.endswith('ch') or word.endswith('sh'):
        plural = word if word.endswith('es') else word + 'es'
    else:
        plural = word + 's'
    return _match_case(orig_word, plural)


def _match_case(master, disciple):
    if not master.strip():
        return disciple
    if master.lower() == master:
        return disciple.lower()
    elif master.upper() == master:
        return disciple.upper()
    elif master.capitalize() == master:
        return disciple.capitalize()
    return disciple


# Singular to plural map of irregular pluralizations
_IRR_S2P = {'addendum': 'addenda', 'alga': 'algae', 'alumna': 'alumnae',
            'alumnus': 'alumni', 'analysis': 'analyses', 'antenna': 'antennae',
            'appendix': 'appendices', 'axis': 'axes', 'bacillus': 'bacilli',
            'bacterium': 'bacteria', 'basis': 'bases', 'beau': 'beaux',
            'bison': 'bison', 'bureau': 'bureaus', 'cactus': 'cacti',
            'calf': 'calves', 'child': 'children', 'corps': 'corps',
            'corpus': 'corpora', 'crisis': 'crises', 'criterion': 'criteria',
            'curriculum': 'curricula', 'datum': 'data', 'deer': 'deer',
            'diagnosis': 'diagnoses', 'die': 'dice', 'dwarf': 'dwarves',
            'echo': 'echoes', 'elf': 'elves', 'ellipsis': 'ellipses',
            'embargo': 'embargoes', 'emphasis': 'emphases', 'erratum': 'errata',
            'fireman': 'firemen', 'fish': 'fish', 'focus': 'foci',
            'foot': 'feet', 'formula': 'formulae', 'formula': 'formulas',
            'fungus': 'fungi', 'genus': 'genera', 'goose': 'geese',
            'half': 'halves', 'hero': 'heroes', 'hippopotamus': 'hippopotami',
            'hoof': 'hooves', 'hypothesis': 'hypotheses', 'index': 'indices',
            'knife': 'knives', 'leaf': 'leaves', 'life': 'lives',
            'loaf': 'loaves', 'louse': 'lice', 'man': 'men',
            'matrix': 'matrices', 'means': 'means', 'medium': 'media',
            'memorandum': 'memoranda', 'millennium': 'milennia', 'moose': 'moose',
            'mosquito': 'mosquitoes', 'mouse': 'mice', 'nebula': 'nebulae',
            'neurosis': 'neuroses', 'nucleus': 'nuclei', 'oasis': 'oases',
            'octopus': 'octopi', 'offspring': 'offspring', 'ovum': 'ova',
            'ox': 'oxen', 'paralysis': 'paralyses', 'parenthesis': 'parentheses',
            'person': 'people', 'phenomenon': 'phenomena', 'potato': 'potatoes',
            'radius': 'radii', 'scarf': 'scarves', 'scissors': 'scissors',
            'self': 'selves', 'series': 'series', 'sheep': 'sheep',
            'shelf': 'shelves', 'species': 'species', 'stimulus': 'stimuli',
            'stratum': 'strata', 'syllabus': 'syllabi', 'symposium': 'symposia',
            'synopsis': 'synopses', 'synthesis': 'syntheses', 'tableau': 'tableaux',
            'that': 'those', 'thesis': 'theses', 'thief': 'thieves',
            'this': 'these', 'tomato': 'tomatoes', 'tooth': 'teeth',
            'torpedo': 'torpedoes', 'vertebra': 'vertebrae', 'veto': 'vetoes',
            'vita': 'vitae', 'watch': 'watches', 'wife': 'wives',
            'wolf': 'wolves', 'woman': 'women'}


# Reverse index of the above
_IRR_P2S = dict([(v, k) for k, v in _IRR_S2P.items()])

HASHTAG_RE = re.compile(r"(?:^|\s)[＃#]{1}(\w+)", re.UNICODE)


def find_hashtags(string):
    """Finds and returns all hashtags in a string, with the hashmark
    removed. Supports full-width hashmarks for Asian languages and
    does not false-positive on URL anchors.

    >>> find_hashtags('#atag http://asite/#ananchor')
    ['atag']

    ``find_hashtags`` also works with unicode hashtags.
    """

    # the following works, doctest just struggles with it
    # >>> find_hashtags(u"can't get enough of that dignity chicken #肯德基 woo")
    # [u'\u80af\u5fb7\u57fa']
    return HASHTAG_RE.findall(string)


def a10n(string):
    """That thing where "internationalization" becomes "i18n", what's it
    called? Abbreviation? Oh wait, no: ``a10n``. (It's actually a form
    of `numeronym`_.)

    >>> a10n('abbreviation')
    'a10n'
    >>> a10n('internationalization')
    'i18n'
    >>> a10n('')
    ''

    .. _numeronym: http://en.wikipedia.org/wiki/Numeronym
    """
    if len(string) < 3:
        return string
    return '%s%s%s' % (string[0], len(string[1:-1]), string[-1])


class StringBuffer(object):
    """
    This is meant to be a better file-like string buffer.
    Faster than StringIO, better encoding handling than cStringIO.

    This one is for unicode text strings. Look for ByteBuffer if you
    want to handle byte strings.

    (NOTE: not quite done yet)
    """
    def __init__(self, default_encoding=None, errors='strict'):
        self.data = collections.deque()
        self.default_encoding = default_encoding or 'utf-8'
        self.errors = errors

    def write(self, s):
        if not isinstance(s, unicode):
            enc = self.default_encoding
            errs = self.errors
            try:
                s = s.decode(enc, errs)
            except AttributeError:
                raise ValueError('write() expected a unicode or byte string')
        self.data.append(s)

    def truncate(self):
        self.data = collections.deque()
        self.write = self.data.append

    def getvalue(self):
        return unicode().join(self.data)

ANSI_ESCAPE_BEGIN = '\x1b['
ANSI_TERMINATORS = ('H', 'f', 'A', 'B', 'C', 'D', 'R', 's', 'u', 'J',
                    'K', 'h', 'l', 'p', 'm')


def strip_ansi(text):
    """Strips ANSI escape codes from *text*. Useful for the occasional
    time when a log or redirected output accidentally captures console
    color codes and the like.

    >>> strip_ansi('\x1b[0m\x1b[1;36mart\x1b[46;34m\xdc')
    'art'

    The test above is an excerpt from ANSI art on
    `sixteencolors.net`_. This function does not interpret or render
    ANSI art, but you can do so with `ansi2img`_ or `escapes.js`_.

    .. _sixteencolors.net: http://sixteencolors.net
    .. _ansi2img: http://www.bedroomlan.org/projects/ansi2img
    .. _escapes.js: https://github.com/atdt/escapes.js
    """
    # TODO: move to cliutils.py
    nansi, keep, i, text_len = [], True, 0, len(text)
    while i < text_len:
        if not keep and text[i] in ANSI_TERMINATORS:
            keep = True
        elif keep:
            keep_end_i = text.find(ANSI_ESCAPE_BEGIN, i)
            if keep_end_i < 0:
                break
            else:
                nansi.append(text[i:keep_end_i])
                i, keep = keep_end_i, False
        i += 1
    if not nansi:
        return text
    return type(text)().join(nansi)  # attempted unicode + str support


def asciify(text, ignore=False):
    """Converts a unicode or bytestring, *text*, into a bytestring with
    just ascii characters. Performs basic deaccenting for all you
    Europhiles out there.

    Also, a gentle reminder that this is a **utility**, primarily meant
    for slugification. Whenever possible, make your application work
    **with** unicode, not against it.

    Args:
        text (str or unicode): The string to be asciified.
        ignore (bool): Configures final encoding to ignore remaining
            unasciified unicode instead of replacing it.

    >>> asciify('Beyoncé') == b'Beyonce'
    True
    """
    try:
        try:
            return text.encode('ascii')
        except UnicodeDecodeError:
            # this usually means you passed in a non-unicode string
            text = text.decode('utf-8')
            return text.encode('ascii')
    except UnicodeEncodeError:
        mode = 'replace'
        if ignore:
            mode = 'ignore'
        transd = unicodedata.normalize('NFKD', text.translate(DEACCENT_MAP))
        ret = transd.encode('ascii', mode)
        return ret


def is_ascii(text):
    """Check if a unicode or bytestring, *text*, is composed of ascii
    characters only. Raises :exc:`ValueError` if argument is not text.

    Args:
        text (str or unicode): The string to be checked.

    >>> is_ascii('Beyoncé')
    False
    >>> is_ascii('Beyonce')
    True
    """
    if isinstance(text, unicode):
        try:
            text.encode('ascii')
        except UnicodeEncodeError:
            return False
    elif isinstance(text, bytes):
        try:
            text.decode('ascii')
        except UnicodeDecodeError:
            return False
    else:
        raise ValueError('expected text or bytes, not %r' % type(text))
    return True


class DeaccenterDict(dict):
    "A small caching dictionary for deaccenting."
    def __missing__(self, key):
        ch = self.get(key)
        if ch is not None:
            return ch
        try:
            de = unicodedata.decomposition(unichr(key))
            p1, _, p2 = de.rpartition(' ')
            if int(p2, 16) == 0x308:
                ch = self.get(key)
            else:
                ch = int(p1, 16)
        except (IndexError, ValueError):
            ch = self.get(key, key)
        self[key] = ch
        return ch

    try:
        from collections import defaultdict
    except ImportError:
        # no defaultdict means that __missing__ isn't supported in
        # this version of python, so we define __getitem__
        def __getitem__(self, key):
            try:
                return super(DeaccenterDict, self).__getitem__(key)
            except KeyError:
                return self.__missing__(key)
    else:
        del defaultdict


# http://chmullig.com/2009/12/python-unicode-ascii-ifier/
# For something more complete, investigate the unidecode
# or isounidecode packages, which are capable of performing
# crude transliteration.
_BASE_DEACCENT_MAP = {
    0xc6: u"AE", # Æ LATIN CAPITAL LETTER AE
    0xd0: u"D",  # Ð LATIN CAPITAL LETTER ETH
    0xd8: u"OE", # Ø LATIN CAPITAL LETTER O WITH STROKE
    0xde: u"Th", # Þ LATIN CAPITAL LETTER THORN
    0xc4: u'Ae', # Ä LATIN CAPITAL LETTER A WITH DIAERESIS
    0xd6: u'Oe', # Ö LATIN CAPITAL LETTER O WITH DIAERESIS
    0xdc: u'Ue', # Ü LATIN CAPITAL LETTER U WITH DIAERESIS
    0xc0: u"A",  # À LATIN CAPITAL LETTER A WITH GRAVE
    0xc1: u"A",  # Á LATIN CAPITAL LETTER A WITH ACUTE
    0xc3: u"A",  # Ã LATIN CAPITAL LETTER A WITH TILDE
    0xc7: u"C",  # Ç LATIN CAPITAL LETTER C WITH CEDILLA
    0xc8: u"E",  # È LATIN CAPITAL LETTER E WITH GRAVE
    0xc9: u"E",  # É LATIN CAPITAL LETTER E WITH ACUTE
    0xca: u"E",  # Ê LATIN CAPITAL LETTER E WITH CIRCUMFLEX
    0xcc: u"I",  # Ì LATIN CAPITAL LETTER I WITH GRAVE
    0xcd: u"I",  # Í LATIN CAPITAL LETTER I WITH ACUTE
    0xd2: u"O",  # Ò LATIN CAPITAL LETTER O WITH GRAVE
    0xd3: u"O",  # Ó LATIN CAPITAL LETTER O WITH ACUTE
    0xd5: u"O",  # Õ LATIN CAPITAL LETTER O WITH TILDE
    0xd9: u"U",  # Ù LATIN CAPITAL LETTER U WITH GRAVE
    0xda: u"U",  # Ú LATIN CAPITAL LETTER U WITH ACUTE
    0xdf: u"ss", # ß LATIN SMALL LETTER SHARP S
    0xe6: u"ae", # æ LATIN SMALL LETTER AE
    0xf0: u"d",  # ð LATIN SMALL LETTER ETH
    0xf8: u"oe", # ø LATIN SMALL LETTER O WITH STROKE
    0xfe: u"th", # þ LATIN SMALL LETTER THORN,
    0xe4: u'ae', # ä LATIN SMALL LETTER A WITH DIAERESIS
    0xf6: u'oe', # ö LATIN SMALL LETTER O WITH DIAERESIS
    0xfc: u'ue', # ü LATIN SMALL LETTER U WITH DIAERESIS
    0xe0: u"a",  # à LATIN SMALL LETTER A WITH GRAVE
    0xe1: u"a",  # á LATIN SMALL LETTER A WITH ACUTE
    0xe3: u"a",  # ã LATIN SMALL LETTER A WITH TILDE
    0xe7: u"c",  # ç LATIN SMALL LETTER C WITH CEDILLA
    0xe8: u"e",  # è LATIN SMALL LETTER E WITH GRAVE
    0xe9: u"e",  # é LATIN SMALL LETTER E WITH ACUTE
    0xea: u"e",  # ê LATIN SMALL LETTER E WITH CIRCUMFLEX
    0xec: u"i",  # ì LATIN SMALL LETTER I WITH GRAVE
    0xed: u"i",  # í LATIN SMALL LETTER I WITH ACUTE
    0xf2: u"o",  # ò LATIN SMALL LETTER O WITH GRAVE
    0xf3: u"o",  # ó LATIN SMALL LETTER O WITH ACUTE
    0xf5: u"o",  # õ LATIN SMALL LETTER O WITH TILDE
    0xf9: u"u",  # ù LATIN SMALL LETTER U WITH GRAVE
    0xfa: u"u",  # ú LATIN SMALL LETTER U WITH ACUTE
    0x2018: u"'",  # ‘ LEFT SINGLE QUOTATION MARK
    0x2019: u"'",  # ’ RIGHT SINGLE QUOTATION MARK
    0x201c: u'"',  # “ LEFT DOUBLE QUOTATION MARK
    0x201d: u'"',  # ” RIGHT DOUBLE QUOTATION MARK
    }


DEACCENT_MAP = DeaccenterDict(_BASE_DEACCENT_MAP)


_SIZE_SYMBOLS = ('B', 'K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y')
_SIZE_BOUNDS = [(1024 ** i, sym) for i, sym in enumerate(_SIZE_SYMBOLS)]
_SIZE_RANGES = list(zip(_SIZE_BOUNDS, _SIZE_BOUNDS[1:]))


def bytes2human(nbytes, ndigits=0):
    """Turns an integer value of *nbytes* into a human readable format. Set
    *ndigits* to control how many digits after the decimal point
    should be shown (default ``0``).

    >>> bytes2human(128991)
    '126K'
    >>> bytes2human(100001221)
    '95M'
    >>> bytes2human(0, 2)
    '0.00B'
    """
    abs_bytes = abs(nbytes)
    for (size, symbol), (next_size, next_symbol) in _SIZE_RANGES:
        if abs_bytes <= next_size:
            break
    hnbytes = float(nbytes) / size
    return '{hnbytes:.{ndigits}f}{symbol}'.format(hnbytes=hnbytes,
                                                  ndigits=ndigits,
                                                  symbol=symbol)


class HTMLTextExtractor(HTMLParser):
    def __init__(self):
        self.reset()
        self.strict = False
        self.convert_charrefs = True
        self.result = []

    def handle_data(self, d):
        self.result.append(d)

    def handle_charref(self, number):
        if number[0] == u'x' or number[0] == u'X':
            codepoint = int(number[1:], 16)
        else:
            codepoint = int(number)
        self.result.append(unichr(codepoint))

    def handle_entityref(self, name):
        try:
            codepoint = htmlentitydefs.name2codepoint[name]
        except KeyError:
            self.result.append(u'&' + name + u';')
        else:
            self.result.append(unichr(codepoint))

    def get_text(self):
        return u''.join(self.result)


def html2text(html):
    """Strips tags from HTML text, returning markup-free text. Also, does
    a best effort replacement of entities like "&nbsp;"

    >>> r = html2text(u'<a href="#">Test &amp;<em>(\u0394&#x03b7;&#956;&#x03CE;)</em></a>')
    >>> r == u'Test &(\u0394\u03b7\u03bc\u03ce)'
    True
    """
    # based on answers to http://stackoverflow.com/questions/753052/
    s = HTMLTextExtractor()
    s.feed(html)
    return s.get_text()


_EMPTY_GZIP_BYTES = b'\x1f\x8b\x08\x089\xf3\xb9U\x00\x03empty\x00\x03\x00\x00\x00\x00\x00\x00\x00\x00\x00'
_NON_EMPTY_GZIP_BYTES = b'\x1f\x8b\x08\x08\xbc\xf7\xb9U\x00\x03not_empty\x00K\xaa,I-N\xcc\xc8\xafT\xe4\x02\x00\xf3nb\xbf\x0b\x00\x00\x00'


def gunzip_bytes(bytestring):
    """The :mod:`gzip` module is great if you have a file or file-like
    object, but what if you just have bytes. StringIO is one
    possibility, but it's often faster, easier, and simpler to just
    use this one-liner. Use this tried-and-true utility function to
    decompress gzip from bytes.

    >>> gunzip_bytes(_EMPTY_GZIP_BYTES) == b''
    True
    >>> gunzip_bytes(_NON_EMPTY_GZIP_BYTES).rstrip() == b'bytesahoy!'
    True
    """
    return zlib.decompress(bytestring, 16 + zlib.MAX_WBITS)


_line_ending_re = re.compile(r'(\r\n|\n|\x0b|\f|\r|\x85|\x2028|\x2029)',
                             re.UNICODE)


def iter_splitlines(text):
    r"""Like :meth:`str.splitlines`, but returns an iterator of lines
    instead of a list. Also similar to :meth:`file.next`, as that also
    lazily reads and yields lines from a file.

    This function works with a variety of line endings, but as always,
    be careful when mixing line endings within a file.

    >>> list(iter_splitlines('\nhi\nbye\n'))
    ['', 'hi', 'bye', '']
    >>> list(iter_splitlines('\r\nhi\rbye\r\n'))
    ['', 'hi', 'bye', '']
    >>> list(iter_splitlines(''))
    []
    """
    prev_end, len_text = 0, len(text)
    # print('last: %r' % last_idx)
    # start, end = None, None
    for match in _line_ending_re.finditer(text):
        start, end = match.start(1), match.end(1)
        # print(start, end)
        if prev_end <= start:
            yield text[prev_end:start]
        if end == len_text:
            yield ''
        prev_end = end
    tail = text[prev_end:]
    if tail:
        yield tail
    return


def indent(text, margin, newline='\n', key=bool):
    """The missing counterpart to the built-in :func:`textwrap.dedent`.

    Args:
        text (str): The text to indent.
        margin (str): The string to prepend to each line.
        newline (str): The newline used to rejoin the lines (default: ``\\n``)
        key (callable): Called on each line to determine whether to
          indent it. Default: :class:`bool`, to ensure that empty lines do
          not get whitespace added.
    """
    indented_lines = [(margin + line if key(line) else line)
                      for line in iter_splitlines(text)]
    return newline.join(indented_lines)


def is_uuid(obj, version=4):
    """Check the argument is either a valid UUID object or string.

    Args:
        obj (object): The test target. Strings and UUID objects supported.
        version (int): The target UUID version, set to 0 to skip version check.

    >>> is_uuid('e682ccca-5a4c-4ef2-9711-73f9ad1e15ea')
    True
    >>> is_uuid('0221f0d9-d4b9-11e5-a478-10ddb1c2feb9')
    False
    >>> is_uuid('0221f0d9-d4b9-11e5-a478-10ddb1c2feb9', version=1)
    True
    """
    if not isinstance(obj, uuid.UUID):
        try:
            obj = uuid.UUID(obj)
        except (TypeError, ValueError, AttributeError):
            return False
    if version and obj.version != int(version):
        return False
    return True


def escape_shell_args(args, sep=' ', style=None):
    """Returns an escaped version of each string in *args*, according to
    *style*.

    Args:
        args (list): A list of arguments to escape and join together
        sep (str): The separator used to join the escaped arguments.
        style (str): The style of escaping to use. Can be one of
          ``cmd`` or ``sh``, geared toward Windows and Linux/BSD/etc.,
          respectively. If *style* is ``None``, then it is picked
          according to the system platform.

    See :func:`args2cmd` and :func:`args2sh` for details and example
    output for each style.
    """
    if not style:
        style = 'cmd' if sys.platform == 'win32' else 'sh'

    if style == 'sh':
        return args2sh(args, sep=sep)
    elif style == 'cmd':
        return args2cmd(args, sep=sep)

    raise ValueError("style expected one of 'cmd' or 'sh', not %r" % style)


_find_sh_unsafe = re.compile(r'[^a-zA-Z0-9_@%+=:,./-]').search


def args2sh(args, sep=' '):
    """Return a shell-escaped string version of *args*, separated by
    *sep*, based on the rules of sh, bash, and other shells in the
    Linux/BSD/MacOS ecosystem.

    >>> print(args2sh(['aa', '[bb]', "cc'cc", 'dd"dd']))
    aa '[bb]' 'cc'"'"'cc' 'dd"dd'

    As you can see, arguments with no special characters are not
    escaped, arguments with special characters are quoted with single
    quotes, and single quotes themselves are quoted with double
    quotes. Double quotes are handled like any other special
    character.

    Based on code from the :mod:`pipes`/:mod:`shlex` modules. Also
    note that :mod:`shlex` and :mod:`argparse` have functions to split
    and parse strings escaped in this manner.
    """
    ret_list = []

    for arg in args:
        if not arg:
            ret_list.append("''")
            continue
        if _find_sh_unsafe(arg) is None:
            ret_list.append(arg)
            continue
        # use single quotes, and put single quotes into double quotes
        # the string $'b is then quoted as '$'"'"'b'
        ret_list.append("'" + arg.replace("'", "'\"'\"'") + "'")

    return ' '.join(ret_list)


def args2cmd(args, sep=' '):
    r"""Return a shell-escaped string version of *args*, separated by
    *sep*, using the same rules as the Microsoft C runtime.

    >>> print(args2cmd(['aa', '[bb]', "cc'cc", 'dd"dd']))
    aa [bb] cc'cc dd\"dd

    As you can see, escaping is through backslashing and not quoting,
    and double quotes are the only special character. See the comment
    in the code for more details. Based on internal code from the
    :mod:`subprocess` module.

    """
    # technique description from subprocess below
    """
    1) Arguments are delimited by white space, which is either a
       space or a tab.

    2) A string surrounded by double quotation marks is
       interpreted as a single argument, regardless of white space
       contained within.  A quoted string can be embedded in an
       argument.

    3) A double quotation mark preceded by a backslash is
       interpreted as a literal double quotation mark.

    4) Backslashes are interpreted literally, unless they
       immediately precede a double quotation mark.

    5) If backslashes immediately precede a double quotation mark,
       every pair of backslashes is interpreted as a literal
       backslash.  If the number of backslashes is odd, the last
       backslash escapes the next double quotation mark as
       described in rule 3.

    See http://msdn.microsoft.com/en-us/library/17w5ykft.aspx
    or search http://msdn.microsoft.com for
    "Parsing C++ Command-Line Arguments"
    """
    result = []
    needquote = False
    for arg in args:
        bs_buf = []

        # Add a space to separate this argument from the others
        if result:
            result.append(' ')

        needquote = (" " in arg) or ("\t" in arg) or not arg
        if needquote:
            result.append('"')

        for c in arg:
            if c == '\\':
                # Don't know if we need to double yet.
                bs_buf.append(c)
            elif c == '"':
                # Double backslashes.
                result.append('\\' * len(bs_buf)*2)
                bs_buf = []
                result.append('\\"')
            else:
                # Normal char
                if bs_buf:
                    result.extend(bs_buf)
                    bs_buf = []
                result.append(c)

        # Add remaining backslashes, if any.
        if bs_buf:
            result.extend(bs_buf)

        if needquote:
            result.extend(bs_buf)
            result.append('"')

    return ''.join(result)


def parse_int_list(range_string, delim=',', range_delim='-'):
    """Returns a sorted list of positive integers based on
    *range_string*. Reverse of :func:`format_int_list`.

    Args:
        range_string (str): String of comma separated positive
            integers or ranges (e.g. '1,2,4-6,8'). Typical of a custom
            page range string used in printer dialogs.
        delim (char): Defaults to ','. Separates integers and
            contiguous ranges of integers.
        range_delim (char): Defaults to '-'. Indicates a contiguous
            range of integers.

    >>> parse_int_list('1,3,5-8,10-11,15')
    [1, 3, 5, 6, 7, 8, 10, 11, 15]

    """
    output = []

    for x in range_string.strip().split(delim):

        # Range
        if range_delim in x:
            range_limits = list(map(int, x.split(range_delim)))
            output += list(range(min(range_limits), max(range_limits)+1))

        # Empty String
        elif not x:
            continue

        # Integer
        else:
            output.append(int(x))

    return sorted(output)


def format_int_list(int_list, delim=',', range_delim='-', delim_space=False):
    """Returns a sorted range string from a list of positive integers
    (*int_list*). Contiguous ranges of integers are collapsed to min
    and max values. Reverse of :func:`parse_int_list`.

    Args:
        int_list (list): List of positive integers to be converted
           into a range string (e.g. [1,2,4,5,6,8]).
        delim (char): Defaults to ','. Separates integers and
           contiguous ranges of integers.
        range_delim (char): Defaults to '-'. Indicates a contiguous
           range of integers.
        delim_space (bool): Defaults to ``False``. If ``True``, adds a
           space after all *delim* characters.

    >>> format_int_list([1,3,5,6,7,8,10,11,15])
    '1,3,5-8,10-11,15'

    """
    output = []
    contig_range = collections.deque()

    for x in sorted(int_list):

        # Handle current (and first) value.
        if len(contig_range) < 1:
            contig_range.append(x)

        # Handle current value, given multiple previous values are contiguous.
        elif len(contig_range) > 1:
            delta = x - contig_range[-1]

            # Current value is contiguous.
            if delta == 1:
                contig_range.append(x)

            # Current value is non-contiguous.
            elif delta > 1:
                range_substr = '{0:d}{1}{2:d}'.format(min(contig_range),
                                                      range_delim,
                                                      max(contig_range))
                output.append(range_substr)
                contig_range.clear()
                contig_range.append(x)

            # Current value repeated.
            else:
                continue

        # Handle current value, given no previous contiguous integers
        else:
            delta = x - contig_range[0]

            # Current value is contiguous.
            if delta == 1:
                contig_range.append(x)

            # Current value is non-contiguous.
            elif delta > 1:
                output.append('{0:d}'.format(contig_range.popleft()))
                contig_range.append(x)

            # Current value repeated.
            else:
                continue

    # Handle the last value.
    else:

        # Last value is non-contiguous.
        if len(contig_range) == 1:
            output.append('{0:d}'.format(contig_range.popleft()))
            contig_range.clear()

        # Last value is part of contiguous range.
        elif len(contig_range) > 1:
            range_substr = '{0:d}{1}{2:d}'.format(min(contig_range),
                                                  range_delim,
                                                  max(contig_range))
            output.append(range_substr)
            contig_range.clear()

    if delim_space:
        output_str = (delim+' ').join(output)
    else:
        output_str = delim.join(output)

    return output_str
