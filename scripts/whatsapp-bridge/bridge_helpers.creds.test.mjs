/**
 * Unit tests for credential durability: isValidCredentialFile,
 * createCredsGuard and recoverCredentialFiles.
 *
 * Regression: Baileys' useMultiFileAuthState persists creds.json with a plain
 * writeFileSync. On a full disk that write truncates the file to 0 bytes and
 * throws. The next start reads an empty creds.json, sees no auth keys, and
 * silently re-enters pairing — a fresh QR on every restart, with the gateway
 * adapter only ever reporting "whatsapp connect timed out after 30s". The
 * operator had no signal that a full disk had un-paired WhatsApp.
 *
 * Covered here: the backup/restore round trip, ENOSPC rollback (live file keeps
 * the old valid content instead of becoming 0 bytes), and startup recovery of a
 * file truncated by a previous run.
 */

import { strict as assert } from 'node:assert';
import { mkdtempSync, writeFileSync, readFileSync, rmSync, existsSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';

import { createCredsGuard, recoverCredentialFiles, isValidCredentialFile } from './bridge_helpers.js';

const GOOD_CREDS = JSON.stringify({ noiseKey: 'abc', me: { id: '918076538956:1@s.whatsapp.net' }, registered: true });
const NEXT_CREDS = JSON.stringify({ noiseKey: 'def', me: { id: '918076538956:1@s.whatsapp.net' }, registered: true });

function withTempDir(fn) {
  const dir = mkdtempSync(path.join(tmpdir(), 'creds-guard-'));
  try {
    fn(dir);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
}

function collectLogs() {
  const lines = [];
  return { log: (msg) => lines.push(String(msg)), lines };
}

/** Minimal stand-in for Baileys' saveCreds: writes creds.json non-atomically. */
function fakeSaveCreds(dir, { payload, failWith } = {}) {
  return () => {
    const file = path.join(dir, 'creds.json');
    // Baileys truncates first, then writes — this is the bug being guarded.
    writeFileSync(file, '');
    if (failWith) {
      const err = new Error('ENOSPC: no space left on device, write');
      err.code = failWith;
      throw err;
    }
    writeFileSync(file, payload);
  };
}

function test(name, fn) {
  fn();
  console.log(`  ok  ${name}`);
}

// --- isValidCredentialFile -------------------------------------------------

test('isValidCredentialFile rejects empty, whitespace and non-object payloads', () => {
  assert.equal(isValidCredentialFile(GOOD_CREDS), true);
  assert.equal(isValidCredentialFile(''), false);
  assert.equal(isValidCredentialFile('   '), false);
  assert.equal(isValidCredentialFile(undefined), false);
  assert.equal(isValidCredentialFile('{ truncated'), false);
  assert.equal(isValidCredentialFile('[]'), false);
  assert.equal(isValidCredentialFile('"a string"'), false);
});

// --- createCredsGuard: happy path -----------------------------------------

test('a successful write persists the new creds and leaves a valid backup', () => withTempDir((dir) => {
  writeFileSync(path.join(dir, 'creds.json'), GOOD_CREDS);
  const { log, lines } = collectLogs();
  const guard = createCredsGuard(dir, fakeSaveCreds(dir, { payload: NEXT_CREDS }), { log });

  guard();

  assert.equal(readFileSync(path.join(dir, 'creds.json'), 'utf8'), NEXT_CREDS);
  assert.equal(isValidCredentialFile(readFileSync(path.join(dir, 'creds.json.bak'), 'utf8')), true);
  assert.deepEqual(lines, []);
}));

test('the backup holds the previous good creds, not the new ones', () => withTempDir((dir) => {
  writeFileSync(path.join(dir, 'creds.json'), GOOD_CREDS);
  const { log } = collectLogs();
  createCredsGuard(dir, fakeSaveCreds(dir, { payload: NEXT_CREDS }), { log })();

  assert.equal(readFileSync(path.join(dir, 'creds.json.bak'), 'utf8'), GOOD_CREDS);
}));

// --- createCredsGuard: the ENOSPC regression ------------------------------

test('ENOSPC mid-write does NOT truncate the live creds file', () => withTempDir((dir) => {
  writeFileSync(path.join(dir, 'creds.json'), GOOD_CREDS);
  const { log } = collectLogs();
  const guard = createCredsGuard(dir, fakeSaveCreds(dir, { failWith: 'ENOSPC' }), { log });

  guard(); // must not throw

  const live = readFileSync(path.join(dir, 'creds.json'), 'utf8');
  assert.equal(live, GOOD_CREDS, 'live creds must survive a full disk');
  assert.equal(isValidCredentialFile(live), true);
}));

test('ENOSPC is reported loudly so the operator knows the disk is the cause', () => withTempDir((dir) => {
  writeFileSync(path.join(dir, 'creds.json'), GOOD_CREDS);
  const { log, lines } = collectLogs();
  createCredsGuard(dir, fakeSaveCreds(dir, { failWith: 'ENOSPC' }), { log })();

  assert.ok(lines.some((l) => l.includes('DISK FULL') && l.includes('ENOSPC')), lines.join('\n'));
}));

test('a non-disk write error is reported without claiming the disk is full', () => withTempDir((dir) => {
  writeFileSync(path.join(dir, 'creds.json'), GOOD_CREDS);
  const { log, lines } = collectLogs();
  const guard = createCredsGuard(dir, () => {
    writeFileSync(path.join(dir, 'creds.json'), '');
    const err = new Error('EACCES: permission denied');
    err.code = 'EACCES';
    throw err;
  }, { log });

  guard();

  assert.ok(!lines.some((l) => l.includes('DISK FULL')), lines.join('\n'));
  assert.equal(readFileSync(path.join(dir, 'creds.json'), 'utf8'), GOOD_CREDS);
}));

test('a write that lands invalid JSON is rolled back, not left broken', () => withTempDir((dir) => {
  writeFileSync(path.join(dir, 'creds.json'), GOOD_CREDS);
  const { log } = collectLogs();
  createCredsGuard(dir, () => writeFileSync(path.join(dir, 'creds.json'), '{ half-writ'), { log })();

  assert.equal(readFileSync(path.join(dir, 'creds.json'), 'utf8'), GOOD_CREDS);
}));

test('a first-ever pairing write that fails is not resurrected from nothing', () => withTempDir((dir) => {
  const { log, lines } = collectLogs();
  createCredsGuard(dir, fakeSaveCreds(dir, { failWith: 'ENOSPC' }), { log })();

  assert.ok(!existsSync(path.join(dir, 'creds.json.bak')), 'no backup should be invented');
  assert.ok(lines.some((l) => l.includes('DISK FULL')), lines.join('\n'));
}));

// --- recoverCredentialFiles ------------------------------------------------

test('recoverCredentialFiles restores a 0-byte creds.json from its backup', () => withTempDir((dir) => {
  writeFileSync(path.join(dir, 'creds.json'), '');
  writeFileSync(path.join(dir, 'creds.json.bak'), GOOD_CREDS);

  const restored = recoverCredentialFiles(dir, { log: () => {} });

  assert.deepEqual(restored, ['creds.json']);
  assert.equal(readFileSync(path.join(dir, 'creds.json'), 'utf8'), GOOD_CREDS);
}));

test('recoverCredentialFiles restores app-state-sync-key.json too', () => withTempDir((dir) => {
  writeFileSync(path.join(dir, 'app-state-sync-key.json'), '');
  writeFileSync(path.join(dir, 'app-state-sync-key.json.bak'), GOOD_CREDS);

  const restored = recoverCredentialFiles(dir, { log: () => {} });

  assert.deepEqual(restored, ['app-state-sync-key.json']);
  assert.equal(isValidCredentialFile(readFileSync(path.join(dir, 'app-state-sync-key.json'), 'utf8')), true);
}));

test('recoverCredentialFiles leaves healthy files untouched', () => withTempDir((dir) => {
  writeFileSync(path.join(dir, 'creds.json'), GOOD_CREDS);
  writeFileSync(path.join(dir, 'creds.json.bak'), GOOD_CREDS);

  assert.deepEqual(recoverCredentialFiles(dir, { log: () => {} }), []);
  assert.equal(readFileSync(path.join(dir, 'creds.json'), 'utf8'), GOOD_CREDS);
}));

test('recoverCredentialFiles warns when a re-pair is unavoidable', () => withTempDir((dir) => {
  writeFileSync(path.join(dir, 'creds.json'), '');
  const { log, lines } = collectLogs();

  const restored = recoverCredentialFiles(dir, { log });

  assert.deepEqual(restored, []);
  assert.ok(lines.some((l) => l.includes('re-paired')), lines.join('\n'));
}));

test('recoverCredentialFiles ignores unrelated session files', () => withTempDir((dir) => {
  writeFileSync(path.join(dir, 'session-155933250478325_1.0.json'), '');
  writeFileSync(path.join(dir, 'pre-key-1.json'), '');

  assert.deepEqual(recoverCredentialFiles(dir, { log: () => {} }), []);
}));

test('recoverCredentialFiles tolerates a missing session dir', () => {
  assert.deepEqual(recoverCredentialFiles(path.join(tmpdir(), 'does-not-exist-creds'), { log: () => {} }), []);
});

console.log('\nAll credential-durability tests passed.');
