// Fichier: frontend/src/components/DashboardDisplay.tsx
"use client";

import React, { useState, MouseEvent } from "react";
// MODIFIÉ : Importer le type "Variants" en plus de "motion"
import { motion, Variants } from "framer-motion"; 
import type { Certificate } from '../app/page';

// Le composant StatusBadge ne change pas...
const StatusBadge = ({ status }: { status: Certificate['status'] }) => {
  const colorClasses = {
    'OK': 'bg-green-500/20 text-green-400 border-green-500/30',
    'Expire bientôt': 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30 animate-pulse',
    'Expiré': 'bg-red-500/20 text-red-400 border-red-500/30',
    'Erreur': 'bg-red-500/20 text-red-400 border-red-500/30',
  };
  return (
    <span className={`px-3 py-1 text-xs font-medium rounded-full border ${colorClasses[status]}`}>
      {status}
    </span>
  );
};

// MODIFIÉ : On ajoute le type "Variants" à notre constante
const containerVariants: Variants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.08,
    },
  },
};

// MODIFIÉ : On ajoute le type "Variants" à notre constante
const itemVariants: Variants = {
  hidden: { y: 20, opacity: 0 },
  visible: {
    y: 0,
    opacity: 1,
    transition: {
      type: "spring",
      stiffness: 100,
    },
  },
};

export default function DashboardDisplay({ certificates }: { certificates: Certificate[] }) {
  const [spotlightStyle, setSpotlightStyle] = useState({});
  const [searchQuery, setSearchQuery] = useState("");

  const handleMouseMove = (e: MouseEvent<HTMLDivElement>) => {
    const { clientX, clientY } = e;
    setSpotlightStyle({
      background: `radial-gradient(600px at ${clientX}px ${clientY}px, rgba(29, 78, 216, 0.15), transparent 80%)`
    });
  };

  const filteredCertificates = certificates.filter(cert =>
    cert.domain.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div 
      className="min-h-screen p-4 md:p-8 relative" 
      onMouseMove={handleMouseMove}
    >
      <div 
        className="pointer-events-none fixed inset-0 z-30 transition duration-300" 
        style={spotlightStyle}
      />
      
      <div className="max-w-7xl mx-auto">
        <header className="text-center mb-8">
          <h1 className="text-4xl md:text-5xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-cyan-300">
            SSL Certificate Dashboard
          </h1>
          <p className="text-slate-400 mt-2">Vue d&apos;ensemble de la validité de vos certificats</p>
        </header>

        <div className="mb-8 flex justify-center">
          <div className="relative w-full max-w-lg">
            <input
              type="text"
              placeholder="Rechercher un domaine..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-3 bg-slate-900/50 backdrop-blur-md border border-slate-700 rounded-lg
                         text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50"
            />
            <div className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500">
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line>
              </svg>
            </div>
          </div>
        </div>

        {filteredCertificates.length > 0 ? (
          <motion.div
            className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
            variants={containerVariants}
            initial="hidden"
            animate="visible"
          >
            {filteredCertificates.map((cert) => (
              <motion.div 
                key={cert.domain} 
                variants={itemVariants}
                className="bg-slate-900/50 backdrop-blur-md border border-slate-800 rounded-xl p-6
                           transform hover:-translate-y-1 transition-transform duration-300"
              >
                <div className="flex justify-between items-start mb-4">
                  <h2 className="font-bold text-lg text-slate-200">{cert.domain}</h2>
                  <StatusBadge status={cert.status} />
                </div>
                
                {cert.status !== 'Erreur' ? (
                  <div>
                    <p className="text-sm text-slate-400">Expire dans</p>
                    <p className="text-3xl font-semibold text-slate-50 mb-4">{cert.days_left ?? 'N/A'} jours</p>
                    <p className="text-xs text-slate-500">
                      Date d&apos;expiration : {cert.expiry_date ? new Date(cert.expiry_date).toLocaleDateString('fr-FR') : 'Inconnue'}
                    </p>
                  </div>
                ) : (
                  <div className="bg-red-900/20 p-3 rounded-lg">
                     <p className="text-xs text-red-300">{cert.error_message}</p>
                  </div>
                )}
              </motion.div>
            ))}
          </motion.div>
        ) : (
          <div className="text-center py-10">
            <p className="text-slate-400">Aucun certificat trouvé.</p>
            <p className="text-sm text-slate-500">Essayez de modifier votre recherche ou vérifiez votre liste de domaines.</p>
          </div>
        )}
      </div>
    </div>
  );
}