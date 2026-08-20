import { useMemo, useState, type ReactNode } from "react";
import ReactMarkdown, { type Components } from "react-markdown";
import {
  ArrowRight,
  BookOpen,
  Check,
  ChevronRight,
  Clipboard,
  Code2,
  ExternalLink,
  FileText,
  Layers3,
  MessageCircle,
  Search,
  Settings2,
  Sparkles,
  Terminal,
} from "lucide-react";
import { Link as RouterLink, useParams } from "react-router-dom";
import remarkGfm from "remark-gfm";
import {
  docCategoryLabels,
  docs,
  docsByCategory,
  findDoc,
  type DocCategory,
  type DocEntry,
} from "./docRegistry";

type Heading = { level: number; title: string; id: string };

const categoryOrder: DocCategory[] = ["start", "features", "development", "reference"];

function headingId(value: string) {
  const normalized = value
    .toLowerCase()
    .replace(/[`*_]/g, "")
    .replace(/[^\p{L}\p{N}\u4e00-\u9fff\s-]/gu, "")
    .trim()
    .replace(/\s+/g, "-");
  return normalized || "section";
}

function extractHeadings(content: string): Heading[] {
  return content
    .split("\n")
    .map((line) => line.match(/^(#{2,3})\s+(.+?)\s*#*\s*$/))
    .filter((match): match is RegExpMatchArray => Boolean(match))
    .map((match) => ({ level: match[1].length, title: match[2].trim(), id: headingId(match[2]) }));
}

function displaySource(sourcePath: string) {
  return sourcePath.replace(/^.*[\\/]docs[\\/]?/, "").replace(/^.*[\\/]content[\\/]?/, "").split("\\").join("/") || "document.md";
}

function resolveDocHref(href: string, currentSlug: string) {
  const [pathPart, hash] = href.split("#", 2);
  if (!pathPart) return `#${hash ?? ""}`;

  const rawPath = pathPart.replace(/\.md$/i, "");
  const base = rawPath.startsWith(".")
    ? currentSlug.split("/").slice(0, -1).concat(rawPath.split("/")).join("/")
    : rawPath;
  const parts: string[] = [];
  base.split("/").forEach((part) => {
    if (!part || part === ".") return;
    if (part === "..") parts.pop();
    else parts.push(part);
  });
  const target = parts.join("/");
  return `/docs/${target}${hash ? `#${hash}` : ""}`;
}

function DocsSidebar({ activeSlug, filter, onFilterChange }: { activeSlug?: string; filter: string; onFilterChange: (value: string) => void }) {
  const visibleDocs = docs.filter((doc) => doc.slug !== "index" && `${doc.title} ${doc.description}`.toLowerCase().includes(filter.toLowerCase()));

  return (
    <aside className="docs-sidebar" aria-label="文档导航">
      <div className="docs-sidebar-label"><BookOpen size={14} /> 文档目录</div>
      <label className="docs-search">
        <Search size={15} aria-hidden="true" />
        <input value={filter} onChange={(event) => onFilterChange(event.target.value)} placeholder="搜索文档" aria-label="搜索文档" />
        {filter ? <span className="docs-search-count">{visibleDocs.length}</span> : null}
      </label>
      <nav className="docs-sidebar-nav">
        {categoryOrder.map((category) => {
          const categoryDocs = docsByCategory(category).filter((doc) => doc.slug !== "index" && visibleDocs.includes(doc));
          if (!categoryDocs.length) return null;
          return (
            <section className="docs-sidebar-section" key={category}>
              <h2>{docCategoryLabels[category]}</h2>
              {categoryDocs.map((doc) => (
                <RouterLink className={`docs-sidebar-link${doc.slug === activeSlug ? " is-active" : ""}`} key={doc.slug} to={`/docs/${doc.slug}`}>
                  <span>{doc.title}</span>
                  {doc.slug === activeSlug ? <ChevronRight size={13} aria-hidden="true" /> : null}
                </RouterLink>
              ))}
            </section>
          );
        })}
        {!visibleDocs.length ? <p className="docs-sidebar-empty">没有匹配的文档</p> : null}
      </nav>
      <div className="docs-sidebar-footnote">
        <span className="docs-status-dot" />
        <span>公开内容来自 <code>docs/content/</code></span>
      </div>
    </aside>
  );
}

export default function DocsPage() {
  const params = useParams();
  const slug = params["*"]?.replace(/^\/+|\/+$/g, "") || undefined;
  const [filter, setFilter] = useState("");
  const currentDoc = findDoc(slug);

  return (
    <div className="docs-page">
      <DocsSidebar activeSlug={slug} filter={filter} onFilterChange={setFilter} />
      <main className="docs-main">
        {!slug ? <DocsHome entries={docs} /> : currentDoc ? <DocsArticle doc={currentDoc} /> : <DocsNotFound />}
      </main>
    </div>
  );
}

function DocsHome({ entries }: { entries: DocEntry[] }) {
  const learningPath = entries.filter((entry) => entry.slug !== "index" && entry.category !== "reference").slice(0, 6);

  return (
    <div className="docs-landing">
      <div className="docs-breadcrumb"><span>Resume Studio</span><ChevronRight size={13} /><strong>Documentation</strong></div>
      <section className="docs-hero">
        <div className="docs-hero-copy">
          <p className="docs-kicker">AI-NATIVE CAREER WORKSPACE</p>
          <h1>把一份简历，变成可迭代的求职工作流。</h1>
          <p>Resume Studio 把导入、结构化、对话式优化、版式预览和模拟面试放进同一个工作区。先跑通本地环境，再沿着功能和架构文档深入。</p>
          <div className="docs-hero-actions">
            <RouterLink className="docs-primary-action" to="/docs/development/setup"><Terminal size={15} /> 本地启动 <ArrowRight size={14} /></RouterLink>
            <RouterLink className="docs-secondary-action" to="/docs/development/architecture"><Code2 size={15} /> 看懂架构</RouterLink>
          </div>
        </div>
        <div className="docs-hero-signal" aria-hidden="true">
          <span className="docs-hero-signal-line" />
          <span className="docs-hero-signal-core">JOB</span>
          <span className="docs-hero-signal-line" />
          <small>IMPORT / TAILOR / INTERVIEW</small>
        </div>
      </section>

      <section className="docs-section">
        <div className="docs-section-heading">
          <div><p className="docs-kicker">01 / WORKFLOW MAP</p><h2>先看懂一份简历如何流动</h2></div>
          <p>每一步都保留可见状态，方便继续修改、复盘和导出。</p>
        </div>
        <WorkflowDiagram />
      </section>

      <section className="docs-section">
        <div className="docs-section-heading">
          <div><p className="docs-kicker">02 / LEARNING PATH</p><h2>按这个顺序读，会更快</h2></div>
        </div>
        <div className="docs-learning-grid">
          {learningPath.map((entry, index) => (
            <RouterLink className="docs-learning-card" key={entry.slug} to={`/docs/${entry.slug}`}>
              <span className="docs-learning-number">{String(index + 1).padStart(2, "0")}</span>
              <span className="docs-learning-copy"><strong>{entry.title}</strong><small>{entry.description}</small></span>
              <ArrowRight size={15} aria-hidden="true" />
            </RouterLink>
          ))}
        </div>
      </section>

      <section className="docs-section docs-source-panel">
        <div className="docs-source-icon"><Sparkles size={18} /></div>
        <div>
          <p className="docs-kicker">DOCS AS CODE</p>
          <h2>新增 Markdown，就会自动进入导航</h2>
          <p>文档页面在构建时读取 <code>frontend/src/docs/content/**/*.md</code>，支持 frontmatter 的标题、描述、分类和顺序。</p>
        </div>
        <pre><code>{"---\ntitle: My guide\ncategory: features\norder: 25\n---"}</code></pre>
      </section>
    </div>
  );
}

function WorkflowDiagram() {
  return (
    <div className="docs-architecture-card">
      <div className="docs-architecture-flow">
        <div className="docs-architecture-node docs-architecture-node-definition"><FileText size={17} /><span><strong>Import / Create</strong><small>导入或从零建立资料</small></span></div>
        <span className="docs-flow-arrow" aria-hidden="true"><ArrowRight size={16} /></span>
        <div className="docs-architecture-node docs-architecture-node-runtime"><MessageCircle size={17} /><span><strong>AI Tailor</strong><small>Agent 对话与变更追踪</small></span></div>
        <span className="docs-flow-arrow" aria-hidden="true"><ArrowRight size={16} /></span>
        <div className="docs-architecture-node docs-architecture-node-director"><Settings2 size={17} /><span><strong>Builder</strong><small>版式、分页和实时预览</small></span></div>
        <span className="docs-flow-arrow" aria-hidden="true"><ArrowRight size={16} /></span>
        <div className="docs-architecture-node docs-architecture-node-event"><Layers3 size={17} /><span><strong>Export / Interview</strong><small>交付简历并验证表达</small></span></div>
      </div>
      <div className="docs-architecture-contexts"><span className="docs-architecture-context-dot" /><strong>Local-first</strong><span>个人简历、导入文件和偏好优先保存在浏览器；后端只处理当前工作流需要的请求。</span></div>
    </div>
  );
}

function DocsArticle({ doc }: { doc: DocEntry }) {
  const headings = useMemo(() => extractHeadings(doc.content), [doc.content]);

  return (
    <article className="docs-article">
      <div className="docs-breadcrumb"><RouterLink to="/docs">Documentation</RouterLink><ChevronRight size={13} /><strong>{doc.title}</strong></div>
      <header className="docs-article-header">
        <div>
          <span className="docs-article-category">{docCategoryLabels[doc.category]}</span>
          <h1>{doc.title}</h1>
          <p>{doc.description}</p>
        </div>
        <span className="docs-source-chip"><FileText size={14} /> {displaySource(doc.sourcePath)}</span>
      </header>
      <div className="docs-article-layout">
        <div className="docs-markdown"><ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents(doc.slug)}>{doc.content}</ReactMarkdown></div>
        <aside className="docs-toc" aria-label="本页目录">
          <strong>本页目录</strong>
          {headings.length ? headings.map((heading) => <a className={heading.level === 3 ? "is-sub" : ""} href={`#${heading.id}`} key={`${heading.id}-${heading.level}`}>{heading.title}</a>) : <span>这篇文档没有二级目录</span>}
        </aside>
      </div>
    </article>
  );
}

function DocsNotFound() {
  return (
    <div className="docs-not-found">
      <span className="docs-not-found-mark">404</span>
      <h1>这篇文档还不存在</h1>
      <p>检查 URL，或者从文档首页选择一篇已发布的 Markdown。</p>
      <RouterLink className="docs-primary-action" to="/docs">回到文档首页 <ArrowRight size={14} /></RouterLink>
    </div>
  );
}

function MarkdownCode({ className, children }: { className?: string; children?: ReactNode }) {
  const code = String(children ?? "").replace(/\n$/, "");
  const language = className?.replace("language-", "") || "code";
  const [copied, setCopied] = useState(false);

  if (!className) return <code className="docs-inline-code">{children}</code>;

  const copyCode = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1600);
    } catch {
      setCopied(false);
    }
  };

  return (
    <div className="docs-code-block">
      <div className="docs-code-toolbar"><span><Code2 size={13} /> {language}</span><button type="button" onClick={copyCode}>{copied ? <Check size={13} /> : <Clipboard size={13} />} {copied ? "已复制" : "复制"}</button></div>
      <pre><code>{code}</code></pre>
    </div>
  );
}

function markdownComponents(currentSlug: string): Components {
  return {
    h1: ({ children }) => <h1>{children}</h1>,
    h2: ({ children }) => {
      const title = String(children);
      return <h2 id={headingId(title)}>{children}</h2>;
    },
    h3: ({ children }) => {
      const title = String(children);
      return <h3 id={headingId(title)}>{children}</h3>;
    },
    code: ({ className, children }) => <MarkdownCode className={className} children={children} />,
    a: ({ href, children }) => {
      if (!href || href.startsWith("#")) return <a href={href}>{children}</a>;
      if (href.startsWith("http")) return <a href={href} target="_blank" rel="noreferrer">{children}<ExternalLink size={12} /></a>;
      return <RouterLink to={resolveDocHref(href, currentSlug)}>{children}</RouterLink>;
    },
    blockquote: ({ children }) => <blockquote><span className="docs-blockquote-mark">“</span>{children}</blockquote>,
  };
}
