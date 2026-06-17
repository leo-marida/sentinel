"use client";

import { useRouter } from "next/navigation";
import { type FormEvent, useRef, useState } from "react";
import { toast } from "sonner";
import { ArrowRight, Loader2, Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { createScan } from "@/lib/api";
import { addScanToHistory } from "@/lib/scan-history";

const GITHUB_URL_PATTERN = /^https:\/\/github\.com\/[\w.-]+\/[\w.-]+\/?$/;

export function ScanInput() {
  const router = useRouter();
  const [repoUrl, setRepoUrl] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [warmingUp, setWarmingUp] = useState(false);
  const warmupTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const trimmed = repoUrl.trim();
    if (!GITHUB_URL_PATTERN.test(trimmed)) {
      toast.error(
        "Enter a valid GitHub repo URL, e.g. https://github.com/owner/repo"
      );
      return;
    }

    setIsSubmitting(true);
    warmupTimer.current = setTimeout(() => setWarmingUp(true), 4000);

    try {
      const scan = await createScan(trimmed);
      addScanToHistory({
        scanId: scan.scan_id,
        repoUrl: scan.repo_url,
        repoName: scan.repo_name,
        createdAt: new Date().toISOString(),
      });
      router.push(`/dashboard/${scan.scan_id}`);
    } catch (err) {
      toast.error(
        err instanceof Error
          ? err.message
          : "Failed to start scan. Please try again."
      );
    } finally {
      if (warmupTimer.current) clearTimeout(warmupTimer.current);
      setWarmingUp(false);
      setIsSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="w-full max-w-xl">
      <div className="flex flex-col gap-3 sm:flex-row">
        <div className="relative flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={repoUrl}
            onChange={(e) => setRepoUrl(e.target.value)}
            placeholder="https://github.com/owner/repo"
            className="h-11 pl-9"
            disabled={isSubmitting}
            autoComplete="off"
            spellCheck={false}
          />
        </div>
        <Button
          type="submit"
          size="lg"
          className="h-11 gap-2"
          disabled={isSubmitting}
        >
          {isSubmitting ? (
            <Loader2 className="size-4 animate-spin" />
          ) : (
            <ArrowRight className="size-4" />
          )}
          {isSubmitting ? "Starting scan…" : "Scan repository"}
        </Button>
      </div>
      {warmingUp && (
        <p className="mt-2 text-xs text-muted-foreground">
          Waking up the server… first request after idle can take ~30s on the
          free tier.
        </p>
      )}
    </form>
  );
}
