// Fichier: frontend/app/page.tsx
"use client"; // Nécessaire pour les hooks comme useState et useEffect

import React, { useState, useEffect, MouseEvent } from "react";
import certificatesData from '../data/ssl_status.json';

// Définir le type pour les données d'un certificat
interface Certificate {
  domain: string;
  status: 'OK' | 'Expire bientôt' | 'Expiré' | 'Erreur';
  days_left?: number;
  expiry_date?: string;
  error_message?: string;
}

// Composant pour le badge de statut
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

// Page principale du Dashboard
export default function DashboardPage() {
  const [spotlightStyle, setSpotlightStyle] = useState({});

  const handleMouseMove = (e: MouseEvent<HTMLDivElement>) => {
    const { clientX, clientY } = e;
    setSpotlightStyle({
      background: `radial-gradient(600px at ${clientX}px ${clientY}px, rgba(29, 78, 216, 0.15), transparent 80%)`
    });
  };

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
        <header className="text-center mb-12">
          <h1 className="text-4xl md:text-5xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-cyan-300">
            SSL Certificate Dashboard
          </h1>
          <p className="text-slate-400 mt-2">Vue d'ensemble de la validité de vos certificats</p>
        </header>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {certificatesData.map((cert: Certificate) => (
            <div 
              key={cert.domain} 
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
                    Date d'expiration : {cert.expiry_date ? new Date(cert.expiry_date).toLocaleDateString('fr-FR') : 'Inconnue'}
                  </p>
                </div>
              ) : (
                <div className="bg-red-900/20 p-3 rounded-lg">
                   <p className="text-xs text-red-300">{cert.error_message}</p>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}