
## Processing of digitalized collections:

These tools can be used only internally within the SBB in order to:
   * perform NER+EL on the digitalized collection of the SBB given a running [NER](https://github.com/qurator-spk/sbb_ner)+[EL](https://github.com/qurator-spk/sbb_ned) system
   * augment the ALTO-XML files of the digitalized collections with NER+EL information
   * extract BERT pre-training data from the ALTO-XML files of the digital collections of the SBB. 

See [Makefile](Makefile) for entire processing chain.

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

## NER + EL of digitalized collections:

### batchner

```
batchner --help

Usage: batchner [OPTIONS] FULLTEXT_SQLITE_FILE SELECTION_FILE MODEL_NAME
                NER_ENDPOINT...

  Reads the text content per page of digitalized collections from sqlite
  file FULLTEXT_SQLITE_FILE.

  Considers only a subset of documents that is defined by SELECTION_FILE.

  Performs NER on the text content using the REST endpoint[s] NER_ENDPOINT
  ....

  Writes the NER results back to another sqlite file whose name is equal to
  FULLTEXT_SQLITE_FILE + '-ner-' or to the file specified in the --outfile
  option.

  Writes results in chunks of size <chunksize>.

  Suppress proxy with option --noproxy.

Options:
  --chunksize INTEGER  size of chunks used for processing. default: 10**4
  --noproxy            disable proxy. default: enabled.
  --processes INTEGER  number of parallel processes, default: number of NER
                       endpoints.

  --outfile PATH       Write results to this file. default: derive name from
                       fulltext sqlite file.

  --help               Show this message and exit.
```

### batch-el
```
batchel --help

Usage: batchel [OPTIONS] SQLITE_FILE LANG_FILE EL_ENDPOINTS

  Performs entity linking on all the PPNs resp. files whose NER-tagging is
  contained in the input SQLITE_FILE. Stores the linking results in the same
  file in a table 'entity_linking'.

  SQLITE_FILE: File that has been produced by batchner, i.e., a file that
  contains all the NER results per PPN and page in table named 'tagged'.

  LANG_FILE: Pickled pandas DataFrame that specifies the language of all
  files per PPN:

              ppn      filename language
  0  PPN646426230  00000045.xml       fr
  1  PPN646426230  00000218.xml       fr
  2  PPN646426230  00000394.xml       fr
  3  PPN646426230  00000071.xml       fr
  4  PPN646426230  00000317.xml       fr
  see also ->corpuslanguage --help

  EL_ENDPOINTS: JSON structure that defines EL-endpoints per language:

  { "de": "http://b-lx0053.sbb.spk-berlin.de/sbb-tools/de-ned" }

  Suppress proxy by option --noproxy.

Options:
  --chunk-size INTEGER   size of chunks sent to EL-Linking system. Default:
                         100.

  --noproxy              disable proxy. default: proxy is enabled.
  --start-from-ppn TEXT
  --help                 Show this message and exit.
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
