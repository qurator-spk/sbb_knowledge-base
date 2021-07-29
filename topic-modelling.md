## Topic modelling of digitalized collections:

Our topic modeling visualisation is currently derived from the very nice and useful [LDAvis package](https://github.com/cpsievert/LDAvis).
This sbb-tools package contains an adapted version of the html/js visualisation interface of LDAvis that has been extended such that 
it can switch between different topic models and provides links into wikidata and the digitalized collections of the SBB.

***
### Computation of LDA models and visualisation data (JSON):

Complete processing chain can be found in the  [Makefile](Makefile.topm).

```
lda-grid-search --help
Usage: lda-grid-search [OPTIONS] OUT_FILE CORPUS_FILE DOCS_FILE                                                                                                                                        
                                                                                                                                                                                                       
  Perform LDA-evaluation in a grid-search over different parameters.                                                                                                                                   
                                                                                                                                                                                                       
  OUT_FILE: Store results of the grid search as pickled pandas DataFrame in                                                                                                                            
  this file.                                                                                                                                                                                           
                                                                                                                                                                                                       
  CORPUS_FILE: Read the text corpus from this file.                                                                                                                                                    
                                                                                                                                                                                                       
  DOCS_FILE: Read the documents (required to evalute coherence model c_v)                                                                                                                              
  from this file.                                                                                                                                                                                      
                                                                                                                                                                                                       
Options:                                                                                                                                                                                               
  --num-runs INTEGER              Repeat each experiment num-runs times.                                                                                                                               
                                  Default 10

  --max-passes INTEGER            Max number of passes through the data.
                                  Default 50

  --passes-step INTEGER           Increase number of passes by this step size.
                                  Default 5.

  --max-topics INTEGER            Max number of topics in LDA topic model.
                                  Default 100.

  --topic-step INTEGER            Increase number of topics by this step size.
                                  Default 10.

  --coherence-model [c_v|u_mass]  Which coherence model to use. Default: c_v.
  --processes INTEGER             Number of workers. Default 4.
  --mods-info-file PATH           Read MODS info from this file.
  --gen-vis-data                  Generate visualisation JSON data (LDAvis)
                                  for each tested grid configuration.

  --mini-batch-size INTEGER       Mini-batch size. Default 256
  --help                          Show this message and exit.


```

### Setup visualization:

Run sbb-tools webservice like:

```
env CONFIG=config.json env FLASK_APP=qurator/webapp/app.py env FLASK_ENV=development env flask run --host=0.0.0.0 --port=8000
```

Topic modeling interface can be found at: http://localhost:8000/ldavis.html .

Configuration of displayed topic models is done via [config.json](qurator/webapp/config.json).

### Screenshots:

![sbb-ner-demo example](.screenshots/topicm0.png?raw=true)

![sbb-ner-demo example](.screenshots/topicm1.png?raw=true)

![sbb-ner-demo example](.screenshots/topicm2.png?raw=true)