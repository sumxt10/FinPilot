# FinPilot Demonstration Context

This document is a complete explanation of the FinPilot project for the
demonstration, viva, review, or judging session. It assumes the reader has
not seen the code before.

---

## 1. Project identity

**Project:** FinPilot  
**Problem statement:** PS-05: Personal Finance Agent  
**Domain:** FinTech  
**Interface:** Streamlit  
**Architecture:** Deterministic multi-agent financial analysis pipeline with
optional LLM narration, lightweight RAG, MCP tool exposure, and a
Planner-Executor-Reviewer workflow.

FinPilot is not intended to be a passive expense tracker. A traditional
budgeting application usually shows charts after the user asks for them.
FinPilot tries to behave more like a continuous financial wellness advisor:

```text
Financial data
      ↓
Understand transactions
      ↓
Categorize spending
      ↓
Find patterns and anomalies
      ↓
Check budget and financial health
      ↓
Forecast future cash flow
      ↓
Recommend measurable actions
      ↓
Create proactive alerts
      ↓
Show evidence and execution trace
```

The system is designed to answer questions such as:

- Where is the user's money going?
- Is a category growing too quickly?
- Is a transaction unusual or duplicated?
- Are subscriptions being paid for but not used?
- Is the user's budget at risk?
- What balance is likely after upcoming recurring payments?
- How much could the user save by changing a behavior?
- Is the user financially ready to increase investment risk?

---

## 2. The problem we are solving

People receive financial data from many sources:

- Bank statements
- Credit card statements
- UPI transaction histories
- Wallet exports
- Investment account records
- CSV files
- JSON bank APIs
- Text-based PDF statements

These sources do not use one consistent format. One source may call a field
`narration`, another `description`, another `merchant`. Dates and amounts may
also appear in different formats. A user therefore has to manually clean the
data before understanding it.

Even after cleaning, a basic finance application may only display:

```text
Food: ₹12,000
Travel: ₹3,000
Shopping: ₹6,000
```

That is descriptive, but not sufficiently helpful. FinPilot attempts to
produce higher-value conclusions:

```text
Food spending is increasing.
An electricity payment is unusually high.
A subscription has been idle for several months.
A duplicate charge may exist.
The next salary and recurring bills affect the projected balance.
Reducing delivery orders could save an estimated amount per year.
```

The core problem is therefore:

> Convert messy personal financial records into explainable, proactive,
> personalized financial wellness actions.

---

## 3. Our solution in one sentence

FinPilot is an autonomous financial wellness agent composed of eleven
specialized agents. It normalizes transaction data, classifies it, analyzes
spending, detects risks, forecasts cash flow, generates advice, and presents
the evidence through a Streamlit dashboard.

---

## 4. What makes the solution agentic?

The word "agent" should not mean only "an LLM that chats." In this project,
an agent is a specialized software role with:

1. A clear responsibility.
2. A defined input.
3. A defined output.
4. A decision or transformation step.
5. A trace entry explaining what happened.

For example, the Anomaly Detection Agent receives normalized and categorized
transactions. It returns possible unusual payments and duplicate charges. It
does not need to know how PDF parsing works, and it does not need to render a
chart.

The Master Orchestrator composes these independent roles in a meaningful
order. That decomposition is more maintainable, testable, and explainable
than putting every responsibility into one large function.

The current agent modules are under:

[`agents/`](C:/Users/Lakshmikant/Downloads/FinPilot/FinPilot/agents)

The public compatibility surface is:

[`agents/__init__.py`](C:/Users/Lakshmikant/Downloads/FinPilot/FinPilot/agents/__init__.py)

Shared constants, RAG, and LLM helpers are in:

[`agents/shared_agent.py`](C:/Users/Lakshmikant/Downloads/FinPilot/FinPilot/agents/shared_agent.py)

The goal planner, life-event simulator, Financial Twin, and investment
readiness tools are implemented in:

[`agents/planning_agent.py`](C:/Users/Lakshmikant/Downloads/FinPilot/FinPilot/agents/planning_agent.py)

---

## 5. The eleven agents

### Agent 1: Financial Data Ingestion Agent

File:

