"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { Toaster, toast } from "react-hot-toast";
import AddDomainModal from "./AddDomainModal";
import CertificateDetailModal from "./CertificateDetailModal";
import { API_BASE_URL } from "@/lib/api";

export interface Certificate {
  domain: string;
  status: "OK" | "Expire bientôt" | "Expiré" | "Erreur" | "En attente" | "Vérification...";
  days_left?: number;
  expiry_date?: string;
  valid_from?: string;
  valid_until?: string;
  issuer?: string;
  subject?: string;
  serial_number?: string;
  fingerprint?: string;
  san?: string[];
  checked_at?: string;
  error_type?: string;
  error_message?: string;
}

type View = "overview" | "domains" | "alerts" | "history" | "onboarding";
type Filter = "all" | "OK" | "Expire bientôt" | "Expiré" | "Erreur";

const navItems: { id: View; label: string; mark: string; shortcut: string }[] = [
  { id: "overview", label: "Overview", mark: "✦", shortcut: "O" },
  { id: "domains", label: "Domains", mark: "◇", shortcut: "D" },
  { id: "alerts", label: "Alerts", mark: "!", shortcut: "A" },
  { id: "history", label: "History", mark: "◷", shortcut: "H" },
];

const statusMeta: Record<Certificate["status"], { label: string; tone: string }> = {
  OK: { label: "Healthy", tone: "ok" },
  "Expire bientôt": { label: "Watch", tone: "watch" },
  Expiré: { label: "Critical", tone: "critical" },
  Erreur: { label: "Error", tone: "critical" },
  "En attente": { label: "Pending", tone: "muted" },
  "Vérification...": { label: "Checking", tone: "info" },
};

function formatDate(value?: string) {
  return value ? new Date(value).toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" }) : "—";
}

function StatusPill({ status }: { status: Certificate["status"] }) {
  const meta = statusMeta[status];
  return <span className={`status-pill ${meta.tone}`}><span className="status-dot" />{meta.label}</span>;
}

function EmptyState({ title, text, action }: { title: string; text: string; action?: React.ReactNode }) {
  return <div className="empty-state"><div className="empty-icon">◇</div><h2>{title}</h2><p>{text}</p>{action}</div>;
}

