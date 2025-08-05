// Fichier: frontend/src/components/AddDomainModal.tsx
"use client";

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import toast from 'react-hot-toast';

const API_URL = "http://localhost:8000";

interface AddDomainModalProps {
  isOpen: boolean;
  onClose: () => void;
  onDomainAdded: () => void; // Pour rafraîchir la liste après l'ajout
}

export default function AddDomainModal({ isOpen, onClose, onDomainAdded }: AddDomainModalProps) {
  const [domainsText, setDomainsText] = useState(""); // État pour la zone de texte
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    // Sépare le texte en une liste de domaines, en retirant les lignes vides et les espaces superflus
    const domains = domainsText.split('\n').map(d => d.trim()).filter(d => d);

    if (domains.length === 0) {
      toast.error("Veuillez entrer au moins un nom de domaine.");
      return;
    }

    setIsLoading(true);
    const toastId = toast.loading("Ajout des domaines en cours...");

    try {
      // On utilise le nouvel endpoint "bulk" pour l'ajout en masse
      const response = await fetch(`${API_URL}/api/domains/bulk`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ domains: domains }), // On envoie la liste
      });

      const responseData = await response.json();
      if (!response.ok) {
        throw new Error(responseData.detail || "Une erreur est survenue.");
      }

      toast.success(responseData.message, { id: toastId, duration: 4000 });
      setDomainsText("");
      onDomainAdded();
      onClose();

    } catch (err) {
      toast.dismiss(toastId);
      if (err instanceof Error) {
        toast.error(err.message);
      } else {
        toast.error("Une erreur inconnue est survenue.");
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4"
          onClick={onClose}
        >
          <motion.div
            initial={{ scale: 0.9, opacity: 0, y: 50 }}
            animate={{ scale: 1, opacity: 1, y: 0 }}
            exit={{ scale: 0.9, opacity: 0, y: 50 }}
            transition={{ type: 'spring', stiffness: 300, damping: 30 }}
            className="bg-slate-900 border border-slate-700 rounded-xl p-8 w-full max-w-md"
            onClick={(e) => e.stopPropagation()}
          >
            <h2 className="text-2xl font-bold mb-4">Ajouter des Domaines</h2>
            <form onSubmit={handleSubmit}>
              <p className="text-sm text-slate-400 mb-4">
                Collez une liste de domaines (un par ligne). Les doublons et les formats invalides seront ignorés par le serveur.
              </p>
              <textarea
                value={domainsText}
                onChange={(e) => setDomainsText(e.target.value)}
                placeholder={"exemple.com\nautre-domaine.net\nsite-web.org"}
                className="w-full px-4 py-3 bg-slate-800 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 h-40 resize-y font-mono"
                disabled={isLoading}
              />
              <div className="flex justify-end gap-4 mt-6">
                <button
                  type="button"
                  onClick={onClose}
                  disabled={isLoading}
                  className="px-5 py-2 rounded-lg bg-slate-700 hover:bg-slate-600 transition-colors"
                >
                  Annuler
                </button>
                <button
                  type="submit"
                  disabled={isLoading}
                  className="px-5 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 transition-colors disabled:bg-slate-500 disabled:cursor-not-allowed"
                >
                  {isLoading ? 'Ajout en cours...' : 'Ajouter'}
                </button>
              </div>
            </form>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}