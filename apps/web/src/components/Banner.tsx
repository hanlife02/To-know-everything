export function Banner({
  tone,
  text,
}: {
  tone: 'good' | 'danger' | 'warning'
  text: string
}) {
  return <div className={`banner banner--${tone}`}>{text}</div>
}
