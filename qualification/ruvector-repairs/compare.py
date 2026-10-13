import json,pathlib,re,sys
BASE='31549f798997cbb16b1ec872ca30b9e690bbd3ff'
HEADS={'1161':'1bc63a19957ec770a1f9ceccdef04a43b90c0997','1072':'2af7b0304c6ea39cd005b9af1052d0f67564b5e4'}
NEW={'replacement_returns_only_the_latest_vector_score','deleting_a_replaced_id_removes_all_searchable_versions','repeated_ids_in_a_batch_keep_only_the_final_version','deleted_nearby_graph_nodes_do_not_underfill_live_top_k','replacement_roundtrip_keeps_unique_latest_ids','ordinary_search_and_empty_live_index_keep_existing_behavior','legacy_replacement_snapshot_restores_only_canonical_live_rows','sparse_deleted_labels_survive_restore_and_new_insertion'}
EXPECTED_FAILED=NEW-{'ordinary_search_and_empty_live_index_keep_existing_behavior','sparse_deleted_labels_survive_restore_and_new_insertion'}
def suite_header(line):
    match=re.search(r'Running .*?[/\\]([^/\\ )]+?)-[0-9a-f]+(?:\)|$)',line)
    if match:return match.group(1)
    match=re.match(r'\s*Doc-tests (\S+)',line)
    if match:return 'doc:'+match.group(1)
    return None

def inventory(text):
    out={};suite=None;counts={};summaries=set()
    for line in text.splitlines():
        head=suite_header(line)
        if head:suite=head;assert suite not in counts,'duplicate suite';counts[suite]=0
        match=re.fullmatch(r'(.+): (test|benchmark)',line)
        if match:
            assert suite and match.group(2)=='test','unknown benchmark/list semantics'
            key=(suite,match.group(1));assert key not in out,'duplicate inventory case';out[key]='listed';counts[suite]+=1
        match=re.fullmatch(r'(\d+) tests?, (\d+) benchmarks?',line)
        if match:
            assert suite and suite not in summaries and int(match.group(1))==counts[suite] and int(match.group(2))==0,'inventory terminal count mismatch'
            summaries.add(suite)
    assert counts and summaries==set(counts),'missing complete suite inventory'
    return out

def cases(text):
    out={};suite=None;expected={};summaries=set()
    for line in text.splitlines():
        head=suite_header(line)
        if head:suite=head;assert suite not in expected,'duplicate suite';expected[suite]=None
        match=re.fullmatch(r'running (\d+) tests?',line)
        if match:assert suite;expected[suite]=int(match.group(1))
        match=re.fullmatch(r'test (.+) \.\.\. (ok|FAILED|ignored(?:,.*)?)',line)
        if match:
            assert suite,'missing suite identity';key=(suite,match.group(1));assert key not in out,'duplicate case';out[key]=match.group(2)
        match=re.match(r'test result: (?:ok|FAILED)\. (\d+) passed; (\d+) failed; (\d+) ignored; (\d+) measured; (\d+) filtered out;',line)
        if match:
            assert suite and suite not in summaries,'duplicate summary';summaries.add(suite)
            vals=[int(x) for x in match.groups()];rows=[v for (s,_),v in out.items() if s==suite]
            assert vals[3:]==[0,0],'unsupported measured/filtered test semantics'
            assert expected[suite] is not None and len(rows)==expected[suite]==sum(vals[:3]),'running/terminal count mismatch'
            assert [sum(v=='ok' for v in rows),sum(v=='FAILED' for v in rows),sum(v.startswith('ignored') for v in rows)]==vals[:3],'summary outcome mismatch'
    assert expected and set(expected)==summaries,'missing complete suite outcomes'
    return out

def against_inventory(list_text,run_text):
    listed=inventory(list_text);terminal=cases(run_text)
    assert set(listed)==set(terminal),'listed cases omitted from actual terminal outcomes'
    return terminal

def compare_cases(base,fixed,extra=()):
    filtered={k:v for k,v in fixed.items() if k[1] not in extra}
    assert base==filtered,'original case names/outcomes or skip reasons changed'
    for k,v in fixed.items():
        if k[1] in extra:assert v=='ok','new case must pass, no skip/failure'
def check_receipt(r,number,phase):
    from contract import specs
    import datetime
    assert r['source']==(BASE if phase=='baseline' else HEADS[number]),'source drift'
    assert r['number']==number and r['phase']==phase
    assert r['status']=='COMPLETED_RAW_REQUIRES_INDEPENDENT_COMPARISON'
    assert r['platform'].startswith('Linux-') and r['tracked_status']==''
    expected=specs(number,r['source_path'],r['proof_path'],r['harness_path'])
    assert [(c['name'],c['command'],c['cwd']) for c in r['commands']]==expected,'exact command argv/cwd drift'
    last=None
    for command in r['commands']:
        exit_code=101 if phase=='baseline' and command['name']=='regressions' else (1 if phase=='baseline' and command['name']=='actual-mcp-regression' else 0)
        assert command['exit']==exit_code,(command['name'],command['exit'],exit_code)
        begin=datetime.datetime.fromisoformat(command['start_utc']);end=datetime.datetime.fromisoformat(command['end_utc'])
        assert begin.tzinfo and end.tzinfo and end>=begin
        assert command['end_monotonic']>=command['start_monotonic']
        if last is not None:assert command['start_monotonic']>=last
        last=command['end_monotonic']
        assert len(command['raw_sha256'])==64

