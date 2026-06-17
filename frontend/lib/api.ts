import type {
  ApprovalDecision,
  ApprovalResponse,
  CreateScanResponse,
  Finding,
  Scan,
} from "@/lib/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function parseError(res: Response): Promise<string> {
  try {
    const body = await res.json();
    return body?.detail ?? `Request failed with status ${res.status}`;
  } catch {
    return `Request failed with status ${res.status}`;
  }
}

interface RequestOptions extends RequestInit {
  retries?: number;
  retryDelayMs?: number;
}

/**
 * Render's free tier spins down after 15min idle and takes ~30s to cold-start;
 * Supabase free tier pauses after 7 days. Both surface as network failures or
 * 502/503 on the first request, so retry with backoff before surfacing an error.
 */
async function request<T>(path: string, opts: RequestOptions = {}): Promise<T> {
  const { retries = 3, retryDelayMs = 4000, ...init } = opts;

  let lastError: unknown;
  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      const res = await fetch(`${API_URL}${path}`, {
        ...init,
        headers: {
          "Content-Type": "application/json",
          ...init.headers,
        },
      });

      if (!res.ok) {
        if ((res.status === 502 || res.status === 503) && attempt < retries) {
          await new Promise((r) => setTimeout(r, retryDelayMs));
          continue;
        }
        throw new ApiError(await parseError(res), res.status);
      }

      if (res.status === 204) return undefined as T;
      return (await res.json()) as T;
    } catch (err) {
      lastError = err;
      if (err instanceof ApiError) throw err;
      if (attempt < retries) {
        await new Promise((r) => setTimeout(r, retryDelayMs));
        continue;
      }
    }
  }
  throw lastError instanceof Error
    ? lastError
    : new Error("Network request failed");
}

export function checkHealth(): Promise<{ status: string }> {
  return request("/health", { retries: 0 });
}

export function createScan(repoUrl: string): Promise<CreateScanResponse> {
  return request("/api/v1/scans", {
    method: "POST",
    body: JSON.stringify({ repo_url: repoUrl }),
  });
}

export function getScan(scanId: string): Promise<Scan> {
  return request(`/api/v1/scans/${scanId}`, { retries: 1 });
}

export function getScanFindings(scanId: string): Promise<Finding[]> {
  return request(`/api/v1/scans/${scanId}/findings`, { retries: 1 });
}

export function submitApproval(
  scanId: string,
  decisions: ApprovalDecision[]
): Promise<ApprovalResponse> {
  return request(`/api/v1/scans/${scanId}/approve`, {
    method: "POST",
    retries: 1,
    body: JSON.stringify({ decisions }),
  });
}

export function getApiUrl(): string {
  return API_URL;
}
