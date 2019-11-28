DATA_DIR ?=data/digisam
OCR_DIR ?=/srv/digisam_ocr
PROCESSES ?=20
MIN_LANG_CONFIDENCE ?=1.0
MIN_ENTROPY_QUANTILE ?=0.2
MAX_ENTROPY_QUANTILE ?=0.8

NER_ENDPOINT ?=http://localhost:8080/ner/1

NER_ENDPOINTS ?=http://b-lx0053.sbb.spk-berlin.de:8080 http://b-lx0053.sbb.spk-berlin.de:8081 http://b-lx0053.sbb.spk-berlin.de:8082 http://b-lx0059.sbb.spk-berlin.de:8080 http://b-lx0059.sbb.spk-berlin.de:8081 http://b-lx0059.sbb.spk-berlin.de:8082

$(DATA_DIR):
	mkdir -p $@

$(DATA_DIR)/fulltext.sqlite3:	$(DATA_DIR)
	altotool $(OCR_DIR) $@ --processes=$(PROCESSES)

$(DATA_DIR)/entropy.pkl:	$(DATA_DIR)/fulltext.sqlite3
	corpusentropy $< $@ --processes=$(PROCESSES)

$(DATA_DIR)/language.pkl:	$(DATA_DIR)/fulltext.sqlite3
	corpuslanguage $< $@ --processes=$(PROCESSES)

$(DATA_DIR)/selection_de.pkl:	$(DATA_DIR)/language.pkl $(DATA_DIR)/entropy.pkl
	select-by-lang-and-entropy $? $@ --min-lang-confidence=$(MIN_LANG_CONFIDENCE) --min-entropy-quantile=$(MIN_ENTROPY_QUANTILE) --max-entropy-quantile=$(MAX_ENTROPY_QUANTILE)

$(DATA_DIR)/digisam-ner-tagged-DC-SBB\\+CONLL\\+GERMEVAL.sqlite3:	$(DATA_DIR)/fulltext.sqlite3 $(DATA_DIR)/selection_de.pkl
	batchner --noproxy $? DC-SBB+CONLL+GERMEVAL digisam-ner-tagged.sqlite3  $(NER_ENDPOINTS) --chunksize=1000

$(DATA_DIR)/digisam-ner-tagged-DC-SBB\\+CONLL\\+GERMEVAL\\+SBB.sqlite3:	$(DATA_DIR)/fulltext.sqlite3 $(DATA_DIR)/selection_de.pkl
	batchner --noproxy $? DC-SBB+CONLL+GERMEVAL+SBB digisam-ner-tagged.sqlite3  $(NER_ENDPOINTS) --chunksize=1000

corpus:	$(DATA_DIR)/language.pkl $(DATA_DIR)/entropy.pkl

alto:	$(DATA_DIR)/digisam-ner-tagged-DC-SBB\\+CONLL\\+GERMEVAL\\+SBB.sqlite3
	alto-annotator $? /srv/digisam_ocr /qurator-share/tmp/alto-ner-annotated --processes=20

sbb-ner: $(DATA_DIR)/digisam-ner-tagged-DC-SBB\\+CONLL\\+GERMEVAL.sqlite3 $(DATA_DIR)/digisam-ner-tagged-DC-SBB\\+CONLL\\+GERMEVAL\\+SBB.sqlite3
	
