// Fichier: frontend/src/components/DashboardDisplay.tsx
"use client";

import React, { useState, useEffect, useCallback, useMemo, useRef } from "react";
import Link from "next/link";
import { motion, Variants } from "framer-motion";
import { Toaster, toast } from 'react-hot-toast';

import ExpirationGauge from "./ExpirationGauge";
import AddDomainModal from "./AddDomainModal";
import CertificateDetailModal from "./CertificateDetailModal";
import { API_BASE_URL } from "@/lib/api";

// --- Types et Constantes ---
export interface Certificate {
  domain: string;
  status: 'OK' | 'Expire bientôt' | 'Expiré' | 'Erreur' | 'En attente' | 'Vérification...';
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
type SortKey = 'days_left' | 'domain';
type SortDirection = 'asc' | 'desc';
type BackendStatus = 'unknown' | 'healthy' | 'unavailable';
type StatusFilter = Certificate['status'] | 'all';

// --- Sous-Composant : Badge de Statut ---
const StatusBadge = ({ status }: { status: Certificate['status'] }) => {
    const colorClasses = {
        'OK': 'bg-green-500/20 text-green-400 border-green-500/30',
        'Expire bientôt': 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30 animate-pulse',
        'Expiré': 'bg-red-500/20 text-red-400 border-red-500/30',
        'Erreur': 'bg-red-500/20 text-red-400 border-red-500/30',
        'En attente': 'bg-gray-500/20 text-gray-400 border-gray-500/30',
        'Vérification...': 'bg-blue-500/20 text-blue-400 border-blue-500/30 animate-spin',
      };
      return <span className={`px-3 py-1 text-xs font-medium rounded-full border ${colorClasses[status]}`}>{status}</span>;
};

// --- Variantes d'animation ---
const itemVariants: Variants = { hidden: { y: 20, opacity: 0 }, visible: { y: 0, opacity: 1, transition: { type: "spring", stiffness: 100 } } };

// --- Sous-Composant : Carte Certificat ---
const CertificateCard = ({ cert, onCardClick, onDeleteClick }: { cert: Certificate, onCardClick: () => void, onDeleteClick: (domain: string) => void }) => (
    <motion.div variants={itemVariants} layout onClick={onCardClick} className="cursor-pointer bg-slate-900/50 backdrop-blur-md border border-slate-800 rounded-xl p-5 flex flex-col justify-between transition-all hover:border-blue-500/50 hover:-translate-y-1">
        <div>
            <div className="flex justify-between items-start mb-4">
                <h2 className="font-bold text-lg text-slate-200 break-all pr-2">{cert.domain}</h2>
                <div className="flex items-center gap-2">
                    <StatusBadge status={cert.status} />
                    <button onClick={(e) => { e.stopPropagation(); onDeleteClick(cert.domain); }} className="text-slate-500 hover:text-red-500 transition-colors z-10 flex-shrink-0" aria-label={`Supprimer ${cert.domain}`}>
                        <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
                    </button>
                </div>
            </div>
        </div>
        {(cert.status !== 'Erreur' && cert.status !== 'En attente' && cert.status !== 'Vérification...') ? (
            <div className="flex items-end justify-between mt-4">
                <div><p className="text-sm text-slate-400">Expiration</p><p className="text-xs text-slate-500">{cert.expiry_date ? new Date(cert.expiry_date).toLocaleDateString('fr-FR') : 'Inconnue'}</p></div>
                {cert.days_left !== undefined && <ExpirationGauge daysLeft={cert.days_left} />}
            </div>
        ) : (<div className="bg-slate-800/50 p-3 rounded-lg text-xs text-slate-300 flex items-center justify-center h-full mt-4 min-h-[52px]">{cert.status === 'En attente' ? 'En attente de la vérification...' : cert.status === 'Vérification...' ? 'Vérification en cours...' : cert.error_message}</div>)}
    </motion.div>
);

// --- Sous-Composant : Carte "Fantôme" ---
const SkeletonCard = () => (
    <div className="bg-slate-900/50 backdrop-blur-md border border-slate-800 rounded-xl p-5 animate-pulse">
        <div className="flex justify-between items-start mb-4"><div className="h-6 w-3/5 rounded bg-slate-700"></div><div className="h-6 w-1/4 rounded-full bg-slate-700"></div></div>
        <div className="flex items-end justify-between mt-8">
            <div className="w-1/2"><div className="h-4 w-full rounded bg-slate-700 mb-2"></div><div className="h-3 w-2/3 rounded bg-slate-700"></div></div>
            <div className="w-12 h-12 rounded-full bg-slate-700"></div>
        </div>
    </div>
);


// --- Composant principal du Dashboard ---
export default function DashboardDisplay() {
    const [certificates, setCertificates] = useState<Certificate[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [isRefreshing, setIsRefreshing] = useState(false);
    const [syncError, setSyncError] = useState<string | null>(null);
    const [lastSyncedAt, setLastSyncedAt] = useState<Date | null>(null);
    const [backendStatus, setBackendStatus] = useState<BackendStatus>('unknown');
    const refreshInFlight = useRef(false);
    const [inputValue, setInputValue] = useState("");
    const [searchTerm, setSearchTerm] = useState("");
    const [isAddModalOpen, setIsAddModalOpen] = useState(false);
    const [selectedCert, setSelectedCert] = useState<Certificate | null>(null);
    const [sortKey, setSortKey] = useState<SortKey>('days_left');
    const [sortDirection, setSortDirection] = useState<SortDirection>('asc');
    const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');
    const [page, setPage] = useState(1);
    const [viewMode, setViewMode] = useState<'table' | 'cards'>('table');
    const pageSize = 25;

    const fetchInitialData = useCallback(async () => {
        if (refreshInFlight.current) return;
        refreshInFlight.current = true;
        setIsRefreshing(true);
        try {
            const [statusRes, domainsRes] = await Promise.all([
                fetch(`${API_BASE_URL}/api/status?t=${Date.now()}`),
                fetch(`${API_BASE_URL}/api/domains`),
            ]);
            if (!statusRes.ok) throw new Error(`API status indisponible (${statusRes.status}).`);
            if (!domainsRes.ok) throw new Error(`API domaines indisponible (${domainsRes.status}).`);
            const statuses = await statusRes.json() as Certificate[];
            const domainsPayload = await domainsRes.json() as { domains?: string[] };
            if (!Array.isArray(statuses) || !Array.isArray(domainsPayload.domains)) {
                throw new Error("Réponse API invalide.");
            }
            const domains = domainsPayload.domains;
            const statusMap = new Map(statuses.map(s => [s.domain, s]));

            const mergedCertificates = domains.map(domain => {
                const status = statusMap.get(domain);
                if (status) return status;
                return { domain, status: 'En attente' } as Certificate;
            });
            setCertificates(mergedCertificates);
            setSyncError(null);
            setBackendStatus('healthy');
            setLastSyncedAt(new Date());
        } catch (err) {
            setSyncError(err instanceof Error ? err.message : "Erreur de synchronisation inconnue.");
            setBackendStatus('unavailable');
        } finally {
            refreshInFlight.current = false;
            setIsLoading(false);
            setIsRefreshing(false);
        }
    }, []);

    useEffect(() => {
        const initialLoad = window.setTimeout(() => void fetchInitialData(), 0);
        const interval = setInterval(fetchInitialData, 5 * 60 * 1000);
        return () => {
            clearTimeout(initialLoad);
            clearInterval(interval);
        };
    }, [fetchInitialData]);

    const handleDomainsAdded = (newDomains: string[]) => {
        const placeholderCerts: Certificate[] = newDomains.map(domain => ({
            domain,
            status: 'Vérification...',
        }));
        setCertificates(prevCerts => [...prevCerts, ...placeholderCerts]);

        newDomains.forEach(async (domain) => {
            try {
                const res = await fetch(`${API_BASE_URL}/api/check/${domain}`);
                if (!res.ok) throw new Error("La vérification a échoué.");
                const checkedCert: Certificate = await res.json();
                setCertificates(prevCerts => 
                    prevCerts.map(cert => cert.domain === domain ? checkedCert : cert)
                );
            } catch {
                setCertificates(prevCerts => 
                    prevCerts.map(cert => cert.domain === domain ? { ...cert, status: 'Erreur', error_message: 'Échec de la vérification' } : cert)
                );
            }
        });
    };
    
    const handleDelete = async (domain: string) => {
        if (!window.confirm(`Êtes-vous sûr de vouloir supprimer ${domain} ?`)) return;
        
        const toastId = toast.loading(`Suppression de ${domain}...`);
        try {
            const response = await fetch(`${API_BASE_URL}/api/domains/${domain}`, { method: 'DELETE' });
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || "Erreur lors de la suppression.");
            }
            toast.success(`Domaine '${domain}' supprimé !`, {id: toastId});
            await fetchInitialData();
        } catch (err) {
            toast.dismiss(toastId);
            if (err instanceof Error) toast.error(err.message);
            else toast.error("Erreur inconnue lors de la suppression.");
        }
    };

