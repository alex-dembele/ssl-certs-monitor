// Fichier: frontend/app/layout.tsx
import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

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
      <body className={inter.className}>
        <main className="relative min-h-screen overflow-hidden">
          {/* L'effet de spotlight sera ajouté directement dans la page principale pour plus de simplicité */}
          {children}
        </main>
      </body>
    </html>
  );
}