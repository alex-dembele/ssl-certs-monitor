// Fichier: frontend/src/components/AddDomainModal.tsx
"use client";

import React, { useCallback, useEffect, useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import toast from 'react-hot-toast';
import { API_BASE_URL } from '@/lib/api';

// La prop attend bien un tableau de string[]
interface AddDomainModalProps {
  isOpen: boolean;
  onClose: () => void;
  onDomainsAdded: (newDomains: string[]) => void;
}

interface BulkResult {
  added: string[];
  duplicates: string[];
  invalid: { value: string; reason: string }[];
  message: string;
}

export default function AddDomainModal({ isOpen, onClose, onDomainsAdded }: AddDomainModalProps) {
  const [domainsText, setDomainsText] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<BulkResult | null>(null);

  const handleClose = useCallback(() => {
    setResult(null);
    onClose();
  }, [onClose]);
  const dialogRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!isOpen) return;
    dialogRef.current?.focus();
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && !isLoading) handleClose();
    };
    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [isOpen, isLoading, handleClose]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const domains = domainsText
      .split('\n')
      .map(d => d.trim().replace(/\.+$/, '').toLowerCase())
      .filter(d => d);

    if (domains.length === 0) {
      toast.error("Veuillez entrer au moins un nom de domaine.");
      return;
    }

    setIsLoading(true);
    const toastId = toast.loading("Ajout des domaines à la liste...");

    try {
      const response = await fetch(`${API_BASE_URL}/api/domains/bulk`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ domains: domains }),
      });

      const responseData = await response.json();
      if (!response.ok) {
        throw new Error(responseData.detail || "Une erreur est survenue.");
      }

      const bulkResult: BulkResult = {
        added: responseData.added ?? [],
        duplicates: responseData.duplicates ?? [],
        invalid: responseData.invalid ?? [],
        message: responseData.message,
      };
      toast.success(responseData.message, { id: toastId });
      setResult(bulkResult);
      setDomainsText("");
      if (bulkResult.added.length > 0) onDomainsAdded(bulkResult.added);

    } catch (err) {
      toast.dismiss(toastId);
      if (err instanceof Error) { toast.error(err.message); }
      else { toast.error("Une erreur inconnue est survenue."); }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4" onClick={handleClose}>
          <motion.div initial={{ scale: 0.9, y: 50 }} animate={{ scale: 1, y: 0 }} exit={{ scale: 0.9, y: 50 }} transition={{ type: 'spring', stiffness: 300, damping: 30 }} className="bg-slate-900 border border-slate-700 rounded-xl p-8 w-full max-w-md" role="dialog" aria-modal="true" aria-labelledby="add-domain-dialog-title" tabIndex={-1} ref={dialogRef} onClick={(e) => e.stopPropagation()}>
            <h2 id="add-domain-dialog-title" className="text-2xl font-bold mb-4">Ajouter des Domaines</h2>
            <form onSubmit={handleSubmit}>
              <p className="text-sm text-slate-400 mb-4">Collez une liste de domaines (un par ligne).</p>
              <textarea value={domainsText} onChange={(e) => setDomainsText(e.target.value)} placeholder="exemple.com&#10;autre-domaine.net" className="w-full px-4 py-3 bg-slate-800 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 h-40 resize-y font-mono" disabled={isLoading}/>
              {result && (
                <div className="mt-4 rounded-lg bg-slate-800/70 p-4 text-sm space-y-2">
                  <p className="font-medium text-slate-200">{result.message}</p>
                  {result.added.length > 0 && <p className="text-green-400">Ajoutés : {result.added.join(', ')}</p>}
                  {result.duplicates.length > 0 && <p className="text-yellow-400">Doublons : {result.duplicates.join(', ')}</p>}
                  {result.invalid.length > 0 && (
                    <div className="text-red-400">
                      <p>Invalides :</p>
                      <ul className="list-disc list-inside">{result.invalid.map((item, index) => <li key={`${item.value}-${index}`}>{item.value || '(vide)'} — {item.reason}</li>)}</ul>
                    </div>
                  )}
                </div>
              )}
              <div className="flex justify-end gap-4 mt-6">
                <button type="button" onClick={handleClose} disabled={isLoading} className="px-5 py-2 rounded-lg bg-slate-700 hover:bg-slate-600 transition-colors">Fermer</button>
                <button type="submit" disabled={isLoading} className="px-5 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 transition-colors disabled:bg-slate-500 disabled:cursor-not-allowed">{isLoading ? 'En cours...' : 'Ajouter'}</button>
              </div>
            </form>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
