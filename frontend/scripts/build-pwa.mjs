import fs from 'node:fs';
import crypto from 'node:crypto';
const assets = fs.readdirSync('dist/assets').map(name => '/assets/' + name);
const files = ['/index.html', '/manifest.webmanifest', '/icon-192.png', '/icon-512.png', '/outbox.js', ...assets];
const version = crypto.createHash('sha256').update(files.map(f => fs.readFileSync('dist'+f)).reduce((a,b) => Buffer.concat([a,b]), Buffer.alloc(0))).digest('hex').slice(0,16);
const sw = fs.readFileSync('public/sw.js','utf8').replace('__BUILD__', version).replace('__PRECACHE__', JSON.stringify(files));
fs.writeFileSync('dist/sw.js', sw);
