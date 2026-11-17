"""Build a conservative EN/PT subtitle locale override from the installed resources.
No third-party Python packages. Binary layout follows akintos/UnrealLocres LocresLib.
Keeps original namespace/key bytes, hashes, version and entry order unchanged.
"""
from pathlib import Path
import argparse, collections, hashlib, json, struct, subprocess

MAGIC=bytes.fromhex('0e147475674a03fc4a15909dc3377f1b')
SAFE_PREFIXES=('ST_CS_','ST_IWD_','ST_BD_','ST_BK_')

class Locres:
    def __init__(self,path):
        self.path=Path(path); self.raw=self.path.read_bytes(); b=self.raw
        assert b[:16]==MAGIC and b[16]==3, 'Expected version 3 locres'
        self.table_offset=struct.unpack_from('<q',b,17)[0]
        self.entries=[]; self.namespaces=[]; self.pos=25
        def u32():
            n=struct.unpack_from('<I',b,self.pos)[0];self.pos+=4;return n
        def string():
            start=self.pos; n=struct.unpack_from('<i',b,self.pos)[0];self.pos+=4
            z=b[self.pos:self.pos+abs(n)*(2 if n<0 else 1)];self.pos+=len(z)
            if n<0: return z[:-2].decode('utf-16-le') if n else ''
            return z[:-1].decode('utf-8') if n else ''
        expected=u32();nc=u32()
        for _ in range(nc):
            nh=u32();ns=string(); kc=u32();self.namespaces.append((ns,nh,kc))
            for _ in range(kc):
                kh=u32();key=string();source_hash=u32(); ip=self.pos;idx=u32()
                self.entries.append(dict(namespace=ns,key=key,key_hash=kh,source_hash=source_hash,index_offset=ip,string_index=idx))
        assert self.pos==self.table_offset and len(self.entries)==expected
        self.strings=[];count=u32()
        for _ in range(count):
            start=self.pos; value=string(); raw=b[start:self.pos];refs=u32()
            self.strings.append(dict(value=value,raw=raw,refs=refs))
        assert self.pos==len(b),'Unexpected trailing data'
        self.lookup={}
        for e in self.entries:
            e['value']=self.strings[e['string_index']]['value']; ident=(e['namespace'],e['key'])
            assert ident not in self.lookup,'Duplicate namespace/key';self.lookup[ident]=e
        assert all(x['refs']>=0 for x in self.strings)
        assert collections.Counter(e['string_index'] for e in self.entries)==collections.Counter({i:x['refs'] for i,x in enumerate(self.strings)}),'Bad refcounts'

    def write(self,path,replacements):
        prefix=bytearray(self.raw[:self.table_offset]);strings=[dict(x) for x in self.strings]
        byvalue={x['value']:i for i,x in enumerate(strings)}
        for ident,text in replacements.items():
            e=self.lookup[ident]; old=e['string_index']
            if text not in byvalue:
                enc=text.encode('utf-16-le')+b'\0\0'
                byvalue[text]=len(strings);strings.append(dict(value=text,raw=struct.pack('<i',-len(enc)//2)+enc,refs=0))
            new=byvalue[text];strings[old]['refs']-=1;strings[new]['refs']+=1
            struct.pack_into('<I',prefix,e['index_offset'],new)
        result=bytes(prefix)+struct.pack('<I',len(strings))+b''.join(x['raw']+struct.pack('<I',x['refs']) for x in strings)
        Path(path).parent.mkdir(parents=True,exist_ok=True);Path(path).write_bytes(result)

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def stats(values):
    a=sorted(values)
    return dict(count=len(a),min=min(a),median=a[len(a)//2],p90=a[int((len(a)-1)*.9)],p95=a[int((len(a)-1)*.95)],p99=a[int((len(a)-1)*.99)],max=max(a))

def build(base,output,extra=None,block=None):
    base=Path(base);output=Path(output);output.mkdir(parents=True,exist_ok=True)
    root=base/'extracted/Sandfall/Content/Localization/Game'
    en=Locres(root/'en-US/Game.locres');pt=Locres(root/'pt-BR/Game.locres')
    extra=set(tuple(x) for x in json.loads(Path(extra).read_text(encoding='utf-8'))) if extra else set()
    assert all(i[0].startswith(('ST_D_','ST_DS_')) for i in extra),'Extra allowlist must use dialogue-only namespaces'
    candidates={i for i in en.lookup if i[0].startswith(SAFE_PREFIXES) or i[0]=='ST_BL_Entries'}|extra
    block=set(tuple(x) for x in json.loads(Path(block).read_text(encoding='utf-8'))) if block else set()
    blocked_candidates=sorted(candidates&block);candidates-=block
    replacements={};missing=[];empty=[];mismatch=[];pairs=[]
    for ident in sorted(candidates):
        if ident not in en.lookup or ident not in pt.lookup:missing.append(ident);continue
        ee=en.lookup[ident];pe=pt.lookup[ident]
        if ee['source_hash']!=pe['source_hash']:mismatch.append(ident);continue
        if not ee['value'].strip() or not pe['value'].strip():empty.append(ident);continue
        text=ee['value']+'\n'+pe['value'];replacements[ident]=text
        pairs.append(dict(namespace=ident[0],key=ident[1],english=ee['value'],portuguese=pe['value'],result=text))
    assert not mismatch,'Source hash mismatch (see input)'
    roundtrip=base/'roundtrip.locres';pt.write(roundtrip,{})
    assert roundtrip.read_bytes()==pt.raw,'Identity roundtrip changed bytes'
    stage=base/'stage';dest=stage/'Sandfall/Content/Localization/Game/pt-BR/Game.locres';pt.write(dest,replacements)
    check=Locres(dest)
    assert list(check.lookup)==list(pt.lookup)
    changed=[]
    for ident,old in pt.lookup.items():
        new=check.lookup[ident]
        assert all(old[k]==new[k] for k in ['namespace','key','key_hash','source_hash','index_offset'])
        assert new['value']==replacements.get(ident,old['value'])
        if old['value']!=new['value']:changed.append(ident)
    assert set(changed)==set(replacements)
    assert len(check.namespaces)==len(pt.namespaces) and check.namespaces==pt.namespaces
    pak=output/'zzz_ClairObscur_EN_PT_Dialogos_P.pak'
    subprocess.run([str(base/'tools/repak/repak.exe'),'pack',str(stage.resolve()),str(pak.resolve()),'--version','V11','--mount-point','../../../'],check=True)
    verify=base/'pak_verify';subprocess.run([str(base/'tools/repak/repak.exe'),'unpack',str(pak.resolve()),'-o',str(verify.resolve()),'-f'],check=True)
    assert (verify/'Sandfall/Content/Localization/Game/pt-BR/Game.locres').read_bytes()==dest.read_bytes()
    files=subprocess.check_output([str(base/'tools/repak/repak.exe'),'list',str(pak.resolve())],text=True).splitlines()
    assert files==['Sandfall/Content/Localization/Game/pt-BR/Game.locres']
    report=dict(input_english_count=len(en.entries),input_portuguese_count=len(pt.entries),candidate_count=len(candidates),changed_count=len(changed),unchanged_count=len(pt.entries)-len(changed),missing_pt_or_en=missing,empty_entries=empty,source_hash_mismatches=mismatch,namespace_changes=dict(collections.Counter(x[0] for x in changed)),line_lengths={lang:stats([len(s) for x in pairs for s in x[lang].splitlines()]) for lang in ['english','portuguese','result']},full_text_lengths={lang:stats([len(x[lang]) for x in pairs]) for lang in ['english','portuguese','result']},source_en_sha256=sha(en.path),source_pt_sha256=sha(pt.path),output_locres_sha256=sha(dest),pak_sha256=sha(pak),pak_files=files,checks=['Byte-exact identity roundtrip','Exact namespace+key pairing','Matching source hashes','No duplicate identities','Every replacement is exact English + LF + official Portuguese','Unselected values and all entry metadata unchanged','Pak contains only pt-BR/Game.locres','Pak extraction byte-equals built locres'],limitations=['No game launch or visual validation performed by builder','Keys absent from official PT resource are explicitly skipped and listed','Mixed interactive namespaces require asset-level allowlist; never inferred from row position'])
    report['blocked_candidates_preserved']=blocked_candidates
    (output/'build_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    (output/'modified_pairs.json').write_text(json.dumps(pairs,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:report[k] for k in ['changed_count','unchanged_count','candidate_count','pak_sha256']},indent=2))
    return report

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--base',default=str(Path(__file__).resolve().parent));ap.add_argument('--output',default=str(Path(__file__).resolve().parent/'candidate'));ap.add_argument('--extra-allowlist');ap.add_argument('--blocklist');a=ap.parse_args();build(a.base,a.output,a.extra_allowlist,a.blocklist)
