export interface BarChartDatum {
  label: string
  value: number
}

interface BarChartProps {
  data: BarChartDatum[]
  formatValue?: (value: number) => string
}

/** A minimal, dependency-free vertical bar chart — no charting library,
 * just proportionally-scaled divs. Good enough for a handful of bars on
 * a dashboard; reach for a real charting library if this ever needs to
 * do more (tooltips, multiple series, zooming). */
export function BarChart({ data, formatValue = String }: BarChartProps) {
  const max = Math.max(...data.map((d) => d.value), 1)

  return (
    <div className="flex h-40 items-end gap-2">
      {data.map((d) => (
        <div key={d.label} className="flex flex-1 flex-col items-center gap-1.5">
          <div
            className="flex h-32 w-full flex-col justify-end"
            title={`${d.label}: ${formatValue(d.value)}`}
          >
            <div
              className="w-full rounded-t bg-indigo-500 transition-all"
              style={{ height: d.value > 0 ? `${(d.value / max) * 100}%` : '2px' }}
            />
          </div>
          <span className="text-xs text-slate-500">{d.label}</span>
        </div>
      ))}
    </div>
  )
}
