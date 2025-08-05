// Fichier: frontend/src/app/page.tsx
import DashboardDisplay from '../components/DashboardDisplay';

// On repasse le composant en "async" pour pouvoir lire le fichier
export default async function DashboardPage() {
  return (
    <DashboardDisplay />
  );
}