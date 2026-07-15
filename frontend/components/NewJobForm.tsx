"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { createJob, type FieldSpec } from "@/lib/api";
import { Button, Card, Input, Label, Textarea } from "@/components/ui";

interface FieldRow {
  name: string;
  selector: string;
  attr: string;
}

export function NewJobForm() {
  const router = useRouter();
  const [urlsText, setUrlsText] = useState("");
  const [mode, setMode] = useState<"auto" | "custom">("auto");
  const [fields, setFields] = useState<FieldRow[]>([{ name: "", selector: "", attr: "" }]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  function updateField(i: number, key: keyof FieldRow, value: string) {
    setFields((fs) => fs.map((f, idx) => (idx === i ? { ...f, [key]: value } : f)));
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    const urls = urlsText
      .split("\n")
      .map((s) => s.trim())
      .filter(Boolean);
    if (urls.length === 0) {
      setError("Add at least one URL (one per line).");
      return;
    }

    let fieldMap: Record<string, FieldSpec> | undefined;
    if (mode === "custom") {
      fieldMap = {};
      for (const f of fields) {
        if (f.name.trim() && f.selector.trim()) {
          fieldMap[f.name.trim()] = {
            selector: f.selector.trim(),
            ...(f.attr.trim() ? { attr: f.attr.trim() } : {}),
          };
        }
      }
      if (Object.keys(fieldMap).length === 0) {
        setError("Custom mode needs at least one field with a name and selector.");
        return;
      }
    }

    setLoading(true);
    try {
      const job = await createJob({ urls, mode, fields: fieldMap });
      router.push(`/dashboard/jobs/${job.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start job");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card>
      <form onSubmit={onSubmit} className="space-y-5">
        <div>
          <Label htmlFor="urls">URLs (one per line)</Label>
          <Textarea
            id="urls"
            rows={5}
            placeholder={"https://example.com/product/1\nhttps://example.com/product/2"}
            value={urlsText}
            onChange={(e) => setUrlsText(e.target.value)}
          />
        </div>

        <div>
          <Label>Extraction mode</Label>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => setMode("auto")}
              className={`rounded-lg border px-3 py-2 text-sm ${
                mode === "auto"
                  ? "border-brand-500 bg-brand-50 text-brand-700"
                  : "border-slate-300 text-slate-600"
              }`}
            >
              Auto (product schema)
            </button>
            <button
              type="button"
              onClick={() => setMode("custom")}
              className={`rounded-lg border px-3 py-2 text-sm ${
                mode === "custom"
                  ? "border-brand-500 bg-brand-50 text-brand-700"
                  : "border-slate-300 text-slate-600"
              }`}
            >
              Custom fields
            </button>
          </div>
        </div>

        {mode === "custom" && (
          <div className="space-y-2">
            <Label>Fields (name → CSS selector → optional attribute)</Label>
            {fields.map((f, i) => (
              <div key={i} className="grid grid-cols-1 gap-2 sm:grid-cols-[1fr_1fr_1fr_auto]">
                <Input
                  placeholder="field name"
                  value={f.name}
                  onChange={(e) => updateField(i, "name", e.target.value)}
                />
                <Input
                  placeholder="CSS selector (e.g. h1.title)"
                  value={f.selector}
                  onChange={(e) => updateField(i, "selector", e.target.value)}
                />
                <Input
                  placeholder="attr (optional, e.g. href)"
                  value={f.attr}
                  onChange={(e) => updateField(i, "attr", e.target.value)}
                />
                <Button
                  type="button"
                  variant="ghost"
                  onClick={() => setFields((fs) => fs.filter((_, idx) => idx !== i))}
                >
                  Remove
                </Button>
              </div>
            ))}
            <Button
              type="button"
              variant="secondary"
              onClick={() => setFields((fs) => [...fs, { name: "", selector: "", attr: "" }])}
            >
              + Add field
            </Button>
          </div>
        )}

        {error && <p className="text-sm text-red-600">{error}</p>}

        <Button type="submit" disabled={loading}>
          {loading ? "Starting…" : "Start scraping"}
        </Button>
      </form>
    </Card>
  );
}
