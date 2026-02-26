import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import type { SessionItem } from "src/storage";
import { clearToken } from "@/lib/auth";

export default function Sidebar(props: {
  sessions: SessionItem[];
  activeId: string;
  activeSession: SessionItem | null;
  onSelectSession: (id: string) => void;
  onLastResult: () => void;
  onExportJSON: () => void;
  onExportPDF: () => void;
  canExportPDF: boolean;
}) {
  const { sessions, activeId, activeSession } = props;

  return (
    <div className="space-y-4">
      <Card className="bg-white/5 border-white/10">
        <CardHeader>
          <CardTitle className="text-base">Sessions</CardTitle>
          <div className="text-xs text-white/60">Saved in browser</div>
        </CardHeader>

        <CardContent>
          <ScrollArea className="h-72 pr-2">
            {sessions.length === 0 ? (
              <div className="text-sm text-white/60">
                No sessions yet. Upload a PDF.
              </div>
            ) : (
              <div className="space-y-2">
                {sessions.map((s) => {
                  const active = s.contract_id === activeId;

                  return (
                    <button
                      key={s.contract_id}
                      onClick={() => props.onSelectSession(s.contract_id)}
                      className={[
                        "w-full text-left rounded-lg px-3 py-2 border transition",
                        active
                          ? "bg-white/10 border-white/20"
                          : "bg-white/0 border-white/10 hover:bg-white/5",
                      ].join(" ")}
                      title={s.filename}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0">
                          <div className="font-medium text-sm truncate">
                            {s.filename}
                          </div>
                          <div className="text-xs text-white/60 truncate mt-1">
                            {s.contract_id}
                          </div>
                        </div>

                        {typeof s.num_clauses === "number" && (
                          <Badge
                            variant="secondary"
                            className="bg-white/10 shrink-0 text-[11px] px-2 py-1"
                          >
                            {s.num_clauses} clauses
                          </Badge>
                        )}
                      </div>
                    </button>
                  );
                })}
              </div>
            )}
          </ScrollArea>

          <div className="mt-3 text-xs text-white/60">
            Active session:{" "}
            <span className="text-white/80">
              {activeSession ? activeSession.contract_id : "None"}
            </span>
          </div>
        </CardContent>
      </Card>

      <Card className="bg-white/5 border-white/10">
        <CardHeader>
          <CardTitle className="text-base">Quick actions</CardTitle>
          <div className="text-xs text-white/60">Export</div>
        </CardHeader>
        <CardContent className="grid grid-cols-2 gap-2">
          <Button
            variant="secondary"
            className="bg-white/10"
            disabled={!activeId}
            onClick={props.onLastResult}
          >
            Last Result
          </Button>

          <Button
            variant="secondary"
            className="bg-white/10"
            disabled={!activeId}
            onClick={props.onExportJSON}
          >
            Export JSON
          </Button>

          <Button
            variant="secondary"
            className="bg-white/10 col-span-2"
            disabled={!activeId || !props.canExportPDF}
            onClick={props.onExportPDF}
          >
            Export PDF(full report mode)
          </Button>

          <Button
      variant="secondary"
      className="bg-white/10 col-span-2"
      onClick={() => {
        clearToken();
        window.location.reload();
      }}
    >
      Logout
    </Button>
        </CardContent>
      </Card>
    </div>
  );
}