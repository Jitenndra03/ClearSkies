/**
 * Purpose-built skeleton loaders matching each page's real layout.
 */

export function SkeletonStatCards({ count = 3 }) {
  return (
    <div className="stats-grid">
      {Array.from({ length: count }, (_, i) => (
        <div key={i} className="stat-card" style={{ padding: '20px' }}>
          <div className="skeleton skeleton-text" style={{ width: '60%' }} />
          <div className="skeleton skeleton-stat" style={{ width: '40%' }} />
          <div className="skeleton skeleton-text-short" style={{ width: '50%' }} />
        </div>
      ))}
    </div>
  );
}

export function SkeletonWardList({ count = 8 }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
      {Array.from({ length: count }, (_, i) => (
        <div
          key={i}
          className="skeleton"
          style={{ height: '44px', opacity: 1 - i * 0.08, animationDelay: `${i * 60}ms` }}
        />
      ))}
    </div>
  );
}

export function SkeletonMap() {
  return (
    <div
      className="skeleton"
      style={{
        height: '480px',
        borderRadius: 'var(--radius-lg)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="var(--color-text-muted)" strokeWidth="1" strokeLinecap="round" strokeLinejoin="round" style={{ opacity: 0.15 }}>
        <path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z" />
        <circle cx="12" cy="10" r="3" />
      </svg>
    </div>
  );
}

export function SkeletonChart() {
  return (
    <div className="skeleton" style={{ height: '320px', borderRadius: 'var(--radius-lg)' }} />
  );
}

export function SkeletonTable({ rows = 6 }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
      <div className="skeleton" style={{ height: '36px', marginBottom: '4px' }} />
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} className="skeleton" style={{ height: '52px', animationDelay: `${i * 50}ms` }} />
      ))}
    </div>
  );
}

export function SkeletonAqiDisplay() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '40px 20px' }}>
      <div className="skeleton skeleton-circle" style={{ width: '120px', height: '120px' }} />
      <div className="skeleton skeleton-text" style={{ width: '140px', marginTop: '16px' }} />
    </div>
  );
}
