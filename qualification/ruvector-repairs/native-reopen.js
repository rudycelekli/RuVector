// Native persistence control: separate processes, no MCP intelligence JSON import.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const {spawnSync} = require('node:child_process');
const root = process.argv[2];
const database = process.argv[3];
const phase = process.argv[4];
const native = require(path.join(root, 'node_modules/@ruvector/core'));
const metadata = require(path.join(root, 'node_modules/@ruvector/core/package.json'));
assert.equal(metadata.version, '0.1.31');
const addonPaths = Object.keys(require.cache).filter(p => p.endsWith('.node'));
assert.ok(addonPaths.length > 0, 'actual native addon required');
if (!phase) {
  for (const step of ['write', 'read']) {
    const run = spawnSync(process.execPath, [__filename, root, database, step], {encoding:'utf8'});
    process.stdout.write(run.stdout); process.stderr.write(run.stderr);
    assert.equal(run.status, 0, `${step} process must succeed`);
  }
  assert.ok(!fs.existsSync(path.join(path.dirname(database), 'intelligence.json')));
} else {
  (async () => {
    const Constructor = native.VectorDb || native.VectorDB;
    assert.equal(typeof Constructor, 'function');
    const db = new Constructor({dimensions:2, distanceMetric:'Euclidean', storagePath:database,
      hnswConfig:{m:8,efConstruction:100,efSearch:100,maxElements:100}});
    if (phase === 'write') {
      assert.equal(await db.insert({id:'persisted-offline-id',vector:new Float32Array([1,2])}), 'persisted-offline-id');
    } else {
      assert.equal(await db.len(), 1);
      const row = await db.get('persisted-offline-id');
      assert.ok(row); assert.deepEqual(Array.from(row.vector), [1,2]);
      const hits = await db.search({vector:new Float32Array([1,2]),k:1});
      assert.equal(hits.length,1);assert.equal(hits[0].id,'persisted-offline-id');assert.equal(hits[0].score,0);
    }
    console.log(JSON.stringify({phase,version:metadata.version,platform:process.platform,arch:process.arch,
      addons:addonPaths.map(p=>({path:p,sha256:crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex')}))}));
  })().catch(e=>{console.error(e);process.exitCode=1;});
}
