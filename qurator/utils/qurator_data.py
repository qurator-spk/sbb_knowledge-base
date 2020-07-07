"""
Handle a qurator-data submodule in Jupyter Notebooks.

1. Create a quorator-data submodule for your notebook and add a "nfs" remote:

    git submodule add git@code.dev.sbb.berlin:qurator/qurator-data.git qurator-data
    cd qurator-data; git remote add nfs /path/to/GitNX-Repository/qurator/qurator-data

2. In your notebook, use variables with the filenames relative to the
   qurator-data repo:

    mods_info_pickle = 'digisam/mods_info_df_all.2019-07-05.pkl'
    mods_issues_csv = mods_info_pickle + '.warnings.csv'
    data_files = [mods_info_pickle, mods_issues_csv]

3. Use this module to get the files and print info about data used:

    import qurator.utils.qurator_data

    qurator.utils.qurator_data.get(data_files, qurator_data_subdir='qurator-data')
    qurator.utils.qurator_data.notebook_preamble(data_files, qurator_data_subdir='qurator-data')

Then, use e.g. `os.path.join('qurator-data', mods_info_pickle)` to get the path
of the individual file.
"""

import os
import subprocess
import sys

from subprocess import PIPE
from IPython.core.display import display, Markdown


def get(data_files, qurator_data_subdir='qurator-data'):
    error = None

    subprocess.run(
            ['git', 'annex', 'init',
                os.path.join(os.getcwd(), qurator_data_subdir)])
    for data_file in data_files:
        res = subprocess.run(
                ['git', 'annex', 'get', data_file],
                cwd=qurator_data_subdir, stdout=PIPE, stderr=PIPE)
        if res.stderr:
            print(res.stderr.decode('utf-8'), file=sys.stderr)
        if res.stdout:
            print(res.stdout.decode('utf-8'))
        if res.returncode != 0:
            print('You may have to setup the nfs git remote for {}!'.format(
                qurator_data_subdir), file=sys.stderr)
            error = (res.returncode, res.args)
    if error:
        raise subprocess.CalledProcessError(*error)


def notebook_preamble(data_files, qurator_data_subdir='qurator-data'):
    res = subprocess.run(
            ['git', 'describe', '--always', '--long', '--dirty'],
            cwd=qurator_data_subdir, stdout=PIPE, stderr=PIPE)
    qurator_data_version = res.stdout.decode('utf-8').rstrip()

    display(Markdown('qurator-data {}:'.format(qurator_data_version)))
    display(Markdown('\n'.join('* {}'.format(data_file) for data_file in data_files)))
