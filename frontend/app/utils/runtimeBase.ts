const DEV_BACKEND_PORT = "18765";
const LOOPBACK_HOSTS = new Set(["localhost", "127.0.0.1"]);

type BackendTransport = "http" | "ws";

interface ResolveBackendBaseOptions {
  envUrl?: string;
  pageUrl?: string;
  transport: BackendTransport;
  dev: boolean;
}

function getProtocol(transport: BackendTransport, pageProtocol: string): string {
  if (transport === "ws") {
    return pageProtocol === "https:" ? "wss" : "ws";
  }

  return pageProtocol === "https:" ? "https" : "http";
}

function isLoopbackHost(hostname: string): boolean {
  return LOOPBACK_HOSTS.has(hostname);
}

function alignLoopbackUrl(envUrl: string, pageUrl: string): string {
  const resolvedEnvUrl = new URL(envUrl);
  const resolvedPageUrl = new URL(pageUrl);

  if (!isLoopbackHost(resolvedEnvUrl.hostname) || !isLoopbackHost(resolvedPageUrl.hostname)) {
    return envUrl;
  }

  if (resolvedEnvUrl.hostname === resolvedPageUrl.hostname) {
    return envUrl;
  }

  resolvedEnvUrl.hostname = resolvedPageUrl.hostname;
  return resolvedEnvUrl.toString().replace(/\/$/, "");
}

export function resolveBackendBase({ envUrl, pageUrl, transport, dev }: ResolveBackendBaseOptions): string {
  if (envUrl) {
    if (dev && pageUrl) {
      return alignLoopbackUrl(envUrl, pageUrl);
    }

    return envUrl;
  }

  if (dev && pageUrl) {
    const url = new URL(pageUrl);
    const protocol = getProtocol(transport, url.protocol);
    return `${protocol}://${url.hostname}:${DEV_BACKEND_PORT}`;
  }

  return transport === "ws"
    ? `ws://localhost:${DEV_BACKEND_PORT}`
    : `http://localhost:${DEV_BACKEND_PORT}`;
}

export function getApiBase(): string {
  return resolveBackendBase({
    envUrl: import.meta.env.VITE_API_URL,
    pageUrl: typeof window !== "undefined" ? window.location.href : undefined,
    transport: "http",
    dev: import.meta.env.DEV,
  });
}

export function getWsBase(): string {
  return resolveBackendBase({
    envUrl: import.meta.env.VITE_WS_URL,
    pageUrl: typeof window !== "undefined" ? window.location.href : undefined,
    transport: "ws",
    dev: import.meta.env.DEV,
  });
}
