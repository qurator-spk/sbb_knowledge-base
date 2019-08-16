***
# Preprocessing of digital collections:
## Modstool

Extract the MODS meta data of a bunch of METS files into a pandas Dataframe 
that is saved as .pkl.  

### Usage
```
modstool --help
```

## Altotool

Extract the OCR confidences as well as the text from a bunch of ALTO files 
and save them into one large .csv file.

### Usage

```
altotool --help
```

***
# BERT-NER:

## altocsv2corpus

Takes the csv file created with the altotool and converts it into one text
file that can be used to generate data for unsupervised
BERT training.

### Usage

```
altocsv2corpus --help
```

## corpusentropy

Read the documents of the corpus from a .csv file where each line of
the .csv file describes one document. Foreach document compute its
character entropy rate and store the result as a pickled pandas DataFrame.

### Usage

```
corpusentropy --help
```

## corpuslanguage

Read the documents of the corpus from a .csv file where each line of
the .csv file describes one document. Foreach document classify its
language by means of langid. Store the classification results as a pickled
pandas DataFrame.

### Usage

```
corpuslanguage --help
```

## bert-pregenerate-trainingdata

Generate data for BERT unsupervised pre-training from a corpus text file where the documents are
separated by an empty line (output of altocsv2corpus).

### Usage

```
bert-pregenerate-trainingdata --help
```

## bert-finetune

Perform BERT unsupervised pre-training on pre-generated data.

### Usage

```
bert-finetune --help
```
