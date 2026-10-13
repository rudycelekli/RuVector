import copy,unittest
from compare import compare_cases,check_receipt,BASE,HEADS,cases,against_inventory,source_receipt,runtime_logs
class Controls(unittest.TestCase):
 def test_original_exact(self):compare_cases({('suite','a'):'ignored, reason'},{('suite','a'):'ignored, reason'})
 def test_missing(self):
  with self.assertRaises(AssertionError):compare_cases({('s','a'):'ok'}, {})
 def test_changed_failure(self):
  with self.assertRaises(AssertionError):compare_cases({('s','a'):'ok'},{('s','a'):'FAILED'})
 def test_new_skip(self):
  with self.assertRaises(AssertionError):compare_cases({('s','a'):'ok'},{('s','a'):'ok',('s','new'):'ignored'}, {'new'})
 def test_skip_reason(self):
  with self.assertRaises(AssertionError):compare_cases({('s','a'):'ignored, old'},{('s','a'):'ignored, new'})
 def test_unknown_extra(self):
  with self.assertRaises(AssertionError):compare_cases({('s','a'):'ok'},{('s','a'):'ok',('s','other'):'ok'})
 def test_duplicate(self):
  with self.assertRaises(AssertionError):cases('Running tests/x (target/debug/deps/x-123abcd)\ntest a ... ok\ntest a ... ok')
 def test_empty_compile_failure(self):
  with self.assertRaises(AssertionError):cases('error: compile failed')
 def test_parser_actual_shape(self):self.assertEqual(cases('     Running tests/foo.rs (target/debug/deps/foo-123abc)\nrunning 1 test\ntest a ... ok\ntest result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out;'),{('foo','a'):'ok'})
 def receipt(self):
  from contract import specs
  names=specs('1161','/source','/proof','/harness')
  commands=[{'name':n,'command':a,'cwd':c,'exit':0,'start_utc':'2026-10-13T00:00:00+00:00','end_utc':'2026-10-13T00:00:01+00:00','start_monotonic':i*2,'end_monotonic':i*2+1,'raw_sha256':'0'*64} for i,(n,a,c) in enumerate(names)]
  return {'source':HEADS['1161'],'number':'1161','phase':'fixed','status':'COMPLETED_RAW_REQUIRES_INDEPENDENT_COMPARISON','platform':'Linux-native','tracked_status':'','source_path':'/source','proof_path':'/proof','harness_path':'/harness','commands':commands}
 def test_valid_receipt(self):check_receipt(self.receipt(),'1161','fixed')
 def test_source_drift(self):
  r=self.receipt();r['source']=BASE
  with self.assertRaises(AssertionError):check_receipt(r,'1161','fixed')
 def test_missing_gate(self):
  r=self.receipt();r['commands'].pop()
  with self.assertRaises(AssertionError):check_receipt(r,'1161','fixed')
 def test_real_gate_failure(self):
  r=self.receipt();r['commands'][3]['exit']=1
  with self.assertRaises(AssertionError):check_receipt(r,'1161','fixed')
 def test_incomplete_run(self):
  r=self.receipt();r['status']='PENDING'
  with self.assertRaises(AssertionError):check_receipt(r,'1161','fixed')
 def test_dirty_source(self):
  r=self.receipt();r['tracked_status']=' M source'
  with self.assertRaises(AssertionError):check_receipt(r,'1161','fixed')
 def test_changed_argv(self):
  r=self.receipt();r['commands'][0]['command']=['rustc','--help']
  with self.assertRaises(AssertionError):check_receipt(r,'1161','fixed')
 def test_clock_reversal(self):
  r=self.receipt();r['commands'][1]['start_monotonic']=0
  with self.assertRaises(AssertionError):check_receipt(r,'1161','fixed')
 def test_common_omission_caught_by_listing(self):
  listing='Running tests/foo.rs (target/debug/deps/foo-123abc)\na: test\nb: test\n2 tests, 0 benchmarks'
  run='Running tests/foo.rs (target/debug/deps/foo-123abc)\nrunning 1 test\ntest a ... ok\ntest result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out;'
  for _ in range(2):
   with self.assertRaises(AssertionError):against_inventory(listing,run)
 def test_running_count_guard(self):
  with self.assertRaises(AssertionError):cases('Running tests/foo.rs (target/debug/deps/foo-123abc)\nrunning 2 tests\ntest a ... ok\ntest result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out;')
 def test_doctest_preserved(self):
  listing='   Doc-tests crate\nsrc/lib.rs - item (line 7): test\n1 test, 0 benchmarks'
  run='   Doc-tests crate\nrunning 1 test\ntest src/lib.rs - item (line 7) ... ok\ntest result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out;'
  self.assertEqual(against_inventory(listing,run),{('doc:crate','src/lib.rs - item (line 7)'):'ok'})
 def test_source_blob_drift(self):
  expected={'path':{'mode':'120000','git_object':'1'*40}}
  row={'path':{'mode':'120000','git_object':'2'*40,'sha256':'3'*64}}
  with self.assertRaises(AssertionError):source_receipt({'source_before':row,'source_after':row},expected)
 def test_source_common_omission(self):
  with self.assertRaises(AssertionError):source_receipt({'source_before':{},'source_after':{}},{'path':{'mode':'100644','git_object':'1'*40}})
 def test_runtime_drift(self):
  with self.assertRaises(AssertionError):runtime_logs('rustc 1.98.1 (a b)\n','cargo 1.98.1 (a b)\n','v20.20.0\n')
 def test_missing_list_summary(self):
  from compare import inventory
  with self.assertRaises(AssertionError):inventory('Running tests/foo.rs (target/debug/deps/foo-123abc)\na: test')
 def test_both_omit_outcome(self):
  listing='Running tests/foo.rs (target/debug/deps/foo-123abc)\na: test\nb: test\n2 tests, 0 benchmarks'
  omitted='Running tests/foo.rs (target/debug/deps/foo-123abc)\nrunning 2 tests\ntest a ... ok\ntest result: ok. 2 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out;'
  for _ in range(2):
   with self.assertRaises(AssertionError):against_inventory(listing,omitted)
if __name__=='__main__' :unittest.main()
