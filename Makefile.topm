
# b-lx0053:
#make -f ~/qurator/mono-repo/sbb_tools/Makefile.topm corpus docs ENTITY_LINKING_FILE=digisam/digisam-ner-tagged-DC-SBB-MULTILANG.sqlite3 ENTITIES_FILE=wikipedia/de-ned.sqlite PROCESSES=10

ENTITIES_FILE ?=data/wikidata/de-wikipedia-ner-entities.pkl
MIN_PROBA ?=0.5
PROCESSES ?=4
ENTITY_LINKING_FILE ?=data/digisam/digisam-ner-tagged-DC-SBB-MULTILANG.sqlite3

MODS_INFO ?=data/digisam/mods_info/mods_info_df_all.2019-07-16.pkl

MAX_PASSES ?=200
MIN_FREQ ?=0.1
MAX_TOPICS ?=500
TOPIC_STEP ?=20

ned-corpus-min_proba$(MIN_PROBA)-min_freq$(MIN_FREQ)-%.pkl:	$(ENTITIES_FILE) $(ENTITY_LINKING_FILE)
	extract-corpus --entities-file=$< --processes=$(PROCESSES) --min-proba=$(MIN_PROBA) --min-freq=$(MIN_FREQ) --filter-type="$*" $(word 2,$^) $@

ned-docs-min_proba$(MIN_PROBA)-min_freq$(MIN_FREQ)-%.pkl:	$(ENTITIES_FILE) $(ENTITY_LINKING_FILE)
	extract-docs --entities-file=$< --processes=$(PROCESSES) --min-proba=$(MIN_PROBA) --min-freq=$(MIN_FREQ) --filter-type="$*" $(word 2,$^) $@

corpus:	ned-corpus-min_proba$(MIN_PROBA)-min_freq$(MIN_FREQ)-PER.pkl ned-corpus-min_proba$(MIN_PROBA)-min_freq$(MIN_FREQ)-LOC.pkl ned-corpus-min_proba$(MIN_PROBA)-min_freq$(MIN_FREQ)-ORG.pkl ned-corpus-min_proba$(MIN_PROBA)-min_freq$(MIN_FREQ)-PER,LOC,ORG.pkl

docs:	ned-docs-min_proba$(MIN_PROBA)-min_freq$(MIN_FREQ)-PER.pkl ned-docs-min_proba$(MIN_PROBA)-min_freq$(MIN_FREQ)-LOC.pkl ned-docs-min_proba$(MIN_PROBA)-min_freq$(MIN_FREQ)-ORG.pkl ned-docs-min_proba$(MIN_PROBA)-min_freq$(MIN_FREQ)-PER,LOC,ORG.pkl

ned-lda-grid-search-min_proba$(MIN_PROBA)-min_freq$(MIN_FREQ)-%.pkl:	ned-corpus-min_proba$(MIN_PROBA)-min_freq$(MIN_FREQ)-%.pkl ned-docs-min_proba$(MIN_PROBA)-min_freq$(MIN_FREQ)-%.pkl
	lda-grid-search --processes=$(PROCESSES) --gen-vis-data --num-runs=1 --max-passes=$(MAX_PASSES) --passes-step=$(MAX_PASSES) --max-topics=$(MAX_TOPICS) --topic-step=$(TOPIC_STEP) --mods-info-file=$(MODS_INFO) $@ $^

.PRECIOUS: ned-lda-grid-search-min_proba$(MIN_PROBA)-min_freq$(MIN_FREQ)-%.pkl

grid-search-%:	ned-lda-grid-search-min_proba$(MIN_PROBA)-min_freq$(MIN_FREQ)-%.pkl ;

config-%:
	make-topicm-config data/topic_modelling/ned-lda-grid-search-min_proba$(MIN_PROBA)-min_freq$(MIN_FREQ)-$*.pkl data/topic_modelling/ned-corpus-min_proba$(MIN_PROBA)-min_freq$(MIN_FREQ)-$*.pkl $*

config:	config-PER config-LOC config-ORG config-PER,LOC,ORG
