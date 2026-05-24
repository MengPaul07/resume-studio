import { useParams } from 'react-router-dom';

export function PrintCoverLetterPage() {
  const { id } = useParams();

  return (
    <main className="min-h-screen bg-[var(--brand-paper)] p-6 md:p-10">
      <article className="mx-auto max-w-[210mm] min-h-[297mm] border border-black bg-white p-8 cover-letter-print">
        <h1 className="font-serif text-4xl uppercase border-b border-black pb-4">Cover Letter</h1>
        <p className="font-mono text-xs uppercase text-[var(--brand-ink-muted)] mt-2">Print Cover Letter / ID: {id}</p>
        <section className="mt-8 font-mono text-sm leading-7">
          Dear Hiring Manager,
          <br />
          <br />
          I am excited to apply for this role. My recent work focused on scaling backend systems, building reliable
          data pipelines, and shipping measurable product outcomes.
        </section>
      </article>
    </main>
  );
}