def source_receipt(r,expected):
    for field in ['source_before','source_after']:
        actual=r[field];assert set(actual)==set(expected),'source inventory omission'
        for name,row in actual.items():
            wanted=expected[name];assert row['mode']==wanted['mode'] and row['git_object']==wanted['git_object'],'source blob drift'
            if wanted.get('gitlink'):assert row.get('gitlink') is True
            else:assert len(row['sha256'])==64 and not row.get('gitlink')
    assert r['source_before']==r['source_after'],'source bytes changed'

def runtime_logs(rust,cargo,node):
    assert re.fullmatch(r'rustc 1\.98\.1 \(.+\)\n?',rust),'rust runtime drift'
    assert re.fullmatch(r'cargo 1\.98\.1 \(.+\)\n?',cargo),'cargo runtime drift'
    assert node=='v20.19.0\n','node runtime drift'

def compare(number,base,fixed):
    import hashlib
    trees=json.loads((pathlib.Path(__file__).parent/'expected-trees.json').read_text())
    for directory,phase in [(base,'baseline'),(fixed,'fixed')]:
        r=json.loads((directory/'receipt.json').read_text());check_receipt(r,number,phase)
        source_receipt(r,trees['baseline' if phase=='baseline' else number])
        assert r['harness_head'] and len(r['harness_head'])==40
        assert set(r['harness_hashes'])=={'native.py','contract.py','compare.py','native-reopen.js','manifest.json','expected-trees.json'}
        for name,wanted in r['harness_hashes'].items():assert hashlib.sha256((pathlib.Path(__file__).parent/name).read_bytes()).hexdigest()==wanted,'harness byte drift'
        assert set(r['raw_hashes'])=={p.name for p in directory.glob('*.log')}
        for name,wanted in r['raw_hashes'].items():assert hashlib.sha256((directory/name).read_bytes()).hexdigest()==wanted
        for command in r['commands']:assert command['raw_sha256']==r['raw_hashes'][command['name']+'.log']
        runtime_logs((directory/'rust-version.log').read_text(),(directory/'cargo-version.log').read_text(),(directory/'node-version.log').read_text())
    if number=='1161':
        b=against_inventory((base/'regression-list.log').read_text(),(base/'regressions.log').read_text());f=against_inventory((fixed/'regression-list.log').read_text(),(fixed/'regressions.log').read_text())
        assert {k[1] for k in b}==NEW and {k[1] for k in f}==NEW
        assert {k[1] for k,v in b.items() if v=='FAILED'}==EXPECTED_FAILED
        assert all(v in ('FAILED','ok') for v in b.values()) and all(v=='ok' for v in f.values())
        compare_cases(against_inventory((base/'core-list.log').read_text(),(base/'original-core.log').read_text()),against_inventory((fixed/'core-list.log').read_text(),(fixed/'original-core.log').read_text()),NEW)
    if number=='1072':
        expected_errors=['server wrote ruvector.db into project root','server-owned .ruvector/vectors.db was not created','second server claimed VectorDb after lock failure','second server did not report the lock failure on stderr','RUVECTOR_STORAGE_PATH did not select a working VectorDb path','override server wrote ruvector.db into project root']
        negative=(base/'actual-mcp-regression.log').read_text()
        assert all(error in negative for error in expected_errors),'baseline not the expected actual MCP boundary failure'
        assert 'MCP VectorDb path, lock reporting, and HNSW checks passed (#1026)' in (fixed/'actual-mcp-regression.log').read_text()
        for directory in [base,fixed]:
            rows=[json.loads(line) for line in (directory/'native-reopen.log').read_text().splitlines() if line.startswith('{')]
            assert len(rows)==2 and [row['phase'] for row in rows]==['write','read']
            for row in rows:
                assert row['version']=='0.1.31' and row['platform']=='linux' and row['addons']
                assert all(len(addon['sha256'])==64 and addon['path'].endswith('.node') for addon in row['addons'])
    # Full mandatory cargo test inventory and original skip identities remain equal.
    compare_cases(against_inventory((base/'workspace-list.log').read_text(),(base/'cargo-test.log').read_text()),against_inventory((fixed/'workspace-list.log').read_text(),(fixed/'cargo-test.log').read_text()),NEW if number=='1161' else ())
    return {'status':'PASS','number':number,'base':BASE,'candidate':HEADS[number]}
if __name__=='__main__':print(json.dumps(compare(sys.argv[1],pathlib.Path(sys.argv[2]),pathlib.Path(sys.argv[3])),indent=2))
