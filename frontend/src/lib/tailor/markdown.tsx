import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeSanitize from 'rehype-sanitize';
import { Fragment } from 'react';

export function renderAssistantMarkdown(text: string): JSX.Element {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      rehypePlugins={[rehypeSanitize]}
      components={{
        h1: ({ children }) => <h1 className="mb-2 text-lg font-semibold">{children}</h1>,
        h2: ({ children }) => <h2 className="mb-2 text-base font-semibold">{children}</h2>,
        h3: ({ children }) => <h3 className="mb-1.5 text-sm font-semibold">{children}</h3>,
        h4: ({ children }) => <h4 className="mb-1 text-sm font-medium">{children}</h4>,
        p: ({ children }) => <p className="mb-2 last:mb-0 leading-6">{children}</p>,
        ul: ({ children }) => <ul className="mb-2 list-disc space-y-1 pl-5">{children}</ul>,
        ol: ({ children }) => <ol className="mb-2 list-decimal space-y-1 pl-5">{children}</ol>,
        li: ({ children }) => <li className="leading-6">{children}</li>,
        a: ({ href, children }) => (
          <a
            href={href}
            target="_blank"
            rel="noreferrer"
            className="underline decoration-black/40 underline-offset-2 hover:decoration-black"
          >
            {children}
          </a>
        ),
        code: ({ className, children }) => {
          const isBlock = Boolean(className && className.includes('language-'));
          return isBlock ? (
            <code className="block overflow-auto rounded border border-black/20 bg-black/5 p-2 font-mono text-[11px] leading-5">
              {children}
            </code>
          ) : (
            <code className="rounded bg-black/10 px-1 py-0.5 font-mono text-[11px]">
              {children}
            </code>
          );
        },
        pre: ({ children }) => <pre className="mb-2">{children}</pre>,
        blockquote: ({ children }) => (
          <blockquote className="mb-2 border-l-2 border-black/30 pl-3 italic">
            {children}
          </blockquote>
        ),
        table: ({ children }) => (
          <table className="mb-2 w-full border-collapse border border-black/30 text-sm">
            {children}
          </table>
        ),
        thead: ({ children }) => <thead className="bg-black/5">{children}</thead>,
        tbody: ({ children }) => <tbody>{children}</tbody>,
        tr: ({ children }) => <tr className="border-b border-black/20">{children}</tr>,
        th: ({ children }) => (
          <th className="border border-black/30 px-3 py-1.5 text-left font-semibold">{children}</th>
        ),
        td: ({ children }) => (
          <td className="border border-black/30 px-3 py-1.5">{children}</td>
        ),
      }}
    >
      {text || ''}
    </ReactMarkdown>
  );
}

/** Render code problem text: markdown + KaTeX math ($...$ and $$...$$) */
export function renderProblemMarkdown(text: string): JSX.Element {
  if (!text) return <></>;

  // Split text into segments: markdown text and KaTeX math blocks
  const segments: Array<{ type: 'md' | 'math'; content: string }> = [];
  let remaining = text;
  const mathRegex = /\$\$([\s\S]*?)\$\$|\$([^\s$][^$]*?[^\s$])\$/g;

  let lastIndex = 0;
  let match: RegExpExecArray | null;
  while ((match = mathRegex.exec(remaining)) !== null) {
    // Text before this match
    if (match.index > lastIndex) {
      segments.push({ type: 'md', content: remaining.slice(lastIndex, match.index) });
    }
    const expr = (match[1] || match[2]).trim();
    segments.push({ type: 'math', content: expr });
    lastIndex = match.index + match[0].length;
  }
  // Remaining text
  if (lastIndex < remaining.length) {
    segments.push({ type: 'md', content: remaining.slice(lastIndex) });
  }

  // Render each segment
  let keyCounter = 0;
  return (
    <div className="font-sans text-[13px] leading-relaxed text-zinc-600 dark:text-zinc-400">
      {segments.map((seg) => {
        if (seg.type === 'math') {
          // Inline KaTeX rendering
          try {
            const katex = (window as any).katex;
            if (katex?.renderToString) {
              return (
                <span
                  key={keyCounter++}
                  dangerouslySetInnerHTML={{
                    __html: katex.renderToString(seg.content, {
                      displayMode: false,
                      throwOnError: false,
                    }),
                  }}
                />
              );
            }
          } catch {}
          return <code key={keyCounter++}>{seg.content}</code>;
        }
        // Markdown segment
        return (
          <ReactMarkdown
            key={keyCounter++}
            remarkPlugins={[remarkGfm]}
            components={{
              p: ({ children }) => <span>{children}</span>,
              h1: ({ children }) => <h1 className="mb-2 text-base font-bold">{children}</h1>,
              h2: ({ children }) => <h2 className="mb-1.5 text-sm font-bold">{children}</h2>,
              h3: ({ children }) => <h3 className="mb-1 text-[13px] font-semibold">{children}</h3>,
              ul: ({ children }) => <ul className="mb-2 list-disc space-y-0.5 pl-5">{children}</ul>,
              ol: ({ children }) => <ol className="mb-2 list-decimal space-y-0.5 pl-5">{children}</ol>,
              li: ({ children }) => <li className="leading-6">{children}</li>,
              code: ({ children }) => (
                <code className="rounded bg-black/10 px-1 py-0.5 font-mono text-[11px]">{children}</code>
              ),
              pre: ({ children }) => (
                <pre className="mb-2 overflow-auto rounded border border-zinc-200 bg-zinc-50 p-2 font-mono text-[11px] leading-5">{children}</pre>
              ),
              strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
              em: ({ children }) => <em>{children}</em>,
            }}
          >
            {seg.content}
          </ReactMarkdown>
        );
      })}
    </div>
  );
}
