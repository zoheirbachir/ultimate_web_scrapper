import { NewJobForm } from "@/components/NewJobForm";
import { JobsTable } from "@/components/JobsTable";

export default function DashboardPage() {
  return (
    <div className="space-y-8">
      <div>
        <h2 className="mb-4 text-xl font-semibold text-slate-900">New scraping job</h2>
        <NewJobForm />
      </div>
      <div>
        <h2 className="mb-4 text-xl font-semibold text-slate-900">History</h2>
        <JobsTable />
      </div>
    </div>
  );
}