    const handleSearch = () => {
        setSearchTerm(inputValue);
        setPage(1);
    };

    const summary = useMemo(() => ({
        total: certificates.length,
        healthy: certificates.filter(cert => cert.status === 'OK').length,
        expiring: certificates.filter(cert => cert.status === 'Expire bientôt').length,
        expired: certificates.filter(cert => cert.status === 'Expiré').length,
        errors: certificates.filter(cert => cert.status === 'Erreur').length,
    }), [certificates]);

    const filteredCertificates = useMemo(() => {
        return certificates
            .filter(cert => cert.domain.toLowerCase().includes(searchTerm.toLowerCase()))
            .filter(cert => statusFilter === 'all' || cert.status === statusFilter)
            .sort((a, b) => {
                const aDays = a.days_left ?? (sortDirection === 'asc' ? Infinity : -Infinity);
                const bDays = b.days_left ?? (sortDirection === 'asc' ? Infinity : -Infinity);
                if (sortKey === 'days_left') {
                    return sortDirection === 'asc' ? aDays - bDays : bDays - aDays;
                } else {
                    return sortDirection === 'asc' ? a.domain.localeCompare(b.domain) : b.domain.localeCompare(a.domain);
                }
            });
    }, [certificates, searchTerm, statusFilter, sortKey, sortDirection]);

