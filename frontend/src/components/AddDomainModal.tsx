// Fichier: frontend/src/components/AddDomainModal.tsx
"use client";

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import toast from 'react-hot-toast';

const API_URL = "http://localhost:8000";

// ✅ CORRECTION : Le type de onDomainsAdded est maintenant string[]
interface AddDomainModalProps {
  isOpen: boolean;
  onClose: () => void;
  onDomainsAdded: (newDomains: string[]) => void;
}

export default function AddDomainModal({ isOpen, onClose, onDomainsAdded }: AddDomainModalProps) {
  const [domainsText, setDomainsText] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const domains = domainsText.split('\n').map(d => d.trim()).filter(d => d);
    if (domains.length === 0) {
      toast.error("Veuillez entrer au moins un nom de domaine.");
      return;
    }

    setIsLoading(true);
    const toastId = toast.loading("Ajout des domaines à la liste...");

    try {
      const response = await fetch(`${API_URL}/api/domains/bulk`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ domains: domains }),
      });

      const responseData = await response.json();
      if (!response.ok) { throw new Error(responseData.detail || "Une erreur est survenue."); }

      toast.success(responseData.message, { id: toastId });
      setDomainsText("");
      onDomainsAdded(domains); // On renvoie bien la liste des NOMS de domaines
      onClose();

    } catch (err) {
      toast.dismiss(toastId);
      if (err instanceof Error) { toast.error(err.message); }
      else { toast.error("Une erreur inconnue est survenue."); }
    } finally {
      setIsLoading(false);
    }
  };

  // Le JSX de la modale ne change pas
  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div /* ... */ onClick={onClose}>
          <motion.div /* ... */ onClick={(e) => e.stopPropagation()}>
            <h2 className="text-2xl font-bold mb-4">Ajouter des Domaines</h2>
            <form onSubmit={handleSubmit}>
              <p className="text-sm text-slate-400 mb-4">
                Collez une liste de domaines (un par ligne).
              </p>
              <textarea
                value={domainsText}
                onChange={(e) => setDomainsText(e.target.value)}
                placeholder="exemple.com&#10;autre-domaine.net"
                className="w-full px-4 py-3 bg-slate-800 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 h-40 resize-y font-mono"
                disabled={isLoading}
              />
              <div className="flex justify-end gap-4 mt-6">
                <button type="button" onClick={onClose} disabled={isLoading} className="px-5 py-2 rounded-lg bg-slate-700 hover:bg-slate-600 transition-colors">Annuler</button>
                <button type="submit" disabled={isLoading} className="px-5 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 transition-colors disabled:bg-slate-500 disabled:cursor-not-allowed">{isLoading ? 'En cours...' : 'Ajouter'}</button>
              </div>
            </form>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}