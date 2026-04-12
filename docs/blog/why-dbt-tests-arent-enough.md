# Why dbt Tests Aren't Enough for Data Quality

*Your pipelines are green. Your dashboards are wrong. Here's the gap nobody talks about.*

---

dbt changed how we think about data transformation. Models as code, version-controlled SQL, testable pipelines — it brought software engineering discipline to analytics. And dbt tests were a revelation: `unique`, `not_null`, `accepted_values`, `relationships`. Simple. Declarative. Beautiful.

But if you've been running dbt in production for more than a few months, you've probably felt the limits. Not because dbt tests are bad — they're excellent at what they do. The problem is what they *don't* do.

This post isn't a criticism of dbt. It's about the data quality problems that exist in the spaces between what dbt tests cover. Problems that break your dashboards, corrupt your ML models, and erode stakeholder trust — silently.

## 1. dbt tests are binary. Data quality is a spectrum.

A dbt test either passes or fails. `not_null` on `order_id`? Pass. Done.

But what about this: your `orders` table has a 2% null rate on `shipping_address`. That's expected — some orders are digital. Then one morning it's 15%. No dbt test fired because you never set a threshold. The CEO sees a revenue dashboard that's off by 13% and asks what happened.

The real question isn't "are there nulls?" — it's "are there *more* nulls than usual?"

Data quality lives on a continuum. Row counts fluctuate. Null rates drift. Value distributions shift. You need a system that understands what "normal" looks like for *your* data and alerts you when things deviate — not just when they cross a hardcoded boundary.

## 2. dbt doesn't know what happened yesterday

dbt tests run against the current state of your data. They have no memory. They can't tell you:

- "Row count dropped 40% compared to last Tuesday"
- "This column's cardinality has been declining for 3 weeks"
- "The average order value shifted from $45 to $120 overnight"

These are **temporal anomalies** — they only make sense in the context of historical baselines. A row count of 10,000 might be perfectly normal on a Monday and catastrophic on a Friday.

Without historical comparison, you're flying blind. You catch the data *after* it's broken something downstream. By then, the damage is done — wrong reports went out, wrong decisions were made, wrong models were trained.

## 3. Freshness is a first-class concern (and dbt treats it as an afterthought)

dbt does have `source freshness` checks. Credit where it's due. But in practice:

- They only work on sources, not models
- They require a `loaded_at_field` — which not every table has
- They run separately from your test suite (`dbt source freshness` is a different command)
- There's no built-in way to say "this table should update every 2 hours, alert me if it doesn't"

Freshness is arguably the most critical data quality signal. Stale data is worse than wrong data — at least wrong data is visibly wrong. Stale data *looks* fine. It just quietly stops reflecting reality.

A proper freshness check should be a core part of your quality framework, not a bolt-on that runs in a separate pipeline step.

## 4. Distribution drift is invisible to declarative tests

Here's a scenario that no dbt test catches:

Your `products` table has a `category` column with accepted values: `electronics`, `clothing`, `home`, `food`. dbt's `accepted_values` test passes every day. Green checkmark.

But over the last month, `electronics` went from 40% of rows to 8%. `food` went from 5% to 60%. Your recommendation model — trained on the old distribution — is now serving irrelevant suggestions to 60% of your users.

This is **distribution drift**, and it's one of the most common ways data quality degrades without any test failing. The values are still valid. The proportions are completely wrong.

Catching drift requires statistical tests (Kolmogorov-Smirnov, chi-squared, Jensen-Shannon divergence) that compare current distributions against historical baselines. This is a fundamentally different capability than declarative assertions.

## 5. Volume anomalies need context, not thresholds

You can write a dbt test that checks `row_count > 1000`. But what should the threshold be? It depends on the day of week, the season, whether there was a marketing campaign, whether it's a holiday.

Static thresholds are a trap:

- Set them too tight → constant false alarms → alert fatigue → people ignore them
- Set them too loose → real problems slip through → the test is useless

What you actually want is a system that learns the natural rhythm of your data. One that knows your orders table gets 50k rows on weekdays, 30k on weekends, and 80k during Black Friday — without you manually encoding every pattern.

This is time-series forecasting territory (SARIMA, Prophet, exponential smoothing). It's not something you can express in a YAML test definition, and it shouldn't be. It's a different layer of intelligence entirely.

## 6. Cross-source reconciliation doesn't exist in dbt

"Do the numbers in our PostgreSQL match the numbers in our BigQuery warehouse?"

This is a question that comes up constantly in data teams, and dbt has no answer for it. dbt operates within a single warehouse. It can't reach across to your production database, your CRM, or your payment processor and say "these numbers should match."

Cross-source reconciliation — verifying that row counts, aggregates, or specific records match across systems — is a critical quality check for any team that moves data between environments. ETL pipelines lose rows. Sync jobs silently fail. Incremental loads miss records.

You need something that can connect to multiple sources simultaneously and compare.

## 7. The "everything is fine" problem

Perhaps the most insidious issue: when all your dbt tests pass, you get a false sense of security. The green checkmarks create confidence. And that confidence means you *stop looking*.

But the absence of test failures is not evidence of data quality. It's evidence that the specific things you thought to test are within the specific bounds you defined. That's a much weaker statement.

Real data quality monitoring needs to be proactive — discovering problems you didn't anticipate, surfacing patterns you didn't think to check for, and continuously learning what "normal" looks like as your data evolves.

## So what's the answer?

I'm not suggesting you rip out dbt tests. They're the foundation. `unique`, `not_null`, `accepted_values` — keep all of it. That's your baseline.

But you need additional layers:

**Layer 1: Richer declarative checks.** Beyond the four built-in tests — null percentage thresholds, value range validation, regex pattern matching, custom SQL assertions. Still declarative, still in YAML, but more expressive.

**Layer 2: Statistical anomaly detection.** Time-series forecasting for volume. Distribution comparison for drift. Outlier detection for individual records. These run automatically and learn from your data's history.

**Layer 3: Cross-source validation.** Reconciliation checks that compare data across systems. Row count matching between source and warehouse. Aggregate validation between your app database and your analytics layer.

**Layer 4: Proactive discovery.** AI that explores your data, understands the domain, and suggests checks you haven't thought of. Not replacing human judgment — augmenting it.

Each layer catches what the previous layers miss. Together, they form a complete quality framework.

dbt gave us the discipline. Now we need the depth.

---

*What data quality problems have bitten you that dbt tests didn't catch? I'd love to hear your war stories — find me on [Twitter/X] or in the dbt Slack.*
