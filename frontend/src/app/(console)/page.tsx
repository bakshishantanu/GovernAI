export default function DashboardPage() {
  return (
    <div className="max-w-5xl mx-auto space-y-8">
      <div>
        <h1 className="text-2xl font-semibold text-slate-100">Overview</h1>
        <p className="text-sm text-slate-400 mt-1">Metrics and recent activity across your organization.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-[#111] border border-slate-800 rounded-lg p-5">
          <div className="text-sm font-medium text-slate-400">Active Agents</div>
          <div className="mt-2 text-2xl font-semibold text-slate-100">4</div>
        </div>
        <div className="bg-[#111] border border-slate-800 rounded-lg p-5">
          <div className="text-sm font-medium text-slate-400">Policy Blocks (30d)</div>
          <div className="mt-2 text-2xl font-semibold text-slate-100">12</div>
        </div>
        <div className="bg-[#111] border border-slate-800 rounded-lg p-5">
          <div className="text-sm font-medium text-slate-400">Usage Cost (MTD)</div>
          <div className="mt-2 text-2xl font-semibold text-slate-100">$42.50</div>
        </div>
      </div>

      <div className="bg-[#111] border border-slate-800 rounded-lg p-8 min-h-[350px] flex items-center justify-center">
        <p className="text-slate-500 text-sm">Dashboard Charts (Pending Task #11)</p>
      </div>
    </div>
  );
}
