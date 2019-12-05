
ALTOSOURCEPATH ?=/srv/digisam_ocr
ALTOTARGETPATH ?=/qurator-share/alto-ner-annotated

DATA_DIR ?=data/digisam

PROCESSES ?=20

MIN_LANG_CONFIDENCE ?=1.0
MIN_ENTROPY_QUANTILE ?=0.2
MAX_ENTROPY_QUANTILE ?=0.8

NER_ENDPOINTS ?=http://b-lx0053.sbb.spk-berlin.de:8080 http://b-lx0053.sbb.spk-berlin.de:8081 http://b-lx0053.sbb.spk-berlin.de:8082 http://b-lx0059.sbb.spk-berlin.de:8080 http://b-lx0059.sbb.spk-berlin.de:8081 http://b-lx0059.sbb.spk-berlin.de:8082

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

sbb-ner: $(DATA_DIR)/digisam-ner-tagged-DC-SBB-MULTILANG.sqlite3
	
