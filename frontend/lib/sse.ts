import { getApiUrl } from "@/lib/api";
import type { ScanEvent } from "@/lib/types";

export function buildStreamUrl(scanId: string): string {
  return `${getApiUrl()}/api/v1/scans/${scanId}/stream`;
}

export function openScanStream(
  scanId: string,
  onEvent: (event: ScanEvent) => void,
  onConnectionError: () => void
): EventSource {
  const es = new EventSource(buildStreamUrl(scanId));

  es.onmessage = (raw) => {
    try {
      const data = JSON.parse(raw.data) as ScanEvent;
      onEvent(data);
    } catch {
      // Ignore malformed frames rather than tearing down the connection.
    }
  };

  es.onerror = () => {
    onConnectionError();
  };

  return es;
}
