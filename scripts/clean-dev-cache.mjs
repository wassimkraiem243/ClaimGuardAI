import { rmSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');

const targets = [
  join(root, '.turbo'),
  join(root, 'packages', 'shared-types', '.turbo'),
  join(root, 'apps', 'web', '.next', 'cache'),
];

for (const path of targets) {
  try {
    rmSync(path, { recursive: true, force: true });
    console.log(`Removed ${path.replace(root, '.')}`);
  } catch {
    // already gone
  }
}

console.log('Dev cache cleanup done.');
