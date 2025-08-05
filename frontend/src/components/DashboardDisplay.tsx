// Fichier: frontend/src/components/DashboardDisplay.tsx
"use client";

import React, { useState, useEffect, useCallback, useMemo } from "react";
import { motion, AnimatePresence, Variants } from "framer-motion";
import { Toaster, toast } from 'react-hot-toast';

import ExpirationGauge from "./ExpirationGauge";
import AddDomainModal from "./AddDomainModal";
import CertificateDetailModal from "./CertificateDetailModal";

// --- Types et Constantes ---
export interface Certificate {
  domain: string;
  status: 'OK' | 'Expire bientôt' | 'Expiré' | 'Erreur' | 'Vérification...';
  days_left?: number;
  expiry_date?: string;
  error_message?: string;
}
type SortKey = 'days_left' | 'domain';
type SortDirection = 'asc' | 'desc';

const API_URL = "http://localhost:8000";

// --- Sous-Composant : Badge de Statut ---
const StatusBadge = ({ status }: { status: Certificate['status'] }) => {
    const colorClasses = {
        'OK': 'bg-green-500/20 text-green-400 border-green-500/30',
        'Expire bientôt': 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30 animate-pulse',
        'Expiré': 'bg-red-500/20 text-red-400 border-red-500/30',
        'Erreur': 'bg-red-500/20 text-red-400 border-red-500/30',
        'Vérification...': 'bg-blue-500/20 text-blue-400 border-blue-500/30 animate-spin',
      };
      return <span className={`px-3 py-1 text-xs font-medium rounded-full border ${colorClasses[status]}`}>{status}</span>;
};

// --- Variantes d'animation ---
const containerVariants: Variants = { hidden: { opacity: 0 }, visible: { opacity: 1, transition: { staggerChildren: 0.08 } } };
const itemVariants: Variants = { hidden: { y: 20, opacity: 0 }, visible: { y: 0, opacity: 1, transition: { type: "spring", stiffness: 100 } } };

