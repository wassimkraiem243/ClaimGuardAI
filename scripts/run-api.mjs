import { existsSync, readFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
import { spawn } from 'child_process';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const apiDir = join(root, 'apps', 'api');
const venvWin = join(apiDir, '.venv', 'Scripts', 'python.exe');
const venvUnix = join(apiDir, '.venv', 'bin', 'python');

/** Merge apps/api/.env into the process env for the API child (Windows npm run dev). */
function apiProcessEnv() {
  const env = { ...process.env };
  const dotenvPath = join(apiDir, '.env');
  if (!existsSync(dotenvPath)) return env;
  for (const line of readFileSync(dotenvPath, 'utf8').split(/\r?\n/)) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) continue;
    const eq = trimmed.indexOf('=');
    if (eq <= 0) continue;
    const key = trimmed.slice(0, eq).trim();
    let value = trimmed.slice(eq + 1).trim();
    if (
      (value.startsWith('"') && value.endsWith('"')) ||
      (value.startsWith("'") && value.endsWith("'"))
    ) {
      value = value.slice(1, -1);
    }
    env[key] = value;
  }
  return env;
}

let python = 'python';
if (existsSync(venvWin)) python = venvWin;
else if (existsSync(venvUnix)) python = venvUnix;
else {
  console.warn(
    'No apps/api/.venv found. Using system python — run: cd apps/api && python -m venv .venv && pip install -r requirements.txt',
  );
}

const child = spawn(
  python,
  ['-m', 'uvicorn', 'app.main:app', '--reload', '--host', '127.0.0.1', '--port', '4001'],
  { cwd: apiDir, stdio: 'inherit', shell: process.platform === 'win32', env: apiProcessEnv() },
);

child.on('exit', (code) => process.exit(code ?? 1));
