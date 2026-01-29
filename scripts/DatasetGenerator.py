# ml_experiments/data/generate_synthetic.py
# Synthetic high-noise bank-statement-like transaction generator
# Output schema (NO user_id):
# transaction_id,transaction_date,timestamp,description,merchant,amount,currency,payment_method,is_credit,
# category,is_amount_anomaly,is_frequency_anomaly,is_merchant_anomaly
#
# Generates exactly 10,000 rows within a single calendar month window.

import csv
import random
import string
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

# =========================
# CONFIG
# =========================
RANDOM_SEED = 42
NUM_RECORDS = 500

# Exactly one-month window (inclusive)
MONTH_START = datetime(2025, 4, 1)
MONTH_END = datetime(2025, 4, 30)

OUTPUT_FILE = "Data5.csv"

CURRENCIES = ["EUR"]  # keep simple; can extend later if needed
PAYMENT_METHODS = ["CARD", "CONTACTLESS", "ONLINE", "TRANSFER"]

# To simulate refunds/chargebacks
CREDIT_PROB = 0.10  # 10% credits

# Anomaly injection probabilities (base). Additional logic below.
FREQ_ANOMALY_PROB = 0.06  # baseline injection; also reinforced with bursts
AMOUNT_OUTLIER_PROB = 0.06
MERCHANT_NOVELTY_PROB = 0.12  # create truly new/unseen merchants sometimes

# =========================
# CATEGORIES
# =========================
CATEGORIES = [
    "Food",
    "Transport",
    "Entertainment",
    "Shopping",
    "Bills",
    "Healthcare",
    "Other",
]

# =========================
# MERCHANT POOLS (EXPANDED)
# Canonical merchant (stored in `merchant`) + noisy description variants built around it.
# =========================
MERCHANTS: Dict[str, List[str]] = {
    "Food": [
        "STARBUCKS", "COSTA COFFEE", "PRET A MANGER", "DUNKIN",
        "MCDONALDS", "BURGER KING", "SUBWAY", "KFC", "DOMINOS",
        "PIZZA HUT", "TACO BELL", "WENDYS", "FIVE GUYS",
        "NANDO'S", "SHAKE SHACK", "LOCAL CAFE", "BAKERY HOUSE",
        "FOOD TRUCK", "SUSHI BAR", "THAI KITCHEN", "INDIAN SPICE",
        "GROCERY DELI", "FARMERS MARKET", "COFFEE ROASTERS",
        "SANDWICH CO", "JUICE BAR", "ICE CREAM SHOP",
        "CHIPPER", "BISTRO", "BRUNCH HOUSE",
    ],
    "Transport": [
        "UBER", "LYFT", "BOLT", "FREE NOW", "LUAS", "DART",
        "IRISH RAIL", "CITY TAXI", "METRO BUS", "BUS EIREANN",
        "AIRPORT TRANSFER", "PARKING METER", "APCOA PARKING",
        "NCP PARKING", "SHELL FUEL", "CIRCLE K", "BP FUEL",
        "ESSO", "TOLL ROAD", "M7 TOLL", "CHARGING STATION",
        "BIKE SHARE", "SCOOTER RENTAL", "TRAIN TICKET",
        "LEAP TOPUP", "TRANSIT TOPUP",
    ],
    "Entertainment": [
        "NETFLIX", "SPOTIFY", "PRIME VIDEO", "DISNEY PLUS",
        "APPLE MUSIC", "YOUTUBE PREMIUM", "HBO MAX", "HULU",
        "STEAM", "PLAYSTATION", "XBOX", "NINTENDO", "EPIC GAMES",
        "CINEMA WORLD", "ODEON CINEMA", "EVENT TICKETS",
        "TICKETMASTER", "GIG TICKETS", "MUSEUM PASS",
        "BOWLING ALLEY", "ARCADE", "THEATRE HOUSE",
        "LIVE NATION", "AUDIBLE", "PATREON",
    ],
    "Shopping": [
        "AMAZON", "AMZN MKTPLACE", "EBAY", "ETSY", "ASOS",
        "ZARA", "H&M", "UNIQLO", "NIKE", "ADIDAS",
        "IKEA", "ARGOS", "CURRYS", "HARVEY NORMAN",
        "TESCO", "ALDI", "LIDL", "DUNNES STORES", "SPAR",
        "PENNEYS", "BOOTS RETAIL", "LOCAL STORE", "ONLINE SHOP",
        "DECATHLON", "TK MAXX", "THE HOME STORE",
        "APPLE STORE", "GOOGLE STORE", "SAMSUNG STORE",
        "BOOKSHOP", "STATIONERY MART",
    ],
    "Bills": [
        "EIR", "VODAFONE", "THREE", "ELECTRIC IRELAND",
        "GAS NETWORKS", "UTILITY PAYMENT", "WATER CHARGES",
        "INTERNET PROVIDER", "MOBILE BILL", "BROADBAND BILL",
        "TV LICENSE", "RENT PAYMENT", "MORTGAGE PAYMENT",
        "INSURANCE PREMIUM", "CAR INSURANCE", "HEALTH INSURANCE",
        "GYM MEMBERSHIP", "PROPERTY MGMT", "SERVICE CHARGE",
        "SUBSCRIPTION BILL", "ELECTRIC BILL", "GAS BILL",
    ],
    "Healthcare": [
        "BOOTS", "CVS PHARMACY", "WALGREENS", "MEDICAL CLINIC",
        "CITY HOSPITAL", "DENTAL CARE", "OPTICIAN", "LAB TEST",
        "PHYSIO CENTER", "MRI SCAN", "XRAY CLINIC",
        "DERMATOLOGY", "GP CONSULT", "HEALTH CHECK",
        "VACCINATION", "PHARMACY PLUS", "HEALTH STORE",
        "DENTAL HYGIENE", "VISION CARE",
    ],
    "Other": [
        "PAYPAL", "REVOLUT", "WISE TRANSFER", "BANK FEE",
        "ATM WITHDRAWAL", "CARD VERIFICATION", "MISC PAYMENT",
        "GOVT SERVICE", "POST OFFICE", "CHARITY DONATION",
        "UNIVERSITY FEES", "COURSE PAYMENT", "TRANSFER OUT",
        "TRANSFER IN", "LOAN PAYMENT", "INTEREST CHARGE",
        "FOREIGN EXCHANGE", "PAYMENT ADJUSTMENT", "CHARGEBACK",
        "CASH WITHDRAWAL", "FINTECH TOPUP",
    ],
}

