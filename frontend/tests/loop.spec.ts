import { mockWorkspace } from "./workspace-fixtures";
import {test,expect} from "@playwright/test";
const base={runs:[],events:[],assignments:[],plans:[],evaluations:[],practice:[],drills:[{key:"drill/1",status:"DRAFT_REVIEW_REQUIRED",payload:{}}]};
test.beforeEach(async({page})=>{
 await page.route("**/api/session",route=>route.fulfill({json:{authenticated:true,csrf:"fixture",local_uploads:false}}));
 await page.route("**/api/match-providers",route=>route.fulfill({json:{providers:[]}}));
 await page.route("**/api/player-identities",route=>route.fulfill({json:{identities:[]}}));
 await page.route("**/api/matches?*",route=>route.fulfill({json:{matches:[],total:0,next_offset:null,syncs:[]}}));
});
test("capture, evidence and drill gates are visible",async({page})=>{
 await page.route("**/api/overview",route=>route.fulfill({json:base}));await mockWorkspace(page); await page.goto("/");
 await expect(page.getByRole("heading",{name:"02 / Inspect the evidence"})).toBeVisible();
 await expect(page.getByRole("button",{name:"Assign reviewed drill"})).toBeDisabled();
 await expect(page.getByRole("button",{name:"Queue capture"})).toBeDisabled();
 await expect(page.getByText("No adjudicated opportunities.",{exact:false})).toBeVisible();
 await page.screenshot({path:"test-results/workspace.png",fullPage:true});
});
test("uncertainty and unknowns remain visible",async({page})=>{
 const counts={numerator:20,denominator:40,eligible_unknown:4,unknown_eligibility:2,coverage:40/44,rate:.5};
 await page.route("**/api/overview",route=>route.fulfill({json:{...base,evaluations:[{id:"e",revision:1,invalidated_at:null,result:{status:"INCONCLUSIVE",dataset_kind:"synthetic",baseline:counts,followup:counts,verified_practice:40,observed_change:0,change_interval:[-.3,.3],next_action:"Gather independent sessions; do not claim improvement."}}]}}));
 await mockWorkspace(page); await page.goto("/");await expect(page.getByText("INCONCLUSIVE",{exact:true})).toBeVisible();
 await expect(page.getByText("Unknown outcomes: 4; unknown eligibility: 2.")).toHaveCount(2);
 await expect(page.getByText("Gather independent sessions; do not claim improvement.")).toBeVisible();
});
