import Link from 'next/link'

export default function HomePage() {
  const divisions = [
    { href: '/artists', label: 'Artists', desc: 'Roster · Bios · Latest Releases', icon: '🎤' },
    { href: '/releases', label: 'Releases', desc: 'Catalog · Players · Credits', icon: '💿' },
    { href: '/mercantile', label: 'Grit & Grace Mercantile', desc: 'Merch · Vinyl · Exclusives', icon: '🛍️' },
    { href: '/marketing', label: 'Titan Marketing', desc: 'Radio · Streaming · Sync · Tour', icon: '📈' },
  ]

  return (
    <div className="min-h-screen">
      <section className="relative min-h-[90vh] flex items-center justify-center overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-[var(--primary)]/20 via-transparent to-[var(--secondary)]/20" />
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_var(--primary)/10,_transparent_70%)]" />
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20 text-center">
          <span className="inline-block px-4 py-1 rounded-full bg-[var(--primary)]/20 text-[var(--primary)] text-sm font-medium mb-6">
            Redemption Road Music Group
          </span>
          <h1 className="text-5xl sm:text-7xl font-bold tracking-tight bg-gradient-to-r from-white via-[var(--gold)] to-[var(--cyan)] bg-clip-text text-transparent mb-6">
            Where Faith Meets Sound
          </h1>
          <p className="text-xl sm:text-2xl text-[var(--muted)] max-w-3xl mx-auto mb-10 text-balance">
            Independent label. Major-label infrastructure. Four divisions. One mission.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link href="/artists" className="btn-primary text-lg px-8 py-3">
              Explore the Roster
            </Link>
            <Link href="/marketing" className="btn-gold text-lg px-8 py-3">
              Promote Your Music
            </Link>
          </div>
        </div>
        <div className="absolute bottom-10 left-1/2 -translate-x-1/2 animate-bounce">
          <svg className="w-6 h-6 text-[var(--muted)]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
          </svg>
        </div>
      </section>

      <section className="py-20 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto">
          <h2 className="text-3xl sm:text-4xl font-bold text-center mb-12 bg-gradient-to-r from-white to-[var(--gold)] bg-clip-text text-transparent">
            Four Divisions. One Ecosystem.
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {divisions.map((d) => (
              <Link key={d.href} href={d.href} className="card group hover:border-[var(--primary)]/50 transition-all">
                <div className="text-4xl mb-4">{d.icon}</div>
                <h3 className="text-xl font-bold mb-2 group-hover:text-[var(--primary)] transition-colors">{d.label}</h3>
                <p className="text-[var(--muted)]">{d.desc}</p>
              </Link>
            ))}
          </div>
        </div>
      </section>

      <section className="py-20 px-4 sm:px-6 lg:px-8 bg-[var(--card)]/50">
        <div className="max-w-7xl mx-auto text-center">
          <h2 className="text-3xl sm:text-4xl font-bold mb-6">For Artists</h2>
          <p className="text-[var(--muted)] max-w-2xl mx-auto mb-10">
            Submit your music. Get distributed. Get promoted. Get paid.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link href="/submit" className="btn-primary text-lg px-8 py-3">
              Submit Your Demo
            </Link>
            <Link href="/releases" className="btn-secondary text-lg px-8 py-3">
              Browse Releases
            </Link>
          </div>
        </div>
      </section>
    </div>
  )
}