import {test, expect, type Page} from "@playwright/test";
import {mockWorkspace} from "./workspace-fixtures";

const id="73a0d020-602d-49bf-8ef5-fdf8ab3ff981";
const record={asset_id:id,uploaded_at:"2026-10-12T20:00:00Z",bytes:240000000,preview:{state:"READY",media_url:`/api/assets/${id}/preview/media`,quality:{frame_count:9363,gaps_over_limit:68,irregular_intervals:1403,max_frame_gap_us:333332,precise_gameplay_analysis_approved:false}}};

async function session(page: Page) {
  await page.route("**/api/**", route => {
    const path = new URL(route.request().url()).pathname;
    const data = path === "/api/session" ? {authenticated:true,csrf:"fixture",local_uploads:true}
      : path === "/api/overview" ? {runs:[],events:[],drills:[],assignments:[],plans:[],evaluations:[],practice:[]}
      : path === "/api/match-providers" ? {providers:[]}
      : path === "/api/player-identities" ? {identities:[]}
      : {matches:[],total:0,syncs:[],recordings:[],enabled:false,devices:[]};
    return route.fulfill({json:data});
  });
  await mockWorkspace(page,false);
}

test("private player shows timing limits and paged recorded positions on mobile",async({page})=>{
  await session(page);
  await page.route("**/api/private-recordings",route=>route.fulfill({json:{recordings:[record]}}));
  await page.route(`**/api/assets/${id}/preview/quality?offset=0`,route=>route.fulfill({json:{intervals:[{start_us:3500000,end_us:3833332,gap_us:333332,reason:"FRAME_GAP"}],total:1403,next_offset:100}}));
  await page.setViewportSize({width:390,height:844});await page.goto("/");
  const region=page.getByRole("region",{name:"Private recordings",exact:true});
  await expect(region.getByText("Playback ready",{exact:true})).toBeVisible();
  await expect(region.getByText(/68 large gaps/)).toBeVisible();
  await expect(region.getByText(/Frame-accurate coaching is unapproved/)).toBeVisible();
  await expect(region.locator("video")).toHaveAttribute("src",record.preview.media_url);
  await region.getByRole("button",{name:"Review timing positions"}).click();
  await expect(region.getByText("3.500–3.833 s")).toBeVisible();
  await expect(region.getByRole("button",{name:"Next timing positions"})).toBeVisible();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  await region.screenshot({path:"test-results/private-preview-mobile.png"});
});

test("read failure clears stale private playback and quality",async({page})=>{
  await session(page);let revoked=false;
  await page.route("**/api/private-recordings",route=>revoked?route.fulfill({status:403,json:{error:"revoked"}}):route.fulfill({json:{recordings:[record]}}));
  await page.goto("/");const region=page.getByRole("region",{name:"Private recordings",exact:true});
  await expect(region.locator("video")).toHaveCount(1);revoked=true;
  await expect(region.locator("video")).toHaveCount(0,{timeout:10000});
  await expect(region.getByRole("alert")).toContainText("Playback has been cleared");
});

test("preparation retries keep identity and cancellation immediately removes playback",async({page})=>{
  await session(page);let prepared=false;const keys:string[]=[];
  await page.route("**/api/private-recordings",route=>route.fulfill({json:{recordings:[prepared?record:{...record,preview:{state:"NOT_PREPARED",media_url:null}}]}}));
  await page.route(`**/api/assets/${id}/preview`,async route=>{
    if(route.request().method()==="DELETE"){prepared=false;await route.fulfill({json:{state:"PURGED",media_url:null}});return;}
    keys.push(route.request().postDataJSON().request_id);
    if(keys.length===1)await route.fulfill({status:503,json:{error:"temporary"}});
    else {prepared=true;await route.fulfill({json:record.preview});}
  });
  await page.goto("/");const region=page.getByRole("region",{name:"Private recordings",exact:true});
  await region.getByRole("button",{name:"Prepare playback"}).click();
  await expect(region.getByRole("alert")).toContainText("temporary");
  await region.getByRole("button",{name:"Prepare playback"}).click();
  await expect(region.locator("video")).toHaveCount(1);expect(keys[0]).toBe(keys[1]);
  await region.getByRole("button",{name:"Remove converted playback"}).click();
  await expect(region.locator("video")).toHaveCount(0);
  await expect(region.getByRole("status")).toContainText("original recording remains");
});
