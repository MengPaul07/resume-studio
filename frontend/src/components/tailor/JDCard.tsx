import { useTranslation } from 'react-i18next';

interface JDMatch {
  id: string;
  text: string;
  metadata?: Record<string, unknown>;
}

interface Props {
  jd: JDMatch;
  index: number;
  onTarget?: (jd: JDMatch) => void;
}

function parseJD(text: string): {
  title: string;
  company: string;
  location: string;
  type: string;
  category: string;
  keywords: string[];
  responsibilities: string[];
  requirements: string[];
  url: string;
} {
  const lines = text.split('\n');
  const title = lines[0] || '';
  const meta = lines[1] || '';
  const metaParts = meta.split(' | ');
  const company = metaParts[0] || '';
  const location = metaParts[1] || '';
  const jobType = metaParts[2] || '';

  let category = '';
  let url = '';
  let keywords: string[] = [];
  let responsibilities: string[] = [];
  let requirements: string[] = [];

  for (const line of lines) {
    if (line.startsWith('链接: ')) url = line.slice(4);
    else if (line.startsWith('类别: ')) category = line.slice(4);
    else if (line.startsWith('关键词: ')) keywords = line.slice(5).split(', ').filter(Boolean);
    else if (line.startsWith('职责: ')) responsibilities = line.slice(4).split('; ').filter(Boolean);
    else if (line.startsWith('要求: ')) requirements = line.slice(4).split('; ').filter(Boolean);
  }

  return { title, company, location, type: jobType, category, keywords, responsibilities, requirements, url };
}

export function JDCard({ jd, index, onTarget }: Props) {
  const { t } = useTranslation();
  const j = parseJD(jd.text);

  return (
    <div className="mb-3 overflow-hidden rounded-lg border border-black/20 dark:border-zinc-600 bg-white dark:bg-zinc-900 shadow-sm dark:shadow-none">
      <div className="flex items-center gap-2 border-b border-black/10 bg-black/5 px-4 py-2.5">
        <span className="flex size-5 shrink-0 items-center justify-center rounded-full bg-black/80 text-[10px] font-bold text-white">
          {index + 1}
        </span>
        <h4 className="truncate text-sm font-semibold text-gray-900 dark:text-zinc-100">
          {j.url ? (
            <a href={j.url} target="_blank" rel="noreferrer" className="hover:underline">
              {j.title}
            </a>
          ) : (
            j.title
          )}
        </h4>
        {j.type && (
          <span className="shrink-0 rounded border border-black/20 px-1.5 py-0.5 text-[10px] text-gray-500 dark:text-zinc-400">
            {j.type}
          </span>
        )}
        {onTarget && (
          <button
            className="shrink-0 rounded border border-blue-400 px-2 py-0.5 text-[10px] text-blue-600 hover:bg-blue-50"
            onClick={() => onTarget(jd)}
          >
            {t('jd.target')}
          </button>
        )}
      </div>
      <div className="space-y-2 px-4 py-3">
        <div className="flex flex-wrap items-center gap-x-3 gap-y-0.5 text-xs text-gray-500 dark:text-zinc-400">
          {j.company && <span>{j.company}</span>}
          {j.location && <span>· {j.location}</span>}
          {j.category && <span>· {j.category}</span>}
        </div>

        {j.keywords.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {j.keywords.map((kw) => (
              <span key={kw} className="rounded bg-blue-50 px-1.5 py-0.5 text-[10px] font-medium text-blue-700">
                {kw}
              </span>
            ))}
          </div>
        )}

        {j.responsibilities.length > 0 && (
          <div>
            <p className="mb-1 text-[11px] font-semibold text-gray-500 dark:text-zinc-400">{t('jd.responsibilities')}</p>
            <ul className="space-y-0.5 text-[12px] leading-5 text-gray-700 dark:text-zinc-300">
              {j.responsibilities.slice(0, 3).map((r, i) => (
                <li key={i} className="before:mr-1.5 before:text-gray-400 dark:before:text-zinc-500 before:content-['·']">
                  {r}
                </li>
              ))}
              {j.responsibilities.length > 3 && (
                <li className="text-[11px] text-gray-400 dark:text-zinc-500">... {t('jd.moreItems', { count: j.responsibilities.length })}</li>
              )}
            </ul>
          </div>
        )}

        {j.requirements.length > 0 && (
          <div>
            <p className="mb-1 text-[11px] font-semibold text-gray-500 dark:text-zinc-400">{t('jd.requirements')}</p>
            <ul className="space-y-0.5 text-[12px] leading-5 text-gray-700 dark:text-zinc-300">
              {j.requirements.slice(0, 3).map((r, i) => (
                <li key={i} className="before:mr-1.5 before:text-gray-400 dark:before:text-zinc-500 before:content-['·']">
                  {r}
                </li>
              ))}
              {j.requirements.length > 3 && (
                <li className="text-[11px] text-gray-400 dark:text-zinc-500">... {t('jd.moreItems', { count: j.requirements.length })}</li>
              )}
            </ul>
          </div>
        )}

      </div>
    </div>
  );
}
