"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import { API_BASE_URL } from "@/lib/api";

type Scope = "personal" | "organization";
type Settings = {
  threshold_days: number;
  check_interval_minutes: number;
  channel: "email" | "webhook" | "slack" | "teams" | "discord";
  recipients: string[];
  enabled: boolean;
  updated_at?: string | null;
};

const defaults: Settings = { threshold_days: 30, check_interval_minutes: 60, channel: "email", recipients: [], enabled: true };

export default function SettingsPage() {
  const [scope, setScope] = useState<Scope>("personal");
  const [values, setValues] = useState<Record<Scope, Settings>>({ personal: defaults, organization: defaults });
  const [smtpConfigured, setSmtpConfigured] = useState(false);
  const [status, setStatus] = useState("Chargement...");
  const [error, setError] = useState<string | null>(null);
  const current = values[scope];

  useEffect(() => {
    void fetch(`${API_BASE_URL}/api/settings`)
      .then(async response => {
        if (!response.ok) throw new Error("Impossible de charger les paramètres.");
        return response.json();
      })
      .then(data => {
        setValues({ personal: { ...defaults, ...data.personal }, organization: { ...defaults, ...data.organization } });
        setSmtpConfigured(Boolean(data.smtp_configured));
        setStatus("");
      })
      .catch(reason => setError(reason instanceof Error ? reason.message : "Erreur de chargement."));
  }, []);

  const update = (field: keyof Settings, value: string | number | boolean | string[]) => {
    setValues(previous => ({ ...previous, [scope]: { ...previous[scope], [field]: value } }));
  };

  const save = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    setStatus("Enregistrement...");
    const response = await fetch(`${API_BASE_URL}/api/settings/${scope}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(current),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      setError(data.detail || "Les paramètres n'ont pas été enregistrés.");
      setStatus("");
      return;
    }
    setValues(previous => ({ ...previous, [scope]: data }));
    setStatus("Paramètres enregistrés.");
  };

  const testNotification = async () => {
    setError(null);
    setStatus("Envoi du test...");
    const response = await fetch(`${API_BASE_URL}/api/notifications/test`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ scope }),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) setError(data.detail || "La notification de test a échoué.");
    else setStatus(data.message);
  };

  return (
    <main className="min-h-screen bg-slate-950 text-white p-6 md:p-10">
      <div className="max-w-3xl mx-auto">
        <Link href="/" className="text-blue-400 hover:text-blue-300">← Retour au dashboard</Link>
        <h1 className="text-4xl font-bold mt-6">Paramètres</h1>
        <p className="text-slate-400 mt-2">Configurez vos préférences sans exposer les secrets du serveur.</p>
        {status && <p className="mt-4 text-sm text-emerald-400">{status}</p>}
        {error && <p className="mt-4 rounded-lg bg-red-950/60 p-3 text-sm text-red-300">{error}</p>}
        <div className="flex gap-2 mt-8">
          {(["personal", "organization"] as Scope[]).map(item => (
            <button key={item} type="button" onClick={() => setScope(item)} className={`px-4 py-2 rounded-lg ${scope === item ? "bg-blue-600" : "bg-slate-800 text-slate-300"}`}>
              {item === "personal" ? "Personnel" : "Organisation"}
            </button>
          ))}
        </div>
        <form onSubmit={save} className="mt-4 space-y-6 rounded-xl border border-slate-800 bg-slate-900/70 p-6">
          <label className="block"><span className="text-sm text-slate-300">Seuil d&apos;alerte (jours)</span><input type="number" min="1" max="3650" value={current.threshold_days} onChange={event => update("threshold_days", Number(event.target.value))} className="mt-2 w-full rounded-lg bg-slate-800 p-3" /></label>
          <label className="block"><span className="text-sm text-slate-300">Fréquence de contrôle (minutes)</span><input type="number" min="1" max="10080" value={current.check_interval_minutes} onChange={event => update("check_interval_minutes", Number(event.target.value))} className="mt-2 w-full rounded-lg bg-slate-800 p-3" /></label>
          <label className="block"><span className="text-sm text-slate-300">Canal</span><select value={current.channel} onChange={event => update("channel", event.target.value)} className="mt-2 w-full rounded-lg bg-slate-800 p-3"><option value="email">Email</option><option value="webhook">Webhook</option><option value="slack">Slack</option><option value="teams">Teams</option><option value="discord">Discord</option></select></label>
          <label className="block"><span className="text-sm text-slate-300">Destinataires (séparés par des virgules)</span><input type="text" value={current.recipients.join(", ")} onChange={event => update("recipients", event.target.value.split(",").map(item => item.trim()).filter(Boolean))} className="mt-2 w-full rounded-lg bg-slate-800 p-3" /></label>
          <label className="flex items-center gap-3 text-sm text-slate-300"><input type="checkbox" checked={current.enabled} onChange={event => update("enabled", event.target.checked)} /> Notifications activées</label>
          <div className="flex flex-wrap gap-3">
            <button type="submit" className="rounded-lg bg-blue-600 px-5 py-3 font-semibold hover:bg-blue-500">Enregistrer</button>
            <button type="button" onClick={() => void testNotification()} className="rounded-lg bg-slate-700 px-5 py-3 font-semibold hover:bg-slate-600">Tester la notification</button>
          </div>
          <p className="text-xs text-slate-500">Configuration SMTP : {smtpConfigured ? "disponible" : "non configurée"}. Les mots de passe et secrets ne sont jamais renvoyés par l&apos;API.</p>
        </form>
      </div>
    </main>
  );
}
