/** Per-role and per-collection presentation. Display only - never authorisation. */

export interface RoleStyle {
  label: string;
  chip: string;
  dot: string;
}

export const ROLE_STYLES: Record<string, RoleStyle> = {
  doctor: {
    label: "Doctor",
    chip: "bg-blue-50 text-blue-800 ring-blue-200",
    dot: "bg-blue-500",
  },
  nurse: {
    label: "Nurse",
    chip: "bg-emerald-50 text-emerald-800 ring-emerald-200",
    dot: "bg-emerald-500",
  },
  billing_executive: {
    label: "Billing Executive",
    chip: "bg-amber-50 text-amber-900 ring-amber-200",
    dot: "bg-amber-500",
  },
  technician: {
    label: "Technician",
    chip: "bg-violet-50 text-violet-800 ring-violet-200",
    dot: "bg-violet-500",
  },
  admin: {
    label: "Admin",
    chip: "bg-rose-50 text-rose-800 ring-rose-200",
    dot: "bg-rose-500",
  },
};

export function roleStyle(role: string): RoleStyle {
  return (
    ROLE_STYLES[role] ?? {
      label: role,
      chip: "bg-slate-100 text-slate-700 ring-slate-200",
      dot: "bg-slate-400",
    }
  );
}

export const COLLECTION_STYLES: Record<string, string> = {
  general: "bg-slate-100 text-slate-700 ring-slate-300",
  clinical: "bg-blue-50 text-blue-800 ring-blue-200",
  nursing: "bg-emerald-50 text-emerald-800 ring-emerald-200",
  billing: "bg-amber-50 text-amber-900 ring-amber-200",
  equipment: "bg-violet-50 text-violet-800 ring-violet-200",
};

export function collectionStyle(collection: string): string {
  return COLLECTION_STYLES[collection] ?? "bg-slate-100 text-slate-700 ring-slate-300";
}

export interface DemoAccount {
  username: string;
  password: string;
  role: string;
  blurb: string;
}

/** The five demo accounts, one per role. Published in the README. */
export const DEMO_ACCOUNTS: DemoAccount[] = [
  { username: "dr.mehta", password: "doctor", role: "doctor", blurb: "clinical + nursing + general" },
  { username: "nurse.priya", password: "nurse", role: "nurse", blurb: "nursing + general" },
  { username: "billing.ravi", password: "billing", role: "billing_executive", blurb: "billing + general, SQL analytics" },
  { username: "tech.anand", password: "technician", role: "technician", blurb: "equipment + general" },
  { username: "admin.sys", password: "admin", role: "admin", blurb: "everything, SQL analytics" },
];
