import hashlib,json,os,pathlib,platform,subprocess,sys,time,datetime
from contract import tracked_source,specs
source=pathlib.Path(sys.argv[1]).resolve(); proof=pathlib.Path(sys.argv[2]).resolve(); proof.mkdir(parents=True,exist_ok=True)
number=sys.argv[3];phase=sys.argv[4]; here=pathlib.Path(__file__).resolve().parent
manifest=json.loads((here/'manifest.json').read_text());expected=manifest['base'] if phase=='baseline' else manifest['candidates'][number]
assert platform.system()=='Linux'
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,text=True).strip()==expected
receipt={'status':'PENDING','source':expected,'phase':phase,'number':number,'platform':platform.platform(),'commands':[],'source_path':str(source),'proof_path':str(proof),'harness_path':str(here),'source_before':tracked_source(source),'harness_head':os.environ.get('GITHUB_SHA'),'harness_hashes':{name:hashlib.sha256((here/name).read_bytes()).hexdigest() for name in ['native.py','contract.py','compare.py','native-reopen.js','manifest.json','expected-trees.json']}}
def run(name,cmd,cwd=source):
    start=time.monotonic();iso_start=datetime.datetime.now(datetime.timezone.utc).isoformat()
    with (proof/(name+'.log')).open('wb') as log:
        result=subprocess.run(cmd,cwd=cwd,stdout=log,stderr=subprocess.STDOUT,env=dict(os.environ,RUVECTOR_EMBEDDER='hash',NO_COLOR='1'))
    receipt['commands'].append({'name':name,'command':cmd,'cwd':str(cwd),'exit':result.returncode,'start_utc':iso_start,'end_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'start_monotonic':start,'end_monotonic':time.monotonic(),'raw_sha256':hashlib.sha256((proof/(name+'.log')).read_bytes()).hexdigest()})
    (proof/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return result.returncode
try:
    run('rust-version',['rustc','--version']);run('cargo-version',['cargo','--version']);run('node-version',['node','--version'])
    for path,wanted in manifest['source_hashes'][number].items():
        if phase=='fixed':assert hashlib.sha256((source/path).read_bytes()).hexdigest()==wanted,path
    if number=='1161':
        run('core-list',['cargo','test','--locked','-p','ruvector-core','--lib','--tests','--','--list'])
        run('original-core',['cargo','test','--locked','-p','ruvector-core','--lib','--tests'])
        if phase=='baseline':
            for path in manifest['source_hashes'][number]:
                if path.startswith('crates/ruvector-core/tests/'):
                    target=source/path;assert not target.exists(),path;target.parent.mkdir(parents=True,exist_ok=True)
                    target.write_bytes(subprocess.check_output(['git','show',manifest['candidates'][number]+':'+path],cwd=source))
        run('regression-list',['cargo','test','--locked','-p','ruvector-core','--test','hnsw_live_replacements','--','--list'])
        run('regressions',['cargo','test','--locked','-p','ruvector-core','--test','hnsw_live_replacements','--','--test-threads=1'])
        if phase=='baseline':
            for path in manifest['source_hashes'][number]:
                if path.startswith('crates/ruvector-core/tests/'):(source/path).unlink()
    else:
        package=source/'npm/packages/ruvector'
        assert run('npm-install',['npm','install','--no-audit','--no-fund','--package-lock=false'],package)==0
        assert run('native-exact-install',['npm','install','--no-save','--no-audit','--no-fund','--package-lock=false','@ruvector/core@0.1.31'],package)==0
        assert run('package-build',['npm','run','build'],package)==0
        run('native-reopen',['node',str(here/'native-reopen.js'),str(package),str(proof/'native.db')])
        run('canonical-package',['npm','test'],package)
        if phase=='baseline':
            path='npm/packages/ruvector/test/mcp-vector-store.js';target=source/path;assert not target.exists(),path;target.write_bytes(subprocess.check_output(['git','show',manifest['candidates'][number]+':'+path],cwd=source))
        run('actual-mcp-regression',['node','test/mcp-vector-store.js'],package)
        if phase=='baseline':(source/'npm/packages/ruvector/test/mcp-vector-store.js').unlink()
    # Contribution guide mandatory gates: preserve real failures, no substitutions.
    run('cargo-fmt',['cargo','fmt','--all','--','--check'])
    run('cargo-clippy',['cargo','clippy','--locked','--all-targets','--all-features','--','-D','warnings'])
    run('workspace-list',['cargo','test','--locked','--','--list'])
    run('cargo-test',['cargo','test','--locked'])
    run('cargo-bench',['cargo','bench','--locked'])
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,text=True).strip()==expected
    receipt['tracked_status']=subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=source,text=True)
    assert receipt['tracked_status']=='',receipt['tracked_status']
    for path,wanted in manifest['source_hashes'][number].items():
        if phase=='fixed':assert hashlib.sha256((source/path).read_bytes()).hexdigest()==wanted,path
    receipt['source_after']=tracked_source(source)
    assert receipt['source_before']==receipt['source_after']
    assert [(c['name'],c['command'],c['cwd']) for c in receipt['commands']]==specs(number,source,proof,here)
    receipt['status']='COMPLETED_RAW_REQUIRES_INDEPENDENT_COMPARISON'
finally:
    receipt['raw_hashes']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in proof.glob('*.log')}
    (proof/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
# Deliberately no aggregate PASS: baseline regressions should fail; full inventory must be reviewed.
