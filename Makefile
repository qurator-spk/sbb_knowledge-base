
ALTOSOURCEPATH ?=/srv/digisam_ocr
ALTOTARGETPATH ?=/qurator-share/alto-ner-annotated

DATA_DIR ?=data/digisam
WIKI_DATA_DIR ?=data/wikidata

PROCESSES ?=20

MIN_LANG_CONFIDENCE ?=1.0
MIN_ENTROPY_QUANTILE ?=0.2
MAX_ENTROPY_QUANTILE ?=0.8

NER_ENDPOINTS ?=http://b-lx0053.sbb.spk-berlin.de:8080 http://b-lx0053.sbb.spk-berlin.de:8081 http://b-lx0053.sbb.spk-berlin.de:8082 http://b-lx0059.sbb.spk-berlin.de:8080 http://b-lx0059.sbb.spk-berlin.de:8081 http://b-lx0059.sbb.spk-berlin.de:8082

SPARQL_ENDPOINT ?=http://b-lx0053.sbb.spk-berlin.de/wikidata2/namespace/wdq/sparql

$(DATA_DIR):
	mkdir -p $@

$(DATA_DIR)/fulltext.sqlite3:	$(DATA_DIR)
	altotool $(ALTOSOURCEPATH) $@ --processes=$(PROCESSES)

$(DATA_DIR)/entropy.pkl:	$(DATA_DIR)/fulltext.sqlite3
	corpusentropy $< $@ --processes=$(PROCESSES)

$(DATA_DIR)/language.pkl:	$(DATA_DIR)/fulltext.sqlite3
	corpuslanguage $< $@ --processes=$(PROCESSES)

$(DATA_DIR)/DE-NL-FR-EN.pkl:    $(DATA_DIR)/language.pkl
	select-by-lang $? $@ DE NL FR EN

$(DATA_DIR)/DE.pkl:    $(DATA_DIR)/language.pkl
	select-by-lang $? $@ DE

$(DATA_DIR)/selection_de.pkl:	$(DATA_DIR)/language.pkl $(DATA_DIR)/entropy.pkl
	select-by-lang-and-entropy $? $@ --min-lang-confidence=$(MIN_LANG_CONFIDENCE) --min-entropy-quantile=$(MIN_ENTROPY_QUANTILE) --max-entropy-quantile=$(MAX_ENTROPY_QUANTILE)

$(DATA_DIR)/digisam-ner-tagged-DC-SBB-MULTILANG.sqlite3:	$(DATA_DIR)/fulltext.sqlite3 $(DATA_DIR)/DE-NL-FR-EN.pkl
	batchner --noproxy --chunksize=1000 --outfile $@ $? DC-SBB-MULTILANG  $(NER_ENDPOINTS)

corpus:	$(DATA_DIR)/language.pkl $(DATA_DIR)/entropy.pkl

alto-ner:	$(DATA_DIR)/digisam-ner-tagged-DC-SBB-MULTILANG.sqlite3
	alto-annotator $? $(ALTOSOURCEPATH) $(ALTOTARGETPATH) --processes=$(PROCESSES)

QUERIES:=$(wildcard sparql/*.query)
DE_QUERY_RESULTS:=$(patsubst sparql/%.query, $(WIKI_DATA_DIR)/de-%.pkl, $(QUERIES))
FR_QUERY_RESULTS:=$(patsubst sparql/%.query, $(WIKI_DATA_DIR)/fr-%.pkl, $(QUERIES))
EN_QUERY_RESULTS:=$(patsubst sparql/%.query, $(WIKI_DATA_DIR)/en-%.pkl, $(QUERIES))

$(WIKI_DATA_DIR)/de-%.pkl : sparql/%.query
	run-sparql --query-file $< $@  --endpoint $(SPARQL_ENDPOINT) --lang de --site de.wikipedia.org

$(WIKI_DATA_DIR)/fr-%.pkl : sparql/%.query
	run-sparql --query-file $< $@  --endpoint $(SPARQL_ENDPOINT) --lang fr --site fr.wikipedia.org

$(WIKI_DATA_DIR)/en-%.pkl : sparql/%.query
	run-sparql --query-file $< $@  --endpoint $(SPARQL_ENDPOINT) --lang en --site en.wikipedia.org


sparql:	$(DE_QUERY_RESULTS) $(FR_QUERY_RESULTS) $(EN_QUERY_RESULTS)  

sbb-ner: $(DATA_DIR)/digisam-ner-tagged-DC-SBB-MULTILANG.sqlite3
	
