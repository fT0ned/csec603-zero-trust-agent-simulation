"""Presentation-only original/amended comparison; no statistical recomputation.

Run only after actual replacement data and the amendment's independent quality
review exist. Missing input files fail before any output is created. Defaults:
  python scripts/compare_timing_amendment.py
Optional --original, --amended, --output and --quality-review override locations.
This helper never endorses analyzer support labels over the original quality veto.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
ORIGINAL_LABEL='Original collection: quality veto retained; raw analyzer judgments are not accepted confirmatory claims'
AMENDED_LABEL='Amended collection: conditional amendment only; requires independent quality acceptance and preserves original veto'

# Remaining scalar fields are identity/stratum fields by default. This safely
# retains condition-specific S4 records and future added strata, rather than
# accidentally matching them across different model/mode/payload populations.
OUTPUT_FIELDS={
 'n_left','n_right','expected_n_left','expected_n_right','paired','p_value','p_holm','family_size',
 'method','statistic','discordant_left','discordant_right','effect','inferential_role','interpretation','interpretation_note',
 'judgment','reason','alpha','minimum_practical_difference','expected_direction',
 'statistical_requirement_met','practical_requirement_met','contrast_judgments','note',
 'detected','altered_copies','rate','count','successes','n','ci_low','ci_high','estimate',
 'eligibility','eligibility_by_collection','supported','support','exposure_effect_bounds',
 'conservative_effect','practical_effect','exposure_effect','effect_bounds',
}
EXCLUDED_IDENTITY={'collection_id','collection_root','collection_manifest_sha256','collection_config_sha256'}

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def key_fields(records):
    return sorted({name for row in records for name,value in row.items()
                   if name not in OUTPUT_FIELDS and name not in EXCLUDED_IDENTITY
                   and not name.startswith('source') and not name.endswith('_path')
                   and not isinstance(value,(dict,list))})

def join_rows(original,amended):
    fields=key_fields(original+amended)
    def indexed(rows):
        result={}
        for row in rows:
            key=json.dumps({field:row.get(field) for field in fields},sort_keys=True,separators=(',',':'))
            if key in result:raise ValueError('Duplicate contrast identity; refusing ambiguous join: '+key)
            result[key]=row
        return result
    before,after=indexed(original),indexed(amended)
    return [{'key':json.loads(key),'match_status':'matched' if key in before and key in after else 'missing_amended' if key in before else 'missing_original',
             'original_quality_label':ORIGINAL_LABEL,'amended_quality_label':AMENDED_LABEL,
             'original':before.get(key),'amended':after.get(key)} for key in sorted(set(before)|set(after))]

def flatten(value,prefix=''):
    result={}
    for key,item in value.items():
        name=prefix+key
        if isinstance(item,dict):result.update(flatten(item,name+'.'))
        else:result[name]=json.dumps(item,sort_keys=True) if isinstance(item,list) else item
    return result

def write_csv(path,rows):
    flattened=[]
    for row in rows:
        flat={**row['key'],'match_status':row['match_status'],
              'original_quality_label':row['original_quality_label'],'amended_quality_label':row['amended_quality_label']}
        for side in ['original','amended']:
            flat[side+'_present']=row[side] is not None
            if row[side] is not None:flat.update(flatten(row[side],side+'.'))
        flattened.append(flat)
    fields=list(dict.fromkeys(key for row in flattened for key in row)) or ['No contrast rows']
    with path.open('w',encoding='utf-8',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader();writer.writerows(flattened)

def assessment(report,path):
    # Prefer the assessment embedded in the exact supplied report; never join a
    # newer sibling assessment to an older report silently.
    data=report.get('hypothesis_assessment')
    if isinstance(data,dict):return data,None
    sibling=path.parent/'hypothesis-assessment.json'
    if sibling.is_file():return json.loads(sibling.read_text(encoding='utf-8')),sibling
    return {},None

def compare(original_path,amended_path,output_path,quality_review=None):
    original_path=Path(original_path).resolve();amended_path=Path(amended_path).resolve();out=Path(output_path).resolve()
    # Validate every input before creating directories. No placeholder/future
    # observations are generated when the amended report is unavailable.
    for path in [original_path,amended_path]+([Path(quality_review).resolve()] if quality_review else []):
        if not path.is_file():raise FileNotFoundError('Required actual evidence is unavailable: '+str(path))
    if original_path==amended_path:raise ValueError('Original and amended report must be distinct preserved files')
    if out.is_relative_to(original_path.parent) or out.is_relative_to(amended_path.parent):
        raise ValueError('Select a new presentation output directory, not an original/amended analysis directory')
    original=json.loads(original_path.read_text(encoding='utf-8'));amended=json.loads(amended_path.read_text(encoding='utf-8'))
    for name,report in [('original',original),('amended',amended)]:
        if not isinstance(report.get('comparisons'),list):raise ValueError(name+' report has no comparisons array')
    oh,ohpath=assessment(original,original_path);ah,ahpath=assessment(amended,amended_path)
    sections={'contrasts':join_rows(original['comparisons'],amended['comparisons']),
              'hypothesis-summary':join_rows(oh.get('hypotheses',[]),ah.get('hypotheses',[])),
              'hypothesis-contrasts':join_rows(oh.get('contrasts',[]),ah.get('contrasts',[])),
              'sanity-checks':join_rows(oh.get('sanity_checks',[]),ah.get('sanity_checks',[]))}
    paths=[original_path,amended_path]+[p for p in [ohpath,ahpath] if p is not None]
    if quality_review:paths.append(Path(quality_review).resolve())
    result={'schema_version':1,'kind':'Presentation-only full outer join; no test, effect, CI or Holm recomputation',
            'original_quality_label':ORIGINAL_LABEL,'amended_quality_label':AMENDED_LABEL,
            'claim_boundary':'Side-by-side numbers do not erase the original veto or imply exchangeability of replacements; raw analyzer labels are retained solely for transparency.',
            'join_rule':'All scalar identity/stratum fields except collection identity/source paths; includes left/right/metric, condition when present, model/mode/phase, scenario, lifetime, revocation and approval strata. Unknown scalar fields are retained by default; ambiguous duplicate identities fail.',
            'sources':{str(p):sha(p) for p in paths},'helper_sha256':sha(Path(__file__)),
            'quality_review_attached':bool(quality_review),'quality_acceptance_inferred':False,
            'original_hypothesis_eligibility':oh.get('eligibility'),
            'amended_hypothesis_eligibility':ah.get('eligibility'),
            'original_hypothesis_eligibility_by_collection':oh.get('eligibility_by_collection'),
            'amended_hypothesis_eligibility_by_collection':ah.get('eligibility_by_collection'),
            'sections':sections,
            'counts':{name:{'rows':len(rows),'matched':sum(r['match_status']=='matched' for r in rows),
                      'missing_original':sum(r['match_status']=='missing_original' for r in rows),
                      'missing_amended':sum(r['match_status']=='missing_amended' for r in rows)} for name,rows in sections.items()}}
    out.mkdir(parents=True,exist_ok=True)
    for name,rows in sections.items():write_csv(out/(name+'.csv'),rows)
    (out/'comparison.json').write_text(json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')
    (out/'README.md').write_text('# Original versus conditional timing amendment\n\n'+ORIGINAL_LABEL+'\n\n'+AMENDED_LABEL+'\n\nAll contrasts are retained in a full outer join, including unmeasured and unmatched entries. CSV columns preserve original/amended effect estimates, confidence bounds, sample counts, p-values, Holm adjustments, methods and raw judgments. Missing sides are blank/null, never zero. `comparison.json` preserves complete source rows and report hashes, eligibility diagnostics and wrapper quality labels. No statistical procedure is rerun.\n\nUse only after actual replacement data and independent quality review. A supplied quality-review file is pinned for traceability; the helper does not infer that its contents approve the amendment. Original unqualified analyzer support labels remain quality-vetoed. The amendment is conditional and cannot retroactively fix the original collection.\n',encoding='utf-8')
    return result

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--original',default=str(ROOT/'results/study-002/analysis/report.json'))
    parser.add_argument('--amended',default=str(ROOT/'results/timing-repair-001/analysis-amended/report.json'))
    parser.add_argument('--output',default=str(ROOT/'results/timing-repair-001/analysis-comparison'))
    parser.add_argument('--quality-review',help='Optional already-reviewed actual quality document to pin, never an inferred approval')
    args=parser.parse_args(argv)
    result=compare(args.original,args.amended,args.output,args.quality_review)
    print(json.dumps(result['counts']))

if __name__=='__main__':main()
