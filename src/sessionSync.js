import fs from 'fs';
import path from 'path';

export function encodeProjectName(cwdPath = null) {
  const p = path.resolve(cwdPath || process.cwd());
  const parsed = path.parse(p);

  if (parsed.root && parsed.root.includes(':')) {
    // Windows: E:\PP\accs -> E--PP-accs
    const drive = parsed.root.replace(':', '').replace(/[\/\\]/g, '');
    const relativeParts = p.slice(parsed.root.length).split(/[\\/]/).filter(Boolean);
    if (relativeParts.length === 0) return `${drive}--`;
    return `${drive}--` + relativeParts.join('-');
  } else {
    // POSIX (macOS / Linux): /home/user/app -> -home-user-app
    const parts = p.split('/').filter(Boolean);
    return '-' + parts.join('-');
  }
}

export class SessionSyncEngine {
  static getLatestSessionId(account, cwdPath = null) {
    const projName = encodeProjectName(cwdPath);
    const projDir = path.join(account.configDir, 'projects', projName);

    if (!fs.existsSync(projDir)) return null;

    try {
      const files = fs
        .readdirSync(projDir)
        .filter(f => f.endsWith('.jsonl') && !f.includes('subagents'))
        .map(f => {
          const fullPath = path.join(projDir, f);
          return { name: f, stem: path.basename(f, '.jsonl'), mtime: fs.statSync(fullPath).mtimeMs };
        });

      if (files.length === 0) return null;
      files.sort((a, b) => b.mtime - a.mtime);
      return files[0].stem;
    } catch {
      return null;
    }
  }

  static transferSession(sourceAccount, targetAccount, sessionId = null, cwdPath = null) {
    const projName = encodeProjectName(cwdPath);
    const srcProjDir = path.join(sourceAccount.configDir, 'projects', projName);
    const dstProjDir = path.join(targetAccount.configDir, 'projects', projName);

    if (!fs.existsSync(srcProjDir)) return null;

    const actualSessionId = sessionId || this.getLatestSessionId(sourceAccount, cwdPath);
    if (!actualSessionId) return null;

    const srcSessionFile = path.join(srcProjDir, `${actualSessionId}.jsonl`);
    if (!fs.existsSync(srcSessionFile)) return null;

    fs.mkdirSync(dstProjDir, { recursive: true });
    const dstSessionFile = path.join(dstProjDir, `${actualSessionId}.jsonl`);

    // Copy session transcript
    fs.copyFileSync(srcSessionFile, dstSessionFile);

    // Copy sidecar folder if present (tool-results, subagents)
    const srcSidecarDir = path.join(srcProjDir, actualSessionId);
    if (fs.existsSync(srcSidecarDir) && fs.statSync(srcSidecarDir).isDirectory()) {
      const dstSidecarDir = path.join(dstProjDir, actualSessionId);
      fs.cpSync(srcSidecarDir, dstSidecarDir, { recursive: true, force: true });
    }

    // Copy custom-title.json if present
    const titleFile = path.join(srcProjDir, 'custom-title.json');
    if (fs.existsSync(titleFile)) {
      fs.copyFileSync(titleFile, path.join(dstProjDir, 'custom-title.json'));
    }

    return actualSessionId;
  }
}