[`ingestion_agent.py`](C:/Users/Lakshmikant/Downloads/FinPilot/FinPilot/agents/ingestion_agent.py)

#### Responsibility

Accept different input formats and convert them into one canonical table.

#### Supported inputs

- Pandas DataFrames
- CSV files
- Lists of transaction dictionaries
- Wrapped JSON objects such as `{"transactions": [...]}`.
- FI-style bank JSON such as `Account → Transactions → Transaction`
- Text-based PDF statements

#### Canonical output

Every valid transaction is converted to fields similar to:

```text
date
merchant
amount
type
```

The amount is converted to a positive numeric value. The direction is stored
in `type`:

```text
debit  = outgoing money
credit = incoming money
```

The ingestion agent also:

- Removes invalid dates and amounts.
- Converts timezone-aware dates to timezone-naive dates.
- Recognizes rupee symbols, commas, debit/credit labels, and negative values.
- Maps alternative column names to standard names.
- Sorts the result by date.

#### Why it matters

All later agents depend on trustworthy normalized data. This is the
preprocessing foundation of the system.

---

### Agent 2: Transaction Categorization Agent

File:

[`categorization_agent.py`](C:/Users/Lakshmikant/Downloads/FinPilot/FinPilot/agents/categorization_agent.py)

#### Responsibility

Assign each transaction to a financial category.

#### Current categories

- Income
- Debt/EMI
- Investments
- Subscriptions
- Bills
- Food & Dining
- Transportation
- Shopping
- Healthcare
- Education
- Others

#### How it works

The agent uses keyword rules and merchant normalization. Examples:

```text
Swiggy       → Food & Dining
Uber         → Transportation
Netflix      → Subscriptions
Zerodha SIP  → Investments
Salary       → Income
House Rent   → Bills
```

Matching is boundary-aware. This is important because a naive substring
search could incorrectly match `jio` inside `ajio`. The current logic
normalizes the merchant and checks complete keyword boundaries.

Credit transactions are treated as income unless a more specific category
applies.

#### Confidence and learning

The agent returns a confidence value. A known keyword match receives high
confidence; an unknown merchant is assigned `Others` with lower confidence.

The UI allows the user to teach the system:

```text
Merchant: unknown merchant
Correct category: Shopping
```

That correction is kept in Streamlit session state and passed back as an
override on the next pipeline run.

---

### Agent 3: Spending Pattern Analysis Agent

File:

[`spending_agent.py`](C:/Users/Lakshmikant/Downloads/FinPilot/FinPilot/agents/spending_agent.py)

#### Responsibility

Convert categorized transactions into time-based spending insights.

#### Outputs

- Monthly category pivot table.
- Increasing category trends.
- Current-month spikes compared with historical behavior.

#### Trend example

If the last three monthly values increase consistently and the total growth
is significant, the agent may produce:

```text
Food & Dining spending is rising from ₹5,000 to ₹8,000.
```

#### Spike example

If the current category value is more than twice its historical average and
the difference is meaningful, the agent reports a spike:

```text
Electricity is ₹4,200 this month versus a usual ₹2,000.
```

These insights feed the Advisor Agent and the Spending screen.

---

### Agent 4: Budget Management Agent

File:

[`budget_agent.py`](C:/Users/Lakshmikant/Downloads/FinPilot/FinPilot/agents/budget_agent.py)

#### Responsibility

Create a budget view from income and spending behavior.

#### Base allocation

The default planning model follows an approximate 50/30/20 split:

```text
Needs   → 50%
Wants   → 30%
Savings → 20%
```

Needs currently include items such as:

- Bills
- Healthcare
- Debt/EMI
- Transportation
- Education

Wants currently include:

- Food & Dining
- Shopping
- Subscriptions
- Others

#### Adaptive category caps

The agent also calculates an adaptive cap from historical spending. The
current approach compares recent spending with a historical baseline and
shows utilization.

The UI may show a category as over 100% utilized. That is intentional: it
means current spending is higher than the calculated target or adaptive cap.

---

### Agent 5: Financial Health Scoring Agent

File:

