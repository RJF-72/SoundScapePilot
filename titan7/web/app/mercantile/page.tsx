'use client'

import { useEffect, useState } from 'react'

interface Product {
  id: string
  name: string
  description: string
  price: number
  image: string
  category: string
  inventory: number
}

export default function MercantilePage() {
  const [products, setProducts] = useState<Product[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch('/api/proxy/mercantile/products')
      .then(r => r.json())
      .then(data => { setProducts(data); setLoading(false) })
      .catch(() => setLoading(false))
  }, [])

  if (loading) return <div className="min-h-[60vh] flex items-center justify-center text-[var(--muted)]">Loading shop…</div>

  return (
    <div className="min-h-screen py-16 px-4 sm:px-6 lg:px-8">
      <div className="max-w-7xl mx-auto">
        <header className="mb-12 text-center">
          <h1 className="text-4xl sm:text-5xl font-bold mb-4">Grit & Grace Mercantile</h1>
          <p className="text-[var(--muted)] max-w-2xl mx-auto">Faith-driven merch. Vinyl. Exclusives. Limited runs.</p>
        </header>
        {products.length === 0 ? (
          <div className="text-center text-[var(--muted)] py-20">
            Shop opening soon. Check back for merch, vinyl, and exclusives.
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {products.map((p) => (
              <div key={p.id} className="card group">
                <div className="aspect-square bg-[var(--bg)] rounded-lg mb-4 relative overflow-hidden">
                  {p.image ? (
                    <img src={p.image} alt={p.name} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300" />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center text-[var(--muted)]">No Image</div>
                  )}
                  {p.inventory < 10 && (
                    <span className="absolute top-2 right-2 bg-[var(--primary)] text-white text-xs px-2 py-1 rounded">
                      Only {p.inventory} left
                    </span>
                  )}
                </div>
                <span className="text-xs font-medium px-2 py-1 rounded-full bg-[var(--secondary)]/20 text-[var(--primary)] inline-block mb-2">
                  {p.category}
                </span>
                <h3 className="text-lg font-bold mb-1 group-hover:text-[var(--primary)] transition-colors">{p.name}</h3>
                <p className="text-[var(--muted)] text-sm mb-3 line-clamp-2">{p.description}</p>
                <div className="flex items-center justify-between">
                  <span className="text-xl font-bold text-[var(--gold)]">${p.price.toFixed(2)}</span>
                  <button className="btn-primary text-sm px-4" disabled={p.inventory === 0}>
                    {p.inventory === 0 ? 'Sold Out' : 'Add to Cart'}
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}