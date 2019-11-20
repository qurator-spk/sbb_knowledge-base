DATA_DIR ?=data/digisam
OCR_DIR ?=/srv/digisam_ocr
PROCESSES ?=20
MIN_LANG_CONFIDENCE ?=1.0
MIN_ENTROPY_QUANTILE ?=0.2
MAX_ENTROPY_QUANTILE ?=0.8

NER_ENDPOINT ?=http://localhost:8080/ner/1

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

$(DATA_DIR)/digisam-ner-tagged.sqlite3:	$(DATA_DIR)/fulltext.sqlite3 $(DATA_DIR)/selection_de.pkl
	ner $? $(NER_ENDPOINT) $@

all: $(DATA_DIR)/digisam-ner-tagged.sqlite3
	
