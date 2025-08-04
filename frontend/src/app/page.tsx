// Fichier: frontend/src/app/page.tsx

import fs from 'fs/promises'; // Utiliser la version asynchrone de fs
import path from 'path';
import DashboardDisplay from '../components/DashboardDisplay'; // Importer le nouveau composant client

// Définir le type pour les données d'un certificat
export interface Certificate {
  domain: string;
  status: 'OK' | 'Expire bientôt' | 'Expiré' | 'Erreur';
  days_left?: number;
  expiry_date?: string;
  error_message?: string;
}

async function getCertificateData(): Promise<Certificate[]> {
  // Le chemin vers le fichier de données partagé par Docker
  const dataPath = path.join('/app/data', 'ssl_status.json');
  
  try {
    const fileContents = await fs.readFile(dataPath, 'utf8');
    return JSON.parse(fileContents);
  } catch (error) {
    console.error("Impossible de lire le fichier de statut. Il n'existe peut-être pas encore.", error);
    // Retourner un tableau vide si le fichier n'est pas trouvé ou s'il y a une erreur
    return [];
  }
}

export default async function DashboardPage() {
  const certificates = await getCertificateData();

  return (
    <DashboardDisplay certificates={certificates} />
  );
}