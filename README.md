***
## Wikipedia knowledge-base extraction:

See [Makefile](Makefile.wikipedia) for entire processing chain. It also contains build rules for the 
wikipedia sqlite database files to start with. 

### extract-wiki-ner-entities
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


***


## Preprocessing of digital collections:

These tools can be used only internally within the SBB in order to extract BERT pre-training 
data from the ALTO-XML files of the digital collections of the SBB.
See [Makefile](Makefile) for entire pre-processing chain.

### altotool

```
altotool --help

Usage: altotool [OPTIONS] SOURCE_DIR OUTPUT_FILE

  Extract text from a bunch of ALTO XML files into one big CSV(.csv) or
  SQLITE3(.sqlite3) file.

  SOURCE_DIR: The directory that contains subfolders with the ALTO xml
  files. OUTPUT_FILE: Write the extracted fulltext to this file (either .csv
  or .sqlite3).

Options:
  --processes INTEGER  number of parallel processes. default: 6.
  --help               Show this message and exit.

```

### corpusentropy

```
corpusentropy --help

Usage: corpusentropy [OPTIONS] ALTO_FULLTEXT_FILE ENTROPY_FILE

  Read the documents of the corpus from ALTO_FULLTEXT_FILE where each line
  of the .csv file describes one page.

  Foreach page compute its character entropy rate and store the result as a
  pickled pandas DataFrame in ENTROPY_FILE.

Options:
  --chunksize INTEGER  size of chunks used for processing alto-csv-file
  --processes INTEGER  number of parallel processes. default: 6.
  --help               Show this message and exit.
```

### corpuslanguage

```
corpuslanguage --help

Usage: corpuslanguage [OPTIONS] ALTO_FULLTEXT_FILE LANGUAGE_FILE

  Read the documents of the corpus from ALTO_FULLTEXT_FILE where each line
  of the .csv file describes one page.

  Foreach page classify its language by means of langid. Store the
  classification results as a pickled pandas DataFrame in LANGUAGE_FILE.

Options:
  --chunksize INTEGER  size of chunks used for processing alto-csv-file
  --processes INTEGER  number of parallel processes. default: 6.
  --help               Show this message and exit.

```

### batchner

```
batchner --help

Usage: batchner [OPTIONS] FULLTEXT_SQLITE_FILE SELECTION_FILE MODEL_NAME
                NER_ENDPOINT...

  Reads the text content per page of digitalized collections from sqlite
  file FULLTEXT_SQLITE_FILE. Considers only a subset of documents that is
  defined by SELECTION_FILE. Performs NER on the text content using the REST
  endpoint[s] NER_ENDPOINT .... Writes the NER results back to another
  sqlite file whose name is equal to FULLTEXT_SQLITE_FILE + '-ner-' or to
  the file specified in the --outfile option. Writes results in chunks of
  size <chunksize>. Suppress proxy with option --noproxy.

Options:
  --chunksize INTEGER  size of chunks used for processing. default: 10**4
  --noproxy            disable proxy. default: enabled.
  --processes INTEGER  number of parallel processes, default: number of NER
                       endpoints.

  --outfile PATH       Write results to this file. default: derive name from
                       fulltext sqlite file.

  --help               Show this message and exit.

```


### alto-annotator:
```
alto-annotator --help

Usage: alto-annotator [OPTIONS] TAGGED_SQLITE_FILE SOURCE_DIR DEST_DIR

  Read NER tagging results from TAGGED_SQLITE_FILE. Read ALTO XML files in
  subfolders of directory SOURCE_DIR. Annotate the XML content with NER
  information and write the annotated ALTO XML back to the same directory
  structure in DEST_DIR.

Options:
  --processes INTEGER  number of parallel processes. default: 0.
  --help               Show this message and exit.
```

***
## BERT-Pre-training:

### collectcorpus

```
collectcorpus --help

Usage: collectcorpus [OPTIONS] FULLTEXT_FILE SELECTION_FILE CORPUS_FILE

  Reads the fulltext from a CSV or SQLITE3 file (see also altotool) and
  write it to one big text file.

  FULLTEXT_FILE: The CSV or SQLITE3 file to read from.

  SELECTION_FILE: Consider only a subset of all pages that is defined by the
  DataFrame that is stored in <selection_file>.

  CORPUS_FILE: The output file.

Options:
  --chunksize INTEGER     Process the corpus in chunks of <chunksize>.
                          default:10**4

  --processes INTEGER     Number of parallel processes. default: 6
  --min-line-len INTEGER  Lower bound of line length in output file.
                          default:80

  --help                  Show this message and exit.

```

### bert-pregenerate-trainingdata

Generate data for BERT pre-training from a corpus text file where 
the documents are separated by an empty line (output of corpuscollect).

#### Usage

```
bert-pregenerate-trainingdata --help
```

### bert-finetune

Perform BERT pre-training on pre-generated data.

#### Usage

```
bert-finetune --help
```

***