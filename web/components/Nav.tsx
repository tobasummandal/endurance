import Link from 'next/link';

export default function Nav() {
  return (
    <nav className="helios-nav">
      <Link href="/sessions" className="brand">
        HELIOS
      </Link>
      <div style={{ display: 'flex', gap: '2rem' }}>
        <Link href="/live">Live</Link>
        <Link href="/sessions">Sessions</Link>
        <a href="/" className="ver">v0.1</a>
      </div>
    </nav>
  );
}
