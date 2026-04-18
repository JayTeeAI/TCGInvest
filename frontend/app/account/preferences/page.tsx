"use client";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";

type Frequency = "daily" | "weekly" | "monthly" | "off";

const OPTIONS: { value: Frequency; label: string; description: string }[] = [
  { value: "daily",   label: "Daily",   description: "Get a digest every morning with your watchlist updates." },
  { value: "weekly",  label: "Weekly",  description: "Every Sunday — a summary of the week's price movements." },
  { value: "monthly", label: "Monthly", description: "First of each month, timed with the booster box pipeline." },
  { value: "off",     label: "Off",     description: "No digest emails. You can still visit the site any time." },
];

export default function PreferencesPage() {
  const router = useRouter();
  const [frequency, setFrequency] = useState<Frequency>("weekly");
  const [saved, setSaved] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    fetch("/auth/me", { credentials: "include" })
      .then(r => r.json())
      .then(u => {
        if (!u?.authenticated) { router.push("/"); return; }
        return fetch("/api/internal?path=/api/digest/preferences", { credentials: "include" });
      })
      .then(r => r?.json())
      .then(d => { if (d?.digest_frequency) setFrequency(d.digest_frequency); })
      .catch(() => setError("Failed to load preferences."))
      .finally(() => setLoading(false));
  }, []);

  async function save() {
    setSaving(true);
    setSaved(false);
    setError("");
    try {
      const r = await fetch("/api/internal?path=/api/digest/preferences", {
        method: "PUT",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ digest_frequency: frequency }),
      });
      const d = await r.json();
      if (d.updated) setSaved(true);
      else setError("Save failed. Please try again.");
    } catch {
      setError("Network error. Please try again.");
    } finally {
      setSaving(false);
    }
  }

  if (loading) return (
    <div className="min-h-screen bg-[#0a0a0a] flex items-center justify-center">
      <div className="text-gray-400 text-sm">Loading preferences…</div>
    </div>
  );

  return (
    <div className="min-h-screen bg-[#0a0a0a] py-12 px-4">
      <div className="max-w-lg mx-auto">
        {/* Header */}
        <div className="mb-8">
          <button onClick={() => router.back()} className="text-gray-500 hover:text-gray-300 text-sm mb-4 flex items-center gap-1">
            ← Back
          </button>
          <h1 className="text-white text-2xl font-bold">Email Preferences</h1>
          <p className="text-gray-400 text-sm mt-1">
            Choose how often you receive your watchlist digest.
          </p>
        </div>

        {/* Options */}
        <div className="space-y-3">
          {OPTIONS.map(opt => (
            <button
              key={opt.value}
              onClick={() => { setFrequency(opt.value); setSaved(false); }}
              className={`w-full text-left rounded-xl border p-4 transition-all ${
                frequency === opt.value
                  ? "border-yellow-400 bg-yellow-400/5"
                  : "border-[#2a2a2a] bg-[#111] hover:border-[#444]"
              }`}
            >
              <div className="flex items-center justify-between">
                <span className={`font-semibold text-sm ${frequency === opt.value ? "text-yellow-400" : "text-white"}`}>
                  {opt.label}
                </span>
                {frequency === opt.value && (
                  <span className="text-yellow-400 text-xs font-bold">✓ Selected</span>
                )}
              </div>
              <p className="text-gray-400 text-xs mt-1">{opt.description}</p>
            </button>
          ))}
        </div>

        {/* Save */}
        <div className="mt-6">
          <button
            onClick={save}
            disabled={saving}
            className="w-full bg-yellow-400 hover:bg-yellow-300 text-black font-bold py-3 rounded-xl text-sm transition disabled:opacity-50"
          >
            {saving ? "Saving…" : "Save Preference"}
          </button>
          {saved && (
            <p className="text-green-400 text-sm text-center mt-3">✓ Preference saved</p>
          )}
          {error && (
            <p className="text-red-400 text-sm text-center mt-3">{error}</p>
          )}
        </div>

        {/* Info box */}
        <div className="mt-6 bg-[#111] border border-[#222] rounded-xl p-4">
          <p className="text-gray-400 text-xs leading-relaxed">
            Digests include price changes, 7-day movement, and AI signals for everything in your watchlist.
            Weekly digests go out every <strong className="text-gray-300">Sunday at 9am</strong>.
            Monthly digests go out on the <strong className="text-gray-300">1st of each month</strong> — timed with the data pipeline refresh.
          </p>
        </div>
      </div>
    </div>
  );
}
