const UTF8_META_TAG = '<meta charset="utf-8" />';

const UTF8_META_REGEX = /<meta[^>]+charset\s*=\s*["']?\s*utf-8\s*["']?[^>]*>/i;
const HEAD_OPEN_REGEX = /<head[\s>]/i;
const HEAD_CLOSE_REGEX = /<\/head>/i;
const HTML_OPEN_REGEX = /<html[\s>][\s\S]*?>/i;
const BODY_OPEN_REGEX = /<body[\s>][\s\S]*?>/i;

export function ensureUtf8HtmlDocument(input: string): string {
  const raw = String(input || '').trim();
  if (!raw) {
    return '';
  }

  if (UTF8_META_REGEX.test(raw)) {
    return raw;
  }

  if (HEAD_OPEN_REGEX.test(raw) && HEAD_CLOSE_REGEX.test(raw)) {
    return raw.replace(HEAD_CLOSE_REGEX, `${UTF8_META_TAG}\n</head>`);
  }

  if (HTML_OPEN_REGEX.test(raw)) {
    if (BODY_OPEN_REGEX.test(raw)) {
      return raw.replace(BODY_OPEN_REGEX, `<head>\n${UTF8_META_TAG}\n</head>\n$&`);
    }
    return raw.replace(HTML_OPEN_REGEX, `$&\n<head>\n${UTF8_META_TAG}\n</head>`);
  }

  return `<!doctype html>
<html lang="en">
<head>
${UTF8_META_TAG}
</head>
<body>
${raw}
</body>
</html>`;
}
