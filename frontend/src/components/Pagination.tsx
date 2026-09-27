export default function Pagination({ page, canGoNext, onPageChange }: { page: number; canGoNext: boolean; onPageChange: (page: number) => void }) {
  return <nav aria-label="Pagination" className="flex items-center justify-between gap-3 rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm">
    <button type="button" className="rounded-lg border border-slate-200 px-3 py-2 font-medium disabled:cursor-not-allowed disabled:opacity-40" disabled={page <= 1} onClick={() => onPageChange(page - 1)}>Previous</button>
    <span className="text-muted">Page <strong className="text-ink">{page}</strong></span>
    <button type="button" className="rounded-lg border border-slate-200 px-3 py-2 font-medium disabled:cursor-not-allowed disabled:opacity-40" disabled={!canGoNext} onClick={() => onPageChange(page + 1)}>Next</button>
  </nav>
}
