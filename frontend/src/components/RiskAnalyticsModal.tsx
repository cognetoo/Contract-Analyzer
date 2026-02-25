import React, { useEffect } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import RiskDashboard from "@/components/RiskDashboard";

export default function RiskAnalyticsModal(props: {
  open: boolean;
  onClose: () => void;
  result: any;
  onOpenClause?: (id: number) => void;
}) {
  const { open, onClose } = props;

  // ESC to close
  useEffect(() => {
    if (!open) return;

    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Fullscreen panel */}
      <div className="absolute inset-0 p-4 md:p-8 overflow-auto">
        <Card className="min-h-full bg-slate-950/80 border-white/10 shadow-2xl overflow-hidden">
          <div className="p-4 md:p-6 border-b border-white/10 flex items-center justify-between">
            <div>
              <div className="text-xs text-white/60">Analytics</div>
              <div className="text-lg md:text-2xl font-semibold text-white">
                Risk dashboard
              </div>
              <div className="text-xs text-white/50 mt-1">
                Press <span className="text-white/70">Esc</span> to close
              </div>
            </div>

            <Button
              variant="secondary"
              className="bg-white/10"
              onClick={onClose}
            >
              Close
            </Button>
          </div>

          <div className="p-4 md:p-6">
            <RiskDashboard result={props.result} onOpenClause={props.onOpenClause} />
          </div>
        </Card>
      </div>
    </div>
  );
}