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
  status: 'OK' | 'Expire bientôt' | 'Expiré' | 'Erreur' | 'Vérification...'; // Ajout du statut de chargement
  days_left?: number;
  expiry_date?: string;
  error_message?: string;
}
type SortKey = 'days_left' | 'domain';
type SortDirection = 'asc' | 'desc';

const API_URL = "http://localhost:8000";

// --- Sous-Composants (StatusBadge, Variants, CertificateCard, SkeletonCard) ---
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
const containerVariants: Variants = { hidden: { opacity: 0 }, visible: { opacity: 1, transition: { staggerChildren: 0.08 } } };
const itemVariants: Variants = { hidden: { y: 20, opacity: 0 }, visible: { y: 0, opacity: 1, transition: { type: "spring", stiffness: 100 } } };
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
        {cert.status !== 'Erreur' && cert.status !== 'Vérification...' ? (
            <div className="flex items-end justify-between mt-4">
                <div><p className="text-sm text-slate-400">Expiration</p><p className="text-xs text-slate-500">{cert.expiry_date ? new Date(cert.expiry_date).toLocaleDateString('fr-FR') : 'Inconnue'}</p></div>
                {cert.days_left !== undefined && <ExpirationGauge daysLeft={cert.days_left} />}
            </div>
        ) : (<div className="bg-red-900/20 p-3 rounded-lg text-xs text-red-300 flex items-center h-full mt-4">{cert.status === 'Vérification...' ? 'Vérification en cours...' : cert.error_message}</div>)}
    </motion.div>
);
const SkeletonCard = () => ( /* ... code du SkeletonCard inchangé ... */ );

// --- Composant principal du Dashboard ---
export default function DashboardDisplay() {
    const [certificates, setCertificates] = useState<Certificate[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    // ... autres états pour la recherche, les modales ...
    const [sortKey, setSortKey] = useState<SortKey>('days_left');
    const [sortDirection, setSortDirection] = useState<SortDirection>('asc');

    // Étape 1 : Chargement initial depuis le fichier JSON statique
    const fetchInitialData = useCallback(async () => {
        setIsLoading(true);
        try {
            // On fait un fetch vers notre propre serveur frontend pour lire le fichier dans /public
            const res = await fetch('/ssl_status.json');
            if (!res.ok) throw new Error("Le fichier de statut est introuvable.");
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

    // Charger les données au montage et mettre en place un rafraîchissement périodique
    useEffect(() => {
        fetchInitialData();
        const interval = setInterval(fetchInitialData, 5 * 60 * 1000); // Toutes les 5 minutes
        return () => clearInterval(interval);
    }, [fetchInitialData]);

    // Étape 2 : Logique d'ajout "optimiste" et de vérification instantanée
    const handleDomainsAdded = (newDomains: string[]) => {
        // A. Ajout instantané de placeholders dans l'UI
        const placeholderCerts: Certificate[] = newDomains.map(domain => ({
            domain,
            status: 'Vérification...',
        }));
        setCertificates(prevCerts => [...prevCerts, ...placeholderCerts]);

        // B. Lancement des vérifications individuelles en arrière-plan
        newDomains.forEach(async (domain) => {
            try {
                const res = await fetch(`${API_URL}/api/check/${domain}`);
                const checkedCert: Certificate = await res.json();
                
                // C. Remplacement du placeholder par les vraies données
                setCertificates(prevCerts => 
                    prevCerts.map(cert => cert.domain === domain ? checkedCert : cert)
                );
            } catch (e) {
                // En cas d'échec, on met à jour la carte avec une erreur
                setCertificates(prevCerts => 
                    prevCerts.map(cert => cert.domain === domain ? { ...cert, status: 'Erreur', error_message: 'Échec de la vérification' } : cert)
                );
            }
        });
    };

    const handleDelete = async (domain: string) => { /* ...fonction inchangée... */ };
    const [inputValue, setSearchTerm] = useState('');
    const handleSearch = () => setSearchTerm(inputValue);

    const processedCertificates = useMemo(() => {
        // ... Logique de filtrage et de tri inchangée ...
    }, [certificates, searchTerm, sortKey, sortDirection]);

    return (
        <div className="min-h-screen p-4 md:p-8 bg-slate-950 text-white">
            <Toaster position="bottom-right" toastOptions={{ className: 'bg-slate-800 text-white border border-slate-700' }}/>
            <AddDomainModal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} onDomainsAdded={handleDomainsAdded} />
            <CertificateDetailModal cert={selectedCert} onClose={() => setSelectedCert(null)} />
            
            <div className="max-w-7xl mx-auto">
                <header> {/* ...header inchangé... */} </header>
                <div className="mb-8 flex flex-col md:flex-row justify-between items-center gap-4">
                    {/* ... Barre de recherche inchangée ... */}
                    {/* --- Contrôles de Tri --- */}
                    <div className="flex items-center gap-2 text-sm flex-shrink-0">
                        <span className="text-slate-400">Trier par:</span>
                        <button onClick={() => setSortKey('days_left')} className={`px-3 py-1 rounded-md transition-colors ${sortKey === 'days_left' ? 'bg-blue-600 text-white' : 'bg-slate-700/50 text-slate-300 hover:bg-slate-600'}`}>Expiration</button>
                        <button onClick={() => setSortKey('domain')} className={`px-3 py-1 rounded-md transition-colors ${sortKey === 'domain' ? 'bg-blue-600 text-white' : 'bg-slate-700/50 text-slate-300 hover:bg-slate-600'}`}>Nom</button>
                        <button onClick={() => setSortDirection(prev => prev === 'asc' ? 'desc' : 'asc')} className="p-2 rounded-md bg-slate-700/50 text-slate-300 hover:bg-slate-600 transition-transform active:scale-90">
                            {sortDirection === 'asc' ? '↑' : '↓'}
                        </button>
                    </div>
                    <button onClick={() => setIsModalOpen(true)} className="px-5 py-3 bg-green-600 hover:bg-green-700 font-semibold rounded-lg ...">Ajouter Domaine</button>
                </div>

                {/* ...logique d'affichage des cartes utilisant "processedCertificates"... */}
            </div>
        </div>
    );
}

// NOTE : Pour la lisibilité, les parties répétitives ont été omises.
// Vous devez intégrer ces nouvelles logiques dans votre fichier complet.