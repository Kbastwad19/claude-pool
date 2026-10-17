import fs from 'fs';
import path from 'path';

export class MetricsEngine {
  static readAccountStats(account) {
    const stats = {
      accountName: account.name,
      todayInputTokens: 0,
      todayOutputTokens: 0,
      todayCacheReadTokens: 0,
      todayCacheCreationTokens: 0,
      todayTotalTokens: 0,
      todayTokensByModel: {},
      todayModelsDetail: {},
      lifetimeModels: {},
      lifetimeTotalInput: 0,
      lifetimeTotalOutput: 0,
      lifetimeTotalCache: 0,
      lifetimeTotalTokens: 0,
      totalSessions: 0,
      totalMessages: 0,
    };

    const configPath = account.configDir;

    // 1. Base lifetime metrics from stats-cache.json
    const statsFile = path.join(configPath, 'stats-cache.json');
    if (fs.existsSync(statsFile)) {
      try {
        const raw = JSON.parse(fs.readFileSync(statsFile, 'utf8'));
        stats.totalSessions = raw.totalSessions || 0;
        stats.totalMessages = raw.totalMessages || 0;

        const rawModels = raw.modelUsage || {};
        for (const [mName, u] of Object.entries(rawModels)) {
          const inp = u.inputTokens || 0;
          const out = u.outputTokens || 0;
          const cRead = u.cacheReadInputTokens || 0;
          const cCreate = u.cacheCreationInputTokens || 0;
          const tot = inp + out + cRead + cCreate;

          stats.lifetimeModels[mName] = { input: inp, output: out, cacheRead: cRead, cacheCreate: cCreate, total: tot };
          stats.lifetimeTotalInput += inp;
          stats.lifetimeTotalOutput += out;
          stats.lifetimeTotalCache += cRead + cCreate;
          stats.lifetimeTotalTokens += tot;
        }
      } catch {}
    }

    // 2. Real-time extraction from live project session .jsonl files for today
    const projDir = path.join(configPath, 'projects');
    if (!fs.existsSync(projDir)) return stats;

    const todayUtc = new Date().toISOString().slice(0, 10);
    const todayLocal = new Date().toLocaleDateString('en-CA'); // YYYY-MM-DD
    const cutoffMtime = Date.now() - 48 * 3600 * 1000;

    let sessionCount = 0;

    function walkDir(dir) {
      try {
        const entries = fs.readdirSync(dir, { withFileTypes: true });
        for (const ent of entries) {
          const full = path.join(dir, ent.name);
          if (ent.isDirectory() && ent.name !== 'subagents') {
            walkDir(full);
          } else if (ent.isFile() && ent.name.endsWith('.jsonl') && !full.includes('subagents')) {
            sessionCount++;
            try {
              const st = fs.statSync(full);
              if (st.mtimeMs < cutoffMtime) continue;

              const content = fs.readFileSync(full, 'utf8');
              const lines = content.split('\n');

              for (const line of lines) {
                if (!line.includes('input_tokens')) continue;
                try {
                  const data = JSON.parse(line);
                  const ts = data.timestamp || '';
                  if (!ts.startsWith(todayUtc) && !ts.startsWith(todayLocal)) continue;

                  const msg = data.message || {};
                  const usage = msg.usage || {};
                  const model = msg.model || 'unknown';

                  const inp = usage.input_tokens || 0;
                  const out = usage.output_tokens || 0;
                  const cRead = usage.cache_read_input_tokens || 0;
                  const cCreate = usage.cache_creation_input_tokens || 0;
                  const cTotal = cRead + cCreate;
                  const turnTokens = inp + out + cTotal;

                  stats.todayInputTokens += inp;
                  stats.todayOutputTokens += out;
                  stats.todayCacheReadTokens += cRead;
                  stats.todayCacheCreationTokens += cCreate;
                  stats.todayTotalTokens += turnTokens;

                  stats.todayTokensByModel[model] = (stats.todayTokensByModel[model] || 0) + turnTokens;

                  if (!stats.todayModelsDetail[model]) {
                    stats.todayModelsDetail[model] = { input: 0, output: 0, cacheRead: 0, cacheCreate: 0, total: 0 };
                  }
                  const mDet = stats.todayModelsDetail[model];
                  mDet.input += inp;
                  mDet.output += out;
                  mDet.cacheRead += cRead;
                  mDet.cacheCreate += cCreate;
                  mDet.total += turnTokens;
                } catch {}
              }
            } catch {}
          }
        }
      } catch {}
    }

    walkDir(projDir);

    if (stats.totalSessions === 0) {
      stats.totalSessions = sessionCount;
    }

    return stats;
  }

  static getPoolStats(accounts) {
    const pool = {
      accounts: [],
      todayPoolTokens: 0,
      todayPoolInput: 0,
      todayPoolOutput: 0,
      todayPoolCache: 0,
      lifetimePoolInput: 0,
      lifetimePoolOutput: 0,
      lifetimePoolCache: 0,
      lifetimePoolTokens: 0,
      totalPoolSessions: 0,
    };

    for (const acct of accounts) {
      const acctStats = this.readAccountStats(acct);
      pool.accounts.push(acctStats);
      pool.todayPoolTokens += acctStats.todayTotalTokens;
      pool.todayPoolInput += acctStats.todayInputTokens;
      pool.todayPoolOutput += acctStats.todayOutputTokens;
      pool.todayPoolCache += acctStats.todayCacheReadTokens + acctStats.todayCacheCreationTokens;

      pool.lifetimePoolInput += acctStats.lifetimeTotalInput;
      pool.lifetimePoolOutput += acctStats.lifetimeTotalOutput;
      pool.lifetimePoolCache += acctStats.lifetimeTotalCache;
      pool.lifetimePoolTokens += acctStats.lifetimeTotalTokens;
      pool.totalPoolSessions += acctStats.totalSessions;
    }

    return pool;
  }
}