[`health_agent.py`](C:/Users/Lakshmikant/Downloads/FinPilot/FinPilot/agents/health_agent.py)

#### Responsibility

Produce a financial wellness score from 0 to 100.

#### Score factors

1. Savings rate.
2. Debt ratio.
3. Spending consistency.
4. Emergency-fund coverage.

The maximum contributions are approximately:

```text
Savings rate       → 30 points
Debt ratio         → 20 points
Consistency        → 20 points
Emergency fund     → 30 points
```

#### Important interpretation

This is not a bank-issued credit score. It is an explainable wellness
indicator created for this application. A score of 49 means the rules found
financial improvement opportunities; it does not mean the user is
financially "bad" in every sense.

If there are no debit transactions, the agent safely reports no spending
data rather than inventing a result.

---

### Agent 6: Anomaly Detection Agent

File:

[`anomaly_agent.py`](C:/Users/Lakshmikant/Downloads/FinPilot/FinPilot/agents/anomaly_agent.py)

#### Responsibility

Identify transactions that deserve investigation.

#### Current detections

##### Unusually large transactions

The agent uses a robust comparison based on the median and median absolute
deviation. It looks for transactions that are much larger than comparable
merchant or category history.

Example:

```text
XYZ Trading Unknown — ₹48,000
```

##### Duplicate charges

The agent checks recurring categories such as subscriptions and bills for
the same merchant and amount occurring very close together.

Example:

```text
Netflix charged twice within a few days.
```

#### Important wording

The system says "Potential Fraud / Unusual" or "Duplicate Charge." It does
not claim confirmed fraud. A user must investigate and confirm the result.

---

### Agent 7: Subscription Intelligence Agent

File:

[`subscriptions_agent.py`](C:/Users/Lakshmikant/Downloads/FinPilot/FinPilot/agents/subscriptions_agent.py)

#### Responsibility

Find recurring subscriptions and estimate whether they may be unused.

#### Outputs

For each recurring subscription, it calculates:

- Merchant.
- Typical monthly amount.
- Number of months observed.
- Idle months.
- Estimated annual cost.
- Suggested action: Keep or Cancel.

The synthetic profile contains last-used examples. If a subscription has been
idle for at least three months, the system marks it as potentially unused.

Example:

```text
Spotify — ₹119/month — potentially unused — ₹1,428/year.
```

This supports proactive savings recommendations.

---

### Agent 8: Cash-Flow Forecasting Agent

File:

[`forecast_agent.py`](C:/Users/Lakshmikant/Downloads/FinPilot/FinPilot/agents/forecast_agent.py)

#### Responsibility

Simulate the user's balance day by day for the next 25 days.

#### Inputs

- Current balance.
- Historical recurring debits.
- Historical variable spending.
- Historical income dates and amounts.
- Minimum balance buffer.

#### Outputs

- Current balance.
- Projected minimum balance.
- Projected ending balance.
- Estimated daily variable spend.
- Risk: LOW, MEDIUM, or HIGH.
- A daily balance series for the Forecast chart.

#### Important limitation

This is a transparent rule-based simulation, not a guarantee. It assumes
historical recurring behavior continues and does not know about future events
that are absent from the statement.

---

### Agent 9: Financial Advisor Agent

File:

[`advisor_agent.py`](C:/Users/Lakshmikant/Downloads/FinPilot/FinPilot/agents/advisor_agent.py)

#### Responsibility

Turn analytical results into quantified actions.

Examples:

- Reduce restaurant or delivery orders.
- Set a cap on a rising category.
- Investigate a spending spike.
- Cancel unused subscriptions.
- Build an emergency fund.
- Increase savings rate.

Where possible, each recommendation contains:

```text
title
saving estimate per year
why/evidence
```

The savings figures are estimates based on observed transaction behavior.
They are not promises.

The Advisor Agent does not recommend specific securities or investments.
The investment-readiness feature only determines whether the user's
emergency fund and debt situation suggest readiness to take more risk.

---

### Agent 10: Alert and Notification Agent

File:

[`notifications_agent.py`](C:/Users/Lakshmikant/Downloads/FinPilot/FinPilot/agents/notifications_agent.py)

#### Responsibility

