import Link from "next/link";
import { ShieldHalf } from "lucide-react";
import { Button } from "@/components/ui/button";

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-50 border-b border-border/60 bg-background/80 backdrop-blur-md">
      <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-4 sm:px-6">
        <Link href="/" className="flex items-center gap-2 font-semibold tracking-tight">
          <span className="flex size-7 items-center justify-center rounded-md bg-primary/15 text-primary">
            <ShieldHalf className="size-4" />
          </span>
          <span>
            Sentinel
            <span className="ml-1.5 hidden text-xs font-normal text-muted-foreground sm:inline">
              DevSecOps Copilot
            </span>
          </span>
        </Link>
        <nav className="flex items-center gap-2">
          <Button asChild variant="ghost" size="sm">
            <Link href="/dashboard">Dashboard</Link>
          </Button>
          <Button asChild size="sm">
            <Link href="/">New Scan</Link>
          </Button>
        </nav>
      </div>
    </header>
  );
}
