import hashlib,os,pathlib,subprocess

def tracked_source(source):
    source=pathlib.Path(source)
    assert subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=source,text=True)==''
    tree=subprocess.check_output(['git','ls-tree','-rz','--full-tree','HEAD'],cwd=source)
    inventory={}
    for row in tree.split(b'\0'):
        if not row:continue
        info,name=row.split(b'\t',1);mode,kind,oid=info.decode().split();name=os.fsdecode(name);path=source/name
        if mode=='160000':
            inventory[name]={'mode':mode,'git_object':oid,'gitlink':True};continue
        assert kind=='blob',(name,kind)
        raw=os.fsencode(os.readlink(path)) if mode=='120000' else path.read_bytes()
        actual=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
        assert actual==oid,('source blob drift',name)
        assert path.is_symlink()==(mode=='120000'),('source symlink mode drift',name)
        if mode in ('100644','100755'):assert bool(path.stat().st_mode&0o111)==(mode=='100755'),('source executable drift',name)
        inventory[name]={'mode':mode,'git_object':oid,'sha256':hashlib.sha256(raw).hexdigest()}
    assert inventory
    return inventory

def specs(number,source,proof,here):
    source=str(source);package=str(pathlib.Path(source)/'npm/packages/ruvector')
    out=[('rust-version',['rustc','--version'],source),('cargo-version',['cargo','--version'],source),('node-version',['node','--version'],source)]
    if number=='1161':
        out += [('core-list',['cargo','test','--locked','-p','ruvector-core','--lib','--tests','--','--list'],source),('original-core',['cargo','test','--locked','-p','ruvector-core','--lib','--tests'],source),('regression-list',['cargo','test','--locked','-p','ruvector-core','--test','hnsw_live_replacements','--','--list'],source),('regressions',['cargo','test','--locked','-p','ruvector-core','--test','hnsw_live_replacements','--','--test-threads=1'],source)]
    else:
        out += [('npm-install',['npm','install','--no-audit','--no-fund','--package-lock=false'],package),('native-exact-install',['npm','install','--no-save','--no-audit','--no-fund','--package-lock=false','@ruvector/core@0.1.31'],package),('package-build',['npm','run','build'],package),('native-reopen',['node',str(pathlib.Path(here)/'native-reopen.js'),package,str(pathlib.Path(proof)/'native.db')],source),('canonical-package',['npm','test'],package),('actual-mcp-regression',['node','test/mcp-vector-store.js'],package)]
    out += [('cargo-fmt',['cargo','fmt','--all','--','--check'],source),('cargo-clippy',['cargo','clippy','--locked','--all-targets','--all-features','--','-D','warnings'],source),('workspace-list',['cargo','test','--locked','--','--list'],source),('cargo-test',['cargo','test','--locked'],source),('cargo-bench',['cargo','bench','--locked'],source)]
    return out
