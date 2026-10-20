import json,os,pathlib,subprocess,sys,time
from process_runner import bounded, enable_subreaper
enable_subreaper()
src=pathlib.Path(sys.argv[1]).resolve();n=sys.argv[2];results=[]
def gate(label,args,cwd=src,seconds=1200):
 print('\nGATE_BEGIN',label,json.dumps(args),flush=True);start=time.monotonic()
 code,timed_out=bounded(args,cwd,seconds)
 results.append({'gate':label,'exit':code,'seconds':round(time.monotonic()-start,3),'timed_out':timed_out});print('GATE_END',json.dumps(results[-1]),flush=True)
gate('rust-version',['rustc','--version','--verbose'])
gate('cargo-version',['cargo','--version'])
gate('node-version',['node','--version'])
if n=='1161':
 gate('core-build',['cargo','build','--locked','--offline','-p','ruvector-core'])
 gate('actual-eight-regressions',['cargo','test','--locked','--offline','-p','ruvector-core','--test','hnsw_live_replacements'])
 gate('core-lib-tests',['cargo','test','--locked','--offline','-p','ruvector-core','--lib','--tests'])
 gate('core-clippy',['cargo','clippy','--locked','--offline','-p','ruvector-core','--all-targets','--','-D','warnings'])
else:
 cwd=src/'npm/packages/ruvector';gate('package-build',['npm','run','build'],cwd)
 gate('actual-native-regression',['node','test/mcp-vector-store.js'],cwd)
 gate('canonical-package-tests',['npm','test'],cwd)
# Actual policy gates, unmodified. Baseline failure is evidence, never a waiver or pass.
gate('workspace-format',['cargo','fmt','--','--check'])
gate('workspace-all-feature-clippy',['cargo','clippy','--locked','--offline','--all-targets','--all-features','--','-D','warnings'])
gate('workspace-test',['cargo','test','--locked','--offline'])
gate('workspace-bench',['cargo','bench','--locked','--offline'])
print('FINAL_GATE_RESULTS',json.dumps(results),flush=True)
sys.exit(any(x['exit'] for x in results))
