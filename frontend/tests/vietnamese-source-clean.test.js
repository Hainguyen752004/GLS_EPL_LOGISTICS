const assert = require('assert');
const fs = require('fs');
const path = require('path');

const frontendRoot = path.join(__dirname, '..');
const allowedExtensions = new Set(['.html', '.js', '.css']);
const ignoredDirectories = new Set(['tests', 'node_modules', 'vendor']);

// Keep the detector itself ASCII-only so damaged editor encoding cannot
// silently turn this test into a false positive/negative.
const reliableMojibake = /(?:[\u00C2-\u00C4\u00C6](?=[\u0080-\u00BF])|\u00E1[\u00BA\u00BB]|\u00E2\u20AC|\u00F0\u0178|\uFFFD)/u;
const reliableLostAccent = /(?:Qu\?n|Th\?m|T\?i x\?|Ph\? xe|Tr\?ng th\?|S\? \?i\?n|Ch\?c danh|Ca l\?m vi\?c|Thao tc|ti chnh|Lm theo|thứ tự ny|để trnh|Ph bảo dưỡng|VNĐ\/thng|Ton bộ|thng số|Thm mới|thng tin khch hng|người lin hệ|p dụng cho bo gi|đơn hng|0 dng)/u;
const forbiddenInvisibleCharacters = /[\u0080-\u009F\u00AD]/u;

function maskAllowedUrlQueries(source) {
  const chars = source.split('');
  const allowedUrlPatterns = [
    { pattern: /(?:href|src)=(['"])[^'"\n]*\?v=[^'"\n]*\1/gu, marker: '?v=' },
    { pattern: /(['"])[^'"\n]*search\?format(?:=[^'"\n]*)?\1/gu, marker: '?format' },
  ];

  for (const { pattern, marker } of allowedUrlPatterns) {
    for (const match of source.matchAll(pattern)) {
      const queryIndex = match.index + match[0].indexOf(marker);
      chars[queryIndex] = ' ';
    }
  }
  return chars.join('');
}

function findLostAccentMarkers(source, relativePath) {
  const masked = maskAllowedUrlQueries(source);
  const lines = masked.split(/\r?\n/);
  const failures = [];

  lines.forEach((line, lineIndex) => {
    const characters = [...line];
    characters.forEach((character, characterIndex) => {
      const previous = characters[characterIndex - 1];
      const next = characters[characterIndex + 1];
      const previousIsLetter = previous && previous.toLocaleLowerCase() !== previous.toLocaleUpperCase();
      const nextIsLetter = next && next.toLocaleLowerCase() !== next.toLocaleUpperCase();
      if (character === '?' && previousIsLetter && nextIsLetter) {
        failures.push(`${relativePath}:${lineIndex + 1}: ${line.trim().slice(0, 180)}`);
      }
    });
  });

  return failures;
}

function listSourceFiles(directory) {
  return fs.readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    if (entry.isDirectory()) {
      return ignoredDirectories.has(entry.name)
        ? []
        : listSourceFiles(path.join(directory, entry.name));
    }
    return allowedExtensions.has(path.extname(entry.name).toLowerCase())
      ? [path.join(directory, entry.name)]
      : [];
  });
}

const failures = [];
for (const filePath of listSourceFiles(frontendRoot)) {
  const source = fs.readFileSync(filePath, 'utf8');
  const relativePath = path.relative(frontendRoot, filePath);
  const lines = source.split(/\r?\n/);
  lines.forEach((line, index) => {
    if (
      reliableMojibake.test(line)
      || reliableLostAccent.test(line)
      || forbiddenInvisibleCharacters.test(line)
    ) {
      failures.push(`${relativePath}:${index + 1}: ${line.trim().slice(0, 180)}`);
    }
  });
  if (relativePath === 'index.html') {
    failures.push(...findLostAccentMarkers(source, relativePath));
  }
}

assert.deepStrictEqual(
  failures,
  [],
  `Phat hien tieng Viet hong trong source frontend:\n${failures.slice(0, 80).join('\n')}`
);

const appSource = fs.readFileSync(path.join(frontendRoot, 'js', 'app.js'), 'utf8');
const workflowSource = fs.readFileSync(path.join(frontendRoot, 'js', 'workflow-ui-utils.js'), 'utf8');
assert.doesNotMatch(appSource, /MutationObserver[\s\S]{0,240}fixDocumentVietnamese/);
assert.doesNotMatch(workflowSource, /createTreeWalker|fixDocumentVietnamese/);

console.log('VIETNAMESE_SOURCE_CLEAN_OK');
