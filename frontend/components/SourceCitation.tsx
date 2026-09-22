import type { Source } from "@/lib/api";
import { collectionStyle } from "@/lib/roles";

/**
 * One card per source. The document name and the full section path are both
 * shown, because "staff_handbook.pdf" alone is not a citation a reader can act
 * on - the section path is what makes the claim checkable.
 */
export function SourceCitation({ sources }: { sources: Source[] }) {
  if (sources.length === 0) return null;

  return (
    <div className="mt-3 border-t border-slate-200 pt-3">
      <h4 className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
        Sources ({sources.length})
      </h4>
      <ul className="space-y-1.5">
        {sources.map((source, index) => (
          <li
            key={`${source.source_document}-${source.section_title}-${index}`}
            className="flex items-start gap-2 rounded-lg border border-slate-200 bg-slate-50/70 px-2.5 py-2"
          >
            <span className="mt-0.5 flex h-4 w-4 flex-none items-center justify-center rounded bg-slate-200 text-[10px] font-semibold text-slate-600">
              {index + 1}
            </span>
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-1.5">
                <span className="font-mono text-xs font-medium text-slate-800">
                  {source.source_document}
                </span>
                <span
                  className={`rounded px-1.5 py-0.5 text-[10px] font-medium ring-1 ring-inset ${collectionStyle(source.collection)}`}
                >
                  {source.collection}
                </span>
              </div>
              {source.section_title && (
                <p className="mt-0.5 text-xs leading-snug text-slate-600">
                  {source.section_title}
                </p>
              )}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
