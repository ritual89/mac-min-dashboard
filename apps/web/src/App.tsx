import { useState } from "react";
import { createFleetClient } from "./api/client";
import { AllWorkloadsView } from "./components/AllWorkloadsView";
import { AuditView } from "./components/AuditView";
import { FleetView } from "./components/FleetView";
import { SettingsView } from "./components/SettingsView";

export type View = "fleet" | "all" | "audit" | "settings";

const client = createFleetClient();

export function App() {
  const [view, setView] = useState<View>("fleet");

  return (
    <div
      className="min-h-screen p-4"
      style={{
        background: "linear-gradient(0deg, #06051d 30%, #061434)",
      }}
    >
      <header className="mb-4 flex items-center justify-between">
        <h1 className="text-[30px] font-semibold leading-tight tracking-tight text-ghost-white">
          Fleet
        </h1>
        <nav className="flex gap-1" role="tablist">
          <NavTab
            label="Fleet"
            active={view === "fleet"}
            onClick={() => setView("fleet")}
          />
          <NavTab
            label="All"
            active={view === "all"}
            onClick={() => setView("all")}
          />
          <NavTab
            label="Audit"
            active={view === "audit"}
            onClick={() => setView("audit")}
          />
          <NavTab
            label="Settings"
            active={view === "settings"}
            onClick={() => setView("settings")}
          />
        </nav>
      </header>

      {view === "fleet" && <FleetView client={client} />}
      {view === "all" && <AllWorkloadsView client={client} />}
      {view === "audit" && <AuditView client={client} />}
      {view === "settings" && <SettingsView client={client} />}
    </div>
  );
}

function NavTab({
  label,
  active,
  onClick,
}: {
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      role="tab"
      aria-selected={active}
      className={`rounded-full px-3 py-1.5 text-xs font-medium transition-colors ${
        active
          ? "bg-steel-navy text-portal-blue"
          : "text-mist hover:bg-steel-navy/50 hover:text-ice-blue"
      }`}
      onClick={onClick}
    >
      {label}
    </button>
  );
}
