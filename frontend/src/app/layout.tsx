// Fichier: frontend/app/layout.tsx
import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SSL-Cert-Monitor Dashboard",
  description: "Surveillez vos certificats SSL comme un pro",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="fr">
      <body>
        <main className="relative min-h-screen overflow-hidden">
          {/* L'effet de spotlight sera ajouté directement dans la page principale pour plus de simplicité */}
          {children}
        </main>
      </body>
    </html>
  );
}