Convert risks into proactive, severity-ranked notifications.

#### Alert types

- Potential fraud or unusual transaction.
- Duplicate charge.
- Budget risk.
- Unused subscription.
- Savings rate below target.
- Cash-flow risk.

#### Severity

Alerts are ranked using:

```text
critical → high → medium → info
```

Each alert includes a suggested delivery channel such as App, Email, or SMS
+ App. In this prototype, the queue is displayed in the UI; it is not
connected to a real SMS or email provider.

---

### Agent 11: Master Orchestrator Agent

File:

[`orchestrator_agent.py`](C:/Users/Lakshmikant/Downloads/FinPilot/FinPilot/agents/orchestrator_agent.py)

#### Responsibility

Coordinate the entire workflow.

The orchestration plan is:

```text
1. Ingest
2. Categorize
3. Analyze spending
4. Plan budget
5. Calculate health
6. Detect anomalies
7. Analyze subscriptions
8. Forecast cash flow
9. Generate advice
10. Create alerts
11. Review recommendations
```

The orchestrator stores the output of every step in a shared state object.
It also records:

- Agent name.
- Status.
- Execution time.
- Short summary of the result.

This trace is displayed in the Agent Trace screen.

#### Reviewer guardrail

The Reviewer checks advice before it reaches the final state. It rejects
advice that has missing reasoning or a negative savings estimate. This is a
simple but important safety layer: the application does not blindly display
every generated recommendation.

---

## 6. Shared state and data flow

The pipeline produces a state object containing values such as:

```text
df
income
balance
spending
budget
health
anomalies
subs
forecast
advice
alerts
review
trace
narrative
```

The dashboard does not independently recalculate every number. It consumes
the orchestrator state so that the charts, metrics, alerts, and advice remain
consistent.

---

## 7. RAG: what it means in FinPilot

RAG means **Retrieval-Augmented Generation**.

The application has a small financial knowledge base:

[`financial_kb.json`](C:/Users/Lakshmikant/Downloads/FinPilot/FinPilot/docs/financial_kb.json)

It contains guidance such as:

- A strong emergency fund covers approximately six months of essential
  expenses.
- A healthy savings rate is around 20% or more.
- Debt payments should remain controlled.
- Unused subscriptions should be reviewed.
- Large one-off or duplicate payments deserve investigation.
- A budget can begin with a 50/30/20 framework.

The RAG process is:

```text
Current financial state
      ↓
Build a query from income, savings rate, emergency cushion,
top category, forecast, and alerts
      ↓
Retrieve matching facts from financial_kb.json
      ↓
Use those facts as grounded context
      ↓
Optional Groq model writes a concise narrative
```

The relevant functions are implemented in
[`shared_agent.py`](C:/Users/Lakshmikant/Downloads/FinPilot/FinPilot/agents/shared_agent.py):

- `load_rag_kb()`
- `retrieve_rag_facts()`
- `build_rag_context()`
- `llm_narrate()`

### Why RAG is useful here

Without grounding, an LLM might give generic or unsupported financial
advice. RAG gives it a controlled set of financial rules and the user's
actual computed metrics.

### What the LLM is and is not responsible for

The optional LLM is used for narration and communication. It does not
calculate the core metrics. The deterministic agents calculate:

- Amounts.
- Scores.
- Forecasts.
- Anomalies.
- Subscription costs.
- Advice savings estimates.

This is a strong point to mention during the demonstration:

> The LLM explains the results, but the financial numbers come from
> deterministic, inspectable agents.

If no Groq API key is present, the system uses a deterministic fallback
narrative and remains fully usable.

---

## 8. MCP: what it means in FinPilot

MCP means **Model Context Protocol**.

In this project, MCP is the tool-access layer. It allows an MCP-compatible
AI client to discover and call FinPilot functionality through structured
JSON-RPC messages.

The implementation is:

[`mcp_server.py`](C:/Users/Lakshmikant/Downloads/FinPilot/FinPilot/mcp_server.py)

### Exposed MCP tools

#### `finpilot_normalize_transactions`

Accepts transaction records and returns canonical:

```text
date, merchant, amount, type
```

