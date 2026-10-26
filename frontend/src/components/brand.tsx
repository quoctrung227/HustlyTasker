import { Link } from 'react-router'

export function Brand({ light = false }: { light?: boolean }) {
  return <Link to="/dashboard" className={`brand${light ? ' brand--light' : ''}`} aria-label="HustlyTasker — Tổng quan">
    <span className="brand__mark" aria-hidden="true"><span /><span /><span /></span>
    <span>Hustly<span className="brand__soft">Tasker</span></span>
  </Link>
}
