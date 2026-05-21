import { useCallback, useEffect, useState } from "react";
import type { FleetClient } from "../api/client";

interface Settings {
  notify_orange: boolean;
  notify_red: boolean;
}

interface SettingsViewProps {
  client: FleetClient;
  initialSettings?: Settings;
}

export function SettingsView({ client, initialSettings }: SettingsViewProps) {
  const [settings, setSettings] = useState<Settings | null>(
    initialSettings ?? null,
  );
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (initialSettings !== undefined) {
      return;
    }
    let cancelled = false;
    client
      .fetchSettings()
      .then((s) => {
        if (!cancelled) {
          setSettings(s);
          setError(null);
        }
      })
      .catch((err: Error) => {
        if (!cancelled) {
          setError(err.message);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [client, initialSettings]);

  if (!settings && !error) {
    return <p className="text-sm text-gray-500">Loading settings…</p>;
  }

  return (
    <div>
      {error && (
        <p className="mb-4 rounded border border-red-900 bg-red-950/40 p-3 text-sm text-red-300">
          {error}
        </p>
      )}

      {settings && (
        <SettingsToggles
          settings={settings}
          client={client}
          onUpdate={setSettings}
          onError={setError}
        />
      )}
    </div>
  );
}

function SettingsToggles({
  settings,
  client,
  onUpdate,
  onError,
}: {
  settings: Settings;
  client: FleetClient;
  onUpdate: (s: Settings) => void;
  onError: (e: string | null) => void;
}) {
  const [saving, setSaving] = useState(false);

  const toggle = useCallback(
    async (key: keyof Settings) => {
      setSaving(true);
      onError(null);
      const newValue = !settings[key];
      try {
        await client.patchSettings({ [key]: newValue });
        onUpdate({ ...settings, [key]: newValue });
      } catch (err) {
        onError(err instanceof Error ? err.message : "save failed");
      } finally {
        setSaving(false);
      }
    },
    [client, settings, onUpdate, onError],
  );

  return (
    <div className="space-y-4">
      <h2 className="text-sm font-medium text-gray-300">
        Telegram Notifications
      </h2>
      <ToggleRow
        label="Notify on orange severity"
        checked={settings.notify_orange}
        disabled={saving}
        onToggle={() => toggle("notify_orange")}
      />
      <ToggleRow
        label="Notify on red severity"
        checked={settings.notify_red}
        disabled={saving}
        onToggle={() => toggle("notify_red")}
      />
    </div>
  );
}

function ToggleRow({
  label,
  checked,
  disabled,
  onToggle,
}: {
  label: string;
  checked: boolean;
  disabled: boolean;
  onToggle: () => void;
}) {
  return (
    <label className="flex items-center justify-between rounded border border-border bg-row px-4 py-3">
      <span className="text-sm text-gray-200">{label}</span>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        disabled={disabled}
        className={`relative h-6 w-11 rounded-full transition-colors ${
          checked ? "bg-emerald-600" : "bg-gray-600"
        } ${disabled ? "opacity-50" : ""}`}
        onClick={onToggle}
      >
        <span
          className={`absolute top-0.5 left-0.5 h-5 w-5 rounded-full bg-white transition-transform ${
            checked ? "translate-x-5" : ""
          }`}
        />
      </button>
    </label>
  );
}
