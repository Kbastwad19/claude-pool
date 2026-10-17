import test from 'node:test';
import assert from 'node:assert';
import { encodeProjectName } from '../src/sessionSync.js';
import { ConfigManager, getDefaultAccounts } from '../src/config.js';

test('encodeProjectName converts Windows paths correctly', () => {
  const winPath = 'E:\\PP\\accs\\claude-pool';
  const encoded = encodeProjectName(winPath);
  assert.strictEqual(encoded, 'E--PP-accs-claude-pool');
});

test('getDefaultAccounts returns list with primary account', () => {
  const accounts = getDefaultAccounts();
  assert.ok(Array.isArray(accounts));
  assert.ok(accounts.length > 0);
  assert.strictEqual(accounts[0].name, 'primary');
});

test('ConfigManager initializes cleanly', () => {
  const cm = new ConfigManager();
  const accounts = cm.loadAccounts();
  assert.ok(Array.isArray(accounts));
});
