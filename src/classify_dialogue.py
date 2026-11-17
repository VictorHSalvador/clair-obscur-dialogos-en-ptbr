"""Conservative cooked Blueprint bytecode evidence for mixed string tables.

Recognizes EX_TextConst/StringTableEntry constants and exact assignment sequence
to FRichDialogueLine.LineText. Every other use blocks the key, preserving choices.
Does not require executing game code or changing assets.
"""
from pathlib import Path
import argparse, collections, hashlib, json, re, struct
from build_mod import Locres

BASE=Path(__file__).resolve().parent

def names(path):
    b=path.read_bytes();assert struct.unpack_from('<i',b,4)[0]==-8
    pos=24;custom=struct.unpack_from('<i',b,pos)[0];pos+=4+custom*20+4
    n=struct.unpack_from('<i',b,pos)[0];pos+=4+abs(n)*(2 if n<0 else 1)+4
    count,offset=struct.unpack_from('<ii',b,pos);pos=offset;out=[]
    for _ in range(count):
        n=struct.unpack_from('<i',b,pos)[0];pos+=4
        raw=b[pos:pos+abs(n)*(2 if n<0 else 1)];pos+=len(raw)+4
        out.append(raw[:-2].decode('utf-16-le') if n<0 else raw[:-1].decode('utf-8'))
    return out

def classify():
    refs=collections.defaultdict(list);assets=0;errors=[];types=collections.Counter()
    pattern=re.compile(rb'\x29\x04(.{4})\x1f(/Game/StringTables/[^\x00]+)\x00\x1f([^\x00]+)\x00',re.S)
    for asset in sorted((BASE/'dialogue_assets').rglob('*.uasset')):
        xp=asset.with_suffix('.uexp')
        if not xp.exists():continue
        b=xp.read_bytes()
        if b'/Game/StringTables/' not in b:continue
        try:ns=names(asset)
        except Exception as e:errors.append([str(asset),str(e)]);continue
        assets+=1
        lineidx=next((i for i,x in enumerate(ns) if x.startswith('LineText_')),None)
        richidx=next((i for i,x in enumerate(ns) if x=='K2Node_MakeStruct_FRichDialogueLine'),None)
        hasrich='StartRichDialogueLines' in ns
        choice_offsets=set()
        if 'StartChoice' in ns:
            choice_call=b'\x45'+struct.pack('<II',ns.index('StartChoice'),0)+b'\x17\x00'
            # EX_SetArray of literal text values, consumed directly as StartChoice's
            # first parameter. Require the exact same 16-byte array field path.
            for array in re.finditer(rb'\x31\x00\x01\x00\x00\x00',b):
                start=array.start();field=b[start+2:start+18];pos=start+18;items=[]
                while True:
                    text=pattern.match(b,pos)
                    if not text:break
                    items.append(pos);pos=text.end()
                if items and b[pos:pos+1]==b'\x32' and choice_call+field in b[pos+1:pos+180]:choice_offsets.update(items)
        for m in pattern.finditer(b):
            table=m[2].decode('utf-8').rsplit('.',1)[-1];key=m[3].decode('utf-8');start=m.start()
            # EX_Let + FFieldPath(LineText) + EX_StructMemberContext +
            # FFieldPath(LineText) + EX_LocalVariable + FFieldPath(FRichDialogueLine).
            # Exact 51-byte structure; package indices/instance number may differ.
            prefix=b[max(0,start-51):start]
            kind='other_text_use'
            if start in choice_offsets:kind='choice_array_for_StartChoice'
            if lineidx is not None and richidx is not None and hasrich and len(prefix)==51:
                linename=struct.pack('<II',lineidx,0)
                if (prefix[:5]==b'\x0f\x01\0\0\0' and prefix[5:13]==linename
                    and prefix[17:22]==b'\x42\x01\0\0\0' and prefix[22:30]==linename
                    and prefix[34:39]==b'\x00\x01\0\0\0' and struct.unpack_from('<I',prefix,39)[0]==richidx):
                    kind='rich_dialogue_line_text'
            if key.endswith('_Display'):kind='display_narration'
            types[kind]+=1
            refs[(table,key)].append(dict(asset=str(asset.relative_to(BASE/'dialogue_assets')).replace('\\','/'),offset=start,kind=kind,prefix_hex=prefix.hex()))
    allow=[];shared=[];unknown=[];outside=[];blocked=[]
    for ident,rr in sorted(refs.items()):
        kinds={r['kind'] for r in rr}
        if kinds=={'rich_dialogue_line_text'}:
            if ident[0].startswith(('ST_D_','ST_DS_')):allow.append(ident)
            else:outside.append(ident)
        elif 'rich_dialogue_line_text' in kinds:shared.append(ident);blocked.append(ident)
        else:unknown.append(ident);blocked.append(ident)
    root=BASE/'extracted/Sandfall/Content/Localization/Game'
    en=Locres(root/'en-US/Game.locres');pt=Locres(root/'pt-BR/Game.locres')
    eligible=[i for i in allow if i in en.lookup and i in pt.lookup]
    proven_choices=[i for i,rr in refs.items() if any(x['kind']=='choice_array_for_StartChoice' for x in rr)]
    report=dict(scanned_assets_with_stringtable_refs=assets,parse_errors=errors,reference_types=dict(types),unique_keys=len(refs),rich_only_keys=len(allow),rich_only_paired_keys=len(eligible),shared_spoken_other_keys=len(shared),shared_spoken_other_paired_keys=len([i for i in shared if i in en.lookup and i in pt.lookup]),proven_choice_keys=len(proven_choices),proven_choices_also_spoken=len(set(proven_choices)&set(shared)),other_only_keys=len(unknown),outside_mixed_namespaces_preserved=outside,allowlist_by_namespace=dict(collections.Counter(x[0] for x in eligible)),shared_keys=shared,proven_choice_key_list=sorted(proven_choices),unknown_keys=unknown,method='Exact cooked Blueprint EX_Let assignment to FRichDialogueLine.LineText; asset must contain StartRichDialogueLines. Choice proof: EX_SetArray of TextConst values immediately consumed by StartChoice with identical array field path. Exclude every key with any other TextConst use, plus Display narration. Extra allowlist restricted to ST_D_/ST_DS_; blockers override all subtitle families.',limitations=['Only extracted assets with Dialogue in path scanned. Unreferenced or unsupported expression shapes stay Portuguese.','Other use conservatively includes choice text and unknown uses; counts are upper bounds for actual selectable choices.','No uasset, uexp, blueprint or runtime files are modified.'])
    (BASE/'dialogue_allowlist.json').write_text(json.dumps(allow,ensure_ascii=False,indent=2),encoding='utf-8')
    (BASE/'dialogue_blocklist.json').write_text(json.dumps(blocked,ensure_ascii=False,indent=2),encoding='utf-8')
    (BASE/'classification_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    evidence=[dict(namespace=i[0],key=i[1],references=rr) for i,rr in sorted(refs.items())]
    (BASE/'classification_evidence.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ['shared_keys','unknown_keys','allowlist_by_namespace','proven_choice_key_list','outside_mixed_namespaces_preserved']},indent=2))

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--base',default=str(BASE));args=ap.parse_args();BASE=Path(args.base).resolve();classify()
