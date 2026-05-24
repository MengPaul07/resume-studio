import { useTranslation } from 'react-i18next';
import { Bot, CheckCircle2, Loader2, User, XCircle } from 'lucide-react';
import { renderAssistantMarkdown } from '../../lib/tailor/markdown';
import { isThreadMessage } from '../../lib/tailor/utils';
import { JDCard } from './JDCard';
import type { ChatMessage } from '../../lib/tailor/types';

interface Props {
  message: ChatMessage;
  thinkingText?: string;
  onTargetJd?: (jd: import('../../lib/tailor/types').JDMatch) => void;
}

export function ChatBubble({ message: msg, thinkingText, onTargetJd }: Props) {
  const isThread = isThreadMessage(msg);
  const isMarkdownAssistant = msg.role === 'assistant' && !isThread;
  const isSystem = msg.role === 'system' || (msg.role === 'user' && msg.text.startsWith('[system]'));

  if (isSystem) {
    return (
      <div className="flex justify-center py-2">
        <p className="max-w-[80%] text-center font-sans text-[11px] leading-5 text-gray-400 dark:text-zinc-500">
          {msg.text.replace(/^\[system\]\s*/, '')}
        </p>
      </div>
    );
  }

  const bubbleClass = isThread
    ? ''
    : msg.role === 'user'
      ? 'rounded-2xl rounded-br-md bg-[var(--brand-signal)] text-white'
      : msg.role === 'assistant'
        ? 'rounded-2xl rounded-bl-md bg-[#f0f0f0] text-[var(--brand-ink)] dark:bg-zinc-700 dark:text-zinc-100'
        : 'rounded-2xl bg-[var(--brand-surface-soft)] text-[var(--brand-ink)]';

  return (
    <div className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
      {isThread ? (
        <div className="max-w-[86%] py-1.5">
          <SimpleProgress msg={msg} thinkingText={thinkingText} />
        </div>
      ) : (
        <div className={`max-w-[86%] border px-4 py-3 font-mono text-xs ${bubbleClass}`}>
          <div className="mb-2 inline-flex items-center gap-2 text-[10px] uppercase tracking-wide opacity-80">
            {msg.role === 'user' ? <User className="size-3" /> : <Bot className="size-3" />}
            {msg.role}
          </div>

          {msg.jdMatches && msg.jdMatches.length > 0 ? (
            <>
              <div className="whitespace-normal font-sans text-[13px] leading-6">
                {renderAssistantMarkdown(msg.text.split('\n---\n')[0])}
              </div>
              <div className="mt-3 border-t border-black/10 pt-3 dark:border-white/10">
                {msg.jdMatches.slice(0, 5).map((jd, i) => (
                  <JDCard key={jd.id || i} jd={jd} index={i} onTarget={onTargetJd} />
                ))}
              </div>
            </>
          ) : isMarkdownAssistant ? (
            <div className="whitespace-normal font-sans text-[13px] leading-6">
              {renderAssistantMarkdown(msg.text)}
            </div>
          ) : (
            msg.text
          )}
        </div>
      )}
    </div>
  );
}

function ThinkingLines({ text }: { text: string }) {
  const blocks = text
    .split(/\n{2,}/)
    .map((line) => line.trim())
    .filter(Boolean);
  if (!blocks.length) return null;
  return (
    <div className="space-y-2 pl-5">
      {blocks.map((block, i) => (
        <div key={`${block}-${i}`} className="space-y-0.5">
          <p className="font-mono text-[10px] uppercase tracking-wide text-slate-300 dark:text-zinc-600">
            Think {i + 1}
          </p>
          <p className="whitespace-pre-wrap break-words font-sans text-[11px] leading-5 text-slate-400 dark:text-zinc-500">
            {block}
          </p>
        </div>
      ))}
    </div>
  );
}

function SimpleProgress({ msg, thinkingText }: { msg: ChatMessage; thinkingText?: string }) {
  const { t } = useTranslation();
  const running = msg.threadRunning;
  const steps = msg.threadSteps || [];
  const doneCount = steps.filter((s) => s.status === 'done').length;
  const failedCount = steps.filter((s) => s.status === 'failed').length;
  const thinking = msg.thinking || thinkingText || '';

  if (running) {
    return (
      <div className="space-y-2">
        <div className="flex items-center gap-2">
          <Loader2 className="size-3.5 shrink-0 animate-spin text-slate-400 dark:text-zinc-500" />
          <span className="font-sans text-[12px] text-slate-500 dark:text-zinc-400">
            {msg.threadTitle || t('tailor.thinkingAnalyzing')}
          </span>
        </div>
        {thinking ? <ThinkingLines text={thinking} /> : null}
      </div>
    );
  }

  if (doneCount > 0 || failedCount > 0) {
    return (
      <div className="space-y-1.5">
        <div className="flex items-center gap-2">
          {failedCount === 0 ? (
            <CheckCircle2 className="size-3.5 shrink-0 text-emerald-500" />
          ) : (
            <XCircle className="size-3.5 shrink-0 text-amber-500" />
          )}
          <span className="font-sans text-[12px] text-slate-400 dark:text-zinc-500">
            {msg.threadTitle || t('tailor.stepsDone', { count: doneCount })}
          </span>
        </div>
        {thinking ? <ThinkingLines text={thinking} /> : null}
      </div>
    );
  }

  return null;
}
