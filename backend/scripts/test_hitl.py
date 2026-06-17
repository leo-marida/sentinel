"""
End-to-end HITL test: polls until awaiting_approval, approves all findings,
then polls until complete. Run with the scan_id as argument:
    .venv\Scripts\python scripts/test_hitl.py <scan_id>
"""
import sys
import time

import httpx

BASE = "http://localhost:8000/api/v1"

def poll_scan(scan_id: str, target_status: str, timeout: int = 180) -> dict:
    print(f"Waiting for status: {target_status} ...")
    deadline = time.time() + timeout
    while time.time() < deadline:
        r = httpx.get(f"{BASE}/scans/{scan_id}", timeout=30)
        scan = r.json()
        status = scan["status"]
        print(f"  status: {status}")
        if status == target_status:
            return scan
        if status == "failed":
            print(f"  ERROR: {scan.get('error_message')}")
            sys.exit(1)
        time.sleep(5)
    print(f"Timed out waiting for {target_status}")
    sys.exit(1)

def main():
    scan_id = sys.argv[1] if len(sys.argv) > 1 else None
    if not scan_id:
        print("Usage: python scripts/test_hitl.py <scan_id>")
        sys.exit(1)

    # Wait for scan to reach awaiting_approval
    scan = poll_scan(scan_id, "awaiting_approval")
    print(f"\nScan ready: {scan['summary']}")

    # Fetch findings
    findings = httpx.get(f"{BASE}/scans/{scan_id}/findings", timeout=30).json()
    print(f"Found {len(findings)} findings:")
    for f in findings:
        print(f"  [{f['severity']}] {f['title']} — {f['file_path']}")

    if not findings:
        print("No findings to approve.")
        sys.exit(0)

    # Approve all findings
    decisions = [{"finding_id": f["id"], "decision": "approved"} for f in findings]
    print(f"\nApproving all {len(decisions)} findings ...")
    r = httpx.post(f"{BASE}/scans/{scan_id}/approve", json={"decisions": decisions}, timeout=30)
    print(f"Approval response: {r.json()}")

    # Wait for complete
    scan = poll_scan(scan_id, "complete", timeout=120)
    print("\nScan complete!")
    print(f"Summary: {scan['summary']}")

if __name__ == "__main__":
    main()