This package currently provides:

* [A set of tools to perform NER+EL on the digitalized collections of the SBB.](digitized-collections.md)
* [A set of tools for Wikidata/Wikipedia knowledge-base extraction.](knowledge-base.md) 
* [A set of tools to perform and visualize topic-modelling on the digitalized collections of the SBB.](topic-modelling.md)

# Installation:

Setup virtual environment:
```
virtualenv --python=python3.6 venv
```

Activate virtual environment:
```
source venv/bin/activate
```

Upgrade pip:
```
pip install -U pip
```

Install package together with its dependencies in development mode:
```
pip install -e ./
```