# =========================
# NOISE SOURCES (EXPANDED)
# =========================
PAYMENT_RAILS = ["POS", "VISA", "MASTERCARD", "DEBIT", "CREDIT", "ECOM", "CHIP", "PIN", "TAP"]
BOILERPLATE = [
    "PURCHASE", "TRANSACTION", "AUTH", "AUTHCODE", "APPROVED",
    "CARD PAYMENT", "CONTACTLESS", "MERCHANT", "TERMINAL",
    "INTL", "FEE", "FX", "EXCHANGE", "COMMISSION",
    "RECURRING", "SUBSCRIPTION", "ONLINE", "ECOMMERCE",
    "SETTLEMENT", "PENDING", "COMPLETE",
]
COUNTRIES = ["IE", "IRL", "UK", "US", "DE", "FR", "ES", "NL"]
CITIES = ["DUBLIN", "CORK", "GALWAY", "LIMERICK", "LONDON", "PARIS", "BERLIN", "MADRID"]
SERVICES = ["TRIP", "ORDER", "PAYMENT", "BILL", "TOPUP", "SUBSCRIPTION", "DELIVERY", "BOOKING"]
CHANNEL_HINTS = ["MOBILE", "WEB", "APP", "IN-STORE", "KIOSK", "TERMINAL", "POS"]
SEPARATORS = [" ", "-", "_", "*", "@", ".", "/", "|", "#", ":", ";"]

# Typical bank description prefixes/suffixes
PREFIXES = [
    "POS", "CARD", "CARD PUR", "ECOM", "PAYMENT", "DD", "SO",
    "DIRECT DEBIT", "STANDING ORDER", "CONTACTLESS", "TRANSFER",
]
SUFFIXES = [
    "DUBLIN", "IE", "IRL", "APPROVED", "AUTH", "SETTLED", "REF",
    "TERMINAL", "TXN", "TRACE", "SEQ", "BATCH",
]

# =========================
# AMOUNT RANGES (LOOSE & OVERLAPPING)
# =========================
AMOUNT_RANGES: Dict[str, Tuple[float, float]] = {
    "Food": (2.5, 60.0),
    "Transport": (2.5, 120.0),
    "Entertainment": (3.0, 80.0),
    "Shopping": (5.0, 500.0),
    "Bills": (10.0, 350.0),
    "Healthcare": (8.0, 450.0),
    "Other": (1.0, 800.0),
}


