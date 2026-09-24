# ResolveOps: three-minute recruiter demo

## Demo goal

Show one complete, supervised resolution path:

> A simulated checkout deployment causes production-like errors. ResolveOps
> gathers evidence, proposes an exact rollback, enforces human approval,
> executes the change once, verifies recovery, and preserves an audit trail.

The demo should communicate product judgment and safety, not just model output.
Say **simulated** whenever describing the infrastructure or measured outcome.

## Before recording

- Start the Java simulator, Python API, PostgreSQL, and Streamlit dashboard.
- Confirm their health checks pass.
- Confirm the model key is loaded server-side and is not visible in the browser.
- Reset the `bad-deployment` scenario.
- Keep browser zoom near 100% and close unrelated tabs and notifications.
- Have the architecture diagram ready in a second tab.
- Rehearse once and confirm the full timeline fits on screen.
- Do not quote a percentage time saving unless it comes from a completed,
  reproducible evaluation run.

## Timed walkthrough

### 0:00–0:20 — Frame the product

**On screen:** ResolveOps incident queue or landing page.

**Say:**

> ResolveOps is a supervised AI incident-response copilot. It investigates
> synthetic infrastructure incidents and can resolve them through narrow,
> controlled tools. The model provides judgment, but ordinary Python policy
> code owns authorization, approvals, execution, and verification.

Point briefly to the **Simulation** label. This prevents the audience from
mistaking the demonstration for a live production integration.

### 0:20–0:42 — Launch a coherent incident

**Action:** Start **Checkout failures after deployment**.

**On screen:** Critical alert for `checkout-api` in `production`, version
`2.8.1`, with a 16% error rate.

**Say:**

> This scenario resets the Java simulator and introduces a regression after
> release 2.8.1. The alert is stored as an incident, not pasted into a chatbot.
> Its state, evidence, decisions, and actions are durable workflow records.

Call attention to service, environment, severity, start time, and current
status. Avoid explaining every field.

### 0:42–1:18 — Investigate with evidence

**Action:** Select **Investigate** and let the timeline populate.

**On screen:** Health check, recent deployments, logs, dependencies, retrieved
runbook guidance, and a structured diagnosis.

**Say:**

> The agent chooses only from read-only investigation tools. Here it correlates
> the deployment time with the error spike, finds payment-adapter timeouts, and
> confirms the external payment dependency is healthy. It cites those
> observations and distinguishes them from its hypothesis.

> Logs and runbooks are treated as untrusted evidence. Even if a log line tells
> the model to ignore its rules, it cannot grant permission or call a mutation
> endpoint.

Pause on the diagnosis and show that the recommendation is
`rollback_deployment` to exactly `2.8.0`.

### 1:18–1:53 — Show the authority boundary

**On screen:** Pending approval card.

**Say:**

> The model's recommendation is only a proposal. A deterministic policy engine
> validates the tool, service, environment, target version, role, and risk.
> Because this changes a production-like service, execution pauses here.

Point to:

- exact service and environment;
- current and target versions;
- supporting evidence;
- risk and expected effect; and
- approver identity.

**Action:** Approve the rollback.

**Say:**

> This approval is bound to these exact arguments. Changing the target service
> or version would invalidate it.

### 1:53–2:20 — Execute once and verify recovery

**On screen:** Execution result followed by verification checks.

**Say:**

> The Python executor rechecks policy and approval, then calls one narrow Java
> endpoint with an idempotency key. Retrying the same request returns the first
> result instead of rolling back twice.

> A successful API call does not close the incident. ResolveOps checks the
> simulator again and requires the error rate, latency, instance health, and
> deployed version to meet deterministic runbook thresholds.

Show `2.8.0`, healthy status, and the recovered error rate. Then show the
incident state changing to **Resolved**.

### 2:20–2:44 — Prove what happened

**On screen:** Audit timeline.

**Say:**

> Every important transition is recorded: alert receipt, evidence collection,
> proposal, policy decision, approver, exact action, execution result, and
> verification. This makes the workflow reviewable rather than asking an
> operator to trust a confident paragraph.

Scroll just enough to show timestamps and actor types. Do not read every row.

### 2:44–3:00 — Close with scope and engineering signal

**On screen:** Architecture diagram or metrics/evaluation page.

**Say:**

> This portfolio release resolves repeatable incidents in an isolated
> simulator; it is not connected to real infrastructure. The engineering value
> is the control system around the model: typed tools, least privilege,
> exact-action approvals, idempotent execution, deterministic verification, and
> traceable evaluation. The same interfaces could later be adapted to approved
> observability and deployment platforms after a separate production security
> review.

Stop there. Do not dilute the ending with a tour of every technology used.

## Optional 30-second security follow-up

If the interviewer asks how unsafe content is handled:

1. Launch or open the prompt-injection evaluation case.
2. Show a log entry containing a fake instruction to approve a rollback.
3. Show that the text is retained as evidence but no action is authorized.
4. Explain that the model never receives mutation tools and approval state comes
   from the database, not the prompt.

## Optional 30-second uncertainty follow-up

If the interviewer asks about hallucinations:

1. Launch `ambiguous-login`.
2. Show the conflicting provider, deployment, and database evidence.
3. Show the expected decision: `gather_more_evidence`.
4. Explain that safe abstention is a tested product behavior, not a failure of
   the demo.

## Likely questions and concise answers

### “Is the AI actually fixing something?”

Yes—the approved tool changes Java simulator state, and the Python verifier
checks that state afterward. It does not touch real infrastructure.

### “Why not let the model execute directly?”

Model output is probabilistic and can be influenced by untrusted evidence.
Authorization and side effects therefore stay behind deterministic policy and
an exact-action approval gate.

### “Why use Java as well as Python?”

Python owns the AI workflow and policy layer. Java represents a separate
operated system with an explicit HTTP contract, making the trust boundary and
integration behavior visible while demonstrating work across both ecosystems.

### “Why is this more than a chatbot?”

It maintains incident state, selects tools, gathers evidence, pauses and resumes
around approval, executes an idempotent action, verifies an outcome, and emits a
complete audit timeline.

### “Where does the claimed business impact come from?”

The repository reports simulator evaluation results only. Any time-saving claim
must compare manual and assisted runs on the same synthetic cases, with the
sample size and method disclosed. It is not presented as production ROI.

## Recording notes

- Keep the cursor still while explaining evidence.
- Prefer one polished path over rapidly opening every page.
- If a model or network request fails, explain the failed state honestly; do not
  edit the recording to imply a successful live decision.
- Never expose `.env`, headers, terminal history, API keys, or database passwords.
- Caption the recording and include the simulator disclaimer in the video
  description.
