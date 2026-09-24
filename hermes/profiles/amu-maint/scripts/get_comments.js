const { execSync } = require('child_process');
const fs = require('fs');
const nums = process.argv.slice(2);
const out = {};
for (const n of nums) {
  const j = execSync(`gh issue view ${n} --repo kotoba-lang/amu --json comments --jq '.comments'`, { encoding: 'utf8' });
  const arr = JSON.parse(j);
  out[n] = arr.map(c => ({
    author: c.author.login,
    at: c.createdAt,
    body: c.body.slice(0, 250)
  }));
}
fs.writeFileSync('~/.hermes/profiles/amu-maint/cache/scratch/comments.json', JSON.stringify(out, null, 1));
console.log(Object.keys(out).join(','));
