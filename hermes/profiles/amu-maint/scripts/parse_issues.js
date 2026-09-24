const fs = require('fs');
let s = fs.readFileSync('~/.hermes/profiles/amu-maint/cache/scratch/issues.json', 'utf8');
const start = s.indexOf('[');
const end = s.lastIndexOf(']');
const arr = JSON.parse(s.slice(start, end + 1));
const out = arr.map(i => ({
  n: i.number,
  t: i.title,
  labels: i.labels.map(l => l.name),
  created: i.createdAt,
  updated: i.updatedAt,
  nc: i.comments.length
}));
fs.writeFileSync('~/.hermes/profiles/amu-maint/cache/scratch/issues-compact.json', JSON.stringify(out, null, 1));
console.log(out.length);
