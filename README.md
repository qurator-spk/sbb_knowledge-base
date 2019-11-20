***
# Preprocessing of digital collections:

See Makefile for entire pre-processing chain.

## Altotool

Extract the OCR confidences as well as the text from a bunch of ALTO files
and save them into one large CSV or SQLITE3 file.

### Usage

```
altotool --help
```


## corpusentropy

Read the documents of the corpus from a CSV or SQLITE3 file where each line/table row 
describes one document page. Foreach page compute its
character entropy rate and store the result as a pickled pandas DataFrame.

### Usage

```
corpusentropy --help
```

## corpuslanguage

Read the documents of the corpus from a CSV or SQLITE3 file where each line /table row 
describes one document page. Foreach page classify its language by means of langid. 
Store the classification results as a pickled pandas DataFrame.

### Usage

```
corpuslanguage --help
```

***
# BERT-NER-Pre-training:

## collectcorpus

Takes the CSV/SQLITE3 file created with the altotool and converts it into one text
file that can be used to generate data for BERT pre-training.

### Usage

```
collectcorpus --help
```

## bert-pregenerate-trainingdata

Generate data for BERT pre-training from a corpus text file where 
the documents are separated by an empty line (output of corpuscollect).

### Usage

```
bert-pregenerate-trainingdata --help
```

## bert-finetune

Perform BERT pre-training on pre-generated data.

### Usage

```
bert-finetune --help
```
