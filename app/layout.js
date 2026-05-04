export const metadata = {
  title: 'Dry Dock 2026',
  description: 'Hackathon project',
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
