import { execSync } from 'child_process';
import { existsSync } from 'fs';
import { dirname, join } from 'path';
import { fileURLToPath } from 'url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const ports = [4000, 4001];

function killPort(port) {
  const isWin = process.platform === 'win32';

  try {
    if (isWin) {
      const output = execSync(`netstat -ano | findstr :${port}`, {
        encoding: 'utf8',
        stdio: ['pipe', 'pipe', 'ignore'],
      });

      const pids = new Set();
      for (const line of output.split('\n')) {
        if (!line.includes('LISTENING')) continue;
        const parts = line.trim().split(/\s+/);
        const pid = parts.at(-1);
        if (pid && pid !== '0') pids.add(pid);
      }

      for (const pid of pids) {
        try {
          execSync(`taskkill /PID ${pid} /F`, { stdio: 'ignore' });
          console.log(`Freed port ${port} (PID ${pid})`);
        } catch {
          // process may already be gone
        }
      }
      return;
    }

    execSync(`lsof -ti:${port} | xargs -r kill -9`, { stdio: 'ignore' });
    console.log(`Freed port ${port}`);
  } catch {
    // port already free
  }
}

function ensureSharedTypesBuilt() {
  const distIndex = join(root, 'packages/shared-types/dist/index.js');
  if (existsSync(distIndex)) return;

  console.log('Building @claimguard/shared-types...');
  execSync('npm run build --workspace=@claimguard/shared-types', {
    cwd: root,
    stdio: 'inherit',
  });
}

ensureSharedTypesBuilt();

for (const port of ports) {
  killPort(port);
}

console.log('Dev ports ready (UI: 4000, API: 4001)');
