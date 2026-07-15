import { ReactNode } from "react";
import { Card } from "@/components/ui";

export function AuthShell({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="mb-6 text-center">
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">Ultimate Scraper</h1>
          <p className="mt-1 text-sm text-slate-500">{title}</p>
        </div>
        <Card>{children}</Card>
      </div>
    </div>
  );
}
