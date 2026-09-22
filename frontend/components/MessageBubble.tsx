"use client";

import { useState } from "react";
import type { ChatResponse, RetrievalType } from "@/lib/api";
import { SourceCitation } from "./SourceCitation";

export interface Message {
  id: string;
  kind: "question" | "answer" | "error";
  text: string;
  response?: ChatResponse;
}

const RETRIEVAL_LABEL: Record<RetrievalType, string> = {
  hybrid_rag: "Hybrid RAG",
  sql_rag: "SQL RAG",
  blocked: "Access blocked",
};

const RETRIEVAL_STYLE: Record<RetrievalType, string> = {
  hybrid_rag: "bg-emerald-50 text-emerald-800 ring-emerald-200",
  sql_rag: "bg-indigo-50 text-indigo-800 ring-indigo-200",
  blocked: "bg-amber-100 text-amber-900 ring-amber-300",
};

export function MessageBubble({ message }: { message: Message }) {
  if (message.kind === "question") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[80%] rounded-2xl rounded-br-sm bg-slate-800 px-4 py-2.5 text-sm text-white shadow-sm">
          {message.text}
        </div>
      </div>
    );
  }

  if (message.kind === "error") {
    return (
      <div className="flex justify-start">
        <div className="max-w-[85%] rounded-2xl rounded-bl-sm border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          <div className="mb-1 flex items-center gap-1.5 font-semibold">
            <WarnIcon /> Something went wrong
          </div>
          {message.text}
        </div>
      </div>
    );
  }

  const response = message.response!;
  const blocked = response.blocked || response.retrieval_type === "blocked";

  return (
    <div className="flex justify-start">
      <div
        className={
          blocked
            ? // A refusal is a policy decision, not an error. Amber + a lock, so
              // it is visually distinct from both a normal answer and a failure.
              "max-w-[85%] rounded-2xl rounded-bl-sm border-2 border-amber-300 bg-amber-50 px-4 py-3 shadow-sm"
            : "max-w-[85%] rounded-2xl rounded-bl-sm border border-slate-200 bg-white px-4 py-3 shadow-sm"
        }
      >
        <div className="mb-2 flex flex-wrap items-center gap-2">
          {blocked && <LockIcon />}
          <span
            className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ring-1 ring-inset ${RETRIEVAL_STYLE[response.retrieval_type]}`}
          >
            {RETRIEVAL_LABEL[response.retrieval_type]}
          </span>
          <span className="font-mono text-[10px] text-slate-400">
            answered as {response.role}
          </span>
        </div>

        <p
          className={`whitespace-pre-wrap text-sm leading-relaxed ${blocked ? "text-amber-900" : "text-slate-800"}`}
        >
          {message.text}
        </p>

        {response.sql_query && <SqlBlock sql={response.sql_query} />}
        <SourceCitation sources={response.sources} />

        {response.rerank_scores && response.rerank_scores.length > 0 && (
          <p className="mt-2 font-mono text-[10px] text-slate-400">
            rerank scores: {response.rerank_scores.map((s) => s.toFixed(3)).join(" · ")}
          </p>
        )}
      </div>
    </div>
  );
}

/** Showing the executed query is a trust feature, not debug output. */
function SqlBlock({ sql }: { sql: string }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="mt-3">
      <button
        onClick={() => setOpen((v) => !v)}
        className="text-xs font-medium text-indigo-700 hover:text-indigo-900 hover:underline"
      >
        {open ? "▾ Hide" : "▸ Show"} the SQL that was executed
      </button>
      {open && (
        <pre className="mt-2 overflow-x-auto rounded-lg bg-slate-900 px-3 py-2.5 font-mono text-[11px] leading-relaxed text-slate-100">
          {sql}
        </pre>
      )}
    </div>
  );
}

function LockIcon() {
  return (
    <svg viewBox="0 0 16 16" className="h-3.5 w-3.5 text-amber-700" fill="currentColor" aria-hidden="true">
      <path d="M8 1a3 3 0 0 0-3 3v2H4.5A1.5 1.5 0 0 0 3 7.5v6A1.5 1.5 0 0 0 4.5 15h7a1.5 1.5 0 0 0 1.5-1.5v-6A1.5 1.5 0 0 0 11.5 6H11V4a3 3 0 0 0-3-3Zm2 5H6V4a2 2 0 1 1 4 0v2Z" />
    </svg>
  );
}

function WarnIcon() {
  return (
    <svg viewBox="0 0 16 16" className="h-3.5 w-3.5" fill="currentColor" aria-hidden="true">
      <path d="M8 1.5 15 14H1L8 1.5Zm0 4.5v4h.01V6H8Zm0 5.5v1h.01v-1H8Z" />
    </svg>
  );
}
