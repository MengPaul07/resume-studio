export function isMultiLineField(path: string): boolean {
  const lower = path.toLowerCase();
  return (
    lower === 'summary' ||
    lower.endsWith('.description') ||
    /\.description\[\d+\]$/.test(lower)
  );
}
