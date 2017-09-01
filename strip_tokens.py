import glob
import json
import os
import re
import shutil
import sys

def split_anaconda_token(url):
    """
    Examples:
        >>> split_anaconda_token("https://1.2.3.4/t/tk-123-456/path")
        (u'https://1.2.3.4/path', u'tk-123-456')
        >>> split_anaconda_token("https://1.2.3.4/t//path")
        (u'https://1.2.3.4/path', u'')
        >>> split_anaconda_token("https://some.domain/api/t/tk-123-456/path")
        (u'https://some.domain/api/path', u'tk-123-456')
        >>> split_anaconda_token("https://1.2.3.4/conda/t/tk-123-456/path")
        (u'https://1.2.3.4/conda/path', u'tk-123-456')
        >>> split_anaconda_token("https://1.2.3.4/path")
        (u'https://1.2.3.4/path', None)
        >>> split_anaconda_token("https://10.2.3.4:8080/conda/t/tk-123-45")
        (u'https://10.2.3.4:8080/conda', u'tk-123-45')
    """
    _token_match = re.search(r'/t/([a-zA-Z0-9-]*)', url)
    token = _token_match.groups()[0] if _token_match else None
    cleaned_url = url.replace('/t/' + token, '', 1) if token is not None else url
    return cleaned_url.rstrip('/'), token


prefix = sys.argv[1]
do_it = len(sys.argv) >= 3 and int(sys.argv[2]) >= 1

for meta_file in glob.glob(os.path.join(prefix, 'conda-meta', '*.json')):
    with open(meta_file) as fh:
        data = json.loads(fh.read())
    if 'channel' in data:
        stripped_channel, token = split_anaconda_token(data['channel'])
        if token:
            print("%s:\n  old: %s\n  stripped: %s" % (meta_file, data['channel'], stripped_channel))
            if do_it:
                shutil.copy2(meta_file, meta_file + '.bak')
                data['channel'] = stripped_channel
                with open(meta_file) as fh:
                    fh.write(json.dumps(), indent=2, sort_keys=True, separators=(',', ': '))

