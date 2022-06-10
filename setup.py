from io import open
from setuptools import find_packages, setup

with open('requirements.txt') as fp:
    install_requires = fp.read()

setup(
    name="qurator-sbb-knowledge-base",
    version="0.0.1",
    author="Kai Labusch, The Qurator Team",
    author_email="Kai.Labusch@sbb.spk-berlin.de",
    description="Qurator",
    long_description=open("README.md", "r", encoding='utf-8').read(),
    long_description_content_type="text/markdown",
    keywords='Qurator',
    license='Apache',
    url="https://github.com/qurator-spk/sbb_knowledge-base",
    packages=find_packages(exclude=["*.tests", "*.tests.*",
                                    "tests.*", "tests"]),
    install_requires=install_requires,
    entry_points={
      'console_scripts': [
        "extract-wiki-full-text-sqlite=qurator.wikipedia.xml:to_sqlite",
        "extract-wiki-ner-entities=qurator.wikipedia.entities:extract",
        "wikidatamapping=qurator.wikipedia.entities:wikidatamapping",
        "redirects2entities=qurator.wikipedia.entities:redirects2entities",
        "redirects2pkl=qurator.wikipedia.entities:redirects2pkl",
        "compute-apriori-probs=qurator.wikipedia.entities:compute_apriori_probs",
        "tag-wiki-entities2sqlite=qurator.wikipedia.ner:tag_entities2sqlite",
        "train-test-split-wiki=qurator.wikipedia.ner:train_test_split",

        "run-sparql=qurator.wikidata.cli:cli_run_sparql",
        "join-entities=qurator.wikidata.cli:join_entities",

        "batchel-wp=qurator.wikipedia.ned:run_on_tagged"
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
