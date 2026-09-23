import { displayTime } from "./workspace-api";

type Plan = { id: string; assignment_id: string; specification?: { baseline_end?: string; followup_start?: string; followup_end?: string; baseline_membership?: unknown[] } };
export default function TrainingJourney({ events, assignments, plans, practice, evaluations, zone }: { events: number; assignments: number; plans: Plan[]; practice: number; evaluations: number; zone: string }) {
  return <section className="wide" aria-labelledby="journey-heading"><h2 id="journey-heading">Your training path</h2>
    <ol className="journey"><li><a href="#evidence">Observe a baseline</a><p>{events} reviewed events available. A weakness needs compatible, reachable opportunities; unknown outcomes do not count as misses.</p></li>
      <li><a href="#practice">Choose an approved drill</a><p>{assignments} assignments. Draft drills stay unavailable until expert approval.</p></li>
      <li><a href="#compare">Freeze the plan before practice</a><p>{plans.length} frozen plans. Include complete baseline captures and predeclare follow-up dates.</p></li>
      <li><a href="#practice">Record and review practice</a><p>{practice} linked attempts. Only verified, compatible outcomes satisfy the frozen requirement.</p></li>
      <li><a href="#compare">Collect later matches and compare</a><p>{evaluations} comparison revisions. Follow the same capture and measurement policy; inconclusive, incompatible and negative results remain visible.</p></li></ol>
    {plans.map(plan => <details key={plan.id}><summary>Frozen plan {plan.id.slice(0, 8)}</summary><p>Baseline opportunities: {plan.specification?.baseline_membership?.length ?? "Unknown"}</p>{(["baseline_end", "followup_start", "followup_end"] as const).map(field => plan.specification?.[field] && <p key={field}>{field.replaceAll("_", " ")}: {displayTime(plan.specification[field]!, zone)}</p>)}</details>)}
  </section>;
}
