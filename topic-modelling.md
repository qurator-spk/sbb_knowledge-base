## Topic modelling of digitalized collections:

Our topic modeling visualisation is currently derived from the very nice and useful [LDAvis package](https://github.com/cpsievert/LDAvis).
This sbb-tools package contains an adapted version of the html/js visualisation interface of LDAvis that has been extended such that 
it can switch between different topic models and provides links into wikidata and the digitalized collections of the SBB.

***

Run sbb-tools webservice like:

```
env CONFIG=config.json env FLASK_APP=qurator/webapp/app.py env FLASK_ENV=development env flask run --host=0.0.0.0 --port=8000
```

### Screenshots:

![sbb-ner-demo example](.screenshots/topicm0.png?raw=true)

![sbb-ner-demo example](.screenshots/topicm1.png?raw=true)

![sbb-ner-demo example](.screenshots/topicm2.png?raw=true)