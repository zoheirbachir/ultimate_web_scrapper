"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { Button } from "@/components/ui";

export function Nav({ email }: { email: string }) {
  const router = useRouter();
  const pathname = usePathname();

  async function signOut() {
    await createClient().auth.signOut();
    router.push("/login");
    router.refresh();
  }

  const navItem = (href: string, label: string) => {
    const active = href === "/dashboard" ? pathname === href : pathname.startsWith(href);
    return (
      <Link
        href={href}
        className={`rounded-lg px-3 py-1.5 text-sm font-medium ${
          active ? "bg-brand-50 text-brand-700" : "text-slate-600 hover:bg-slate-100"
        }`}
      >
        {label}
      </Link>
    );
  };

  return (
    <header className="border-b border-slate-200 bg-white">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
        <div className="flex items-center gap-6">
          <Link href="/dashboard" className="text-lg font-bold text-slate-900">
            Ultimate Scraper
          </Link>
          <nav className="flex items-center gap-1">
            {navItem("/dashboard", "Jobs")}
            {navItem("/dashboard/settings", "Settings")}
          </nav>
        </div>
        <div className="flex items-center gap-3">
          <span className="hidden text-sm text-slate-500 sm:inline">{email}</span>
          <Button variant="secondary" onClick={signOut}>
            Sign out
          </Button>
        </div>
      </div>
    </header>
  );
}
