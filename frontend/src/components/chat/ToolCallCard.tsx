"use client";

import { useState } from "react";
import { ToolCallData } from "@/lib/types";

/* Syntax-highlighted JSON */
function JsonSyntax({ data }: { data: unknown }) {
  const json = JSON.stringify(data, null, 2);
  // Simple syntax highlighting via spans
  const highlighted = json.replace(
    /("(?:[^"\\]|\\.)*")\s*:/g,
    '<span class="json-key">$1</span>:'
  ).replace(
    /:\s*("(?:[^"\\]|\\.)*")/g,
    ': <span class="json-string">$1</span>'
  ).replace(
    /:\s*(\d+\.?\d*)/g,
    ': <span class="json-number">$1</span>'
  ).replace(
    /:\s*(true|false)/g,
    ': <span class="json-bool">$1</span>'
  ).replace(
    /:\s*(null)/g,
    ': <span class="json-null">$1</span>'
  );

  return (
    <pre
      className="text-[11px] overflow-auto max-h-48 font-mono leading-relaxed p-3 rounded-lg bg-[#f8f9fc] dark:bg-[#111b21]"
      dangerouslySetInnerHTML={{ __html: highlighted }}
    />
  );
}

/* Tool-specific icons */
function ToolIcon({ name }: { name: string }) {
  const n = name.toLowerCase();
  if (n.includes("search") || n.includes("buscar") || n.includes("find")) {
    return (
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
      </svg>
    );
  }
  if (n.includes("create") || n.includes("add") || n.includes("insert")) {
    return (
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="16" /><line x1="8" y1="12" x2="16" y2="12" />
      </svg>
    );
  }
  if (n.includes("update") || n.includes("edit") || n.includes("modify")) {
    return (
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" /><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
      </svg>
    );
  }
  if (n.includes("send") || n.includes("enviar") || n.includes("message")) {
    return (
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <line x1="22" y1="2" x2="11" y2="13" /><polygon points="22 2 15 22 11 13 2 9 22 2" />
      </svg>
    );
  }
  // Default: wrench
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z" />
    </svg>
  );
}

export function ToolCallCard({ toolCall }: { toolCall: ToolCallData }) {
  const [expanded, setExpanded] = useState(false);
  const isSuccess = toolCall.status === "success";
  const isPending = toolCall.status === "pending" || toolCall.status === "running";

  return (
    <div className="flex justify-center">
      <div
        className={`tool-card inline-flex flex-col max-w-[85%] rounded-xl cursor-pointer ${expanded ? "expanded" : ""}`}
        onClick={() => setExpanded(!expanded)}
      >
        {/* Collapsed header */}
        <div className="flex items-center gap-2 px-3 py-2">
          <span className="text-[#667781] flex-shrink-0">
            <ToolIcon name={toolCall.tool_name} />
          </span>
          <span className="text-[11px] text-[#364c85] dark:text-[#95b2ee] font-mono font-medium">
            {toolCall.tool_name}
          </span>
          {/* Status */}
          {isPending ? (
            <div className="flex items-center gap-1">
              <div className="w-1.5 h-1.5 rounded-full bg-[#95b2ee] animate-pulse" />
            </div>
          ) : (
            <span className={`w-2 h-2 rounded-full ${isSuccess ? "bg-emerald-500" : "bg-red-500"}`} />
          )}
          {/* Duration */}
          {toolCall.duration_ms && (
            <span className="text-[10px] text-[#667781]/60 tabular-nums">
              {toolCall.duration_ms < 1000
                ? `${toolCall.duration_ms.toFixed(0)}ms`
                : `${(toolCall.duration_ms / 1000).toFixed(1)}s`}
            </span>
          )}
          {/* Expand chevron */}
          <svg
            width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#667781"
            strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
            className={`flex-shrink-0 transition-transform duration-300 ${expanded ? "rotate-180" : ""}`}
          >
            <polyline points="6 9 12 15 18 9" />
          </svg>
        </div>

        {/* Progress bar for pending */}
        {isPending && (
          <div className="px-3 pb-1">
            <div className="tool-progress-bar" />
          </div>
        )}

        {/* Expanded: input & result */}
        {expanded && (
          <div className="px-3 pb-3 space-y-2.5 border-t border-[#d0d9f6]/50 dark:border-[#2a3942]/50">
            <div className="mt-2.5">
              <p className="text-[10px] font-semibold text-[#364c85] dark:text-[#95b2ee] mb-1.5 uppercase tracking-wider flex items-center gap-1.5">
                <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                  <polyline points="9 18 15 12 9 6" />
                </svg>
                Input
              </p>
              <JsonSyntax data={toolCall.tool_input} />
            </div>
            {toolCall.tool_result && (
              <div>
                <p className={`text-[10px] font-semibold mb-1.5 uppercase tracking-wider flex items-center gap-1.5 ${isSuccess ? "text-emerald-600 dark:text-emerald-400" : "text-red-600 dark:text-red-400"}`}>
                  <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                    <polyline points="15 18 9 12 15 6" />
                  </svg>
                  Result
                </p>
                {isSuccess ? (
                  <JsonSyntax data={toolCall.tool_result} />
                ) : (
                  <pre className="text-[11px] overflow-auto max-h-48 font-mono leading-relaxed p-3 rounded-lg bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300">
                    {JSON.stringify(toolCall.tool_result, null, 2)}
                  </pre>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
