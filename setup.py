from io import open
from setuptools import find_packages, setup

with open('requirements.txt') as fp:
    install_requires = fp.read()

setup(
    name="qurator-sbb-tools",
    version="0.0.1",
    author="The Qurator Team",
    author_email="qurator@sbb.spk-berlin.de",
    description="Qurator",
    long_description=open("README.md", "r", encoding='utf-8').read(),
    long_description_content_type="text/markdown",
    keywords='qurator',
    license='Apache',
    url="https://qurator.ai",
    packages=find_packages(exclude=["*.tests", "*.tests.*",
                                    "tests.*", "tests"]),
    install_requires=install_requires,
    entry_points={
      'console_scripts': [
        "altotool=qurator.sbb.xml:altotool",
        "corpusentropy=qurator.sbb.entropy:main",
        "corpuslanguage=qurator.sbb.language:main",
        "select-by-lang-and-entropy=qurator.sbb.select:by_lang_and_entropy",

        "collectcorpus=qurator.bert.corpus:collect",
        "bert-pregenerate-trainingdata=qurator.bert.pregenerate_training_data:main",
        "bert-finetune=qurator.bert.finetune_on_pregenerated:main",

        "extract-wiki-full-text-parquet=qurator.wikipedia.xml:to_parquet",
        "extract-wiki-full-text-sqlite=qurator.wikipedia.xml:to_sqlite",
        "extract-wiki-ner-entities=qurator.wikipedia.entities:ner",
        "tag-wiki-entities=qurator.wikipedia.ner:tag_entities",
        "print-wiki-article=qurator.wikipedia.ner:print_article_command_line",
        "train-test-split-wiki=qurator.wikipedia.ner:train_test_split",

        "parquet2csv=qurator.utils.parquet:to_csv",
        "csv2sqlite=qurator.utils.csv:to_sqlite",
        "ner=qurator.sbb.ner:on_db_file",

        "example=qurator.examples.multiprocessing:example"
      ]
    },
    python_requires='>=3.6.0',
    tests_require=['pytest'],
    classifiers=[
          'Intended Audience :: Science/Research',
          'License :: OSI Approved :: Apache Software License',
          'Programming Language :: Python :: 3',
          'Topic :: Scientific/Engineering :: Artificial Intelligence',
    ],
)