#### `finpilot_analyze_transactions`

Runs the financial pipeline and returns a structured result containing:

- Summary.
- Financial health.
- Alerts.
- Advice.
- Agent trace.
- RAG context.

### Architecture with MCP

```text
MCP client or AI model
          ↓
      mcp_server.py
          ↓
    run_pipeline(...)
          ↓
  11 financial agents
          ↓
 structured result
```

MCP is not a replacement for the agents. The agents contain the financial
logic. MCP exposes that logic as tools to another AI system.

The Streamlit app and the MCP server use the same underlying pipeline. This
means the dashboard and an MCP client should receive consistent analysis.

### How to describe MCP to judges

Say:

> MCP standardizes how an external AI client can discover and call our
> finance tools. Instead of hardcoding all capabilities inside one chatbot,
> we expose normalization and analysis as structured tools. The same
> orchestrator powers both the Streamlit dashboard and the MCP interface.

---

## 9. The Streamlit application

The main UI file is:

[`app.py`](C:/Users/Lakshmikant/Downloads/FinPilot/FinPilot/app.py)

The sidebar provides:

- FinPilot branding.
- 11-agent workflow status.
- Data source selection.
- Sample statement mode.
- CSV, JSON, and PDF upload mode.
- Opening balance input for uploaded data.
- Monthly income input for uploaded data.
- Optional Groq configuration guidance.

The current application contains eight main screens/tabs.

---

## 10. Screen-by-screen explanation

### Top area: AI CFO header and coach summary

The top of the page shows:

```text
AI CFO · Personal Finance Agent
Your financial overview
```

The subtitle tells the user:

- How many transactions were normalized.
- The date range.
- That deterministic analysis is grounded by RAG.

The AI Coach Summary displays:

- A concise financial summary.
- Risk level.
- Confidence.
- Up to three recommended actions.

On the right, the user sees:

- Health score.
- Savings rate.
- Emergency cushion.

The "Financial guidance behind this summary" expander shows the retrieved
knowledge-base facts. This is useful evidence that the summary is grounded
and not random.

---

### Screen 1: Overview

The Overview tab is the high-level executive dashboard.

#### Metrics

- Health score.
- Current balance.
- Savings rate.
- Emergency fund coverage.
- Cash-flow risk.
- Active alert count.

#### Charts

- Health score gauge.
- Score breakdown by factor.

#### Alerts

The first five alerts are shown as bordered cards. A typical synthetic-data
demonstration can show:

- An unusual XYZ Trading transaction.
- A duplicate Netflix charge.
- Budget risks.
- Unused subscriptions.
- Savings or cash-flow warnings.

#### What to say

> This screen gives the user an immediate financial health snapshot. It
> combines the outputs of multiple agents instead of presenting only a
> spending chart.

---

### Screen 2: Spending

The Spending tab explains where money is going over time.

#### Monthly spending chart

The chart displays spending by category and month. It helps the user see:

- Food growth.
- Bill growth.
- Shopping changes.
- Transportation patterns.

#### Needs and wants

The screen shows current needs and wants utilization against targets.

#### Category caps

The table shows adaptive category caps, current spend, and utilization.

#### Insights

The Spending Analysis Agent's trend and spike messages are shown below the
tables.

#### What to say

> This is where the application moves from raw transactions to behavior.
> The user can see not only what was spent, but which categories are
> changing and need attention.

---

### Screen 3: Anomalies

The Anomalies tab combines two related capabilities.

#### Anomaly Detection

Each anomaly includes:

- Type.
- Merchant.
- Date.
- Amount.
- Reason.

The important demo wording is:

> The system identifies suspicious or unusual activity for investigation; it
> does not declare confirmed fraud.

#### Subscription Intelligence

The table shows recurring subscriptions, monthly amount, idle months, annual
cost, and suggested action.

The bottom metric estimates annual savings from cancelling subscriptions
marked unused.

#### What to say

> This screen demonstrates proactive protection and savings. The system
> catches both risk, such as duplicate or unusually large payments, and
> waste, such as subscriptions that appear unused.

---

### Screen 4: Forecast

The Forecast tab shows the projected balance for the next 25 days.

