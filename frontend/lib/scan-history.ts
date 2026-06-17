const STORAGE_KEY = "sentinel:scan-history";
const MAX_ENTRIES = 50;

export interface ScanHistoryEntry {
  scanId: string;
  repoUrl: string;
  repoName: string;
  createdAt: string;
}

export function getScanHistory(): ScanHistoryEntry[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as ScanHistoryEntry[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function addScanToHistory(entry: ScanHistoryEntry): void {
  if (typeof window === "undefined") return;
  const existing = getScanHistory().filter((e) => e.scanId !== entry.scanId);
  const next = [entry, ...existing].slice(0, MAX_ENTRIES);
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
}
