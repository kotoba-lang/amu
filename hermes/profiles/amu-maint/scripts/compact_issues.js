const fs = require('fs');
const a = JSON.parse(fs.readFileSync('~/.hermes/profiles/amu-maint/cache/scratch/issues_full.json', 'utf8'));
const out = a.map(i => ({ n: i.number, t: i.title.slice(0, 70), labels: i.labels.map(l => l.name), u: i.updatedAt, nc: i.comments.length }));
fs.writeFileSync('~/.hermes/profiles/amu-maint/cache/scratch/issues_compact.json', JSON.stringify(out, null, 1));
console.log(out.length);
