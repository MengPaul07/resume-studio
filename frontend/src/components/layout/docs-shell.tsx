import { ArrowRight, BookOpen, FileText } from 'lucide-react';
import { Link, Outlet } from 'react-router-dom';

export function DocsShell() {
  return (
    <div className="docs-shell">
      <header className="docs-topbar">
        <Link className="docs-brand" to="/docs" aria-label="Resume Studio 文档首页">
          <span className="docs-brand-mark">JOB</span>
          <span className="docs-brand-copy"><strong>Resume Studio</strong><small>Documentation</small></span>
        </Link>
        <div className="docs-topbar-actions">
          <span className="docs-topbar-status"><i /> docs / live</span>
          <a href="https://chatverse.fun/docs">ChatVerse docs</a>
          <Link to="/dashboard" className="docs-topbar-workspace"><FileText size={14} /> 打开工作台 <ArrowRight size={14} /></Link>
        </div>
      </header>
      <Outlet />
      <footer className="docs-footer">
        <span><BookOpen size={13} /> Markdown 文档与代码一起维护</span>
        <span>Resume Studio · job.chatverse.fun</span>
      </footer>
    </div>
  );
}
