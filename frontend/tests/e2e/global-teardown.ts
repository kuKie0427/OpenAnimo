import { type FullConfig } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const STATE_FILE = path.resolve(__dirname, ".e2e-state.json");

interface E2EState {
	backendPort: number;
	seedProjectId: number;
	tmpDir: string;
	pid: number;
}

function readState(): E2EState | null {
	try {
		const raw = fs.readFileSync(STATE_FILE, "utf-8");
		return JSON.parse(raw) as E2EState;
	} catch {
		return null;
	}
}

function killProcess(pid: number): Promise<void> {
	return new Promise((resolve) => {
		try {
			process.kill(pid, "SIGTERM");
		} catch {
			resolve();
			return;
		}

		const deadline = Date.now() + 10_000;
		const check = setInterval(() => {
			try {
				process.kill(pid, 0);
				if (Date.now() > deadline) {
					clearInterval(check);
					try {
						process.kill(pid, "SIGKILL");
					} catch {
						void 0;
					}
					resolve();
				}
			} catch {
				clearInterval(check);
				resolve();
			}
		}, 200);
	});
}

function removeDir(dir: string): void {
	try {
		fs.rmSync(dir, { recursive: true, force: true });
	} catch {
		console.warn(`[global-teardown] Failed to remove temp dir: ${dir}`);
	}
}

async function globalTeardown(_config: FullConfig): Promise<void> {
	const state = readState();
	if (!state) {
		console.warn("[global-teardown] No state file found — skipping teardown.");
		return;
	}

	console.log(`[global-teardown] Killing uvicorn (pid=${state.pid})...`);
	await killProcess(state.pid);
	console.log("[global-teardown] uvicorn terminated.");

	console.log(`[global-teardown] Removing temp dir: ${state.tmpDir}`);
	removeDir(state.tmpDir);

	try {
		fs.unlinkSync(STATE_FILE);
		console.log("[global-teardown] State file removed.");
	} catch {
		void 0;
	}

	console.log("[global-teardown] Done.");
}

export default globalTeardown;
