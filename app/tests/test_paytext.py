import pytest

import paytext


# hand-read lines from US HR-titled postings, 2026-10-09 (app/docs/jobs/pay-filter.md #Pay read from the posting)
@pytest.mark.parametrize("text, expected", [
    ("The base salary range for this role is $182,000 to $242,000.", (182000, 242000, "year")),
    ("Compensation- $130,000-150,000 Medical, dental, and vision coverage", (130000, 150000, "year")),
    ("District of Columbia is: $115,200—$214,400 USD What We Believe", (115200, 214400, "year")),
    ("Compensation: $100,000-$125,000 + discretionary bonus", (100000, 125000, "year")),
    ("Pay Range $110,000—$130,000 USD", (110000, 130000, "year")),
    ("the pay range for this position is between $131,700.00 and $219,300.00. The Company", (131700, 219300, "year")),
    ("Compensation & Benefits $115-125k + 15% annual bonus potential", (115000, 125000, "year")),
    ("Compensation and Benefits: $23/hr At Moses/Weitzman", (23, 23, "hour")),
    ("SALARY: $18.54 – $20.60 Per Hour GENERAL JOB DESCRIPTION", (18.54, 20.6, "hour")),
    ("Contract Role · $11,000-$15,000/Monthly DOE", (11000, 15000, "month")),
    ("The likely salary range for this position is $107,744 - $71,875.", (71875, 107744, "year")),
    ("a Special Entrance Rate (SER) in the amount of $2,383.20 biweekly", (61963.2, 61963.2, "year")),
    ("base salary range (excluding equity and bonus): $205,785—$242,100 USD", (205785, 242100, "year")),
    ("$5,000 sign-on bonus. Salary range $90,000 to $110,000 per year", (90000, 110000, "year")),
])
def test_pay_said_as_pay_is_read(text, expected):
    lo, hi, period = paytext.stated(text)
    assert (lo, hi, period) == (pytest.approx(expected[0]), pytest.approx(expected[1]), expected[2])


# money that isn't the job's pay: a budget, a raise, a benefit's cost, a perk, a placeholder
@pytest.mark.parametrize("text", [
    "You will manage a $5M budget and $2.5 million in grants.",
    "We have raised over $160M from world-class partners.",
    "Medical starts at $8/week, Dental under $2/week",
    "earn up to $500+ per year for taking care of yourself",
    "Remote work reimbursement: Up to $85/month for mobile and internet.",
    "$2,000 attendance bonus $500 employee referral bonus",
    "Salary Range: $0.00 - $0.00 The above salary range represents",
    "Every donation will be matched, up to $500 per year",
    "Up to $60/day for other meals when in the office",
    "With annual revenues approaching $35 million, Good Shepherd is a nonprofit",
])
def test_money_that_is_not_pay_is_left_alone(text):
    assert paytext.stated(text) is None


# a range per city or level reads as their span; a stray hourly figure never drags a yearly range down
def test_several_ranges_read_as_one_span_in_the_first_ones_period():
    text = ("The salary range for this role by location - McLean, VA: $238,700 - $272,400 for Sr Director. Richmond, VA: $217,000 - $247,700 for Sr Director. "
            "The minimum hourly rate is $18.91.")
    assert paytext.stated(text) == (217000, 272400, "year")
