"""Synthetic bank-statement generator with a much larger 12-month dataset and richer anomalies."""
import random, json, os, datetime as dt
import pandas as pd


def make(out="data"):
    random.seed(7)
    os.makedirs(out, exist_ok=True)
    rows = []

    def add(d, m, a, t="debit", true="Others"):
        rows.append(dict(date=d, description=m, amount=a, type=t, true_category=true))

    months = list(range(1, 13))
    for i, mo in enumerate(months):
        D = lambda d: dt.date(2026, mo, d)
        base_salary = 50000 + (i * 3000)
        add(D(1), "Salary - ACME Corp", base_salary, "credit", "Income")
        add(D(3), "House Rent", 15000, "debit", "Bills")
        add(D(5), "Car Loan EMI", 5000, "debit", "Debt/EMI")
        add(D(6), "Zerodha SIP", 5000, "debit", "Investments")
        add(D(7), "Jio Broadband", 999, "debit", "Bills")
        add(D(8), "Netflix", 649, "debit", "Subscriptions")
        add(D(9), "Spotify", 119, "debit", "Subscriptions")
        add(D(10), "ChatGPT Plus", 1700, "debit", "Subscriptions")
        add(D(11), "Cult Gym Membership", 1000, "debit", "Subscriptions")
        add(D(12), "Electricity Board", [1800, 1750, 1900, 1850, 1800, 2100, 2400, 2700, 2950, 3300, 3650, 4200][i], "debit", "Bills")

        food_count = [10, 11, 13, 15, 17, 19, 22, 24, 26, 28, 31, 34][i]
        for _ in range(food_count):
            add(D(random.randint(1, 28)), random.choice(["Swiggy", "Zomato", "Dominos", "Cafe Coffee Day"]), random.randint(280, 680), "debit", "Food & Dining")

        add(D(14), "BigBasket Groceries", [2200, 2400, 2500, 2700, 2900, 3200, 3400, 3600, 3900, 4100, 4300, 4700][i], "debit", "Food & Dining")

        for _ in range(4):
            add(D(random.randint(1, 28)), "HP Pump Fuel", random.randint(450, 550) if i < 8 else 1600, "debit", "Transportation")

        for _ in range(random.randint(5, 10)):
            add(D(random.randint(1, 28)), "Uber", random.randint(120, 420), "debit", "Transportation")

        for _ in range(random.randint(2, 5)):
            add(D(random.randint(1, 28)), random.choice(["Amazon", "Flipkart", "Myntra", "Ajio"]), random.randint(500, 2400), "debit", "Shopping")

        if i in (1, 4, 7, 10):
            add(D(20), "Apollo Pharmacy", random.randint(400, 1800), "debit", "Healthcare")

        if i in (2, 5, 8, 11):
            add(D(22), "Udemy Course", 1200 + (i * 250), "debit", "Education")

        if i == 10:
            add(D(8), "Netflix", 649, "debit", "Subscriptions")

        if i == 11:
            add(D(21), "XYZ TRADING UNKNOWN", 48000, "debit", "Others")
            add(D(18), "Bank Card Duplicate", 1999, "debit", "Subscriptions")
            add(D(19), "Electricity Board - Duplicate", 4200, "debit", "Bills")

    df = pd.DataFrame(rows).sort_values("date").reset_index(drop=True)
    df.to_csv(f"{out}/transactions.csv", index=False)

    json.dump({
        "name": "Aarav Mehta",
        "opening_balance": 180000,
        "monthly_income": 50000,
        "min_buffer": 5000,
        "subscription_last_used": {
            "Netflix": "2026-12-20",
            "Spotify": "2026-05-01",
            "ChatGPT Plus": "2026-12-25",
            "Cult Gym Membership": "2026-04-10",
            "Amazon Prime": "2026-09-12"
        },
        "portfolio_goals": [
            {"goal": "Emergency fund", "target": 300000},
            {"goal": "Vacation", "target": 120000},
            {"goal": "Home down payment", "target": 600000}
        ]
    }, open(f"{out}/profile.json", "w"), indent=2)

    with open(os.path.join("docs", "financial_kb.json"), "w", encoding="utf-8") as fp:
        json.dump([
            {"title": "Emergency fund", "content": "A strong emergency fund covers 6 months of essential expenses and protects against income shocks."},
            {"title": "Savings rate", "content": "A healthy savings rate is at least 20% of monthly income, with a goal of gradual increase each year."},
            {"title": "Debt management", "content": "Keep recurring debt at or below 30% to 35% of monthly income for sustainable cash flow."},
            {"title": "Subscription cleanup", "content": "Unused subscriptions should be canceled if not consumed for 90 days or more."},
            {"title": "Cash-flow risk", "content": "Maintain a minimum balance buffer and track spikes in essentials, utilities, and recurring charges."},
            {"title": "Budgeting", "content": "Needs around 50%, wants around 30%, savings or debt reduction around 20% of income."},
            {"title": "Anomaly detection", "content": "Large one-off payments, duplicate charges, or sudden category spikes may signal fraud or billing errors."}
        ], fp, indent=2)


if __name__ == "__main__":
    make()
