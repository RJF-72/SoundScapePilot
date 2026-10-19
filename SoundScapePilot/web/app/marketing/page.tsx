import StripeCheckout from '../components/StripeCheckout'

export default function MarketingPage() {
  const packages = [
    { name: 'Radio Campaign', price: '$499', period: '/release', product: 'radio_boost', features: ['Format-specific pitches (500+ stations)', 'Follow-up scheduling (3 rounds)', 'Station strategy docs', 'Success tracking dashboard'], tagline: 'Get on the air' },
    { name: 'Streaming Blitz', price: '$299', period: '/release', product: 'streaming_blitz', features: ['9-platform editorial pitching', 'Algorithmic trigger campaigns', 'Playlist add tracking', 'Pre-save campaigns'], tagline: 'Own the algorithms' },
    { name: 'Sync Licensing', price: '$599', period: ' starter fee', product: 'sync_pack', features: ['15 music supervisor pitches', 'Custom cue sheets', 'TV/Film/Ad placement', 'One-stop licensing'], tagline: 'Land the placement' },
    { name: 'Tour & Booking', price: '$799', period: '/tour', product: 'tour_plan', features: ['60+ market routing', 'P&L per show', 'Venue contracts', 'Booking agent outreach'], tagline: 'Hit the road' },
    { name: 'Neon Church Distribution', price: '$49', period: '/yr per artist', product: 'distro_only', features: ['15+ DSP delivery', 'Royalty collection', 'Monthly statements', 'Neon Church Publishing admin'], tagline: 'Worldwide delivery' },
    { name: 'Full Label Services', price: '$1,499', period: '/mo', product: 'enterprise', features: ['All above + royalty admin', 'Catalog management', 'Audit log & team presence', 'Weekly strategy call', 'Investor-ready reporting'], tagline: 'Complete infrastructure', highlight: true },
  ]

  return (
    <div className="min-h-screen py-16 px-4 sm:px-6 lg:px-8">
      <div className="max-w-7xl mx-auto">
        <header className="mb-16 text-center">
          <h1 className="text-4xl sm:text-5xl font-bold mb-4">SoundScape Marketing</h1>
          <p className="text-[var(--muted)] max-w-2xl mx-auto mb-8">
            Major-label infrastructure. Independent prices. You bring the music. We bring the machine.
          </p>
          <p className="text-[var(--gold)] font-medium">Requires License Agreement · <a href="/marketing/agreements" className="underline">View Contracts</a></p>
        </header>

        <section className="mb-20">
          <h2 className="text-3xl font-bold text-center mb-12">Service Packages</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {packages.map((p) => (
              <div key={p.name} className={`card ${p.highlight ? 'border-[var(--gold)] relative' : ''}`}>
                {p.highlight && <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-[var(--gold)] text-[var(--bg)] text-xs font-bold px-3 py-1 rounded-full">BEST VALUE</div>}
                <h3 className="text-xl font-bold mb-1">{p.name}</h3>
                <p className="text-[var(--gold)] font-medium mb-2">{p.tagline}</p>
                <div className="mb-4">
                  <span className="text-3xl font-bold">{p.price}</span>
                  <span className="text-[var(--muted)]">{p.period}</span>
                </div>
                <ul className="space-y-2 mb-6 text-sm">
                  {p.features.map((f, i) => (
                    <li key={i} className="flex items-center gap-2 text-[var(--muted)]">
                      <svg className="w-4 h-4 text-[var(--primary)]" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd"/></svg>
                      {f}
                    </li>
                  ))}
                </ul>
                <StripeCheckout
                  items={[{ product: p.product, quantity: 1 }]}
                  buttonText={p.highlight ? 'Start Full Services' : 'Checkout'}
                  className={`w-full py-3 rounded-lg font-medium ${p.highlight ? 'bg-[var(--gold)] text-[var(--bg)] hover:opacity-90' : 'btn-secondary'}`}
                />
              </div>
            ))}
          </div>
        </section>

        <section className="card">
          <h2 className="text-2xl font-bold mb-6">Powered by SoundScape Pilot</h2>
          <div className="grid grid-cols-1 sm:grid-cols-4 gap-6 text-sm">
            <div>
              <h3 className="font-bold text-[var(--primary)] mb-3">Radio Autopilot</h3>
              <ul className="space-y-1 text-[var(--muted)]">
                <li>• 500+ station database</li>
                <li>• Format-specific pitches</li>
                <li>• Auto follow-ups</li>
              </ul>
            </div>
            <div>
              <h3 className="font-bold text-[var(--cyan)] mb-3">Streaming Promoter</h3>
              <ul className="space-y-1 text-[var(--muted)]">
                <li>• 9 platforms</li>
                <li>• Editorial + algorithmic</li>
                <li>• Pre-save campaigns</li>
              </ul>
            </div>
            <div>
              <h3 className="font-bold text-[var(--gold)] mb-3">Tour Manager</h3>
              <ul className="space-y-1 text-[var(--muted)]">
                <li>• 60+ markets</li>
                <li>• Real P&L per show</li>
                <li>• Contract generator</li>
              </ul>
            </div>
            <div>
              <h3 className="font-bold text-[var(--cyan)] mb-3">Sync Engine</h3>
              <ul className="space-y-1 text-[var(--muted)]">
                <li>• 15 supervisors</li>
                <li>• Cue sheet generator</li>
                <li>• One-stop licensing</li>
              </ul>
            </div>
          </div>
        </section>

        <section className="mt-12 text-center">
          <h2 className="text-2xl font-bold mb-4">Ready to Scale?</h2>
          <p className="text-[var(--muted)] mb-6 max-w-xl mx-auto">
            Every service is backed by the same infrastructure running Redemption Road Music Group.
            Licensed. Auditable. Real-time.
          </p>
          <a href="/marketing/agreements" className="btn-gold inline-block">Request License Agreements</a>
        </section>
      </div>
    </div>
  )
}