import { useLayoutEffect, useRef, type CSSProperties } from 'react';

interface ScopedResumeHtmlProps {
  html: string;
  className?: string;
  style?: CSSProperties;
}

export function ScopedResumeHtml({ html, className, style }: ScopedResumeHtmlProps) {
  const hostRef = useRef<HTMLDivElement | null>(null);

  useLayoutEffect(() => {
    const host = hostRef.current;
    if (!host) return;
    const root = host.shadowRoot || host.attachShadow({ mode: 'open' });
    root.innerHTML = html;
  }, [html]);

  return <div ref={hostRef} className={className} style={style} />;
}
