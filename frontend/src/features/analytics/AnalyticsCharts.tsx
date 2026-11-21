import { useId, useState } from 'react'
import { Card } from '../../components/ui'
import type { AnalyticsSummary } from '../../services/api/analytics'
import type { TaskStatus } from '../../services/api/work-management'

export const analyticsStatusLabels: Record<TaskStatus, string> = {
  PENDING: 'Chờ phân công', ASSIGNED: 'Đã phân công (trạng thái)', WORKING: 'Đang thực hiện',
  REVIEW: 'Chờ duyệt', COMPLETED: 'Hoàn thành (trạng thái)', CANCELLED: 'Đã hủy (cũ)',
}
const colors: Record<TaskStatus, string> = { PENDING: 'var(--analytics-pending)', ASSIGNED: 'var(--analytics-assigned)', WORKING: 'var(--analytics-working)', REVIEW: 'var(--analytics-review)', COMPLETED: 'var(--analytics-completed)', CANCELLED: 'var(--analytics-cancelled)' }
const number = (value: number) => value.toLocaleString('vi-VN')
export function monthLabel(value: string) { return `${value.slice(5)}/${value.slice(0, 4)}` }

export function StatusChart({ rows, total }: { rows: AnalyticsSummary['distribution']; total: number }) {
  const titleId = useId()
  const [selected, setSelected] = useState<TaskStatus | null>(null)
  let position = 0
  const stops = rows.filter((row) => row.count > 0).map((row) => {
    const start = position; position += row.count / total * 100
    return `${colors[row.status]} ${start}% ${position}%`
  })
  const current = rows.find((row) => row.status === selected && row.count > 0)
  return <Card className="analytics-chart"><h2 id={titleId}>Phân bổ trạng thái Task</h2><p className="field__hint">Task tạo trong kỳ, theo trạng thái hiện tại. Quá hạn là cảnh báo chồng lấp, không phải một lát biểu đồ.</p>
    {total === 0 ? <p className="analytics-chart-empty">Chưa có Task tạo trong khoảng thời gian này.</p> : <>
      <div className="analytics-donut-layout"><div className="analytics-donut" aria-hidden="true" style={{ background: `conic-gradient(${stops.join(',')})` }}><span><strong>{number(total)}</strong>Task</span></div>
        <ul className="analytics-legend" aria-label="Số lượng và tỷ lệ từng trạng thái">{rows.filter((row) => row.count > 0).map((row) => <li key={row.status}><button type="button" className="analytics-legend-button" aria-pressed={selected === row.status} onClick={() => setSelected(row.status)} onFocus={() => setSelected(row.status)} onMouseEnter={() => setSelected(row.status)}><span className="analytics-swatch" aria-hidden="true" style={{ background: colors[row.status] }} /><span>{analyticsStatusLabels[row.status]}</span><strong>{number(row.count)} <small>({(row.count / total * 100).toLocaleString('vi-VN', { maximumFractionDigits: 1 })}%)</small></strong></button></li>)}</ul>
      </div><p className="analytics-chart-insight" role="status">{current ? `${analyticsStatusLabels[current.status]}: ${number(current.count)} Task.` : `${number(total)} Task trong tập tạo mới đã chọn. Chọn chú giải để xem số liệu.`}</p>
    </>}
  </Card>
}

export function ApprovalChart({ rows }: { rows: AnalyticsSummary['approval_trend'] }) {
  const titleId = useId(), [selected, setSelected] = useState('')
  const width = 560, height = 210, left = 42, right = 20, top = 22, bottom = 38
  const maximum = Math.max(1, ...rows.map((row) => row.count))
  const point = (index: number, value: number) => ({ x: rows.length < 2 ? width / 2 : left + index * (width - left - right) / (rows.length - 1), y: height - bottom - value / maximum * (height - top - bottom) })
  const points = rows.map((row, index) => { const p = point(index, row.count); return `${p.x},${p.y}` }).join(' ')
  const current = rows.find((row) => row.month === selected)
  return <Card className="analytics-chart"><h2 id={titleId}>Task được nghiệm thu theo tháng</h2><p className="field__hint">Theo thời điểm Review được phê duyệt trong kỳ, gồm cả Task tạo trước kỳ. Thời gian Asia/Ho_Chi_Minh.</p>
    {!rows.length ? <p className="analytics-chart-empty">Chưa có dữ liệu thời gian phù hợp để hiển thị.</p> : <>
      <svg className="analytics-chart-svg" viewBox={`0 0 ${width} ${height}`} aria-hidden="true">
        {[0, 0.5, 1].map((fraction) => { const y = height - bottom - fraction * (height - top - bottom); return <g key={fraction}><line x1={left} x2={width - right} y1={y} y2={y} className="analytics-chart-grid" /><text x={left - 10} y={y + 4} textAnchor="end">{number(Math.round(maximum * fraction))}</text></g> })}
        <text x={left} y={13}>Task</text>{rows.length > 1 && <polyline points={points} fill="none" className="analytics-trend-line" />}
        {rows.map((row, index) => { const p = point(index, row.count); return <g key={row.month}><circle cx={p.x} cy={p.y} r={selected === row.month ? 6 : 4} className="analytics-trend-dot" />{(rows.length <= 6 || index === 0 || index === rows.length - 1 || index % 3 === 0) && <text x={p.x} y={height - 12} textAnchor="middle">{monthLabel(row.month)}</text>}</g> })}
      </svg>
      <section className="analytics-trend-values" aria-label="Số Task nghiệm thu từng tháng">{rows.map((row) => <button type="button" key={row.month} className="analytics-month-value" aria-pressed={selected === row.month} onFocus={() => setSelected(row.month)} onMouseEnter={() => setSelected(row.month)} onClick={() => setSelected(row.month)}><span>{monthLabel(row.month)}</span><strong>{number(row.count)} Task</strong></button>)}</section>
      <p className="analytics-chart-insight" role="status">{current ? `${monthLabel(current.month)}: ${number(current.count)} Task được nghiệm thu.` : 'Chọn một tháng để xem số nghiệm thu chính xác.'}</p>
      {rows.length === 1 && <p className="field__hint">Chọn khoảng thời gian nhiều tháng để xem xu hướng; không suy diễn xu hướng từ một điểm.</p>}
    </>}
  </Card>
}

