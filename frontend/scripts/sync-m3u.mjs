import { copyFileSync, existsSync, mkdirSync, readdirSync, rmSync, statSync, writeFileSync } from 'node:fs';
import { basename, extname, join, resolve } from 'node:path';

const projectRoot = resolve(import.meta.dirname, '..', '..');
const frontendRoot = resolve(import.meta.dirname, '..');
const sourceDir = resolve(projectRoot, 'm3u');
const publicM3uDir = resolve(frontendRoot, 'public', 'm3u');

mkdirSync(publicM3uDir, { recursive: true });

for (const entry of readdirSync(publicM3uDir, { withFileTypes: true })) {
  const target = join(publicM3uDir, entry.name);
  if (entry.isFile() && (entry.name.endsWith('.m3u') || entry.name.endsWith('.m3u8') || entry.name === 'manifest.json')) {
    rmSync(target);
  }
}

const files = existsSync(sourceDir)
  ? readdirSync(sourceDir, { withFileTypes: true })
      .filter((entry) => entry.isFile())
      .map((entry) => entry.name)
      .filter((name) => ['.m3u', '.m3u8'].includes(extname(name).toLowerCase()))
      .sort((left, right) => left.localeCompare(right))
  : [];

const playlists = files.map((fileName) => {
  const sourcePath = join(sourceDir, fileName);
  const targetPath = join(publicM3uDir, fileName);
  copyFileSync(sourcePath, targetPath);
  const stats = statSync(sourcePath);

  return {
    id: fileName.replace(/[^a-zA-Z0-9_-]/g, '-'),
    name: basename(fileName, extname(fileName)),
    fileName,
    url: `/m3u/${encodeURIComponent(fileName)}`,
    sizeBytes: stats.size,
    updatedAt: stats.mtime.toISOString(),
  };
});

writeFileSync(
  join(publicM3uDir, 'manifest.json'),
  `${JSON.stringify({ generatedAt: new Date().toISOString(), playlists }, null, 2)}\n`,
  'utf8',
);

console.log(`Synced ${playlists.length} M3U playlist file(s) into frontend/public/m3u`);
