import { type FullConfig } from "@playwright/test";
import { spawn, spawnSync, type ChildProcess } from "node:child_process";
import fs from "node:fs";
import net from "node:net";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const BACKEND_DIR = path.resolve(__dirname, "..", "..", "..", "backend");
const STATE_FILE = path.resolve(__dirname, ".e2e-state.json");

/** Common locations where `uv` may be installed. */
const UV_PATHS = [
	"/Users/lanf/.local/bin/uv",
	"/opt/homebrew/bin/uv",
	"/usr/local/bin/uv",
	"/usr/bin/uv",
];

function resolveUvBinary(): string {
	const which = spawnSync("which", ["uv"], { stdio: "pipe", encoding: "utf-8" });
	if (which.status === 0 && which.stdout?.trim()) {
		return which.stdout.trim();
	}
	for (const candidate of UV_PATHS) {
		if (fs.existsSync(candidate)) return candidate;
	}
	throw new Error(
		"`uv` binary not found. Install it from https://docs.astral.sh/uv/ or ensure it is on PATH.",
	);
}

/**
 * Find a random available TCP port by binding to port 0.
 */
function findAvailablePort(): Promise<number> {
	return new Promise((resolve, reject) => {
		const server = net.createServer();
		server.unref();
		server.on("error", reject);
		server.listen(0, () => {
			const addr = server.address();
			if (typeof addr === "object" && addr !== null) {
				const { port } = addr;
				server.close(() => resolve(port));
			} else {
				reject(new Error("Failed to get port from server address"));
			}
		});
	});
}

/**
 * Wait until the given URL responds with HTTP 200.
 * Polls every 500ms, times out after timeoutMs.
 */
async function waitForHealth(url: string, timeoutMs = 30000): Promise<void> {
	const deadline = Date.now() + timeoutMs;
	// eslint-disable-next-line no-constant-condition
	while (true) {
		try {
			const resp = await fetch(url);
			if (resp.ok) return;
		} catch {
			// Connection refused or not ready yet — retry
		}
		if (Date.now() > deadline) {
			throw new Error(`Health endpoint ${url} did not respond within ${timeoutMs}ms`);
		}
		await new Promise((r) => setTimeout(r, 500));
	}
}

/**
 * Run uv commands, automatically resolving the binary path.
 */
function uvCommand(): string {
	const fromWhich = spawnSync("which", ["uv"], { stdio: "pipe", encoding: "utf-8" });
	if (fromWhich.status === 0 && fromWhich.stdout?.trim()) return fromWhich.stdout.trim();
	for (const p of UV_PATHS) {
		if (fs.existsSync(p)) return p;
	}
	return "uv";
}

/**
 * Run alembic from the backend directory.
 */
function runAlembic(env: NodeJS.ProcessEnv): Promise<void> {
	const uvBin = uvCommand();
	return new Promise((resolve, reject) => {
		const child = spawn(uvBin, ["run", "alembic", "upgrade", "head"], {
			cwd: BACKEND_DIR,
			env: { ...process.env, ...env },
			stdio: "inherit",
		});
		child.on("close", (code) => {
			if (code === 0) resolve();
			else reject(new Error(`alembic upgrade head exited with code ${code}`));
		});
		child.on("error", reject);
	});
}

/**
 * Create a seed project via the backend API and return its ID.
 */
async function createSeedProject(backendPort: number): Promise<number> {
	const payload = {
		title: "E2E 种子项目",
		story: "一只勇敢的小猫在魔法森林中寻找传说中的彩虹泉水，途中遇到了会说话的树木和友善的精灵。",
		style: "anime",
		target_shot_count: 4,
		creation_mode: "story",
	};

	const url = `http://localhost:${backendPort}/api/v1/projects`;
	const resp = await fetch(url, {
		method: "POST",
		headers: { "Content-Type": "application/json" },
		body: JSON.stringify(payload),
	});

	if (!resp.ok) {
		const body = await resp.text();
		throw new Error(`Failed to create seed project: ${resp.status} ${resp.statusText} — ${body}`);
	}

	const data = (await resp.json()) as { id: number };
	return data.id;
}

async function globalSetup(_config: FullConfig): Promise<void> {
	// 0. Resolve `uv` binary path
	const uvBin = resolveUvBinary();
	console.log(`[global-setup] Using uv binary: ${uvBin}`);

	// 1. Find a random available port
	const backendPort = await findAvailablePort();
	console.log(`[global-setup] Using backend port: ${backendPort}`);

	// 2. Create a temp directory for SQLite database
	const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "openanimo-e2e-"));
	console.log(`[global-setup] SQLite temp dir: ${tmpDir}`);

	const databaseUrl = `sqlite+aiosqlite:///${tmpDir}/test.db`;

	// 3. Set env vars (inherited by Vite dev server child process)
	process.env.VITE_API_URL = `http://localhost:${backendPort}/api/v1`;
	process.env.VITE_WS_URL = `ws://localhost:${backendPort}/ws`;

	// 4. Spawn uvicorn
	const uvicornEnv: NodeJS.ProcessEnv = {
		...process.env,
		DATABASE_URL: databaseUrl,
		STUB_SERVICES: "true",
		CORS_ORIGINS: '["*"]',
		ANTHROPIC_API_KEY: "sk-fake",
		TEXT_PROVIDER: "fake",
		IMAGE_PROVIDER: "fake",
		VIDEO_PROVIDER: "fake",
		REDIS_URL: "redis://localhost:6379/0",
		WEB_CONCURRENCY: "1",
	};

	console.log("[global-setup] Starting uvicorn...");
	const uvicorn: ChildProcess = spawn(uvBin, ["run", "uvicorn", "app.main:app", "--port", String(backendPort)], {
		cwd: BACKEND_DIR,
		env: uvicornEnv,
		stdio: "pipe",
	});

	// Pipe uvicorn stdout/stderr for debugging
	uvicorn.stdout?.on("data", (chunk: Buffer) => {
		process.stdout.write(`[uvicorn] ${chunk.toString()}`);
	});
	uvicorn.stderr?.on("data", (chunk: Buffer) => {
		process.stderr.write(`[uvicorn:err] ${chunk.toString()}`);
	});

	uvicorn.on("error", (err) => {
		console.error("[global-setup] uvicorn process error:", err);
	});

	// 5. Wait for health endpoint
	const healthUrl = `http://localhost:${backendPort}/health`;
	console.log(`[global-setup] Waiting for ${healthUrl}...`);
	await waitForHealth(healthUrl);
	console.log("[global-setup] Health check passed.");

	// 6. Run alembic
	console.log("[global-setup] Running alembic upgrade head...");
	await runAlembic(uvicornEnv);
	console.log("[global-setup] Alembic migrations applied.");

	// 7. Create seed project
	console.log("[global-setup] Creating seed project...");
	const seedProjectId = await createSeedProject(backendPort);
	console.log(`[global-setup] Seed project created with ID: ${seedProjectId}`);

	// 8. Write state to .e2e-state.json
	const state = {
		backendPort,
		seedProjectId,
		tmpDir,
		pid: uvicorn.pid,
	};
	fs.writeFileSync(STATE_FILE, JSON.stringify(state, null, 2), "utf-8");
	console.log(`[global-setup] State written to ${STATE_FILE}`);

	// Store uvicorn reference for teardown
	(globalThis as Record<string, unknown>).__uvicornProcess = uvicorn;

	console.log("[global-setup] Done.");
}

export default globalSetup;
