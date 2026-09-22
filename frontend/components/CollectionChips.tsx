import { collectionStyle } from "@/lib/roles";

const ALL_COLLECTIONS = ["general", "clinical", "nursing", "billing", "equipment"];

/**
 * Shows every collection in the system, marking which ones this role may read.
 *
 * Showing the restricted ones greyed out is a deliberate UI choice and is not a
 * leak: the set of collection *names* is public (it is in the assignment brief
 * and the README). What is protected is their contents, and the LLM never
 * receives a chunk from a greyed-out collection. Making the boundary visible is
 * what lets a reviewer see RBAC working.
 */
export function CollectionChips({
  permitted,
  sqlAccess,
}: {
  permitted: string[];
  sqlAccess: boolean;
}) {
  return (
    <div className="space-y-4">
      <div>
        <h3 className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
          Document access
        </h3>
        <div className="flex flex-wrap gap-1.5">
          {ALL_COLLECTIONS.map((collection) => {
            const allowed = permitted.includes(collection);
            return (
              <span
                key={collection}
                className={
                  allowed
                    ? `inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs font-medium ring-1 ring-inset ${collectionStyle(collection)}`
                    : "inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs font-medium text-slate-400 ring-1 ring-inset ring-slate-200 line-through decoration-slate-300"
                }
                title={
                  allowed
                    ? `You can retrieve from ${collection}`
                    : `${collection} is filtered out of your queries at the vector store`
                }
              >
                {!allowed && <LockIcon />}
                {collection}
              </span>
            );
          })}
        </div>
      </div>

      <div>
        <h3 className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
          Analytics (SQL)
        </h3>
        <span
          className={
            sqlAccess
              ? "inline-flex items-center gap-1 rounded-md bg-indigo-50 px-2 py-1 text-xs font-medium text-indigo-800 ring-1 ring-inset ring-indigo-200"
              : "inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs font-medium text-slate-400 ring-1 ring-inset ring-slate-200"
          }
        >
          {!sqlAccess && <LockIcon />}
          claims · maintenance_tickets
        </span>
      </div>
    </div>
  );
}

function LockIcon() {
  return (
    <svg viewBox="0 0 16 16" className="h-3 w-3" fill="currentColor" aria-hidden="true">
      <path d="M8 1a3 3 0 0 0-3 3v2H4.5A1.5 1.5 0 0 0 3 7.5v6A1.5 1.5 0 0 0 4.5 15h7a1.5 1.5 0 0 0 1.5-1.5v-6A1.5 1.5 0 0 0 11.5 6H11V4a3 3 0 0 0-3-3Zm2 5H6V4a2 2 0 1 1 4 0v2Z" />
    </svg>
  );
}