#### Chart

The area chart shows the simulated daily balance. A horizontal buffer line
shows the minimum desired balance.

#### Metrics

- Current balance.
- Lowest projected balance.
- Balance after 25 days.

#### Supporting information

The page also displays estimated daily variable spending and explains that
recurring bills and salary are simulated by date.

#### What to say

> This makes the application proactive. Instead of waiting until the
> balance becomes dangerously low, the user can see a projected risk before
> it happens.

#### Limitation to mention if asked

> The forecast is based on historical recurring behavior and is designed as
> an explainable planning estimate, not a guaranteed financial prediction.

---

### Screen 5: Advice

The Advice tab presents action-oriented recommendations.

Each recommendation shows:

- Title.
- Estimated annual saving.
- Evidence or reason.

The page also shows:

- Whether the Reviewer approved the recommendations.
- Total potential annual savings.
- Notification queue.

#### What to say

> The system does not stop at saying "you spent more." It translates the
> pattern into an action and quantifies the potential impact.

Example:

```text
Cut two restaurant or delivery orders per week.
Estimated saving: approximately ₹X/year.
```

---

### Screen 6: Planner

The Planner tab contains advanced decision-support features.

#### Goal-based planning

The user enters:

- Target amount.
- Number of months.
- Amount already saved.

The system calculates:

- Required monthly saving.
- Current surplus.
- Whether the goal is feasible.
- Monthly gap if it is not feasible.

#### Life-event simulation

The user can simulate buying a car by entering:

- Price.
- Down-payment percentage.
- Interest rate.
- Loan duration.

The system calculates:

- EMI.
- Surplus after EMI.
- New savings rate.
- Verdict: Affordable, Risky, or Unaffordable.

#### Financial Twin

The user can simulate:

- Job loss.
- Salary increase.
- New loan.

Examples:

- Job loss produces a runway estimate.
- Salary increase estimates the new savings rate.
- New loan estimates the impact on savings rate.

#### Investment readiness

The readiness check considers emergency fund coverage and debt ratio. It
does not recommend a specific stock, mutual fund, or cryptocurrency.

#### What to say

> The Planner turns FinPilot from a reporting dashboard into a what-if
> decision-support system. A user can test an important life event before
> making the decision.

---

### Screen 7: Agent Trace

The Agent Trace tab is especially important for an academic or judging
demonstration.

It displays:

- Planner entry.
- Each agent.
- Status.
- Execution time in milliseconds.
- A concise result summary.
- Reviewer outcome.

Example trace:

```text
Master Orchestrator (Planner)
1 Data Ingestion
2 Categorization
3 Spending Analysis
4 Budget Management
5 Financial Health
6 Anomaly Detection
7 Subscription Intelligence
8 Cash-Flow Forecast
9 Financial Advisor
10 Alert & Notification
Reviewer (guardrail)
```

#### What to say

> This proves that the dashboard is not one opaque chatbot response. Each
> role ran independently, produced an output, and was recorded for
> observability.

The page also explains that the MCP tools are available through:

```powershell
python mcp_server.py
```

---

### Screen 8: Transactions

The Transactions tab shows the normalized transaction table.

It also provides a human-in-the-loop correction feature:

1. Select a merchant.
2. Select the correct category.
3. Click "Teach agent."

The category override is stored in Streamlit session state and applied when
the pipeline reruns.

#### What to say

> Automation is useful, but the user remains in control. If a merchant was
> incorrectly categorized, the user can correct it and improve the current
> session's analysis.

---

## 11. Synthetic demonstration data

The sample data is generated by:

[`data/generate_data.py`](C:/Users/Lakshmikant/Downloads/FinPilot/FinPilot/data/generate_data.py)

It creates 12 months of synthetic transactions with:

- Increasing salary.
- Rent.
- Loan EMI.
- SIP investment.
- Broadband.
- Subscriptions.
- Increasing electricity bills.
- Growing food spending.
- Fuel and transportation expenses.
- Shopping.
- Healthcare.
- Education.
- Duplicate Netflix charge.
- Suspicious XYZ Trading payment.
- Potentially idle subscriptions.

