## Wikidata + Wikipedia knowledge-base extraction:

Currently, the [SBB entity linking system](https://github.com/qurator-spk/sbb_ned) uses a
knowledge-base that is derived from Wikidata and Wikipedia.

First identification of relevant entities is performed by running SPARQL queries on wikidata 
(**Beware!** In order to do this you need to set up your own wikidata instance since the query time limit 
of wikidata.org prevents us from running these queries directly on their instance.)
See [Makefile.wikidata](Makefile.wikidata) for details.

Once all the relevant entities have been identified, related text material with ground-truth, 
i.e., human annotated entity links, is extracted from wikipedia and processed such that it can be used 
during training and application of the entity linking system.
See [Makefile.wikipedia](Makefile.wikipedia) for that part of the processing chain. 
This part also contains build rules for the wikipedia sqlite database files to start with.

If you want to avoid setup of your own Wikidata instance and re-extraction of the knowledge-bases,
you might want to look at the ready-to-use knowledge-bases for german, french and english that can be downloaded at
https://qurator-data.de/sbb_ned/models.tar.gz 
 
**Beware:** The archive file contains the required models as well as the knowledge bases
for german, french and english, altogether roughly 30GB!!!

 
## Installation:

Clone this project and the [SBB-utils](https://github.com/qurator-spk/sbb_utils).

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

Install packages together with their dependencies in development mode:
```
pip install -e sbb_utils
pip install -e sbb_knowledge-base
```

***

## Command-line interface:
 

### run-sparql
```
run-sparql --help

run-sparql [OPTIONS] OUT_FILE

  Runs a SPARQL query QUERY on ENDPOINT and saves the results as pickled
  pandas DataFrame in OUT_FILE.

Options:
  --endpoint TEXT    SPARQL endpoint. Default
                     https://query.wikidata.org/bigdata/namespace/wdq/sparql.

  --query TEXT       SPARQL query.
  --query-file PATH  Read query from file
  --analytic         Run query in analytic mode (Blazegraph specific).
  --demo             Run demo query.
  --lang TEXT        Replace __LANG__ in query by this value. Default: empty.
  --site TEXT        Replace __SITE__ in query by this value. Default: empty.
  --help             Show this message and exit.

```


### extract-wiki-full-text-sqlite

```
extract-wiki-full-text-sqlite --help

Usage: extract-wiki-full-text-sqlite [OPTIONS] WIKIPEDIA_XML_FILE SQLITE_FILE

  Takes a wikipedia xml multistream dump file, extracts page_id, page_title
  and page_text of each article and writes that information into a sqlite
  file.

  WIKIPEDIA_XML_FILE: wikipedia multistream xml dump of all pages.

  SQLITE_FILE: result file.

Options:
  --chunk-size INTEGER  size of parquet chunks. default:2*10**4
  --help                Show this message and exit.

```

### tag-wiki-entities2sqlite

```
tag-wiki-entities2sqlite --help

Usage: tag-wiki-entities2sqlite [OPTIONS] FULLTEXT_SQLITE ALL_ENTITIES_FILE
                                WIKIPEDIA_SQLITE_FILE TAGGED_SQLITE

  FULLTEXT_SQLITE: SQLITE file that contains the per article fulltext. (see
  extract-wiki-full-text-sqlite)

  ALL_ENTITIES_FILE: pickle file that contains a pandas dataframe that
  describes the entities (see extract-wiki-ner-entities).

  WIKIPEDIA_SQLITE_FILE: sqlite3 dump of wikipedia that contains the
  redirect table.

  TAGGED_SQLITE: result sqlite file. The file provides per article access to
  the fulltext where all relevant entities according to ALL_ENTITIES_FILE
  have been tagged.

Options:
  --processes INTEGER  number of parallel processes. default: 6.
  --help               Show this message and exit.

```

### compute-apriori-probs

```
compute-apriori-probs --help

Usage: compute-apriori-probs [OPTIONS] SQLITE_FILE

  Compute the a-priori probabilities for all entities based on the number of
  links that relate to each entity versus the total number of links in the
  sentence database.

  SQLITE_FILE: sqlite3 sentence database that contains an "entities" as well
  as an related "links" table.

  Adds a new "proba" column to the entities table that contains the a-priori
  probabilities.

Options:
  --processes INTEGER  number of parallel processes. default: 8.
  --help               Show this message and exit.
```

***

## Deprecated: 

### extract-wiki-ner-entities

**Note: We now perform entity identification by running SPARQL queries on wikidata. 
Therefore this tool is not used any more in the knowledge base extraction.** 

```
extract-wiki-ner-entities --help

Usage: extract-wiki-ner-entities [OPTIONS] SQLITE3_FILE ENTITY_FILE

  Runs recursively through the super categories "Organisation",
  "Geographisches Objekt", "Frau", "Mann" in order to determine all ORG,
  LOC, PER entities from the german wikipedia.

  SQLITE3_FILE: German Wikipedia database as sqlite3 file.

  ==>REQUIRED tables: page, categorylinks, redirects.

  ENTITY_FILE: Result file. Contains a pickled pandas DataFrame with all
  PER,LOC and ORG entities. For other non-german languages, ENTITY_FILE can
  be mapped via wikidata-QIDs (see wikidatamapping).

Options:
  --help  Show this message and exit.

```

### wikidatamapping

**Note: We now perform entity identification by running SPARQL queries on wikidata. 
Therefore this tool is not used any more in the knowledge base extraction.** 

```
wikidatamapping --help
Usage: wikidatamapping [OPTIONS] OUTPUT_DIR LANGUAGES ENTITY_FILE
                       ENTITY_WIKIPEDIA [OTHER_WIKIPEDIAS]...

  OUTPUT_DIR: directory to write result files

  LANGUAGES: string that contains the language identifiers of all the
  wikipedia's in correct order, separated by '|'. Example: 'DE|FR|EN'

  ENTITY_FILE: Pickled DataFrame contains the considered entities (created
  by extract-wiki-ner-entities).

  ENTITY_WIKIPEDIA: The wikipedia sqlite database file from where the
  ENTITY_FILE has been obtained.

  OTHER_WIKIPEDIAS: List of wikipedia sqlite database files of other
  languages that should be mapped onto the ENTITY_FILE.

  OUTPUT: wikidata-mapping.pkl: pickled DataFrame containing the mapping
  plus single per language entity files, for instance:

          de-wikipedia-ner-entities.pkl

          fr-wikipedia-ner-entities.pkl

          en-wikipedia-ner-entities.pkl

Options:
  --help  Show this message and exit.

```
