import { useQuery } from "@tanstack/react-query";
import { metricsApi } from "~/services/api";
import { AppShell } from "~/components/layout/AppShell";

function formatTokens(n: number): string {
	if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
	if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
	return String(n);
}

function formatDuration(seconds: number | null): string {
	if (seconds === null) return "—";
	if (seconds < 60) return `${seconds.toFixed(1)}s`;
	const m = Math.floor(seconds / 60);
	const s = Math.round(seconds % 60);
	return `${m}m ${s}s`;
}

function formatCost(usd: string): string {
	const n = parseFloat(usd);
	if (Number.isNaN(n)) return "$0.00";
	return `$${n.toFixed(2)}`;
}

function formatRate(rate: number): string {
	return `${(rate * 100).toFixed(0)}%`;
}

export function MetricsPage() {
	const runs = useQuery({
		queryKey: ["metrics", "runs"],
		queryFn: () => metricsApi.listRuns(),
	});

	const breakdown = useQuery({
		queryKey: ["metrics", "cost-breakdown"],
		queryFn: () => metricsApi.getCostBreakdown(),
	});

	const isLoading = runs.isLoading || breakdown.isLoading;
	const error = runs.error || breakdown.error;

	const runsData = runs.data ?? [];
	const breakdownData = breakdown.data ?? [];

	const totalTokens = runsData.reduce((s, r) => s + r.total_tokens, 0);
	const totalCost = breakdownData.reduce(
		(s, item) => s + parseFloat(item.total_cost_usd || "0"),
		0,
	);
	const totalRuns = runsData.length;

	const content = (
		<div className="space-y-8">
			<header className="space-y-1">
				<h1 className="font-heading text-3xl tracking-wide text-base-content">
					成本仪表板
				</h1>
				<p className="text-sm text-base-content/50 font-heading tracking-wide">
					运行概览 · 成本分析 · 资源用量
				</p>
			</header>

			{isLoading && (
				<div className="flex items-center justify-center py-20">
					<span className="loading loading-spinner loading-lg text-primary" />
				</div>
			)}

			{error && (
				<div className="alert alert-error max-w-lg">
					<span>加载失败: {(error as Error).message || "请稍后重试"}</span>
				</div>
			)}

			{!isLoading && !error && runsData.length === 0 && (
				<div className="text-center py-20 text-base-content/30">
					<p className="text-lg font-heading">暂无运行数据</p>
					<p className="text-sm mt-1">完成一次生成后，指标将显示在此处</p>
				</div>
			)}

			{!isLoading && !error && runsData.length > 0 && (
				<>
					{/* Summary Cards */}
					<div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
						<div className="card bg-base-200 border border-base-content/5">
							<div className="card-body p-4">
								<div className="text-xs text-base-content/40 font-bold tracking-wider uppercase">
									总运行数
								</div>
								<div className="font-mono text-2xl text-primary mt-1">
									{totalRuns}
								</div>
							</div>
						</div>
						<div className="card bg-base-200 border border-base-content/5">
							<div className="card-body p-4">
								<div className="text-xs text-base-content/40 font-bold tracking-wider uppercase">
									总 Token
								</div>
								<div className="font-mono text-2xl text-primary mt-1">
									{formatTokens(totalTokens)}
								</div>
							</div>
						</div>
						<div className="card bg-base-200 border border-base-content/5">
							<div className="card-body p-4">
								<div className="text-xs text-base-content/40 font-bold tracking-wider uppercase">
									估算总成本
								</div>
								<div className="font-mono text-2xl text-warning mt-1">
									{formatCost(String(totalCost))}
								</div>
							</div>
						</div>
					</div>

					{/* Run Overview Table */}
					<section className="space-y-3">
						<h2 className="font-heading text-lg tracking-wide text-base-content">
							运行概览
						</h2>
						<div className="overflow-x-auto rounded-lg border border-base-content/5">
							<table className="table table-zebra table-sm">
								<thead>
									<tr className="text-xs text-base-content/50 uppercase tracking-wider">
										<th>Run ID</th>
										<th>Agents</th>
										<th>LLM Calls</th>
										<th>Tokens</th>
										<th>Images</th>
										<th>Duration</th>
										<th>Cost (USD)</th>
										<th>Success</th>
									</tr>
								</thead>
								<tbody>
									{runsData.map((run) => (
										<tr key={run.run_id} className="hover">
											<td className="font-mono text-primary">
												#{run.run_id}
											</td>
											<td className="font-mono">{run.agent_count}</td>
											<td className="font-mono">{run.total_llm_calls}</td>
											<td className="font-mono">
												{formatTokens(run.total_tokens)}
											</td>
											<td className="font-mono">{run.total_images}</td>
											<td className="font-mono">
												{formatDuration(run.avg_duration_seconds)}
											</td>
											<td className="font-mono text-warning">
												{formatCost(run.total_cost_usd || "0")}
											</td>
											<td>
												<span
													className={`badge badge-sm ${
														run.success_rate >= 0.9
															? "badge-success"
															: run.success_rate >= 0.5
																? "badge-warning"
																: "badge-error"
													}`}
												>
													{formatRate(run.success_rate)}
												</span>
											</td>
										</tr>
									))}
								</tbody>
							</table>
						</div>
					</section>

					{/* Cost Breakdown Table */}
					<section className="space-y-3">
						<h2 className="font-heading text-lg tracking-wide text-base-content">
							成本明细
						</h2>
						{breakdownData.length === 0 ? (
							<p className="text-sm text-base-content/30 py-4">
								暂无成本明细数据
							</p>
						) : (
							<div className="overflow-x-auto rounded-lg border border-base-content/5">
								<table className="table table-zebra table-sm">
									<thead>
										<tr className="text-xs text-base-content/50 uppercase tracking-wider">
											<th>Agent</th>
											<th>Model</th>
											<th>Input Tokens</th>
											<th>Output Tokens</th>
											<th>Images</th>
											<th>Video (s)</th>
											<th>Cost (USD)</th>
										</tr>
									</thead>
									<tbody>
										{breakdownData.map((item, i) => (
											<tr key={`${item.agent_name}-${item.model_name}-${i}`} className="hover">
												<td className="text-base-content/80">
													{item.agent_name}
												</td>
												<td className="font-mono text-xs text-base-content/60">
													{item.model_name}
												</td>
												<td className="font-mono">
													{formatTokens(item.total_input_tokens)}
												</td>
												<td className="font-mono">
													{formatTokens(item.total_output_tokens)}
												</td>
												<td className="font-mono">{item.total_images}</td>
												<td className="font-mono">
													{item.total_video_seconds > 0
														? item.total_video_seconds.toFixed(1)
														: "—"}
												</td>
												<td className="font-mono text-warning font-bold">
													{formatCost(item.total_cost_usd)}
												</td>
											</tr>
										))}
									</tbody>
								</table>
							</div>
						)}
					</section>
				</>
			)}
		</div>
	);

	return (
		<AppShell variant="default">
			<div className="p-4 sm:p-6 max-w-5xl mx-auto">{content}</div>
		</AppShell>
	);
}