This is deliberately constructed so the agents have meaningful behavior to
demonstrate.

The generated profile is:

[`data/profile.json`](C:/Users/Lakshmikant/Downloads/FinPilot/FinPilot/data/profile.json)

The generated transactions are:

[`data/transactions.csv`](C:/Users/Lakshmikant/Downloads/FinPilot/FinPilot/data/transactions.csv)

The data is synthetic and should not be presented as real customer data.

---

## 12. How to run the project

Open PowerShell in:

```powershell
cd C:\Users\Lakshmikant\Downloads\FinPilot\FinPilot
```

### Recommended setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

If PowerShell blocks activation:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\.venv\Scripts\Activate.ps1
```

### Generate sample data

```powershell
python data\generate_data.py
```

### Start the dashboard

```powershell
python -m streamlit run app.py
```

Open:

```text
http://localhost:8501
```

### Run tests

```powershell
python -m pytest tests\test_agents.py -q
```

The tests cover:

- Currency string parsing.
- Basic ingestion.
- Wrapped JSON.
- FI-style bank JSON.
- Alternate transaction field names.
- Credit-only statements.
- PDF text parsing.
- Boundary-aware categorization.
- MCP tool listing.
- MCP analysis response shape.

### Run evaluation

```powershell
python evaluation\run_eval.py
```

The evaluation reports categorization accuracy, anomalies, health, forecast
risk, advice, alert count, and trace status.

### Start MCP server

```powershell
python mcp_server.py
```

The MCP server communicates through standard input and output. It is
normally started by an MCP-compatible client rather than opened as a visual
web page.

---

## 13. Suggested demonstration flow

Use the following order during the presentation.

### Step 1: Introduce the problem

Say:

> Bank statements contain transactions, but users need decisions. FinPilot
> converts raw statements into proactive financial wellness insights.

### Step 2: Show the architecture

Explain:

```text
Input → Ingestion → Categorization → Analysis → Risk detection
      → Forecast → Advice → Alerts → Reviewer → Dashboard
