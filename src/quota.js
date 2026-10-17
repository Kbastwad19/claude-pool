import { spawnSync } from 'child_process';
import fs from 'fs';
import path from 'path';
import os from 'os';

const CACHE_FILE = path.join(os.homedir(), '.claude-pool', 'quota_cache.json');

export class QuotaEngine {
  static loadCache() {
    if (!fs.existsSync(CACHE_FILE)) return {};
    try {
      return JSON.parse(fs.readFileSync(CACHE_FILE, 'utf8'));
    } catch {
      return {};
    }
  }

  static saveCache(data) {
    try {
      fs.mkdirSync(path.dirname(CACHE_FILE), { recursive: true });
      fs.writeFileSync(CACHE_FILE, JSON.stringify(data, null, 2), 'utf8');
    } catch {}
  }

  static fetchAccountQuota(account, forceRefresh = false) {
    const cache = this.loadCache();
    const cachedEntry = cache[account.name];

    if (!forceRefresh && cachedEntry && cachedEntry.lastChecked) {
      const ageSeconds = (Date.now() - cachedEntry.lastChecked) / 1000;
      if (ageSeconds < 300) {
        account.quota = cachedEntry;
        return cachedEntry;
      }
    }

    const env = { ...process.env };
    const defaultClaudePath = path.resolve(path.join(os.homedir(), '.claude'));
    if (path.resolve(account.configDir) !== defaultClaudePath) {
      env.CLAUDE_CONFIG_DIR = account.configDir;
    } else {
      delete env.CLAUDE_CONFIG_DIR;
    }

    delete env.ANTHROPIC_BASE_URL;
    delete env.ANTHROPIC_API_KEY;
    delete env.ANTHROPIC_DEFAULT_SONNET_MODEL;

    try {
      const res = spawnSync('claude', ['-p', '/usage'], {
        input: '',
        env,
        encoding: 'utf8',
        timeout: 15000,
      });

      const output = (res.stdout || '') + '\n' + (res.stderr || '');

      const mSession = output.match(/Current session:\s*(\d+)%[\s\S]*?resets\s*([^(\n\r]+)/i);
      const mWeek = output.match(/Current week[\s\S]*?:\s*(\d+)%[\s\S]*?resets\s*([^(\n\r]+)/i);

      let sessionUsed = null;
      let sessionReset = null;
      let weekUsed = null;
      let weekReset = null;

      if (mSession) {
        sessionUsed = parseInt(mSession[1], 10);
        sessionReset = mSession[2].trim();
      }

      if (mWeek) {
        weekUsed = parseInt(mWeek[1], 10);
        weekReset = mWeek[2].trim();
      }

      if (sessionUsed !== null || weekUsed !== null) {
        const qInfo = {
          sessionUsedPct: sessionUsed,
          sessionRemainingPct: sessionUsed !== null ? Math.max(0, 100 - sessionUsed) : null,
          sessionReset,
          weekUsedPct: weekUsed,
          weekRemainingPct: weekUsed !== null ? Math.max(0, 100 - weekUsed) : null,
          weekReset,
          lastChecked: Date.now(),
        };

        account.quota = qInfo;
        cache[account.name] = qInfo;
        this.saveCache(cache);
        return qInfo;
      }
    } catch {}

    return null;
  }

  static fetchAllQuotas(accounts, forceRefresh = false) {
    for (const a of accounts) {
      if (a.enabled === false) continue;
      this.fetchAccountQuota(a, forceRefresh);
    }
  }
}
