// Fichier: frontend/src/components/CertificateDetailModal.tsx
"use client";

import React, { useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type { Certificate } from './DashboardDisplay'; // On importera le type depuis le dashboard

interface DetailModalProps {
  cert: Certificate | null;
  onClose: () => void;
}

const DetailRow = ({ label, value }: { label: string, value?: string }) => (
  <div className="border-b border-slate-700/50 py-3">
    <p className="text-sm text-slate-400">{label}</p>
    <p className="text-base text-slate-200 break-words font-mono">{value || 'N/A'}</p>
  </div>
);

export default function CertificateDetailModal({ cert, onClose }: DetailModalProps) {
  const dialogRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!cert) return;
    dialogRef.current?.focus();
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [cert, onClose]);

  return (
    <AnimatePresence>
      {cert && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4"
          onClick={onClose}
        >
          <motion.div
            initial={{ scale: 0.95, y: 50 }}
            animate={{ scale: 1, y: 0 }}
            exit={{ scale: 0.95, y: 50 }}
            transition={{ type: 'spring', stiffness: 400, damping: 40 }}
            className="bg-slate-900 border border-slate-700 rounded-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto"
            role="dialog"
            aria-modal="true"
            aria-labelledby="certificate-dialog-title"
            tabIndex={-1}
            ref={dialogRef}
            onClick={(e) => e.stopPropagation()}
          >
            <header className="p-6 border-b border-slate-700 sticky top-0 bg-slate-900/80 backdrop-blur-lg">
              <h2 id="certificate-dialog-title" className="text-2xl font-bold text-slate-100">{cert.domain}</h2>
              <p className="text-sm text-slate-400">Détails du certificat SSL/TLS</p>
            </header>
            <div className="p-6">
              <DetailRow label="Statut" value={cert.status} />
              <DetailRow label="Jours Restants" value={cert.days_left?.toString()} />
              <DetailRow label="Contrôlé le" value={cert.checked_at ? new Date(cert.checked_at).toLocaleString('fr-FR') : undefined} />
              <DetailRow label="Date d'Expiration" value={cert.expiry_date ? new Date(cert.expiry_date).toLocaleString('fr-FR') : 'N/A'} />
              <DetailRow label="Valide depuis" value={cert.valid_from ? new Date(cert.valid_from).toLocaleString('fr-FR') : undefined} />
              <DetailRow label="Émetteur" value={cert.issuer} />
              <DetailRow label="Sujet" value={cert.subject} />
              <DetailRow label="Numéro de série" value={cert.serial_number} />
              <DetailRow label="Empreinte SHA-256" value={cert.fingerprint} />
              <DetailRow label="SAN" value={cert.san?.join(', ')} />
              {cert.error_type && <DetailRow label="Type d'Erreur" value={cert.error_type} />}
              {cert.error_message && <DetailRow label="Message d'Erreur" value={cert.error_message} />}
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