    const totalPages = Math.max(1, Math.ceil(filteredCertificates.length / pageSize));
    const currentPage = Math.min(page, totalPages);
    const visibleCertificates = filteredCertificates.slice((currentPage - 1) * pageSize, currentPage * pageSize);

    return (
        <div className="min-h-screen p-4 md:p-8 bg-slate-950 text-white">
            <Toaster position="bottom-right" toastOptions={{ className: 'bg-slate-800 text-white border border-slate-700' }}/>
            <AddDomainModal isOpen={isAddModalOpen} onClose={() => setIsAddModalOpen(false)} onDomainsAdded={handleDomainsAdded} />
            <CertificateDetailModal cert={selectedCert} onClose={() => setSelectedCert(null)} />
            <div className="max-w-7xl mx-auto">
                <header className="text-center mb-8">
                    <h1 className="text-5xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-cyan-300">SSL-Cert-Monitor</h1>
                    <p className="text-slate-400 mt-2">Votre tour de contrôle pour les certificats SSL/TLS</p>
                </header>

                <div className="mb-6 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-slate-800 bg-slate-900/60 px-4 py-3 text-sm">
                    <div className="flex items-center gap-2 text-slate-300">
                        <span className={`h-2.5 w-2.5 rounded-full ${backendStatus === 'healthy' ? 'bg-emerald-400' : backendStatus === 'unavailable' ? 'bg-red-400' : 'bg-slate-500'}`} />
                        <span>Backend : {backendStatus === 'healthy' ? 'opérationnel' : backendStatus === 'unavailable' ? 'indisponible' : 'inconnu'}</span>
                        {lastSyncedAt && <span className="text-slate-500">· Dernière synchronisation : {lastSyncedAt.toLocaleString('fr-FR')}</span>}
                    </div>
                    <button onClick={() => void fetchInitialData()} disabled={isRefreshing} className="rounded-md bg-slate-700 px-3 py-2 text-slate-200 hover:bg-slate-600 disabled:cursor-not-allowed disabled:opacity-50">
                        {isRefreshing ? 'Synchronisation...' : 'Actualiser'}
                    </button>
                </div>

                <nav aria-label="Navigation du dashboard" className="mb-6 flex flex-wrap gap-2 text-sm">
                    <a href="#domains" className="rounded-md bg-blue-600 px-3 py-2 text-white">Domaines</a>
                    <a href="#alerts" className="rounded-md bg-slate-800 px-3 py-2 text-slate-300 hover:bg-slate-700">Alertes</a>
                    <a href="#history" className="rounded-md bg-slate-800 px-3 py-2 text-slate-300 hover:bg-slate-700">Historique</a>
                    <Link href="/settings" className="rounded-md bg-slate-800 px-3 py-2 text-slate-300 hover:bg-slate-700">Paramètres</Link>
                </nav>

                <section id="alerts" aria-label="Synthèse des alertes" className="mb-8 grid grid-cols-2 gap-3 md:grid-cols-5">
                    {[['Total', summary.total, 'text-slate-200'], ['Sains', summary.healthy, 'text-emerald-400'], ['Bientôt expirés', summary.expiring, 'text-yellow-400'], ['Expirés', summary.expired, 'text-red-400'], ['Erreurs', summary.errors, 'text-red-300']].map(([label, value, color]) => (
                        <div key={label as string} className="rounded-xl border border-slate-800 bg-slate-900/70 p-4">
                            <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
                            <p className={`mt-2 text-3xl font-bold ${color}`}>{value}</p>
                        </div>
                    ))}
                </section>

                <div id="domains" className="mb-4 flex flex-col md:flex-row justify-between items-center gap-4">
                     <div className="flex items-center gap-2 w-full md:w-auto flex-grow">
                        <input type="text" placeholder="Rechercher un domaine..." value={inputValue} onChange={(e) => setInputValue(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter') handleSearch(); }} className="w-full max-w-lg pl-4 pr-10 py-3 bg-slate-900/50 backdrop-blur-md border border-slate-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/50" />
                        <button onClick={handleSearch} className="px-5 py-3 bg-blue-600 hover:bg-blue-700 font-semibold rounded-lg transition-colors active:scale-95">Rechercher</button>
                    </div>
                    <div className="flex items-center gap-2 text-sm flex-shrink-0">
                        <span className="text-slate-400">Trier par:</span>
                        <button onClick={() => setSortKey('days_left')} className={`px-3 py-1 rounded-md transition-colors ${sortKey === 'days_left' ? 'bg-blue-600 text-white' : 'bg-slate-700/50 text-slate-300 hover:bg-slate-600'}`}>Expiration</button>
                        <button onClick={() => setSortKey('domain')} className={`px-3 py-1 rounded-md transition-colors ${sortKey === 'domain' ? 'bg-blue-600 text-white' : 'bg-slate-700/50 text-slate-300 hover:bg-slate-600'}`}>Nom</button>
                        <button onClick={() => setSortDirection(prev => prev === 'asc' ? 'desc' : 'asc')} className="p-2 rounded-md bg-slate-700/50 text-slate-300 hover:bg-slate-600 transition-transform active:scale-90">
                            {sortDirection === 'asc' ? '↑' : '↓'}
                        </button>
                    </div>
                    <label className="flex items-center gap-2 text-sm text-slate-300">Statut
                        <select value={statusFilter} onChange={event => { setStatusFilter(event.target.value as StatusFilter); setPage(1); }} className="rounded-md bg-slate-800 px-3 py-2" aria-label="Filtrer par statut">
                            <option value="all">Tous</option><option value="OK">Sains</option><option value="Expire bientôt">Bientôt expirés</option><option value="Expiré">Expirés</option><option value="Erreur">Erreurs</option>
                        </select>
                    </label>
                    <div className="flex gap-1 rounded-md bg-slate-800 p-1" aria-label="Mode d'affichage">
                        <button onClick={() => setViewMode('table')} className={`rounded px-2 py-1 text-xs ${viewMode === 'table' ? 'bg-blue-600' : 'text-slate-400'}`}>Table</button>
                        <button onClick={() => setViewMode('cards')} className={`rounded px-2 py-1 text-xs ${viewMode === 'cards' ? 'bg-blue-600' : 'text-slate-400'}`}>Cartes</button>
                    </div>
                    <button onClick={() => setIsAddModalOpen(true)} className="px-5 py-3 bg-green-600 hover:bg-green-700 font-semibold rounded-lg transition-colors active:scale-95 whitespace-nowrap">Ajouter Domaines</button>
                    <Link href="/settings" className="px-5 py-3 bg-slate-700 hover:bg-slate-600 font-semibold rounded-lg transition-colors whitespace-nowrap">Paramètres</Link>
                </div>

                {syncError && <div className="mb-6 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-red-800 bg-red-950/50 p-4 text-red-200"><span>Synchronisation impossible : {syncError} {certificates.length > 0 && 'Les dernières données sont conservées.'}</span><button onClick={() => void fetchInitialData()} className="rounded-md bg-red-900 px-3 py-2 hover:bg-red-800">Réessayer</button></div>}

                {isLoading && certificates.length === 0 ? (
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                            {[...Array(6)].map((_, i) => <SkeletonCard key={i} />)}
                        </div>
                    ) : viewMode === 'cards' ? (
                        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                            {visibleCertificates.map(cert => <CertificateCard key={cert.domain} cert={cert} onCardClick={() => setSelectedCert(cert)} onDeleteClick={handleDelete} />)}
                        </motion.div>
                    ) : (
                        <div className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-900/70">
                            <table className="w-full min-w-[720px] text-left text-sm" aria-label="Domaines surveillés">
                                <thead className="border-b border-slate-800 text-xs uppercase tracking-wide text-slate-500"><tr><th scope="col" className="px-4 py-3">Domaine</th><th scope="col" className="px-4 py-3">Statut</th><th scope="col" className="px-4 py-3">Jours</th><th scope="col" className="px-4 py-3">Prochaine échéance</th><th scope="col" className="px-4 py-3">Dernière vérification</th><th scope="col" className="px-4 py-3">Action</th></tr></thead>
                                <tbody className="divide-y divide-slate-800">
                                    {visibleCertificates.map(cert => <tr key={cert.domain} tabIndex={0} onClick={() => setSelectedCert(cert)} onKeyDown={event => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); setSelectedCert(cert); } }} className="cursor-pointer outline-none hover:bg-slate-800/60 focus:bg-slate-800/60">
                                        <th scope="row" className="px-4 py-4 font-medium text-slate-200">{cert.domain}</th><td className="px-4 py-4"><StatusBadge status={cert.status} /></td><td className="px-4 py-4 text-slate-300">{cert.days_left ?? '—'}</td><td className="px-4 py-4 text-slate-400">{cert.expiry_date ? new Date(cert.expiry_date).toLocaleDateString('fr-FR') : '—'}</td><td className="px-4 py-4 text-slate-400">{cert.checked_at ? new Date(cert.checked_at).toLocaleString('fr-FR') : '—'}</td><td className="px-4 py-4"><button onClick={event => { event.stopPropagation(); void handleDelete(cert.domain); }} className="rounded-md px-2 py-1 text-red-300 hover:bg-red-950/60 focus:outline-none focus:ring-2 focus:ring-red-400" aria-label={`Supprimer ${cert.domain}`}>Supprimer</button></td>
                                    </tr>)}
                                </tbody>
                            </table>
                            {visibleCertificates.length === 0 && <p className="p-8 text-center text-slate-400">Aucun domaine correspondant.</p>}
                        </div>
                    )}
                {!isLoading && <div id="history" className="mt-4 flex items-center justify-between text-sm text-slate-400"><span>{filteredCertificates.length} domaine(s) · page {currentPage} / {totalPages}</span><div className="flex gap-2"><button onClick={() => setPage(currentPage - 1)} disabled={currentPage === 1} className="rounded-md bg-slate-800 px-3 py-2 disabled:opacity-40">Précédent</button><button onClick={() => setPage(currentPage + 1)} disabled={currentPage === totalPages} className="rounded-md bg-slate-800 px-3 py-2 disabled:opacity-40">Suivant</button></div></div>}
            </div>
        </div>
    );
}
