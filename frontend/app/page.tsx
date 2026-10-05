"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import Image from "next/image";
import MatchHistory from "./match-history";
import WorkspaceTools from "./workspace-tools";
import EvidenceBrowser from "./evidence-browser";
import PlayerModel from "./player-model";
import PracticeGuide from "./practice-guide";
import ComparisonGuide from "./comparison-guide";
import TrainingJourney from "./training-journey";
import AccountAccess from "./account-access";
import AccountControls from "./account-controls";
import { useResumableUpload, UploadProgress } from "./resumable-upload";

type Event = {id:string;mode:string;start_us:number;eligibility:string;outcome:string;source_asset_id:string};
type Counts = {numerator:number;denominator:number;eligible_unknown:number;unknown_eligibility:number;coverage:number|null;rate:number|null;credible_interval?:number[]|null;excluded?:number;sessions?:number;eligibility_coverage?:number|null};
type Result = {phase?:string;status:string;dataset_kind:string;baseline:Counts;followup:Counts;verified_practice:number;observed_change:number|null;change_interval:number[]|null;next_action:string};
type Data = {
 event_total?:number;
 recommendations?:{id:string;situation:string;state:string;summary:Counts}[];
 runs:{id:string;asset_id:string;status:string;error_code:string}[];
 events:Event[];
 drills:{key:string;status:string;payload:{title?:string;scenario?:string;response?:string;repetitions?:number}}[];
 assignments:{id:string;drill_id:string;status:string}[];
 plans:{id:string;assignment_id:string}[];
 evaluations:{id:string;revision:number;result:Result;invalidated_at:string|null;available?:boolean;unavailable_reasons?:string[]}[];
 practice:{id:string;attempts:number;available_attempts?:number;summary?:Counts}[];
};
const empty:Data={runs:[],events:[],drills:[],assignments:[],plans:[],evaluations:[],practice:[]};
const percent=(n:number|null|undefined)=>n==null?"—":(n*100).toFixed(1)+"%";
const points=(n:number)=>(n*100).toFixed(1)+" pp";
export default function Home(){
 const [authenticated,setAuthenticated]=useState(false),[csrf,setCsrf]=useState(""),[ready,setReady]=useState(false);
 const [operator,setOperator]=useState(false);
 const [localUploads,setLocalUploads]=useState(false),[data,setData]=useState<Data>(empty),[error,setError]=useState("");
 const [busy,setBusy]=useState(false),[selected,setSelected]=useState<string[]>([]);
 const [assignment,setAssignment]=useState(""),[plan,setPlan]=useState(""),[file,setFile]=useState<File|null>(null);
 const [preview,setPreview]=useState(""),[validPreview,setValidPreview]=useState(false),[consent,setConsent]=useState(false);
 const [sourceKind,setSourceKind]=useState("ranked");
 const [zone,setZone]=useState("UTC"),[reportEvent,setReportEvent]=useState(""),[matchEvidence,setMatchEvidence]=useState("");
 const [removingAsset,setRemovingAsset]=useState<string|null>(null);
 const linkRequests=useRef(new Map<string,string>());
 const planRequests=useRef(new Map<string,string>()),[retention,setRetention]=useState(false);
 const transfer=useResumableUpload(csrf);
 const request=useCallback(async(path:string,method="GET",body?:object|FormData)=>{
  const response=await fetch("/api/"+path,{method,credentials:"same-origin",headers:{"X-CSRFToken":csrf,...(body instanceof FormData?{}:{"Content-Type":"application/json"})},body:body?(body instanceof FormData?body:JSON.stringify(body)):undefined});
  const json=await response.json();
  if(!response.ok)throw new Error(json.error||json.detail||"Request failed");
  return json;
 },[csrf]);
 const refresh=useCallback(async()=>{setData(await request("overview"));},[request]);
 useEffect(()=>{fetch("/api/session").then(r=>r.json()).then(s=>{setAuthenticated(s.authenticated);setCsrf(s.csrf);setLocalUploads(s.local_uploads);setOperator(!!s.operator);setReady(true);}).catch(()=>{setError("Start the local API to connect.");setReady(true);});},[]);
 useEffect(()=>{
  if(!authenticated)return;
  const load=()=>{if(document.visibilityState==="visible")void refresh().catch(e=>setError(e.message));};
  load();const timer=setInterval(load,5000);return()=>clearInterval(timer);
 },[authenticated,refresh]);
 useEffect(()=>()=>{if(preview)URL.revokeObjectURL(preview);},[preview]);
 async function act(work:()=>Promise<void>){setBusy(true);setError("");try{await work();await refresh();}catch(e){setError(e instanceof Error?e.message:"Request failed");}finally{setBusy(false);}}
 async function login(event:React.FormEvent<HTMLFormElement>){
  event.preventDefault();const form=new FormData(event.currentTarget);setError("");
  try{const session=await request("session","POST",Object.fromEntries(form));setCsrf(session.csrf);setAuthenticated(session.authenticated);setLocalUploads(session.local_uploads);setOperator(!!session.operator);}catch(e){setError(e instanceof Error?e.message:"Login failed");}
 }
 function chooseFile(value:File|null){setFile(value);setValidPreview(false);setPreview(value?URL.createObjectURL(value):"");}
 async function upload(event:React.FormEvent<HTMLFormElement>){
  event.preventDefault();const form=new FormData(event.currentTarget);if(!file)return;
  const metadata={game_build:form.get("build"),platform:form.get("platform"),session_id:form.get("session"),played_at:new Date(String(form.get("played"))).toISOString(),source_kind:sourceKind,characters:["jin","jin"],dataset_kind:form.get("dataset_kind")};
  const completed=await transfer.start(file,metadata);if(completed){chooseFile(null);await refresh();}
 }
 const picked=selected;
 return <main className={`player-workspace ${authenticated?"is-authenticated":"is-visitor"}`}>
  {authenticated&&<a className="skip-link" href="#workspace-content">Skip to workspace</a>}
  <header className="site-header">
   <Link href="/" className="brand" aria-label="DojoPulse home"><span className="brand-mark" aria-hidden="true"><svg viewBox="0 0 32 32" fill="none"><path d="M3 17h6l4-10 6 18 4-8h6" stroke="currentColor" strokeWidth="3" strokeLinejoin="round"/></svg></span><span>DOJO<span className="brand-accent">PULSE</span><small>Your training workspace</small></span></Link>
   <nav className="header-nav" aria-label="Main navigation"><a href={authenticated?"#training-path":"#training-method"}>The training loop</a><a href={authenticated?"#workspace-content":"#sign-in"}>Workspace <span aria-hidden="true">↗</span></a></nav>
   <span className="tag prototype-tag">LOCAL RESEARCH PROTOTYPE</span>
  </header>
  <div className="hero">
   <Image className="hero-art" src="/images/dojo-training.webp" alt="" fill sizes="(max-width: 740px) 100vw, 1280px" preload/>
   <div className="hero-shade" aria-hidden="true"/>
   <div className="hero-copy"><div className="eyebrow"><span className="eyebrow-rule" aria-hidden="true"/>Tekken 8 · One measured situation</div><h1>MAKE EVERY<br/>SESSION <span>INTENTIONAL.</span></h1><p>Practice with a question. Return with evidence. Your matches, reviewed moments and next training session, in one place.</p>
    <div className="hero-actions"><a className="button-link" href={authenticated?"#matches":"#sign-in"}>{authenticated?"Review your matches":"Open your workspace"}<span aria-hidden="true">↗</span></a><a className="text-link" href={authenticated?"#capture":"#training-method"}>{authenticated?"Capture guide":"Explore the training loop"}<span aria-hidden="true">→</span></a></div>
    <p className="hero-note">One situation. Measured practice. Honest follow-up.</p>
   </div>
   <div className="hero-caption" aria-hidden="true"><span>THE NEXT ROUND STARTS IN THE LAB</span><span>DOJOPULSE / TRAINING SERIES 01</span></div>
  </div>
  <div className="scope-strip" aria-label="Workspace scope"><div><span>01 / FOCUS</span><strong>Tekken 8 defense</strong></div><div><span>02 / METHOD</span><strong>Capture. Review. Practice.</strong></div><div><span>03 / STANDARD</span><strong>Evidence before conclusions</strong></div></div>
  <div className="notice validation-notice"><span className="notice-symbol" aria-hidden="true">!</span><div><strong>Gameplay validation is pending.</strong> Automated judgments and the draft drill are gated until capture, knowledge and reviewer checks pass.</div></div>
  <div className="method-overview" id="training-method"><div className="method-heading"><span className="eyebrow">A deliberate training loop</span><h2>Less guesswork.<br/> A clearer next session.</h2></div><ol className="method-cards"><li><span className="method-number">01</span><h3>Find the moment</h3><p>Keep the match and its context. Separate reviewed evidence from what is still unknown.</p></li><li><span className="method-number">02</span><h3>Work the response</h3><p>Choose a reviewed drill, freeze your baseline and record repeatable practice.</p></li><li><span className="method-number">03</span><h3>Check the change</h3><p>Return to later matches. Compare the same situation, with uncertainty in view.</p></li></ol></div>
  {error&&<div role="alert" className="notice error">{error}</div>}
  {!ready?<p role="status">Connecting to local API…</p>:!authenticated?
   <div className="access-grid" id="sign-in"><section className="login"><span className="eyebrow">Enter the dojo</span><h2>Open your local workspace</h2><p className="muted">Sign in with your verified local account or an existing development account.</p><form onSubmit={login}><label htmlFor="username">Username</label><input id="username" name="username" autoComplete="username" required/><label htmlFor="password">Password</label><input id="password" name="password" type="password" autoComplete="current-password" required/><button>Sign in</button></form></section><AccountAccess csrf={csrf} authenticated={authenticated}/></div>:
   <><nav className="steps" aria-label="Workspace sections"><a href="#workspace">Setup & account</a><a href="#matches">Player & matches</a><a href="#capture">01 Capture</a><a href="#evidence">02 Observe</a><a href="#diagnosis">Priorities</a><a href="#practice">03 Practice</a><a href="#compare">04 Compare</a><Link href="/pilots">Pilot studies</Link>{operator&&<><Link href="/knowledge">Knowledge review</Link><Link href="/datasets">Datasets</Link><Link href="/recognition">Recognition validation</Link><Link href="/operations">Operations</Link></>}</nav>
   <div className="grid" id="workspace-content" tabIndex={-1}>
    <TrainingJourney events={data.event_total??data.events.length} assignments={data.assignments.length} plans={data.plans} practice={data.practice.reduce((sum,p)=>sum+(p.available_attempts??p.attempts),0)} evaluations={data.evaluations.length} zone={zone}/>
    <MatchHistory csrf={csrf} zone={zone} onEvidence={id=>{setMatchEvidence(id);document.getElementById("evidence")?.scrollIntoView();}}/>
    <section id="capture"><h2>01 / Capture one situation</h2><p>Jin defending against Jin’s u/f+4 is the provisional target. Move identity and the response still require expert verification.</p><ol><li>Record Steam PC, English UI, 1920 × 1080 at constant 60 fps.</li><li>Show HUD, both input histories, frame information and battle status. Capture one continuous match or practice block.</li><li>Keep the source uncut, with no pauses, rewinds or missing overlays. Export SDR H.264 MP4, up to 10 minutes / 512 MiB.</li></ol>
     <form onSubmit={upload}><fieldset disabled={transfer.busy}><label htmlFor="capture-file">Capture file</label><input id="capture-file" type="file" accept="video/mp4" onChange={e=>chooseFile(e.target.files?.[0]??null)}/>
      {preview&&<video controls src={preview} onLoadedMetadata={e=>{const v=e.currentTarget;setValidPreview(v.videoWidth===1920&&v.videoHeight===1080&&v.duration>0&&v.duration<=600&&!!file&&file.size<=536870912);}}/>}
      {file&&<p className="muted">{validPreview?"Basic dimensions and duration accepted. The worker checks encoding and timing.":"Checking preview, or dimensions/duration exceed the capture profile."}</p>}
      <div className="rows"><div><label htmlFor="build">Exact game build</label><input id="build" name="build" placeholder="Read from the game" required/></div><div><label htmlFor="session">Play session ID</label><input id="session" name="session" placeholder="Your recording session" required/></div></div>
      <label htmlFor="played">Original play time (local)</label><input id="played" name="played" type="datetime-local" required/>
      <label htmlFor="capture-platform">Recorded platform</label><select id="capture-platform" name="platform" defaultValue="steam"><option value="steam">Steam PC (current capture profile)</option><option value="synthetic">Synthetic test recording</option><option value="unknown">Unknown (cannot verify knowledge)</option></select>
      <label htmlFor="mode">Recording purpose</label><select id="mode" value={sourceKind} onChange={e=>setSourceKind(e.target.value)}><option value="ranked">Ranked baseline / follow-up</option><option value="practice">Recorded practice</option></select>
      <label htmlFor="capture-kind">Recording content</label><select id="capture-kind" name="dataset_kind" required><option value="">Confirm the content</option><option value="real">Real gameplay</option><option value="synthetic">Synthetic test recording</option></select>
      <label><input type="checkbox" required/>This is one continuous, uncut capture without pauses or rewinds.</label>
      <label><input type="checkbox" checked={consent} onChange={e=>setConsent(e.target.checked)}/>I consent to processing this recording for this study. Model training is separate.</label>
      <button disabled={busy||!localUploads||!validPreview||!consent}>{["Upload paused","Upload interrupted"].includes(transfer.phase)?"Resume upload":"Queue capture"}</button>
      {!localUploads&&<p className="muted">Local operator uploads are disabled in this workspace.</p>}
     </fieldset></form><UploadProgress upload={transfer}/>
    </section>
    <section><h2>Processing & review</h2><p className="muted">Analysis happens in a separate worker. Reviewed evidence appears only after an operator imports adjudicated labels.</p>
     {data.runs.length?data.runs.map(run=><div className="result" key={run.id}><span className="tag">{run.status.replaceAll("_"," ")}</span><p className="muted">Capture {run.asset_id.slice(0,8)}</p>{run.error_code&&<p>{run.error_code}</p>}{["QUEUED","PROCESSING"].includes(run.status)&&<button className="secondary" disabled={busy} onClick={()=>void act(async()=>{await request("runs/"+run.id,"DELETE");})}>Cancel analysis</button>}{removingAsset===run.asset_id?<div><p>Delete this recording and withdraw dependent evidence? Imported match metadata is retained.</p><button disabled={busy} onClick={()=>void act(async()=>{await request("assets/"+run.asset_id,"DELETE");setRemovingAsset(null);setSelected([]);})}>Confirm capture deletion</button><button className="secondary" onClick={()=>setRemovingAsset(null)}>Keep capture</button></div>:<button className="secondary" disabled={busy} onClick={()=>setRemovingAsset(run.asset_id)}>Delete capture</button>}</div>):<p className="empty">No captures yet. Upload a supported recording to begin.</p>}
    </section>
    <EvidenceBrowser key={matchEvidence} csrf={csrf} selected={picked} onSelect={setSelected} zone={zone} onReport={setReportEvent} matchId={matchEvidence} onClearMatch={()=>setMatchEvidence("")}/>
    <PlayerModel csrf={csrf} zone={zone} onEvidence={id=>{setMatchEvidence(id);document.getElementById("evidence")?.scrollIntoView();}} onAssigned={id=>{setAssignment(id);void refresh();document.getElementById("practice")?.scrollIntoView();}}/>
    <section id="practice"><h2>03 / Practice the same response</h2><p>Use the diagnosis above to review the supported situation. Frozen-plan baselines below are evidence snapshots; they do not independently establish a weakness.</p>
     {data.recommendations?.map(r=><div className="result" key={r.id}><h3>Your baseline: {r.state.replaceAll("_"," ").toLowerCase()}</h3><p>{r.state==="INVALIDATED"?"This diagnosis was withdrawn because supporting evidence changed or was deleted.":`${r.summary.numerator} successful responses / ${r.summary.denominator} known eligible outcomes. ${r.summary.eligible_unknown} unknown outcomes; ${r.summary.unknown_eligibility} unknown eligibility.`}</p><p className="muted">{r.situation}. Sparse or incompatible evidence cannot establish a reliable weakness.</p></div>)}
     {data.drills.map(d=><div className="result" key={d.key}><span className="tag">{d.status}</span><h3>{d.payload.title||"Standing block-punish drill"}</h3><p className="muted">Select an assignment to see its independently reviewed native setup and response. Legacy versions need a new reviewed workflow.</p><button disabled={busy||d.status!=="APPROVED"} onClick={()=>void act(async()=>{const a=await request("assignments","POST",{drill_key:d.key});setAssignment(a.id);})}>Assign reviewed drill</button></div>)}
     <label htmlFor="assignment">Drill assignment</label><select id="assignment" value={assignment} onChange={e=>setAssignment(e.target.value)}><option value="">Select an assignment</option>{data.assignments.map(a=><option key={a.id} value={a.id}>{a.drill_id} · {a.status}</option>)}</select>
     {assignment&&<PracticeGuide key={assignment} assignment={assignment} csrf={csrf} zone={zone} revision={JSON.stringify([data.plans,data.practice,data.assignments])} onChanged={()=>void refresh().catch(e=>setError(e.message))}/>}
     <button disabled={busy||!assignment||!picked.length||!data.plans.some(p=>p.assignment_id===assignment)} onClick={()=>void act(async()=>{const key=assignment+":"+[...picked].sort().join(",");if(!linkRequests.current.has(key))linkRequests.current.set(key,crypto.randomUUID());await request("assignments/"+assignment+"/practice","POST",{event_ids:picked,request_id:linkRequests.current.get(key)});setSelected([]);})}>Link selected practice evidence</button>
     {assignment&&!data.plans.some(p=>p.assignment_id===assignment)&&<p className="notice">Freeze a baseline plan for this assignment before linking practice. <a href="#compare">Set up your plan</a>.</p>}
     <p className="muted">Reviewed practice attempts linked: {data.practice.reduce((sum,p)=>sum+(p.available_attempts??p.attempts),0)}. Only verified compatible outcomes satisfy the practice requirement.</p>
     {data.practice.map(p=>p.summary&&<p key={p.id} className="muted">Practice block {p.id.slice(0,8)}: {p.summary.numerator}/{p.summary.denominator} known successes · {percent(p.summary.coverage)} coverage · {p.summary.eligible_unknown} unknown outcomes. {p.summary.credible_interval?"Descriptive 95% interval: "+percent(p.summary.credible_interval[0])+" to "+percent(p.summary.credible_interval[1]):"Uncertainty unavailable until known outcomes exist."}</p>)}
    </section>
    <section id="compare"><h2>04 / Freeze & compare</h2><p className="muted">Freeze the baseline before practice. Later select the follow-up match evidence, then evaluate. At least 40 known opportunities across 5 sessions per period and 40 verified practice attempts are required.</p>
     <form onSubmit={e=>{e.preventDefault();const f=new FormData(e.currentTarget);void act(async()=>{const values={assignment_id:assignment,baseline_ids:picked,baseline_end:new Date(String(f.get("baseline"))).toISOString(),followup_start:new Date(String(f.get("start"))).toISOString(),followup_end:new Date(String(f.get("end"))).toISOString(),schedule:{version:"comparison-schedule/1",expected_followup_sessions:Number(f.get("expected")),retention:retention?{start:new Date(String(f.get("retention_start"))).toISOString(),end:new Date(String(f.get("retention_end"))).toISOString(),expected_sessions:Number(f.get("retention_expected"))}:null}};const hash=JSON.stringify(values);if(!planRequests.current.has(hash))planRequests.current.set(hash,crypto.randomUUID());const p=await request("plans","POST",{...values,request_id:planRequests.current.get(hash)});setPlan(p.id);setSelected([]);});}}>
      <label htmlFor="baseline">Baseline cutoff (local)</label><input id="baseline" name="baseline" type="datetime-local" required/><label htmlFor="start">Follow-up starts after practice</label><input id="start" name="start" type="datetime-local" required/><label htmlFor="end">Follow-up ends</label><input id="end" name="end" type="datetime-local" required/><label htmlFor="followup-expected">Planned follow-up sessions</label><input id="followup-expected" name="expected" type="number" min="5" max="100" defaultValue="5" required/><label><input type="checkbox" checked={retention} onChange={e=>setRetention(e.target.checked)}/>Predeclare a later retention check</label>{retention&&<><label htmlFor="retention-start">Retention starts after follow-up ends</label><input id="retention-start" name="retention_start" type="datetime-local" required/><label htmlFor="retention-end">Retention ends</label><input id="retention-end" name="retention_end" type="datetime-local" required/><label htmlFor="retention-expected">Planned retention sessions</label><input id="retention-expected" name="retention_expected" type="number" min="5" max="100" defaultValue="5" required/></>}<p className="muted">Declare collection before practice. Retention cannot be added to an existing plan; all periods are bounded to one year.</p><button disabled={busy||!assignment||!picked.length}>Freeze selected baseline</button>
     </form>
     <label htmlFor="plan">Evaluation plan</label><select id="plan" value={plan} onChange={e=>setPlan(e.target.value)}><option value="">Select a frozen plan</option>{data.plans.map(p=><option key={p.id} value={p.id}>{p.id.slice(0,8)}</option>)}</select><button disabled={busy||!plan} onClick={()=>void act(async()=>{await request("plans/"+plan+"/evaluate","POST",{event_ids:picked});})}>Evaluate selected follow-up</button>
     {plan&&<ComparisonGuide key={plan} plan={plan} csrf={csrf} zone={zone} revision={JSON.stringify(data.evaluations)} onChanged={()=>void refresh().catch(e=>setError(e.message))}/>}
    </section>
    <section className="wide"><h2>What changed?</h2>{!data.evaluations.length?<p className="empty">No comparison yet. A credible result needs baseline evidence, measured practice and later matches.</p>:data.evaluations.map(ev=><div className="result" key={ev.id}>
     <span className="tag">{(ev.invalidated_at||ev.available===false)?"WITHDRAWN · EVIDENCE DELETED":ev.result.status.replaceAll("_"," ")}</span><p className="muted">Revision {ev.revision} {ev.result.phase==="RETENTION"?"· Retention":"· Follow-up"}{ev.result.dataset_kind==="synthetic"?" · SYNTHETIC SOFTWARE TEST — not gameplay evidence":""}</p>
     {!ev.invalidated_at&&ev.available!==false&&<><div className="rows">{(["baseline","followup"] as const).map(period=>{const c=ev.result[period];return <div key={period}><h3>{period==="baseline"?"Baseline":ev.result.phase==="RETENTION"?"Retention":"Follow-up"}</h3><div className="metric">{c.numerator} / {c.denominator}</div><p>{percent(c.rate)} success · {percent(c.coverage)} outcome coverage</p><p className="muted">Unknown outcomes: {c.eligible_unknown}; unknown eligibility: {c.unknown_eligibility}.</p></div>;})}</div>
     {(["baseline","followup"] as const).map(period=>{const c=ev.result[period];return <p className="muted" key={period}>{period}: eligibility coverage {percent(c.eligibility_coverage)} · excluded {c.excluded??0} · sessions {c.sessions??"—"}. {c.credible_interval?"Descriptive 95% interval: "+percent(c.credible_interval[0])+" to "+percent(c.credible_interval[1]):"Uncertainty unavailable until known outcomes exist."}</p>;})}
     {ev.result.change_interval&&<p>Observed change: {points(ev.result.observed_change??0)}. Uncertainty range: {points(ev.result.change_interval[0])} to {points(ev.result.change_interval[1])}.</p>}
     </>}<p>{(ev.invalidated_at||ev.available===false)?"Evidence is no longer available or collection changed. Re-evaluate before using this historical result.":ev.result.next_action}</p><small>This observational comparison does not establish causation.</small>
    </div>)}</section>
    <WorkspaceTools csrf={csrf} onTimezone={setZone} onDeleted={()=>window.location.reload()} reportEvent={reportEvent}/>
    <AccountControls csrf={csrf}/>
   </div></>}
   {authenticated&&<AccountAccess csrf={csrf} authenticated={authenticated}/>}
   <footer><span className="footer-brand">DOJOPULSE <span>/</span> BUILT FOR THE NEXT SESSION</span><span>Private local research workspace · No automated move judgments · No model-training consent implied</span></footer>
  </main>;
}
