import pandas as pd
import click


def by_lang_and_entropy(language_file, entropy_file, output_file):

    entropy = pd.read_pickle('../data/digisam/corpus-entropy.pkl')

    lang = pd.read_pickle('../data/digisam/corpus-language.pkl')

    selector = lang.merge(entropy, on=['ppn', 'filename'])

    selector['selected'] = False
    selector.loc[(selector.language == 'de') & (selector.confidence == 1) &
                 (selector.entropy > selector.entropy.quantile(0.2)) &
                 (selector.entropy < selector.entropy.quantile(0.8)), 'selected'] = True

    selector[['ppn', 'filename', 'selected']].to_pickle('../data/digisam/selection_de.pkl')

    pass