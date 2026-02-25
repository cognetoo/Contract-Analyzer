import React from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

export default function ClauseDrawer(props: {
  open: boolean;
  onClose: () => void;
  loading?: boolean;
  clauseId?: number | null;
  clauseType?: string | null;
  text?: string;
}) {
  const { open, onClose, loading, clauseId, clauseType, text } = props;

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Panel */}
      <div className="absolute right-0 top-0 h-full w-full sm:w-[520px] p-4">
        <Card className="h-full bg-slate-950/80 border-white/10 shadow-2xl overflow-hidden flex flex-col">
          <div className="p-4 border-b border-white/10 flex items-center justify-between">
            <div>
              <div className="text-sm text-white/60">Clause</div>
              <div className="text-lg font-semibold text-white">
                {clauseId != null ? `Clause ${clauseId}` : "—"}
                {clauseType ? <span className="text-white/60"> · {clauseType}</span> : null}
              </div>
            </div>

            <Button variant="secondary" className="bg-white/10" onClick={onClose}>
              Close
            </Button>
          </div>

          <div className="p-4 flex-1 overflow-auto">
            {loading ? (
              <div className="text-sm text-white/60">Loading clause…</div>
            ) : (
              <div className="text-sm text-white/85 whitespace-pre-wrap leading-6">
                {text || "No text."}
              </div>
            )}
          </div>
        </Card>
      </div>
    </div>
  );
}