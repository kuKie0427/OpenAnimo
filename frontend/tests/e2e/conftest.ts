import { type Page } from "@playwright/test";
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

interface E2EState {
	backendPort: number;
	seedProjectId: number;
	tmpDir: string;
	pid: number;
}

function readState(): E2EState {
	try {
		const raw = readFileSync(path.join(__dirname, ".e2e-state.json"), "utf-8");
		return JSON.parse(raw) as E2EState;
	} catch {
		return { backendPort: 0, seedProjectId: 0, tmpDir: "", pid: 0 };
	}
}

const _state = readState();

export const BACKEND_PORT: number = _state.backendPort;
export const SEED_PROJECT_ID: number = _state.seedProjectId;

interface SeedProjectOptions {
	title?: string;
	story?: string;
	style?: string;
}

export async function seedProject(page: Page, options?: SeedProjectOptions): Promise<number> {
	const resp = await page.request.post(`http://localhost:${BACKEND_PORT}/api/v1/projects`, {
		data: {
			title: options?.title ?? "E2E 测试项目",
			story: options?.story ?? "一只小猫的冒险故事。",
			style: options?.style ?? "anime",
			target_shot_count: 4,
			creation_mode: "story",
		},
	});

	if (!resp.ok) {
		const body = await resp.text();
		throw new Error(`seedProject failed: ${resp.status()} ${resp.statusText()} — ${body}`);
	}

	const body = (await resp.json()) as { id: number };
	return body.id;
}