# =========================
# HELPERS
# =========================
def rand_alnum(min_len: int = 6, max_len: int = 16) -> str:
    length = random.randint(min_len, max_len)
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=length))


def rand_digits(min_len: int = 5, max_len: int = 15) -> str:
    length = random.randint(min_len, max_len)
    return "".join(random.choices(string.digits, k=length))


def random_case(token: str) -> str:
    # Randomly change casing per character for uglier text
    return "".join(c.upper() if random.random() < 0.5 else c.lower() for c in token)


def month_random_date() -> datetime:
    delta_days = (MONTH_END - MONTH_START).days
    return MONTH_START + timedelta(days=random.randint(0, delta_days))


def random_timestamp_for_date(d: datetime) -> datetime:
    return datetime(d.year, d.month, d.day,
                    random.randint(0, 23),
                    random.randint(0, 59),
                    random.randint(0, 59))


def pick_category() -> str:
    # Slightly imbalanced distribution to mimic reality
    weights = {
        "Food": 0.20,
        "Transport": 0.14,
        "Entertainment": 0.10,
        "Shopping": 0.18,
        "Bills": 0.16,
        "Healthcare": 0.07,
        "Other": 0.15,
    }
    cats = list(weights.keys())
    w = list(weights.values())
    return random.choices(cats, weights=w, k=1)[0]


def generate_amount(category: str) -> Tuple[float, bool]:
    low, high = AMOUNT_RANGES[category]
    amount = random.uniform(low, high)
    is_amount_anomaly = False

    # Occasional outliers
    if random.random() < AMOUNT_OUTLIER_PROB:
        amount *= random.uniform(2.0, 5.0)
        is_amount_anomaly = True

    # Add cents realism
    amount = round(amount, 2)
    return amount, is_amount_anomaly


def maybe_add_token(tokens: List[str], token_source: List[str], prob: float, count_range=(1, 1)) -> None:
    if random.random() < prob:
        for _ in range(random.randint(count_range[0], count_range[1])):
            tokens.append(random.choice(token_source))


def maybe_duplicate_some_tokens(tokens: List[str], prob: float = 0.15) -> None:
    # Duplicate random tokens to simulate messy bank strings
    if tokens and random.random() < prob:
        k = random.randint(1, min(3, len(tokens)))
        for _ in range(k):
            tokens.append(random.choice(tokens))


def random_separators_join(tokens: List[str]) -> str:
    # Join tokens using random separators between tokens
    out = ""
    for i, t in enumerate(tokens):
        t2 = random_case(t)
        out += t2
        if i < len(tokens) - 1:
            out += random.choice(SEPARATORS)
    return out


def make_description(category: str, canonical_merchant: str, txn_dt: datetime) -> str:
    tokens: List[str] = []

    # Add common prefixes
    maybe_add_token(tokens, PREFIXES, prob=0.65)
    maybe_add_token(tokens, PAYMENT_RAILS, prob=0.55)
    maybe_add_token(tokens, CHANNEL_HINTS, prob=0.35)

    # Merchant with variations in formatting
    merchant_variant = canonical_merchant
    # Sometimes split merchant words with separators or remove spaces
    if " " in merchant_variant and random.random() < 0.35:
        parts = merchant_variant.split()
        merchant_variant = random.choice(SEPARATORS).join(parts)
    elif " " in merchant_variant and random.random() < 0.20:
        merchant_variant = merchant_variant.replace(" ", "")
    tokens.append(merchant_variant)

    # Add service hint / category-ish hints sometimes (not always)
    maybe_add_token(tokens, SERVICES, prob=0.55)

    # Add location/country noise
    maybe_add_token(tokens, CITIES, prob=0.45)
    maybe_add_token(tokens, COUNTRIES, prob=0.35)

    # Add boilerplate spam
    maybe_add_token(tokens, BOILERPLATE, prob=0.70, count_range=(1, 3))

    # Add date-like codes
    if random.random() < 0.35:
        # e.g., 09JUN24 or 20240609
        if random.random() < 0.5:
            code = txn_dt.strftime("%d%b%y").upper()  # 09JUN24
        else:
            code = txn_dt.strftime("%Y%m%d")  # 20240609
        tokens.append(code)

    # Add reference / auth ids
    if random.random() < 0.80:
        tokens.append("REF")
        tokens.append(rand_digits(6, 12))
    if random.random() < 0.55:
        tokens.append("AUTH")
        tokens.append(rand_alnum(6, 12))
    if random.random() < 0.45:
        tokens.append("TERM")
        tokens.append(rand_digits(4, 8))

    # Add suffixes
    maybe_add_token(tokens, SUFFIXES, prob=0.55, count_range=(1, 2))

    # Duplicate tokens to create stuffing
    maybe_duplicate_some_tokens(tokens, prob=0.22)

    # Random ordering (banks reorder fields)
    if random.random() < 0.55:
        random.shuffle(tokens)

    # Final join with random separators and random casing
    return random_separators_join(tokens)


