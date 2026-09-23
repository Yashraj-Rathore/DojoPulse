"use client";
import { useCallback, useEffect, useState } from "react";
import MatchHistory from "./match-history";

type Event = {id:string;mode:string;start_us:number;eligibility:string;outcome:string;source_asset_id:string};
type Counts = {numerator:number;denominator:number;eligible_unknown:number;unknown_eligibility:number;coverage:number|null;rate:number|null;credible_interval?:number[]|null;excluded?:number;sessions?:number;eligibility_coverage?:number|null};
type Result = {status:string;dataset_kind:string;baseline:Counts;followup:Counts;verified_practice:number;observed_change:number|null;change_interval:number[]|null;next_action:string};
type Data = {
 runs:{id:string;asset_id:string;status:string;error_code:string}[];
 events:Event[];
 drills:{key:string;status:string;payload:{title?:string;scenario?:string;response?:string;repetitions?:number}}[];
 assignments:{id:string;drill_id:string;status:string}[];
 plans:{id:string;assignment_id:string}[];
 evaluations:{id:string;revision:number;result:Result;invalidated_at:string|null}[];
 practice:{id:string;attempts:number;summary?:Counts}[];
};
const empty:Data={runs:[],events:[],drills:[],assignments:[],plans:[],evaluations:[],practice:[]};
const percent=(n:number|null|undefined)=>n==null?"—":(n*100).toFixed(1)+"%";
const points=(n:number)=>(n*100).toFixed(1)+" pp";
export default function Home(){
 const [authenticated,setAuthenticated]=useState(false),[csrf,setCsrf]=useState(""),[ready,setReady]=useState(false);
 const [localUploads,setLocalUploads]=useState(false),[data,setData]=useState<Data>(empty),[error,setError]=useState("");
 const [busy,setBusy]=useState(false),[selected,setSelected]=useState<string[]>([]);
 const [assignment,setAssignment]=useState(""),[plan,setPlan]=useState(""),[file,setFile]=useState<File|null>(null);
 const [preview,setPreview]=useState(""),[validPreview,setValidPreview]=useState(false),[consent,setConsent]=useState(false);
 const [sourceKind,setSourceKind]=useState("ranked");
 const request=useCallback(async(path:string,method="GET",body?:object|FormData)=>{
  const response=await fetch("/api/"+path,{method,credentials:"same-origin",headers:{"X-CSRFToken":csrf,...(body instanceof FormData?{}:{"Content-Type":"application/json"})},body:body?(body instanceof FormData?body:JSON.stringify(body)):undefined});
  const json=await response.json();
  if(!response.ok)throw new Error(json.error||"Request failed");
  return json;
 },[csrf]);
 const refresh=useCallback(async()=>{setData(await request("overview"));},[request]);
 useEffect(()=>{fetch("/api/session").then(r=>r.json()).then(s=>{setAuthenticated(s.authenticated);setCsrf(s.csrf);setLocalUploads(s.local_uploads);setReady(true);}).catch(()=>{setError("Start the local API to connect.");setReady(true);});},[]);
 useEffect(()=>{
  if(!authenticated)return;
  const load=()=>{if(document.visibilityState==="visible")void refresh().catch(e=>setError(e.message));};
  load();const timer=setInterval(load,5000);return()=>clearInterval(timer);
 },[authenticated,refresh]);
 useEffect(()=>()=>{if(preview)URL.revokeObjectURL(preview);},[preview]);
 async function act(work:()=>Promise<void>){setBusy(true);setError("");try{await work();await refresh();}catch(e){setError(e instanceof Error?e.message:"Request failed");}finally{setBusy(false);}}
 async function login(event:React.FormEvent<HTMLFormElement>){
  event.preventDefault();const form=new FormData(event.currentTarget);setError("");
  try{const session=await request("session","POST",Object.fromEntries(form));setCsrf(session.csrf);setAuthenticated(session.authenticated);setLocalUploads(session.local_uploads);}catch(e){setError(e instanceof Error?e.message:"Login failed");}
 }
 function chooseFile(value:File|null){setFile(value);setValidPreview(false);setPreview(value?URL.createObjectURL(value):"");}
 async function upload(event:React.FormEvent<HTMLFormElement>){
  event.preventDefault();const form=new FormData(event.currentTarget);if(!file)return;
  const metadata={game_build:form.get("build"),session_id:form.get("session"),played_at:new Date(String(form.get("played"))).toISOString(),source_kind:sourceKind,characters:["jin","jin"],overlays_verified:false,build_verified:false};
  const body=new FormData();body.set("file",file);body.set("metadata",JSON.stringify(metadata));body.set("processing_consent","true");
  await act(async()=>{await request("uploads","POST",body);chooseFile(null);});
 }
 const picked=selected.filter(id=>data.events.some(e=>e.id===id));
 return <main>
  <header><span className="brand">Performance Lab<span style={{color:"#809255"}}> /</span></span><span className="tag">LOCAL RESEARCH PROTOTYPE</span></header>
  <div className="intro"><div className="eyebrow">Tekken 8 · One measured situation</div><h1>Practice with a question.<br/>Return with evidence.</h1><p>Observe a defensive response, practice it, and measure the same situation in later matches. An uncertain result is a useful result.</p></div>
  <div className="notice">Gameplay validation is pending. Automated judgments and the draft drill are gated until capture, knowledge and reviewer checks pass.</div>
  {error&&<div role="alert" className="notice error">{error}</div>}
  {!ready?<p>Connecting to local API…</p>:!authenticated?
   <section className="login"><h2>Open your local workspace</h2><p className="muted">Use the operator account created in the development setup.</p><form onSubmit={login}><label htmlFor="username">Username</label><input id="username" name="username" autoComplete="username" required/><label htmlFor="password">Password</label><input id="password" name="password" type="password" autoComplete="current-password" required/><button>Sign in</button></form></section>:
   <><nav className="steps"><a href="#matches">Player & matches</a><a href="#capture">01 Capture</a><a href="#evidence">02 Observe</a><a href="#practice">03 Practice</a><a href="#compare">04 Compare</a></nav>
   <div className="grid">
    <MatchHistory csrf={csrf}/>
    <section id="capture"><h2>01 / Capture one situation</h2><p>Jin defending against Jin’s u/f+4 is the provisional target. Move identity and the response still require expert verification.</p><ol><li>Record Steam PC, English UI, 1920 × 1080 at constant 60 fps.</li><li>Show HUD, both input histories, frame information and battle status. Capture one continuous match or practice block.</li><li>Keep the source uncut, with no pauses, rewinds or missing overlays. Export SDR H.264 MP4, up to 10 minutes / 512 MiB.</li></ol>
     <form onSubmit={upload}><label htmlFor="capture-file">Capture file</label><input id="capture-file" type="file" accept="video/mp4" onChange={e=>chooseFile(e.target.files?.[0]??null)}/>
      {preview&&<video controls src={preview} onLoadedMetadata={e=>{const v=e.currentTarget;setValidPreview(v.videoWidth===1920&&v.videoHeight===1080&&v.duration>0&&v.duration<=600&&!!file&&file.size<=536870912);}}/>}
      {file&&<p className="muted">{validPreview?"Basic dimensions and duration accepted. The worker checks encoding and timing.":"Checking preview, or dimensions/duration exceed the capture profile."}</p>}
      <div className="rows"><div><label htmlFor="build">Exact game build</label><input id="build" name="build" placeholder="Read from the game" required/></div><div><label htmlFor="session">Play session ID</label><input id="session" name="session" placeholder="Your recording session" required/></div></div>
      <label htmlFor="played">Original play time (local)</label><input id="played" name="played" type="datetime-local" required/>
      <label htmlFor="mode">Recording purpose</label><select id="mode" value={sourceKind} onChange={e=>setSourceKind(e.target.value)}><option value="ranked">Ranked baseline / follow-up</option><option value="practice">Recorded practice</option></select>
      <label><input type="checkbox" checked={consent} onChange={e=>setConsent(e.target.checked)}/>I consent to processing this recording for this study. Model training is separate.</label>
      <button disabled={busy||!localUploads||!validPreview||!consent}>Queue capture</button>
      {!localUploads&&<p className="muted">Local operator uploads are disabled in this workspace.</p>}
     </form>
    </section>
    <section><h2>Processing & review</h2><p className="muted">Analysis happens in a separate worker. Reviewed evidence appears only after an operator imports adjudicated labels.</p>
     {data.runs.length?data.runs.map(run=><div className="result" key={run.id}><span className="tag">{run.status.replaceAll("_"," ")}</span><p className="muted">Capture {run.asset_id.slice(0,8)}</p>{run.error_code&&<p>{run.error_code}</p>}<button className="secondary" disabled={busy} onClick={()=>void act(async()=>{await request("assets/"+run.asset_id,"DELETE");})}>Delete capture</button></div>):<p className="empty">No captures yet. Upload a supported recording to begin.</p>}
    </section>
    <section id="evidence" className="wide"><h2>02 / Inspect the evidence</h2><p className="muted">Select all reviewed opportunities from the relevant sessions. Unknown outcomes remain visible and never count as failure. Baseline membership freezes when you create a plan.</p>
     {data.events.length?<div className="scroll"><table><thead><tr><th>Select</th><th>Purpose</th><th>Evidence</th><th>Eligibility</th><th>Outcome</th></tr></thead><tbody>{data.events.map(e=><tr key={e.id}><td><input aria-label={"Select event "+e.id} type="checkbox" checked={picked.includes(e.id)} onChange={v=>setSelected(v.target.checked?[...picked,e.id]:picked.filter(id=>id!==e.id))}/></td><td>{e.mode}</td><td><a href={"/api/assets/"+e.source_asset_id+"/media#t="+e.start_us/1e6} target="_blank" rel="noreferrer">{(e.start_us/1e6).toFixed(2)} s ↗</a></td><td>{e.eligibility}</td><td>{e.outcome}</td></tr>)}</tbody></table></div>:<p className="empty">No adjudicated opportunities. The absence of a detected attack does not establish a missed punish.</p>}
    </section>
    <section id="practice"><h2>03 / Practice the same response</h2><p>Target weakness: failing to convert a verified, reachable block-punish opportunity. Diagnosis requires eligible reviewed evidence.</p>
     {data.drills.map(d=><div className="result" key={d.key}><span className="tag">{d.status}</span><h3>{d.payload.title||"Standing block-punish drill"}</h3><p className="muted">Jin vs Jin · standing · open space · 40 valid attempts. Randomize with a safe non-target alternative. Unobservable attempts remain unknown.</p><button disabled={busy||d.status!=="APPROVED"} onClick={()=>void act(async()=>{const a=await request("assignments","POST",{drill_key:d.key});setAssignment(a.id);})}>Assign reviewed drill</button></div>)}
     <label htmlFor="assignment">Drill assignment</label><select id="assignment" value={assignment} onChange={e=>setAssignment(e.target.value)}><option value="">Select an assignment</option>{data.assignments.map(a=><option key={a.id} value={a.id}>{a.drill_id} · {a.status}</option>)}</select>
     <button disabled={busy||!assignment||!picked.length} onClick={()=>void act(async()=>{await request("assignments/"+assignment+"/practice","POST",{event_ids:picked});setSelected([]);})}>Link selected practice evidence</button>
     <p className="muted">Reviewed practice attempts linked: {data.practice.reduce((sum,p)=>sum+p.attempts,0)}. Only verified compatible outcomes satisfy the practice requirement.</p>
     {data.practice.map(p=>p.summary&&<p key={p.id} className="muted">Practice block {p.id.slice(0,8)}: {p.summary.numerator}/{p.summary.denominator} known successes · {percent(p.summary.coverage)} coverage · {p.summary.eligible_unknown} unknown outcomes. {p.summary.credible_interval?"Descriptive 95% interval: "+percent(p.summary.credible_interval[0])+" to "+percent(p.summary.credible_interval[1]):"Uncertainty unavailable until known outcomes exist."}</p>)}
    </section>
    <section id="compare"><h2>04 / Freeze & compare</h2><p className="muted">Freeze the baseline before practice. Later select the follow-up match evidence, then evaluate. At least 40 known opportunities across 5 sessions per period and 40 verified practice attempts are required.</p>
     <form onSubmit={e=>{e.preventDefault();const f=new FormData(e.currentTarget);void act(async()=>{const p=await request("plans","POST",{assignment_id:assignment,baseline_ids:picked,baseline_end:new Date(String(f.get("baseline"))).toISOString(),followup_start:new Date(String(f.get("start"))).toISOString(),followup_end:new Date(String(f.get("end"))).toISOString()});setPlan(p.id);setSelected([]);});}}>
      <label htmlFor="baseline">Baseline cutoff (local)</label><input id="baseline" name="baseline" type="datetime-local" required/><label htmlFor="start">Follow-up starts after practice</label><input id="start" name="start" type="datetime-local" required/><label htmlFor="end">Follow-up ends</label><input id="end" name="end" type="datetime-local" required/><button disabled={busy||!assignment||!picked.length}>Freeze selected baseline</button>
     </form>
     <label htmlFor="plan">Evaluation plan</label><select id="plan" value={plan} onChange={e=>setPlan(e.target.value)}><option value="">Select a frozen plan</option>{data.plans.map(p=><option key={p.id} value={p.id}>{p.id.slice(0,8)}</option>)}</select><button disabled={busy||!plan} onClick={()=>void act(async()=>{await request("plans/"+plan+"/evaluate","POST",{event_ids:picked});})}>Evaluate selected follow-up</button>
    </section>
    <section className="wide"><h2>What changed?</h2>{!data.evaluations.length?<p className="empty">No comparison yet. A credible result needs baseline evidence, measured practice and later matches.</p>:data.evaluations.map(ev=><div className="result" key={ev.id}>
     <span className="tag">{ev.invalidated_at?"WITHDRAWN · EVIDENCE DELETED":ev.result.status.replaceAll("_"," ")}</span><p className="muted">Revision {ev.revision}{ev.result.dataset_kind==="synthetic"?" · SYNTHETIC SOFTWARE TEST — not gameplay evidence":""}</p>
     <div className="rows">{(["baseline","followup"] as const).map(period=>{const c=ev.result[period];return <div key={period}><h3>{period==="baseline"?"Baseline":"Follow-up"}</h3><div className="metric">{c.numerator} / {c.denominator}</div><p>{percent(c.rate)} success · {percent(c.coverage)} outcome coverage</p><p className="muted">Unknown outcomes: {c.eligible_unknown}; unknown eligibility: {c.unknown_eligibility}.</p></div>;})}</div>
     {(["baseline","followup"] as const).map(period=>{const c=ev.result[period];return <p className="muted" key={period}>{period}: eligibility coverage {percent(c.eligibility_coverage)} · excluded {c.excluded??0} · sessions {c.sessions??"—"}. {c.credible_interval?"Descriptive 95% interval: "+percent(c.credible_interval[0])+" to "+percent(c.credible_interval[1]):"Uncertainty unavailable until known outcomes exist."}</p>;})}
     {ev.result.change_interval&&<p>Observed change: {points(ev.result.observed_change??0)}. Uncertainty range: {points(ev.result.change_interval[0])} to {points(ev.result.change_interval[1])}.</p>}
     <p>{ev.invalidated_at?"A source was deleted. Rebuild a valid comparison before using this result.":ev.result.next_action}</p><small>This observational comparison does not establish causation.</small>
    </div>)}</section>
   </div></>}
   <footer>Private local research workspace · No automated move judgments · No model-training consent implied</footer>
  </main>;
}
