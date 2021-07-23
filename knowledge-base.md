## Wikidata + Wikipedia knowledge-base extraction:

Currently, the [SBB entity linking system](https://github.com/qurator-spk/sbb_ned) uses a
knowledge-base that is derived from Wikidata and Wikipedia.

First identification of relevant entities is performed by running SPARQL queries on wikidata 
(Beware! In order to do this you need to set up your own wikidata instance since the query time limit 
of wikidata.org prevents us from running these queries directly on their instance.)
See [Makefile.wikidata](Makefile.wikidata) for details.

Once all the relevant entities have been identified, related text material with ground-truth, 
i.e., human annotated entity links, is extracted from wikipedia and processed such that it can be used 
during training and application of the entity linking system.
See [Makefile.wikipedia](Makefile.wikipedia) for that part of the processing chain. 
This part also contains build rules for the wikipedia sqlite database files to start with.

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
