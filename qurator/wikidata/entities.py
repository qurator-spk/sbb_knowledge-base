import pandas as pd


def load_entities(path, lang):

    per_classes = ['subject', 'fictional-character', 'fictional-person']

    loc_classes = ['geographic-entity', 'fictional-location']

    org_classes = ['armed-organization', 'association', 'business', 'fictional-organisation',
                   'group-of-people', 'institution', 'organ']

    woa = pd.read_pickle("{}/{}-work-of-arts.pkl".format(path, lang))

    def load_classes(cl, entity_type):

        files = ['{}/{}-{}.pkl'.format(path, lang, c) for c in cl]

        tmp = pd.concat([pd.read_pickle(f) for f in files]).\
            drop_duplicates(subset=[entity_type]).\
            reset_index(drop=True)

        tmp = tmp.loc[~tmp[entity_type].isin(woa.woa)].\
            reset_index(drop=True).\
            rename(column={entity_type: 'wikidata'})

        return tmp

    per = load_classes(per_classes, 'person')

    loc = load_classes(loc_classes, 'location')

    org = load_classes(org_classes, 'organisation')

    per['TYPE'] = 'PER'
    loc['TYPE'] = 'LOC'
    org['TYPE'] = 'ORG'

    ent = pd.concat([per, loc, org]).drop_duplicates(subset=['wikidata'], keep=False)

    return ent
