export default function DashboardPage() {
  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="flex justify-between items-end">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-white mb-2">Command Center</h1>
          <p className="text-slate-400">Monitor your agent fleet and governance metrics in real-time.</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-slate-950 border border-slate-800 rounded-xl p-6 shadow-sm">
          <h3 className="text-sm font-medium text-slate-400 mb-1">Active Agents</h3>
          <p className="text-3xl font-bold text-white">4</p>
        </div>
        <div className="bg-slate-950 border border-slate-800 rounded-xl p-6 shadow-sm">
          <h3 className="text-sm font-medium text-slate-400 mb-1">Governance Blocks (24h)</h3>
          <p className="text-3xl font-bold text-emerald-400">12</p>
        </div>
        <div className="bg-slate-950 border border-slate-800 rounded-xl p-6 shadow-sm">
          <h3 className="text-sm font-medium text-slate-400 mb-1">Total Token Cost (MTD)</h3>
          <p className="text-3xl font-bold text-red-400">$42.50</p>
        </div>
      </div>

      <div className="bg-slate-950 border border-slate-800 rounded-xl p-8 min-h-[400px] flex items-center justify-center border-dashed">
        <p className="text-slate-500 text-sm">Dashboard Charts (Pending Task #11)</p>
      </div>
    </div>
  );
}