// --- Sous-Composant : Carte Certificat ---
const CertificateCard = ({ cert, onCardClick, onDeleteClick }: { cert: Certificate, onCardClick: () => void, onDeleteClick: (domain: string) => void }) => (
    <motion.div variants={itemVariants} layout onClick={onCardClick} className="cursor-pointer bg-slate-900/50 backdrop-blur-md border border-slate-800 rounded-xl p-5 flex flex-col justify-between transition-all hover:border-blue-500/50 hover:-translate-y-1">
        <div>
            <div className="flex justify-between items-start mb-4">
                <h2 className="font-bold text-lg text-slate-200 break-all pr-2">{cert.domain}</h2>
                <button onClick={(e) => { e.stopPropagation(); onDeleteClick(cert.domain); }} className="text-slate-500 hover:text-red-500 transition-colors z-10 flex-shrink-0" aria-label={`Supprimer ${cert.domain}`}>
                    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path><line x1="10" y1="11" x2="10" y2="17"></line><line x1="14" y1="11" x2="14" y2="17"></line></svg>
                </button>
            </div>
        </div>
        {(cert.status !== 'Erreur' && cert.status !== 'Vérification...') ? (
            <div className="flex items-end justify-between mt-4">
                <div><p className="text-sm text-slate-400">Expiration</p><p className="text-xs text-slate-500">{cert.expiry_date ? new Date(cert.expiry_date).toLocaleDateString('fr-FR') : 'Inconnue'}</p></div>
                {cert.days_left !== undefined && <ExpirationGauge daysLeft={cert.days_left} />}
            </div>
        ) : (<div className="bg-slate-800/50 p-3 rounded-lg text-xs text-slate-300 flex items-center justify-center h-full mt-4 min-h-[52px]">{cert.status === 'Vérification...' ? 'Vérification en cours...' : cert.error_message}</div>)}
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
    const [error, setError] = useState<string | null>(null);
    const [inputValue, setInputValue] = useState("");
    const [searchTerm, setSearchTerm] = useState("");
    const [isAddModalOpen, setIsAddModalOpen] = useState(false);
    const [selectedCert, setSelectedCert] = useState<Certificate | null>(null);
    const [sortKey, setSortKey] = useState<SortKey>('days_left');
    const [sortDirection, setSortDirection] = useState<SortDirection>('asc');

    const fetchInitialData = useCallback(async () => {
        try {
            const res = await fetch(`/ssl_status.json?t=${new Date().getTime()}`);
            if (res.status === 404) {
                setCertificates([]);
                return;
            }
            if (!res.ok) throw new Error("Le fichier de statut est inaccessible.");
            const data: Certificate[] = await res.json();
            setCertificates(data);
            setError(null);
        } catch (err) {
            if (err instanceof Error) { setError(err.message); }
            else { setError("Une erreur de type inconnu est survenue."); }
            setCertificates([]);
        } finally {
            setIsLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchInitialData();
        const interval = setInterval(fetchInitialData, 5 * 60 * 1000);
        return () => clearInterval(interval);
    }, [fetchInitialData]);

    const handleDomainsAdded = (newDomains: string[]) => {
        const placeholderCerts: Certificate[] = newDomains.map(domain => ({ domain, status: 'Vérification...' }));
        setCertificates(prevCerts => [...prevCerts, ...placeholderCerts]);

        newDomains.forEach(async (domain) => {
            try {
                const res = await fetch(`${API_URL}/api/check/${domain}`);
                if (!res.ok) throw new Error("La vérification a échoué");
                const checkedCert: Certificate = await res.json();
                setCertificates(prevCerts => prevCerts.map(cert => cert.domain === domain ? checkedCert : cert));
            } catch (e) {
                setCertificates(prevCerts => prevCerts.map(cert => cert.domain === domain ? { ...cert, status: 'Erreur', error_message: 'Échec de la vérification' } : cert));
            }
        });
    };

    const handleDelete = async (domain: string) => {
        if (!window.confirm(`Êtes-vous sûr de vouloir supprimer ${domain} ?`)) return;
        const originalCerts = [...certificates];
        setCertificates(certs => certs.filter(c => c.domain !== domain));
        const toastId = toast.loading(`Suppression de ${domain}...`);
        try {
            const response = await fetch(`${API_URL}/api/domains/${domain}`, { method: 'DELETE' });
            toast.dismiss(toastId);
            if (!response.ok) {
                setCertificates(originalCerts);
                const errorData = await response.json();
                throw new Error(errorData.detail || "Erreur lors de la suppression.");
            }
            toast.success(`Domaine '${domain}' supprimé !`);
        } catch (err) {
            toast.dismiss(toastId);
            if (err instanceof Error) toast.error(err.message);
            else toast.error("Erreur inconnue lors de la suppression.");
            setCertificates(originalCerts);
        }
    };

    const handleSearch = () => setSearchTerm(inputValue);

    const processedCertificates = useMemo(() => {
        return certificates
            .filter(cert => cert.domain.toLowerCase().includes(searchTerm.toLowerCase()))
            .sort((a, b) => {
                const aDays = a.days_left ?? (sortDirection === 'asc' ? Infinity : -Infinity);
                const bDays = b.days_left ?? (sortDirection === 'asc' ? Infinity : -Infinity);
                if (sortKey === 'days_left') {
                    return sortDirection === 'asc' ? aDays - bDays : bDays - aDays;
                } else {
                    return sortDirection === 'asc' ? a.domain.localeCompare(b.domain) : b.domain.localeCompare(a.domain);
                }
            });
    }, [certificates, searchTerm, sortKey, sortDirection]);

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

                <div className="mb-8 flex flex-col md:flex-row justify-between items-center gap-4">
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
                    <button onClick={() => setIsAddModalOpen(true)} className="px-5 py-3 bg-green-600 hover:bg-green-700 font-semibold rounded-lg transition-colors active:scale-95 whitespace-nowrap">Ajouter Domaines</button>
                </div>

                {error && <div className="text-center py-10 bg-red-900/50 rounded-lg text-red-300">{error}</div>}

                {!error && ( isLoading ? (
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                            {[...Array(6)].map((_, i) => <SkeletonCard key={i} />)}
                        </div>
                    ) : (
                        <motion.div variants={containerVariants} initial="hidden" animate="visible" className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                            <AnimatePresence>
                                {processedCertificates.length > 0 ? (
                                    processedCertificates.map((cert) => ( 
                                        <CertificateCard key={cert.domain} cert={cert} onCardClick={() => setSelectedCert(cert)} onDeleteClick={handleDelete} /> 
                                    ))
                                ) : ( <div className="col-span-full text-center py-10"><p className="text-slate-400">Aucun domaine à surveiller. Ajoutez-en un pour commencer !</p></div> )}
                            </AnimatePresence>
                        </motion.div>
                    )
                )}
            </div>
        </div>
    );
}