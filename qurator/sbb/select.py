import pandas as pd
import click


@click.command()
@click.argument('language-file', type=click.Path(), required=True, nargs=1)
@click.argument('entropy-file', type=click.Path(), required=True, nargs=1)
@click.argument('output-file', type=click.Path(), required=True, nargs=1)
@click.option('--min-lang-confidence', type=float, default=1.0,
              help="Lower bound for the confidence of the per page language estimation. default: 1.0")
@click.option('--min-entropy-quantile', type=float, default=0.2,
              help="Lower quantile of the considered per page character entropy. default: 0.2")
@click.option('--max-entropy-quantile', type=float, default=0.8,
              help="Upper quantile of the considered per page character entropy. default: 0.8")
def by_lang_and_entropy(language_file, entropy_file, output_file, min_lang_confidence,
                        min_entropy_quantile, max_entropy_quantile):
    """
    Filter fulltext pages according to language and character entropy.

    LANGUAGE_FILE: pickled DataFrame that contains the language of each fulltext page (see tool corpuslanguage).

    ENTROPY_FILE: pickled DataFrame that contains the character entropy of each fulltext page
    (see tool corpusentropy).

    OUTPUT_FILE: Write the filter result as a pickled DataFrame to this file.
    """

    lang = pd.read_pickle(language_file)

    entropy = pd.read_pickle(entropy_file)

    selector = lang.merge(entropy, on=['ppn', 'filename'])

    selector['selected'] = False
    selector.loc[(selector.language == 'de') & (selector.confidence == min_lang_confidence) &
                 (selector.entropy > selector.entropy.quantile(min_entropy_quantile)) &
                 (selector.entropy < selector.entropy.quantile(max_entropy_quantile)), 'selected'] = \
        True

    selector[['ppn', 'filename', 'selected']].reset_index(drop=True).to_pickle(output_file)
