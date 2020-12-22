import pandas as pd
import urllib


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
            rename(columns={entity_type: 'wikidata'})

        return tmp

    per = load_classes(per_classes, 'person')

    loc = load_classes(loc_classes, 'location')

    org = load_classes(org_classes, 'organisation')

    ent = pd.concat([per, loc, org], sort=True).drop_duplicates(subset=['wikidata']).reset_index(drop=True).set_index('wikidata')

    ent['PER'] = False
    ent['LOC'] = False
    ent['ORG'] = False

    ent.loc[per.wikidata, 'PER'] = True
    ent.loc[loc.wikidata, 'LOC'] = True
    ent.loc[org.wikidata, 'ORG'] = True

    ent['page_title'] = [urllib.parse.unquote(s) for s in ent.sitelink.str.split('/').str[-1].to_list()]

    ent = ent.reset_index().set_index('page_title')

    ent.loc[ent.PER & ent.ORG, 'PER'] = False

    return ent
