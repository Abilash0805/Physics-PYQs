// Reads a JSON array of answer strings on stdin, prints {"ok": [indices]}
// for the ones whose every $...$ run parses under KaTeX. A malformed run
// blanks the answer in the UI, so answers are checked before being stored.
const katex = require('katex');

let input = '';
process.stdin.on('data', (d) => (input += d));
process.stdin.on('end', () => {
  const answers = JSON.parse(input);
  const ok = [];
  answers.forEach((text, i) => {
    const parts = String(text).split('$');
    if ((parts.length - 1) % 2 !== 0) return; // unbalanced delimiters
    let good = true;
    for (let k = 1; k < parts.length; k += 2) {
      try {
        katex.renderToString(parts[k], { throwOnError: true });
      } catch {
        good = false;
        break;
      }
    }
    if (good) ok.push(i);
  });
  process.stdout.write(JSON.stringify({ ok }));
});
