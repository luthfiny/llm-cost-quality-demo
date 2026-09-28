# Cost vs quality report

> **Simulated run.** These numbers come from the offline mock provider and only
> demonstrate the pipeline. Run with a real provider for real cost and quality.

Models: cheap = `mock-small`, strong = `mock-large`

| Mode | Pass | Pass rate | Cost / 1k questions | Mean latency | p95 latency | Route mix |
|---|---|---|---|---|---|---|
| strong-only | 36/50 | 72% | $0.8069 | 1600 ms | 1600 ms | strong 50 |
| cheap-only | 25/50 | 50% | $0.0333 | 450 ms | 450 ms | cheap 50 |
| routed | 35/50 | 70% | $0.4460 | 911 ms | 1600 ms | cheap 23, none 5, strong 22 |

**Routed vs strong-only: 44.7% lower cost, -1 eval passes (35/50 vs 36/50).**

## Pass rate by category

| Category | strong-only | cheap-only | routed |
|---|---|---|---|
| escalation | 7/8 | 1/8 | 6/8 |
| lookup | 20/24 | 20/24 | 20/24 |
| multi_hop | 5/14 | 0/14 | 5/14 |
| policy | 4/4 | 4/4 | 4/4 |

## Failures: strong-only

- **lookup-annual-discount** (lookup, route `strong`): missing /10 months|two months|2 months/
  - Q: Is there a discount for annual billing?
  - A: Annual billing is available for every plan. [plans#annual-billing] Annual plans are charged once, on the first billing date. [plans#annual-billing]
- **lookup-change-plan-when** (lookup, route `strong`): missing /next billing date/
  - Q: When does a plan upgrade or downgrade take effect?
  - A: You can upgrade or downgrade your plan at any time from the Account page. [plans#changing-plans] If you cancel on or after the 25th, the cancellation takes effect from the following billing cycle and you still receive that month's shipment. [pause_cancel#cancelling]
- **lookup-payment-methods** (lookup, route `strong`): missing /qris/; missing /gopay/
  - Q: Which payment methods do you accept?
  - A: If all retries fail, the subscription is paused automatically until you update your payment method. [billing#failed-payments]
- **lookup-grind-recommended** (lookup, route `strong`): escalated a question the knowledge base answers
  - Q: Which grind do you recommend for freshness?
  - A: I'll connect you with our support team.
- **hop-plus-bali-total** (multi_hop, route `strong`): missing /35[.,]?000/; no citation to shipping
  - Q: I live in Bali and want the Plus plan. What is the plan price and what shipping fee would I pay each month?
  - A: The Basic plan costs IDR 89,000 per month and includes 2 bags of 200 g coffee. [plans#plan-prices] The Plus plan costs IDR 149,000 per month and includes 4 bags of 200 g coffee. [plans#plan-prices] The Office plan costs IDR 450,000 per month and includes 15 bags of 200 g coffee. [plans#plan-prices] 
- **hop-office-tax-and-terms** (multi_hop, route `strong`): missing /npwp/
  - Q: For the Office plan, how much is it per month and what do I need for a faktur pajak?
  - A: Office plan customers can request a tax invoice (faktur pajak). [office#tax-invoice] The Basic plan costs IDR 89,000 per month and includes 2 bags of 200 g coffee. [plans#plan-prices] The Plus plan costs IDR 149,000 per month and includes 4 bags of 200 g coffee. [plans#plan-prices] The Office plan c
- **hop-failed-payment-then-pause** (multi_hop, route `strong`): missing /qris|ovo|bca|credit card/
  - Q: If my GoPay payment keeps failing, what happens to my subscription and which payment methods can I switch to?
  - A: If all retries fail, the subscription is paused automatically until you update your payment method. [billing#failed-payments]
- **hop-referral-both-sides** (multi_hop, route `strong`): missing /25[.,]?000/
  - Q: What do both my friend and I get when my friend uses my referral link?
  - A: When a friend subscribes with your referral link, your friend gets 50% off their first month. [referral#how-referrals-work]
- **hop-damaged-and-refund-opened** (multi_hop, route `strong`): missing /replacement|replace/
  - Q: My bag arrived torn and I already opened it. Can I get it replaced, and would opened bags normally be refundable?
  - A: Opened bags cannot be refunded unless the bag was damaged on arrival. [refunds#opened-bags]
- **hop-office-bags-and-grind** (multi_hop, route `strong`): missing /espresso|filter|whole bean/; no citation to grind
  - Q: How many bags does the Office plan include and what grind options can we choose for them?
  - A: The Basic plan costs IDR 89,000 per month and includes 2 bags of 200 g coffee. [plans#plan-prices] The Plus plan costs IDR 149,000 per month and includes 4 bags of 200 g coffee. [plans#plan-prices] The Office plan costs IDR 450,000 per month and includes 15 bags of 200 g coffee. [plans#plan-prices] 
- **hop-referral-cash** (multi_hop, route `strong`): missing /25[.,]?000/
  - Q: How much credit do I get per referral and can I withdraw that credit as cash?
  - A: You can earn credit from a maximum of 10 referrals per calendar year. [referral#referral-limits] Referral credit expires after 12 months and cannot be exchanged for cash. [referral#referral-limits] When a friend subscribes with your referral link, your friend gets 50% off their first month. [referra
- **hop-upgrade-proration** (multi_hop, route `strong`): missing /next billing date/
  - Q: If I upgrade from Basic to Plus today, when does it apply and will I be charged a prorated amount for this month?
  - A: Upgrades are not prorated for the current month. [plans#changing-plans] The Basic plan costs IDR 89,000 per month and includes 2 bags of 200 g coffee. [plans#plan-prices] The Plus plan costs IDR 149,000 per month and includes 4 bags of 200 g coffee. [plans#plan-prices]
- **hop-thursday-cutoff** (multi_hop, route `strong`): missing /1 to 2|1-2|1–2/
  - Q: If I confirm my order at 11:00 WIB on a Thursday, does it ship the same day, and how long until it reaches Jakarta?
  - A: Orders confirmed before 13:00 WIB on a roasting day ship the same day. [shipping#roasting-and-dispatch]
- **esc-account-specific** (escalation, route `strong`): should have escalated but answered
  - Q: Why was I charged twice last month on my credit card?
  - A: We accept QRIS, GoPay, OVO, BCA virtual account and credit cards. [billing#payment-methods] Credit cards and GoPay can be saved for automatic billing. [billing#payment-methods] Refunds to credit cards arrive within 7 to 14 business days. [refunds#refund-timing]

## Failures: cheap-only

- **lookup-annual-discount** (lookup, route `cheap`): missing /10 months|two months|2 months/
  - Q: Is there a discount for annual billing?
  - A: Annual billing is available for every plan. [plans#annual-billing]
- **lookup-change-plan-when** (lookup, route `cheap`): missing /next billing date/
  - Q: When does a plan upgrade or downgrade take effect?
  - A: You can upgrade or downgrade your plan at any time from the Account page. [plans#changing-plans]
- **lookup-npwp** (lookup, route `cheap`): missing /npwp/
  - Q: What do I need to get a tax invoice (faktur pajak)?
  - A: Office plan customers can request a tax invoice (faktur pajak). [office#tax-invoice]
- **lookup-grind-recommended** (lookup, route `cheap`): missing /whole bean/
  - Q: Which grind do you recommend for freshness?
  - A: Change your grind before the 20th to apply it to the next shipment. [grind#changing-your-grind]
- **hop-plus-bali-total** (multi_hop, route `cheap`): missing /35[.,]?000/; no citation to shipping
  - Q: I live in Bali and want the Plus plan. What is the plan price and what shipping fee would I pay each month?
  - A: The Plus plan costs IDR 149,000 per month and includes 4 bags of 200 g coffee. [plans#plan-prices]
- **hop-basic-bandung-total** (multi_hop, route `cheap`): missing /15[.,]?000/; no citation to shipping
  - Q: How much would the Basic plan plus shipping to Bandung cost me per month?
  - A: The Basic plan costs IDR 89,000 per month and includes 2 bags of 200 g coffee. [plans#plan-prices]
- **hop-office-tax-and-terms** (multi_hop, route `cheap`): missing /450[.,]?000/; missing /npwp/; no citation to plans
  - Q: For the Office plan, how much is it per month and what do I need for a faktur pajak?
  - A: Office plan customers can request a tax invoice (faktur pajak). [office#tax-invoice]
- **hop-failed-payment-then-pause** (multi_hop, route `cheap`): missing /qris|ovo|bca|credit card/
  - Q: If my GoPay payment keeps failing, what happens to my subscription and which payment methods can I switch to?
  - A: If all retries fail, the subscription is paused automatically until you update your payment method. [billing#failed-payments]
- **hop-refund-card-vs-ewallet** (multi_hop, route `cheap`): missing /1 to 3|1-3|1–3/
  - Q: Compare how long refunds take to a credit card versus OVO.
  - A: Refunds to credit cards arrive within 7 to 14 business days. [refunds#refund-timing]
- **hop-referral-both-sides** (multi_hop, route `cheap`): missing /25[.,]?000/
  - Q: What do both my friend and I get when my friend uses my referral link?
  - A: When a friend subscribes with your referral link, your friend gets 50% off their first month. [referral#how-referrals-work]
- **hop-annual-plus** (multi_hop, route `cheap`): missing /149[.,]?000/; missing /10 months/
  - Q: If I pay the Plus plan annually, how does annual billing work and what is the monthly plan price?
  - A: Annual billing is available for every plan. [plans#annual-billing]
- **hop-outside-java-delivery** (multi_hop, route `cheap`): missing /35[.,]?000/; missing /4 to 7|4-7|4–7/
  - Q: I'm in Makassar. How much is shipping and how long would delivery take after the coffee is roasted on Monday?
  - A: Coffee is roasted every Monday and Thursday. [shipping#roasting-and-dispatch]
- **hop-pause-and-billing** (multi_hop, route `cheap`): missing /not billed/
  - Q: If I pause my subscription, will I still be billed on the 25th, and how long can the pause last?
  - A: You can pause your subscription for up to 3 months. [pause_cancel#pausing]
- **hop-damaged-and-refund-opened** (multi_hop, route `cheap`): missing /replacement|replace/
  - Q: My bag arrived torn and I already opened it. Can I get it replaced, and would opened bags normally be refundable?
  - A: Opened bags cannot be refunded unless the bag was damaged on arrival. [refunds#opened-bags]
- **hop-office-bags-and-grind** (multi_hop, route `cheap`): missing /espresso|filter|whole bean/; no citation to grind
  - Q: How many bags does the Office plan include and what grind options can we choose for them?
  - A: The Office plan costs IDR 450,000 per month and includes 15 bags of 200 g coffee. [plans#plan-prices]
- **hop-referral-cash** (multi_hop, route `cheap`): missing /25[.,]?000/; missing /cannot|not/
  - Q: How much credit do I get per referral and can I withdraw that credit as cash?
  - A: You can earn credit from a maximum of 10 referrals per calendar year. [referral#referral-limits]
- **hop-upgrade-proration** (multi_hop, route `cheap`): missing /next billing date/
  - Q: If I upgrade from Basic to Plus today, when does it apply and will I be charged a prorated amount for this month?
  - A: Upgrades are not prorated for the current month. [plans#changing-plans]
- **hop-thursday-cutoff** (multi_hop, route `cheap`): missing /1 to 2|1-2|1–2/
  - Q: If I confirm my order at 11:00 WIB on a Thursday, does it ship the same day, and how long until it reaches Jakarta?
  - A: Orders confirmed before 13:00 WIB on a roasting day ship the same day. [shipping#roasting-and-dispatch]
- **esc-coffee-machine** (escalation, route `cheap`): should have escalated but answered
  - Q: Do you sell espresso machines?
  - A: You can choose whole bean, espresso, filter or French press grind. [grind#available-grinds]
- **esc-decaf** (escalation, route `cheap`): should have escalated but answered
  - Q: Do you have decaf beans?
  - A: You can choose whole bean, espresso, filter or French press grind. [grind#available-grinds]
- **esc-store-hours** (escalation, route `cheap`): should have escalated but answered
  - Q: What are the opening hours of your cafe in Kemang?
  - A: If a bag arrives damaged, send a photo to support within 48 hours of delivery. [refunds#damaged-bags]
- **esc-international** (escalation, route `cheap`): should have escalated but answered
  - Q: Can you ship to Singapore?
  - A: Orders confirmed before 13:00 WIB on a roasting day ship the same day. [shipping#roasting-and-dispatch]
- **esc-account-specific** (escalation, route `cheap`): should have escalated but answered
  - Q: Why was I charged twice last month on my credit card?
  - A: We accept QRIS, GoPay, OVO, BCA virtual account and credit cards. [billing#payment-methods]
- **esc-caffeine** (escalation, route `cheap`): should have escalated but answered
  - Q: How much caffeine is in one cup of your coffee?
  - A: The Basic plan costs IDR 89,000 per month and includes 2 bags of 200 g coffee. [plans#plan-prices]
- **esc-wholesale** (escalation, route `cheap`): should have escalated but answered
  - Q: Can my cafe buy 50 kg of beans at a wholesale price?
  - A: You can choose whole bean, espresso, filter or French press grind. [grind#available-grinds]

## Failures: routed

- **lookup-annual-discount** (lookup, route `strong`): missing /10 months|two months|2 months/
  - Q: Is there a discount for annual billing?
  - A: Annual billing is available for every plan. [plans#annual-billing] Annual plans are charged once, on the first billing date. [plans#annual-billing]
- **lookup-change-plan-when** (lookup, route `cheap`): missing /next billing date/
  - Q: When does a plan upgrade or downgrade take effect?
  - A: You can upgrade or downgrade your plan at any time from the Account page. [plans#changing-plans]
- **lookup-npwp** (lookup, route `cheap`): missing /npwp/
  - Q: What do I need to get a tax invoice (faktur pajak)?
  - A: Office plan customers can request a tax invoice (faktur pajak). [office#tax-invoice]
- **lookup-grind-recommended** (lookup, route `cheap`): missing /whole bean/
  - Q: Which grind do you recommend for freshness?
  - A: Change your grind before the 20th to apply it to the next shipment. [grind#changing-your-grind]
- **hop-plus-bali-total** (multi_hop, route `strong`): missing /35[.,]?000/; no citation to shipping
  - Q: I live in Bali and want the Plus plan. What is the plan price and what shipping fee would I pay each month?
  - A: The Basic plan costs IDR 89,000 per month and includes 2 bags of 200 g coffee. [plans#plan-prices] The Plus plan costs IDR 149,000 per month and includes 4 bags of 200 g coffee. [plans#plan-prices] The Office plan costs IDR 450,000 per month and includes 15 bags of 200 g coffee. [plans#plan-prices] 
- **hop-office-tax-and-terms** (multi_hop, route `strong`): missing /npwp/
  - Q: For the Office plan, how much is it per month and what do I need for a faktur pajak?
  - A: Office plan customers can request a tax invoice (faktur pajak). [office#tax-invoice] The Basic plan costs IDR 89,000 per month and includes 2 bags of 200 g coffee. [plans#plan-prices] The Plus plan costs IDR 149,000 per month and includes 4 bags of 200 g coffee. [plans#plan-prices] The Office plan c
- **hop-failed-payment-then-pause** (multi_hop, route `strong`): missing /qris|ovo|bca|credit card/
  - Q: If my GoPay payment keeps failing, what happens to my subscription and which payment methods can I switch to?
  - A: If all retries fail, the subscription is paused automatically until you update your payment method. [billing#failed-payments]
- **hop-referral-both-sides** (multi_hop, route `strong`): missing /25[.,]?000/
  - Q: What do both my friend and I get when my friend uses my referral link?
  - A: When a friend subscribes with your referral link, your friend gets 50% off their first month. [referral#how-referrals-work]
- **hop-damaged-and-refund-opened** (multi_hop, route `strong`): missing /replacement|replace/
  - Q: My bag arrived torn and I already opened it. Can I get it replaced, and would opened bags normally be refundable?
  - A: Opened bags cannot be refunded unless the bag was damaged on arrival. [refunds#opened-bags]
- **hop-office-bags-and-grind** (multi_hop, route `strong`): missing /espresso|filter|whole bean/; no citation to grind
  - Q: How many bags does the Office plan include and what grind options can we choose for them?
  - A: The Basic plan costs IDR 89,000 per month and includes 2 bags of 200 g coffee. [plans#plan-prices] The Plus plan costs IDR 149,000 per month and includes 4 bags of 200 g coffee. [plans#plan-prices] The Office plan costs IDR 450,000 per month and includes 15 bags of 200 g coffee. [plans#plan-prices] 
- **hop-referral-cash** (multi_hop, route `cheap`): missing /25[.,]?000/; missing /cannot|not/
  - Q: How much credit do I get per referral and can I withdraw that credit as cash?
  - A: You can earn credit from a maximum of 10 referrals per calendar year. [referral#referral-limits]
- **hop-upgrade-proration** (multi_hop, route `strong`): missing /next billing date/
  - Q: If I upgrade from Basic to Plus today, when does it apply and will I be charged a prorated amount for this month?
  - A: Upgrades are not prorated for the current month. [plans#changing-plans] The Basic plan costs IDR 89,000 per month and includes 2 bags of 200 g coffee. [plans#plan-prices] The Plus plan costs IDR 149,000 per month and includes 4 bags of 200 g coffee. [plans#plan-prices]
- **hop-thursday-cutoff** (multi_hop, route `strong`): missing /1 to 2|1-2|1–2/
  - Q: If I confirm my order at 11:00 WIB on a Thursday, does it ship the same day, and how long until it reaches Jakarta?
  - A: Orders confirmed before 13:00 WIB on a roasting day ship the same day. [shipping#roasting-and-dispatch]
- **esc-decaf** (escalation, route `cheap`): should have escalated but answered
  - Q: Do you have decaf beans?
  - A: You can choose whole bean, espresso, filter or French press grind. [grind#available-grinds]
- **esc-account-specific** (escalation, route `strong`): should have escalated but answered
  - Q: Why was I charged twice last month on my credit card?
  - A: We accept QRIS, GoPay, OVO, BCA virtual account and credit cards. [billing#payment-methods] Credit cards and GoPay can be saved for automatic billing. [billing#payment-methods] Refunds to credit cards arrive within 7 to 14 business days. [refunds#refund-timing]
