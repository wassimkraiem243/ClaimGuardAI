import { existsSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
import { spawn } from 'child_process';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const apiDir = join(root, 'apps', 'api');
const venvWin = join(apiDir, '.venv', 'Scripts', 'python.exe');
const venvUnix = join(apiDir, '.venv', 'bin', 'python');

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
  { cwd: apiDir, stdio: 'inherit', shell: process.platform === 'win32' },
);

child.on('exit', (code) => process.exit(code ?? 1));
