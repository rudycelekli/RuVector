import hashlib,json,os,pathlib,subprocess,sys
q=pathlib.Path(sys.argv[1]).resolve();src=pathlib.Path(sys.argv[2]).resolve();n=sys.argv[3];phase=sys.argv[4];m=json.loads((q/'manifest.json').read_text());run=lambda *a:subprocess.check_output(['git','-C',str(src),*a],text=True).strip()
assert run('rev-parse','HEAD')==m['main']
assert run('status','--porcelain')==''
# Verify the exact original public PR object and its ancestry remain available.
original=m['candidates'][n]['published_head'];subprocess.run(['git','-C',str(src),'fetch','--no-tags','https://github.com/rudycelekli/RuVector.git',original],check=True)
assert run('rev-parse','FETCH_HEAD')==original
base=m['candidates'][n]['original_base']
subprocess.run(['git','-C',str(src),'fetch','--no-tags','https://github.com/ruvnet/RuVector.git',base],check=True)
assert run('rev-parse','FETCH_HEAD')==base
subprocess.run(['git','-C',str(src),'merge-base','--is-ancestor',base,original],check=True)
if phase=='fixed':
 subprocess.run(['git','-C',str(src),'apply','--index',str(q/f'{n}.patch')],check=True)
 assert run('write-tree')==m['candidates'][n]['tree']
else:
 # Only the exact candidate regression inputs are overlaid on unchanged baseline production.
 if n=='1161':
  import shutil
  shutil.copytree(q/'regressions1161',src/'crates/ruvector-core/tests',dirs_exist_ok=True)
 else:
  (src/'npm/packages/ruvector/test/mcp-vector-store.js').write_bytes((q/'mcp-vector-store.js').read_bytes())
print(json.dumps({'phase':phase,'candidate':n,'baseline':m['main'],'original_pr_head':original,'expected_candidate_tree':m['candidates'][n]['tree'],'actual_tree':run('write-tree'),'patch_sha256':hashlib.sha256((q/f'{n}.patch').read_bytes()).hexdigest()}))
