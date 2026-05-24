import { useParams } from 'react-router-dom';

export function PrintResumePage() {
  const { id } = useParams();

  return (
    <main className="min-h-screen bg-[var(--brand-paper)] p-6 md:p-10">
      <article className="mx-auto max-w-[210mm] min-h-[297mm] border border-black bg-white p-8 resume-print">
        <header className="border-b border-black pb-4">
          <h1 className="font-serif text-4xl uppercase">John Doe</h1>
          <p className="font-mono text-xs uppercase text-[var(--brand-ink-muted)] mt-2">Print Resume / ID: {id}</p>
        </header>
        <section className="mt-6 font-mono text-sm leading-relaxed">
          <h2 className="font-serif text-xl uppercase mb-3">Summary</h2>
          <p>Product-minded software engineer with 8+ years building distributed systems and internal platforms.</p>
        </section>
      </article>
    </main>
  );
}
