# Groww Product Pulse Log

Shared notes doc. Entries are appended by the MCP `append_to_notes` tool after human approval.

---

## Weekly Product Pulse: 2026-11-26

**Top themes:** App performance & trading reliability; Customer support responsiveness; Charges & fee transparency

**Identified fee issue:** Brokerage & per-order charges on stock trades (incl. DP charges on selling): 89 reviews mention it, 10 explicitly say the charges were unclear or unexpected.

### Weekly pulse

#### Groww Weekly Product Pulse: 19 Nov 2026 to 25 Nov 2026
Source: 11,088 Play Store reviews, 3 Sep 2026 to 25 Nov 2026 (2,734 detailed enough to theme).

##### Top themes
1. **App performance & trading reliability**: 175 critical reviews, avg 2.26★; 4.6% this week (down from 8.7%).
2. **Customer support responsiveness**: 163 critical reviews, avg 1.49★; 5.6% this week (down from 6.7%).
3. **Charges & fee transparency**: 139 critical reviews, avg 2.48★; 9.7% this week (up from 7.6%).

##### What users say
> "worst app... i thought my mobile was slow.. actually this app is slow for trading.." (1★)

> "Worst customer care service, no reply for last few of my complaints till now" (1★)

> "DEMONIC BROKERAGE OF RS.110.45 DEDUCTED OUT OF RS.230 PROFIT IN GROWW BYST TRADE.. UNREASONABLE" (3★)

##### Key observation
**Charges & fee transparency** is rising fastest (9.7% this week vs 7.6% over 12 weeks). Most-confused fee: **brokerage and per-order charges on stock trades** (89 reviews). Users see the total deduction only after selling and call it hidden charges.

##### Action ideas
1. Set latency budgets for charts and order placement in live markets; show an in-app incident banner.
2. Route money-stuck and failed-order tickets to a priority queue with a published first-response time.
3. Show brokerage, DP charge, taxes and net amount on the sell confirmation screen, not only in the contract note.

### Fee explanation

- Brokerage is charged on every executed order, both buy and sell: ₹20 or 0.1% of the trade value, whichever is lower. If that is below ₹5, the minimum is the lower of ₹5 or 2.5% of the trade value.
- Because brokerage is per order, buying and selling a stock are two separate charges, and several orders in one day can add up to more than ₹20. F&O orders are a flat ₹20 each.
- Selling shares from your demat account adds a DP charge of ₹20 per sell order (₹3.50 depository + ₹16.50 Groww; ₹19.75 for women investors), plus GST. Groww's ₹16.50 part is waived when the sale value is below ₹100.
- The DP charge applies per sell order, not per share: selling the same stock in two separate orders means two DP charges.
- Government and exchange charges are added on top. For delivery trades: STT of 0.1% on buy and sell, stamp duty of 0.015% on buy, exchange transaction charges (0.00297% on NSE), SEBI turnover fee (0.0001%), and 18% GST on brokerage and charges.
- Your contract note lists the exact charges for each trade, and the Brokerage Calculator on Groww's pricing page estimates them before you place an order.

**Sources:** https://groww.in/pricing | https://groww.in/help/stocks,-f&o,-ipo-&-mtf/sx-demat-account/how-much-does-groww-charge-for-stocks-1