```

Mention that each major role is isolated in its own `*_agent.py` file.

### Step 3: Start with the Overview

Point out:

- Health score.
- Current balance.
- Savings rate.
- Emergency cushion.
- Cash-flow risk.
- Active alerts.

### Step 4: Show Spending

Explain the category trends and budget utilization.

### Step 5: Show Anomalies

Use the synthetic data to point out:

- XYZ Trading as an unusual high-value payment.
- Netflix duplicate charge.
- Unused subscriptions.

### Step 6: Show Forecast

Explain how historical recurring payments are projected over the next 25
days.

### Step 7: Show Advice

Point out that advice includes a reason and an estimated annual saving.

### Step 8: Show Planner

Demonstrate a car purchase or savings goal. Change the price or EMI and show
how affordability changes.

### Step 9: Show Agent Trace

Use the trace to prove multi-agent execution and reviewer approval.

### Step 10: Show Transactions and correction

Correct an uncertain merchant category if needed. Explain human-in-the-loop
control.

### Step 11: Explain RAG and MCP

Say:

> RAG grounds the optional narrative in financial knowledge and computed
> user metrics. MCP exposes the same analysis pipeline as discoverable tools
> for an external AI client.

---

## 14. Strong points for judging

### Explainability

Every major result has a source:

- Charts come from normalized transactions.
- Alerts come from anomaly, budget, subscription, health, or forecast rules.
- Advice includes a reason.
- The trace records every agent.
- RAG facts are visible in the UI.

### Deterministic financial calculations

The LLM does not control the main calculations. This reduces hallucination
risk and makes the results reproducible.

### Proactive behavior

Forecasting and alerts attempt to warn users before financial stress occurs.

### Modular architecture

Each role is represented by a dedicated `*_agent.py` module. This supports
testing and future replacement of one implementation without rewriting the
whole system.

### Human-in-the-loop control

Users can correct categories and review recommendations.

### Extensibility

The project can later add:

- Real bank APIs.
- More robust PDF/OCR ingestion.
- A vector database for larger RAG knowledge bases.
- Real notification channels.
- User authentication.
- Persistent user profiles.
- Model-based categorization.
- More sophisticated time-series forecasting.

---

## 15. What is intentionally not claimed

Be accurate during the demonstration.

FinPilot currently does **not**:

- Connect to a real bank account.
- Confirm fraud.
- Send real SMS or email notifications.
- Guarantee forecast accuracy.
- Provide regulated investment advice.
- Replace a financial planner.
- Store multi-user profiles in a production database.
- Perform OCR on image-only PDFs.
- Guarantee that every merchant name is categorized correctly.

The correct phrasing is:

```text
potential fraud
possible duplicate
estimated saving
projected balance
rule-based wellness score
```

---

## 16. Likely judge questions and answers

### Why multiple agents instead of one large agent?

Each financial responsibility has different inputs, logic, and validation
needs. Separate agents make the system modular, traceable, testable, and
easier to improve.

### Is this really AI if much of it is rule-based?

Yes, because the system is an intelligent decision pipeline with specialized
roles, context retrieval, planning, tool use, and generated explanations.
The financial calculations are intentionally deterministic for safety and
reproducibility. The optional LLM is used for grounded narration, not for
inventing financial numbers.

### Where is the RAG?

RAG is implemented through the financial knowledge base in
`docs/financial_kb.json`. The current financial state is used to retrieve
relevant guidance, which is shown in the UI and passed to the optional LLM
narrator.

### Where is MCP?

MCP is implemented in `mcp_server.py`. It exposes normalization and full
analysis as JSON-RPC tools over standard input/output.

### What is the difference between MCP and the agents?

Agents perform the work. MCP exposes that work to an external AI client as
tools.

### How is fraud detected?

The anomaly agent compares transaction amounts against robust merchant or
category history and detects duplicate recurring charges. It flags possible
issues for human investigation; it does not confirm fraud.

### How does the forecast work?

The forecasting agent identifies recurring historical debits, estimates
variable daily spending, detects typical income timing, and simulates the
balance for 25 days.

### How does the system learn?

The current UI supports session-level merchant category overrides. A future
version could persist corrections and train a classifier, but the current
prototype does not claim long-term machine learning from every user action.

### How do you protect API keys?

Keys are stored in local `.env` or Streamlit secrets and excluded by
`.gitignore`. `.env.example` contains only a placeholder. Never commit a
real key.

### Why is the data synthetic?

Synthetic data is safe for demonstrations and intentionally includes trends,
duplicates, subscriptions, and anomalies so every feature can be shown
without exposing personal financial information.

### What happens without the Groq key?

The deterministic pipeline still runs. The dashboard uses a fallback
narrative, so the core features do not depend on an external model.

---

## 17. Security and GitHub checklist

Before pushing:

```powershell
git status
git diff --cached
```

Confirm that these are not staged:

```text
.env
.streamlit/secrets.toml
.venv/
__pycache__/
.pytest_cache/
```

The project includes:

[` .gitignore`](C:/Users/Lakshmikant/Downloads/FinPilot/FinPilot/.gitignore)

and:

[` .env.example`](C:/Users/Lakshmikant/Downloads/FinPilot/FinPilot/.env.example)

If a real credential was ever exposed, revoke it and generate a new one
before publishing the repository.

---

## 18. Final one-minute explanation

Use this if someone asks for a short summary:

> FinPilot is an autonomous personal finance wellness agent for PS-05. It
> accepts bank, UPI, card, CSV, JSON, or text-based PDF transactions and
> normalizes them through a dedicated ingestion agent. Ten more specialized
> agents categorize transactions, analyze spending, manage budgets, score
> financial health, detect anomalies, inspect subscriptions, forecast cash
> flow, generate advice, and create alerts. A master orchestrator coordinates
> them and a reviewer checks the recommendations. The Streamlit dashboard
> exposes the resulting overview, spending patterns, anomalies, forecast,
> advice, planning simulations, transactions, and full execution trace.
> RAG grounds the optional LLM narrative in a financial knowledge base, while
> MCP exposes normalization and analysis as tools to an external AI client.
> The main design principle is that the LLM explains the numbers, but
> deterministic agents calculate and trace them.
