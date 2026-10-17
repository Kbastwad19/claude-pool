import fs from 'fs';
import path from 'path';
import os from 'os';

export const DEFAULT_CONFIG_DIR = path.join(os.homedir(), '.claude-pool');
export const CONFIG_FILE = path.join(DEFAULT_CONFIG_DIR, 'config.json');

export function getDefaultAccounts() {
  const home = os.homedir();
  const candidates = [
    { name: 'primary', configDir: path.join(home, '.claude'), priority: 1 },
    { name: 'account4', configDir: path.join(home, '.claude-account4'), priority: 2 },
    { name: 'account2', configDir: path.join(home, '.claude-account2'), priority: 3 },
    { name: 'bedrock', configDir: path.join(home, '.claude-bedrock'), priority: 4 },
  ];

  const detected = [];
  for (const c of candidates) {
    if (fs.existsSync(c.configDir)) {
      detected.push({
        ...c,
        enabled: true,
        email: null,
        orgName: null,
        subscriptionType: null,
        rateLimitedUntil: null,
      });
    }
  }

  if (detected.length === 0) {
    detected.push({
      name: 'primary',
      configDir: path.join(home, '.claude'),
      priority: 1,
      enabled: true,
      email: null,
      orgName: null,
      subscriptionType: null,
      rateLimitedUntil: null,
    });
  }

  return detected;
}

export class ConfigManager {
  constructor(customConfigFile = null) {
    this.configFile = customConfigFile || CONFIG_FILE;
    this.configDir = path.dirname(this.configFile);
  }

  ensureConfigDir() {
    if (!fs.existsSync(this.configDir)) {
      fs.mkdirSync(this.configDir, { recursive: true });
    }
  }

  loadAccounts() {
    if (!fs.existsSync(this.configFile)) {
      const defaults = getDefaultAccounts();
      this.saveAccounts(defaults);
      return defaults;
    }

    try {
      const raw = JSON.parse(fs.readFileSync(this.configFile, 'utf8'));
      const accounts = (raw.accounts || []).map(a => ({
        name: a.name,
        configDir: a.configDir || a.config_dir,
        priority: Number(a.priority || 99),
        enabled: a.enabled !== false,
        email: a.email || null,
        orgName: a.orgName || a.org_name || null,
        subscriptionType: a.subscriptionType || a.subscription_type || null,
        rateLimitedUntil: a.rateLimitedUntil || a.rate_limited_until || null,
        quota: null,
      }));
      accounts.sort((a, b) => a.priority - b.priority);
      return accounts;
    } catch {
      return getDefaultAccounts();
    }
  }

  saveAccounts(accounts) {
    this.ensureConfigDir();
    accounts.sort((a, b) => a.priority - b.priority);
    const data = {
      version: '1.0',
      accounts: accounts.map(a => ({
        name: a.name,
        config_dir: a.configDir,
        priority: a.priority,
        enabled: a.enabled,
        email: a.email,
        org_name: a.orgName,
        subscription_type: a.subscriptionType,
        rate_limited_until: a.rateLimitedUntil,
      })),
      settings: {
        cooldown_minutes: 60,
        auto_switch: true,
      },
    };
    fs.writeFileSync(this.configFile, JSON.stringify(data, null, 2), 'utf8');
  }

  updateAccountPriority(accountName, newPriority) {
    const accounts = this.loadAccounts();
    const target = accounts.find(a => a.name.toLowerCase() === accountName.toLowerCase());
    if (!target) return false;

    const others = accounts.filter(a => a.name.toLowerCase() !== accountName.toLowerCase());
    const insertIdx = Math.max(0, Math.min(newPriority - 1, others.length));
    others.splice(insertIdx, 0, target);

    others.forEach((a, idx) => {
      a.priority = idx + 1;
    });

    this.saveAccounts(others);
    return true;
  }

  reorderPriorities(accountNames) {
    const accounts = this.loadAccounts();
    const map = new Map(accounts.map(a => [a.name.toLowerCase(), a]));
    const newOrder = [];

    for (const name of accountNames) {
      const key = name.trim().toLowerCase();
      if (map.has(key)) {
        newOrder.push(map.get(key));
        map.delete(key);
      }
    }

    for (const remaining of map.values()) {
      newOrder.push(remaining);
    }

    newOrder.forEach((a, idx) => {
      a.priority = idx + 1;
    });

    this.saveAccounts(newOrder);
    return true;
  }
}
