import './globals.css'
import { Inter } from 'next/font/google'
import Link from 'next/link'
import { AuthProvider } from './components/AuthProvider'

const inter = Inter({ subsets: ['latin'], variable: '--font-inter' })

export const metadata = {
  title: 'Redemption Road Music Group',
  description: 'Label · Publishing · Studio · Mercantile · Marketing',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${inter.variable} antialiased`}>
      <body className="min-h-screen bg-[var(--bg)] text-[var(--fg)]">
        <AuthProvider>
        <header className="border-b border-[var(--border)] sticky top-0 bg-[var(--bg)]/95 backdrop-blur z-50">
          <nav className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
            <Link href="/" className="flex items-center gap-2">
              <span className="text-2xl font-bold tracking-tight bg-gradient-to-r from-[var(--primary)] to-[var(--gold)] bg-clip-text text-transparent">
                Redemption Road
              </span>
              <span className="text-xs text-[var(--muted)] uppercase tracking-wider">Music Group</span>
            </Link>
            <div className="hidden md:flex items-center gap-6">
              <Link href="/artists" className="text-sm hover:text-[var(--primary)] transition-colors">Artists</Link>
              <Link href="/releases" className="text-sm hover:text-[var(--primary)] transition-colors">Releases</Link>
              <Link href="/mercantile" className="text-sm hover:text-[var(--primary)] transition-colors">Mercantile</Link>
              <Link href="/marketing" className="text-sm hover:text-[var(--primary)] transition-colors">Marketing</Link>
              <Link href="/submit" className="btn-primary text-sm">Submit Demo</Link>
            </div>
            <Link href="/login" className="text-sm hover:text-[var(--primary)] transition-colors">Owner Login</Link>
            <Link href="/submit" className="btn-primary text-sm">Submit Demo</Link>
          </nav>
        </header>
        <main>{children}</main>
        <footer className="border-t border-[var(--border)] py-8 px-4">
          <div className="max-w-7xl mx-auto grid grid-cols-1 md:grid-cols-5 gap-8 text-sm text-[var(--muted)]">
            <div>
              <h4 className="font-semibold text-[var(--fg)] mb-2">Redemption Road</h4>
              <p>Label · Publishing · Studio · Mercantile · Marketing</p>
            </div>
            <div>
              <h4 className="font-semibold text-[var(--fg)] mb-2">Divisions</h4>
              <ul className="space-y-1">
                <li><Link href="/artists" className="hover:text-[var(--primary)]">Artists</Link></li>
                <li><Link href="/releases" className="hover:text-[var(--primary)]">Releases</Link></li>
                <li><Link href="/mercantile" className="hover:text-[var(--primary)]">Grit & Grace</Link></li>
                <li><Link href="/marketing" className="hover:text-[var(--primary)]">Titan Marketing</Link></li>
              </ul>
            </div>
            <div>
              <h4 className="font-semibold text-[var(--fg)] mb-2">For Artists</h4>
              <ul className="space-y-1">
                <li><Link href="/submit" className="hover:text-[var(--primary)]">Submit Demo</Link></li>
              </ul>
            </div>
            <div>
              <h4 className="font-semibold text-[var(--fg)] mb-2">Services</h4>
              <ul className="space-y-1">
                <li><Link href="/marketing" className="hover:text-[var(--primary)]">Radio Campaigns</Link></li>
                <li><Link href="/marketing" className="hover:text-[var(--primary)]">Streaming Blitz</Link></li>
                <li><Link href="/marketing" className="hover:text-[var(--primary)]">Sync Licensing</Link></li>
                <li><Link href="/marketing" className="hover:text-[var(--primary)]">Tour Booking</Link></li>
              </ul>
            </div>
            <div>
              <h4 className="font-semibold text-[var(--fg)] mb-2">Contact</h4>
              <p>Abilene, Texas</p>
              <p>info@redemptionroadmg.com</p>
            </div>
          </div>
          <div className="max-w-7xl mx-auto mt-8 pt-8 border-t border-[var(--border)] text-center text-xs text-[var(--muted)]">
            <p>© 2026 Redemption Road Music Group™. All rights reserved.</p>
            <p className="mt-2"><Link href="/login" className="hover:text-[var(--primary)]">Owner Login</Link></p>
          </div>
        </footer>
      </AuthProvider>
      </body>
    </html>
  )
}