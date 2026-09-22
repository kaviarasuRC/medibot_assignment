import { roleStyle } from "@/lib/roles";

export function RoleBadge({ role }: { role: string }) {
  const style = roleStyle(role);
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ring-inset ${style.chip}`}
      title={`Signed in as ${style.label}. This role is decoded from your token on every request.`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${style.dot}`} />
      {style.label}
    </span>
  );
}