export default function DashboardDisplay() {
  const [certificates, setCertificates] = useState<Certificate[]>([]);
  const [view, setView] = useState<View>("overview");
  const [filter, setFilter] = useState<Filter>("all");
  const [query, setQuery] = useState("");
  const [sortAscending, setSortAscending] = useState(true);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [addOpen, setAddOpen] = useState(false);
  const [selected, setSelected] = useState<Certificate | null>(null);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [theme, setTheme] = useState<"dark" | "light">(() => {
    if (typeof window === "undefined") return "dark";
    return window.localStorage.getItem("ssl-monitor-theme") === "light" ? "light" : "dark";
  });

  const loadData = useCallback(async () => {
    setIsLoading(true);
    try {
      const [statusResponse, domainsResponse] = await Promise.all([
        fetch(`${API_BASE_URL}/api/status?t=${Date.now()}`),
        fetch(`${API_BASE_URL}/api/domains`),
      ]);
      if (!statusResponse.ok || !domainsResponse.ok) throw new Error("Unable to load monitoring data.");
      const statuses: Certificate[] = await statusResponse.json();
      const { domains } = await domainsResponse.json() as { domains: string[] };
      const statusMap = new Map(statuses.map((status) => [status.domain, status]));
      setCertificates(domains.map((domain) => statusMap.get(domain) ?? { domain, status: "En attente" }));
      setError(null);
    } catch {
      setError("The monitoring API is unavailable. Check the backend and try again.");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => { const initialLoad = window.setTimeout(() => { void loadData(); }, 0); const timer = setInterval(loadData, 5 * 60 * 1000); return () => { window.clearTimeout(initialLoad); clearInterval(timer); }; }, [loadData]);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "/" && document.activeElement?.tagName !== "INPUT") { event.preventDefault(); document.getElementById("global-search")?.focus(); }
      if (event.key.toLowerCase() === "n" && document.activeElement?.tagName !== "INPUT") setAddOpen(true);
      const shortcut = navItems.find((item) => event.key.toLowerCase() === item.shortcut.toLowerCase());
      if (shortcut && document.activeElement?.tagName !== "INPUT") setView(shortcut.id);
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  useEffect(() => { document.documentElement.dataset.theme = theme; window.localStorage.setItem("ssl-monitor-theme", theme); }, [theme]);

  const counts = useMemo(() => ({
    total: certificates.length,
    healthy: certificates.filter((cert) => cert.status === "OK").length,
    watch: certificates.filter((cert) => cert.status === "Expire bientôt").length,
    critical: certificates.filter((cert) => cert.status === "Expiré" || cert.status === "Erreur").length,
  }), [certificates]);

  const rows = useMemo(() => certificates.filter((cert) => {
    const matchesQuery = cert.domain.toLowerCase().includes(query.toLowerCase()) || (cert.issuer ?? "").toLowerCase().includes(query.toLowerCase());
    const matchesFilter = filter === "all" || cert.status === filter || (filter === "Erreur" && cert.status === "Expiré");
    return matchesQuery && matchesFilter;
  }).sort((a, b) => {
    const aDays = a.days_left ?? Number.POSITIVE_INFINITY;
    const bDays = b.days_left ?? Number.POSITIVE_INFINITY;
    return sortAscending ? aDays - bDays : bDays - aDays;
  }), [certificates, filter, query, sortAscending]);

  const handleDomainsAdded = (domains: string[]) => {
    setCertificates((current) => {
      const existing = new Set(current.map((certificate) => certificate.domain));
      return [...current, ...domains.filter((domain) => !existing.has(domain)).map((domain) => ({ domain, status: "Vérification..." as const }))];
    });
    void Promise.all(domains.map(async (domain) => {
      try {
        const response = await fetch(`${API_BASE_URL}/api/check/${encodeURIComponent(domain)}`);
        if (!response.ok) throw new Error("Certificate check failed");
        const certificate: Certificate = await response.json();
        setCertificates((current) => current.map((item) => item.domain === domain ? certificate : item));
      } catch {
        setCertificates((current) => current.map((item) => item.domain === domain ? { ...item, status: "Erreur", error_message: "Certificate check failed" } : item));
      }
    }));
  };

  const handleDelete = async (domain: string) => {
    if (!window.confirm(`Remove ${domain} from monitoring?`)) return;
    try {
      const response = await fetch(`${API_BASE_URL}/api/domains/${domain}`, { method: "DELETE" });
      if (!response.ok) throw new Error("Unable to remove domain.");
      toast.success(`${domain} removed`);
      setSelected(null);
      await loadData();
    } catch (err) { toast.error(err instanceof Error ? err.message : "Unable to remove domain."); }
  };

  const selectView = (next: View) => { setView(next); setMobileNavOpen(false); };
  const title = view === "overview" ? "Overview" : view[0].toUpperCase() + view.slice(1);

  return <div className="console-shell">
    <Toaster position="bottom-right" toastOptions={{ className: "console-toast" }} />
    <AddDomainModal isOpen={addOpen} onClose={() => setAddOpen(false)} onDomainsAdded={handleDomainsAdded} />
    <CertificateDetailModal cert={selected} onClose={() => setSelected(null)} />
    <aside className={`console-sidebar ${mobileNavOpen ? "open" : ""}`}>
      <div className="brand"><span className="brand-mark"><span /></span><span>SSL Certs Monitor</span></div>
      <button className="workspace-switcher" aria-label="Current workspace"><span className="workspace-avatar">NS</span><span><strong>Nimbus SAS</strong><small>Production · {counts.total} domains</small></span><span className="chevron">⌄</span></button>
      <nav className="main-nav" aria-label="Main navigation">{navItems.map((item) => <button key={item.id} className={view === item.id ? "active" : ""} onClick={() => selectView(item.id)}><span className="nav-mark">{item.mark}</span><span>{item.label}</span>{item.id === "alerts" && counts.critical > 0 && <b>{counts.critical}</b>}<kbd>G {item.shortcut}</kbd></button>)}</nav>
      <div className="sidebar-bottom"><button className="setup-link" onClick={() => selectView("onboarding")}><span><strong>Setup guide</strong><small>Connect your first domains</small></span><span className="setup-arrow">→</span></button><div className="scanner-status"><span className="pulse-dot" /><span><strong>Scanner running</strong><small>Next run in 42 min</small></span></div><button className="theme-toggle" onClick={() => setTheme(theme === "dark" ? "light" : "dark")} aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} theme`}><span>{theme === "dark" ? "☼" : "☾"}</span>{theme === "dark" ? "Light theme" : "Dark theme"}</button><div className="user-chip"><span className="user-avatar">AD</span><span><strong>Awa Diallo</strong><small>Owner</small></span></div></div>
    </aside>
    <div className="console-content">
      <header className="topbar"><button className="mobile-menu" onClick={() => setMobileNavOpen((open) => !open)} aria-label="Open navigation">☰</button><div className="breadcrumb"><span>Nimbus SAS</span><span>/</span><strong>{title}</strong></div><label className="global-search"><span>⌕</span><input id="global-search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search domains, issuers, teams…" aria-label="Search domains" /><kbd>/</kbd></label><button className="primary-button" onClick={() => setAddOpen(true)}>＋ Add domains <kbd>N</kbd></button></header>
      <main className="console-main">
        {view === "overview" && <Overview counts={counts} certificates={certificates} isLoading={isLoading} onView={selectView} onSelect={setSelected} />}
        {view === "domains" && <DomainsView rows={rows} filter={filter} setFilter={setFilter} query={query} setQuery={setQuery} sortAscending={sortAscending} setSortAscending={setSortAscending} isLoading={isLoading} onSelect={setSelected} onDelete={handleDelete} onAdd={() => setAddOpen(true)} error={error} />}
        {view === "alerts" && <EmptyState title="Alerts are ready for your rules" text="Alert rules and delivery history will appear here once configured. The current API exposes notification settings from the Settings page." action={<Link className="secondary-button" href="/settings">Open settings</Link>} />}
        {view === "history" && <EmptyState title="No activity history yet" text="Certificate snapshots and audit events will appear here as the scanner completes its first runs." action={<button className="secondary-button" onClick={() => selectView("domains")}>View domains</button>} />}
        {view === "onboarding" && <Onboarding counts={counts} onAdd={() => setAddOpen(true)} />}
        {error && <div className="inline-error" role="alert">{error} <button onClick={() => void loadData()}>Retry</button></div>}
      </main>
    </div>
  </div>;
}

function Overview({ counts, certificates, isLoading, onView, onSelect }: { counts: { total: number; healthy: number; watch: number; critical: number }; certificates: Certificate[]; isLoading: boolean; onView: (view: View) => void; onSelect: (cert: Certificate) => void }) {
  const runway = certificates.filter((cert) => typeof cert.days_left === "number" && cert.days_left >= 0).sort((a, b) => (a.days_left ?? 0) - (b.days_left ?? 0)).slice(0, 6);
  return <div className="screen-stack"><div className="screen-heading"><div><h1>Overview</h1><p>Last full scan · {isLoading ? "Checking…" : "just now"} · {counts.total} domains monitored</p></div><button className="secondary-button" onClick={() => onView("domains")}>Review {counts.watch + counts.critical} domains needing action</button></div><div className="kpi-grid">{[["Monitored domains", counts.total, "total", "info"], ["Healthy certificates", counts.healthy, `${counts.total ? Math.round(counts.healthy / counts.total * 100) : 0}% of total`, "ok"], ["Needs attention", counts.watch, "expiring soon", "watch"], ["Critical", counts.critical, "action required", "critical"]].map(([label, value, sub, tone]) => <div className="kpi-card" key={String(label)}><div className="kpi-label"><span className={`metric-dot ${tone}`} />{label}</div><strong>{value}</strong><small>{sub}</small></div>)}</div><section className="panel runway-panel"><div className="panel-heading"><div><h2>Expiry runway <span>· next 90 days</span></h2><p>Certificates closest to expiration</p></div><button className="text-button" onClick={() => onView("domains")}>View all →</button></div><div className="runway-chart"><div className="runway-zone critical-zone" /><div className="runway-zone watch-zone" />{runway.length === 0 ? <span className="chart-empty">No expiry data available yet</span> : runway.map((cert, index) => <button key={cert.domain} className="runway-marker" style={{ left: `${Math.min(94, Math.max(3, (cert.days_left ?? 0) / 90 * 100))}%`, height: `${55 + index * 13}px` }} onClick={() => onSelect(cert)} title={cert.domain}><span className="marker-label">{cert.domain} <b>{cert.days_left}d</b></span><i /></button>)}<div className="chart-axis"><span>Today</span><span>30 days</span><span>60 days</span><span>90 days</span></div></div></section><div className="overview-columns"><section className="panel action-panel"><div className="panel-heading"><h2>Needs action</h2><button className="text-button" onClick={() => onView("domains")}>View all →</button></div>{certificates.filter((cert) => cert.status !== "OK").slice(0, 4).map((cert) => <button className="action-row" key={cert.domain} onClick={() => onSelect(cert)}><span className={`metric-dot ${statusMeta[cert.status].tone}`} /><span><strong>{cert.domain}</strong><small>{cert.error_message ?? (cert.days_left !== undefined ? `${cert.days_left} days until expiry` : "Awaiting first check")}</small></span><StatusPill status={cert.status} /></button>)}{certificates.filter((cert) => cert.status !== "OK").length === 0 && <p className="panel-empty">Everything looks good. No action required.</p>}</section><section className="panel posture-panel"><div className="panel-heading"><h2>TLS posture</h2><span className="muted-label">Grade per domain</span></div><div className="posture-bar"><span style={{ flex: counts.healthy || 1 }} /><span style={{ flex: counts.watch || 0.01 }} /><span style={{ flex: counts.critical || 0.01 }} /></div><div className="posture-legend"><span><i className="metric-dot ok" />Healthy <b>{counts.healthy}</b></span><span><i className="metric-dot watch" />Watch <b>{counts.watch}</b></span><span><i className="metric-dot critical" />Critical <b>{counts.critical}</b></span></div><p className="risk-label">Most common risks</p><div className="risk-tags"><span>Expiring soon <b>×{counts.watch}</b></span><span>Certificate error <b>×{counts.critical}</b></span></div></section></div></div>;
}

function DomainsView({ rows, filter, setFilter, query, setQuery, sortAscending, setSortAscending, isLoading, onSelect, onDelete, onAdd, error }: { rows: Certificate[]; filter: Filter; setFilter: (value: Filter) => void; query: string; setQuery: (value: string) => void; sortAscending: boolean; setSortAscending: (value: boolean) => void; isLoading: boolean; onSelect: (cert: Certificate) => void; onDelete: (domain: string) => void; onAdd: () => void; error: string | null }) {
  return <div className="screen-stack"><div className="screen-heading"><div><h1>Domains</h1><p>Every domain is checked hourly on port 443.</p></div><button className="primary-button" onClick={onAdd}>＋ Add domains <kbd>N</kbd></button></div><div className="domain-toolbar"><div className="filter-tabs" role="tablist">{([["all", "All"], ["OK", "Healthy"], ["Expire bientôt", "Watch"], ["Expiré", "Critical"], ["Erreur", "Errors"]] as [Filter, string][]).map(([value, label]) => <button key={value} className={filter === value ? "selected" : ""} onClick={() => setFilter(value)} role="tab" aria-selected={filter === value}>{label}</button>)}</div><label className="table-search"><span>⌕</span><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Filter domains…" aria-label="Filter domains" /></label></div><section className="panel domain-table-wrap"><div className="domain-table" role="table"><div className="table-row table-head" role="row"><span>Domain</span><span>Status</span><button onClick={() => setSortAscending(!sortAscending)}>Expires {sortAscending ? "↑" : "↓"}</button><span>Issuer</span><span>Last check</span><span aria-label="Actions" /></div>{isLoading ? [...Array(5)].map((_, index) => <div className="table-row skeleton-row" key={index}><i /><i /><i /><i /><i /></div>) : rows.map((cert) => <div className="table-row table-body-row" role="row" key={cert.domain} onClick={() => onSelect(cert)} tabIndex={0} onKeyDown={(event) => event.key === "Enter" && onSelect(cert)}><span className="domain-name">{cert.domain}</span><StatusPill status={cert.status} /><span className="expiry-cell"><b>{cert.days_left !== undefined ? `${cert.days_left}d` : "—"}</b><small>{formatDate(cert.expiry_date)}</small></span><span className="issuer-cell">{cert.issuer?.split(",")[0] ?? "—"}</span><span className="last-check">{formatDate(cert.checked_at)}</span><button className="delete-button" onClick={(event) => { event.stopPropagation(); onDelete(cert.domain); }} aria-label={`Remove ${cert.domain}`}>×</button></div>)}{!isLoading && rows.length === 0 && <EmptyState title={error ? "Unable to load domains" : "No matching domains"} text={error ?? "Add a domain or reset your filters to see monitoring results."} action={!error ? <button className="secondary-button" onClick={() => { setQuery(""); setFilter("all"); }}>Reset filters</button> : undefined} />}</div><div className="table-footer"><span>{rows.length} domain{rows.length === 1 ? "" : "s"}</span><span>Click a row to inspect certificate details</span></div></section></div>;
}

function Onboarding({ counts, onAdd }: { counts: { total: number }; onAdd: () => void }) {
  return <div className="onboarding screen-stack"><div className="screen-heading"><div><h1>Setup guide</h1><p>Get your monitoring workspace ready in three steps.</p></div></div><section className="panel onboarding-card"><span className="eyebrow">{counts.total ? "Workspace active" : "Welcome to SSL Certs Monitor"}</span><h2>{counts.total ? "Your scanner is watching your domains." : "Start with your first domain."}</h2><p>Add a domain and the scanner will fetch its certificate, issuer, expiry date and current health status.</p><button className="primary-button" onClick={onAdd}>＋ Add domains</button><div className="setup-steps"><div className="complete"><span>1</span><div><strong>Connect your workspace</strong><small>Nimbus SAS · Production</small></div></div><div className={counts.total ? "complete" : ""}><span>2</span><div><strong>Add monitored domains</strong><small>{counts.total ? `${counts.total} domain${counts.total === 1 ? "" : "s"} connected` : "Not started"}</small></div></div><div><span>3</span><div><strong>Configure notifications</strong><small>Available in Settings</small></div></div></div></section></div>;
}