def make_novel_merchant() -> str:
    # Generate a plausible new merchant name (to test unseen merchants)
    prefixes = ["THE", "NEW", "CITY", "GLOBAL", "URBAN", "GREEN", "METRO", "NORTH", "SOUTH", "EAST", "WEST"]
    nouns = ["MARKET", "STORE", "CAFE", "PHARMACY", "CLINIC", "ELECTRICS", "OUTLET", "DINER", "BAKERY", "TRAVEL"]
    suffixes = ["LTD", "INC", "PLC", "GROUP", "SERVICES", "CO", "EU", "IRELAND"]
    name = f"{random.choice(prefixes)} {random.choice(nouns)} {random.choice(suffixes)}"
    return name


# =========================
# DATASET GENERATION
# =========================
def generate_dataset() -> List[List]:
    random.seed(RANDOM_SEED)

    rows: List[List] = []
    seen_merchants: set = set()  # used for merchant novelty anomaly

    # Create some "bursts" to simulate frequency anomalies (e.g. repeated small charges)
    burst_days = set(random.sample(range((MONTH_END - MONTH_START).days + 1), k=6))  # 6 burst days
    burst_merchants = random.sample(MERCHANTS["Food"], k=min(4, len(MERCHANTS["Food"])))

    for i in range(NUM_RECORDS):
        transaction_id = f"TXN_202406_{i+1:06d}"

        category = pick_category()
        txn_date = month_random_date()
        txn_ts = random_timestamp_for_date(txn_date)

        # Occasionally generate a brand-new merchant never in pools (merchant drift)
        if random.random() < MERCHANT_NOVELTY_PROB:
            merchant = make_novel_merchant()
            # Assign a plausible category based on keywords sometimes, else keep existing category
            # (We keep category from pick_category() to preserve label distribution; merchant novelty will test model robustness.)
        else:
            merchant = random.choice(MERCHANTS[category])

        amount, is_amount_anomaly = generate_amount(category)

        currency = random.choice(CURRENCIES)
        payment_method = random.choice(PAYMENT_METHODS)
        is_credit = random.random() < CREDIT_PROB

        # Make noisy description derived from canonical merchant + extra junk
        description = make_description(category, merchant, txn_date)

        # Merchant novelty anomaly: merchant not seen before in dataset (global novelty)
        is_merchant_anomaly = merchant not in seen_merchants
        seen_merchants.add(merchant)

        # Frequency anomaly:
        #  - baseline random injection
        #  - plus "burst days" where certain merchants appear more often
        is_frequency_anomaly = random.random() < FREQ_ANOMALY_PROB
        day_index = (txn_date - MONTH_START).days
        if day_index in burst_days and any(m in merchant.upper() for m in burst_merchants):
            # Amplify anomaly chance for burst merchants on burst days
            if random.random() < 0.45:
                is_frequency_anomaly = True

        # If amount anomaly is true, increase the chance that merchant anomaly doesn't override (keep independent)
        # (No extra logic needed; flags are orthogonal.)

        # Optional: if is_credit (refund), reduce anomaly likelihood a bit (still can be anomalous)
        if is_credit and random.random() < 0.6:
            is_amount_anomaly = False  # refunds often large; don't over-flag

        rows.append([
            transaction_id,
            txn_date.strftime("%Y-%m-%d"),
            txn_ts.strftime("%Y-%m-%d %H:%M:%S"),
            description,
            merchant,
            amount,
            currency,
            payment_method,
            is_credit,
            category,
            is_amount_anomaly,
            is_frequency_anomaly,
            is_merchant_anomaly,
        ])

    return rows


def write_csv(rows: List[List]) -> None:
    header = [
        "transaction_id",
        "transaction_date",
        "timestamp",
        "description",
        "merchant",
        "amount",
        "currency",
        "payment_method",
        "is_credit",
        "category",
        "is_amount_anomaly",
        "is_frequency_anomaly",
        "is_merchant_anomaly",
    ]
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)


if __name__ == "__main__":
    data = generate_dataset()
    write_csv(data)
    print(f"Generated {NUM_RECORDS} transactions -> {OUTPUT_FILE}")
