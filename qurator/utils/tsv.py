import pandas as pd
import re
import json


def read_tsv(tsv_file):

    tsv = pd.read_csv(tsv_file, sep='\t', comment='#', quoting=3).rename(columns={'GND-ID': 'ID'})

    parts = extract_doc_links(tsv_file)

    urls = [part['url'] for part in parts]
    contexts = [part['context'] for part in parts]

    return tsv, urls, contexts


def write_tsv(tsv, urls, contexts, tsv_out_file):

    if 'conf' in tsv.columns:
        out_columns = ['No.', 'TOKEN', 'NE-TAG', 'NE-EMB', 'ID', 'url_id', 'left', 'right', 'top', 'bottom', 'conf']
    else:
        out_columns = ['No.', 'TOKEN', 'NE-TAG', 'NE-EMB', 'ID', 'url_id', 'left', 'right', 'top', 'bottom']

    if len(urls) == 0:
        print('Writing to {}...'.format(tsv_out_file))

        tsv.to_csv(tsv_out_file, sep="\t", quoting=3, index=False)
    else:
        pd.DataFrame([], columns=out_columns).to_csv(tsv_out_file, sep="\t", quoting=3, index=False)

        for url_id, part in tsv.groupby('url_id'):
            with open(tsv_out_file, 'a') as f:

                if urls[int(url_id)] is not None:
                    f.write('# ' + urls[int(url_id)] + '\n')
                elif contexts[int(url_id)] is not None:
                    f.write('#__CONTEXT__:' + json.dumps(contexts[int(url_id)]) + '\n')

            part.to_csv(tsv_out_file, sep="\t", quoting=3, index=False, mode='a', header=False)


def extract_doc_links(tsv_file):
    parts = []

    header = None

    with open(tsv_file, 'r') as f:

        text = []
        url = None
        context = None

        for line in f:

            if header is None:
                header = "\t".join(line.split()) + '\n'
                continue

            is_context = re.match(r'#\s*__CONTEXT__\s*:\s*(.*)', line)

            urls = [url for url in
                    re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', line)]

            if is_context or len(urls) > 0:
                if url is not None or context is not None:
                    parts.append({"url": url, 'header': header, 'text': "".join(text), 'context': context})
                    text = []

                if is_context:
                    context = json.loads(is_context.group(1))
                else:
                    url = urls[-1]
            else:
                if url is None and context is None:
                    continue

                line = '\t'.join(line.split())

                if line.count('\t') == 2:
                    line = "\t" + line

                if line.count('\t') >= 3:
                    text.append(line + '\n')

                    continue

                if line.startswith('#'):
                    continue

                if len(line) == 0:
                    continue

                print('Line error: |', line, '|Number of Tabs: ', line.count('\t'))

        if url is not None:
            parts.append({"url": url, 'header': header, 'text': "".join(text), 'context': context})

    return parts
