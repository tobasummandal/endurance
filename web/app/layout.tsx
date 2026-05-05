import type { Metadata } from 'next';
import BackgroundCanvas from '@/components/BackgroundCanvas';
import CustomCursor from '@/components/CustomCursor';
import Nav from '@/components/Nav';
import Providers from '@/components/Providers';
import '@/styles/globals.css';

export const metadata: Metadata = {
  title: 'HELIOS — Reviewer',
  description: 'The correctness layer for scientific code',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        <link
          href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,300;0,9..144,400;0,9..144,600;1,9..144,300;1,9..144,400&family=Inter:wght@300;400;500&family=JetBrains+Mono:wght@300;400;500;600&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>
        <BackgroundCanvas />
        <CustomCursor />
        <Nav />
        <main className="helios-main">
          <Providers>{children}</Providers>
        </main>
      </body>
    </html>
  );
}
