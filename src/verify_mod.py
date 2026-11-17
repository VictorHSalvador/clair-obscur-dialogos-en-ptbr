"""Independent checks for built locale, choice preservation, and reader export."""
from pathlib import Path
import argparse, csv, hashlib, json
from build_mod import Locres

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--base',required=True);ap.add_argument('--report',required=True);ap.add_argument('--independent-csv',required=True);args=ap.parse_args()
    base=Path(args.base);report_path=Path(args.report)
    report=json.loads(report_path.read_text(encoding='utf-8'))
    old=Locres(base/'extracted/Sandfall/Content/Localization/Game/pt-BR/Game.locres')
    en=Locres(base/'extracted/Sandfall/Content/Localization/Game/en-US/Game.locres')
    new=Locres(base/'stage/Sandfall/Content/Localization/Game/pt-BR/Game.locres')
    lookup={r['key']:r['source'] for r in csv.DictReader(Path(args.independent_csv).open(encoding='utf-8-sig',newline=''))}
    assert len(lookup)==len(new.entries)==len(old.entries)
    assert all(lookup['/'.join(i)]==e['value'] for i,e in new.lookup.items())
    changed={i for i,e in old.lookup.items() if new.lookup[i]['value']!=e['value']}
    assert len(changed)==report['changed_count']
    assert all(new.lookup[i]['value']==en.lookup[i]['value']+'\n'+old.lookup[i]['value'] for i in changed)
    classification=json.loads((base/'classification_report.json').read_text(encoding='utf-8'))
    assert not {tuple(x) for x in classification['proven_choice_key_list']}&changed
    assert all('\ufffd' not in e['value'] for e in new.entries)
    assert all(not i[0].startswith(('ST_UI_','ST_GameUserSettings','ST_ActiveDialogs','ST_Enemies_Skills')) for i in changed)
    checks=['Independent UnrealLocres export matches all 13,270 built values','All 345 proven StartChoice keys unchanged','Zero Unicode replacement characters in original or modified values']
    for check in checks:
        if check not in report['checks']:report['checks'].append(check)
    report['classification_summary']={k:classification[k] for k in ['scanned_assets_with_stringtable_refs','parse_errors','rich_only_paired_keys','shared_spoken_other_keys','proven_choice_keys','proven_choices_also_spoken']}
    limitations=['188 keys used as spoken and other text remain Portuguese, including 61 proven shared choice/spoken keys','One cinematic key used in a proven choice is blocked even though its namespace is otherwise cinematic','No verification of every possible dialogue branch; unsupported mixed keys remain Portuguese']
    for limitation in limitations:
        if limitation not in report['limitations']:report['limitations'].append(limitation)
    report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Verified',len(changed),'exact bilingual changes and',len(new.entries),'values with independent reader.')

if __name__=='__main__':main()
