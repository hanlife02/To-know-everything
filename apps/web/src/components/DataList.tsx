export function DataList({
  emptyTitle,
  emptyBody,
  items,
}: {
  emptyTitle: string
  emptyBody: string
  items: Array<{ title: string; meta: string; note: string }>
}) {
  if (items.length === 0) {
    return (
      <div className="empty-state">
        <strong>{emptyTitle}</strong>
        <p>{emptyBody}</p>
      </div>
    )
  }

  return (
    <div className="list-grid">
      {items.map((item) => (
        <article key={`${item.title}-${item.meta}`} className="list-card">
          <strong>{item.title}</strong>
          <span>{item.meta}</span>
          <p>{item.note}</p>
        </article>
      ))}
    </div>
  )
}
