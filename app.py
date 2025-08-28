import streamlit as st
import requests
import pandas as pd
from bs4 import BeautifulSoup
import time
import random

st.set_page_config(page_title="USC Bill Fetcher", layout="wide")

# --- Password Protection ---
if "auth" not in st.secrets or "password" not in st.secrets["auth"]:
    st.error("Password not set in secrets. Please configure before using.")
    st.stop()

if "authenticated" not in st.session_state:
    pwd = st.text_input("Enter Password", type="password")
    if pwd == st.secrets["auth"]["password"]:
        st.session_state["authenticated"] = True
        st.rerun()
    elif pwd:
        st.warning("Incorrect password. Please try again.")
    st.stop()

st.title("⚡ Electricity Bill Payment Dashboard")

st.markdown("""
- Enter your USC numbers (one per line) below.
- You can add a specific USC number to fetch using the field below.
- Click **Fetch Bills** to view payment details.
- Unpaid bills after due date are highlighted in red.
- Download results as CSV.
""")

# --- USC Numbers Input ---
usc_input = st.text_area("Enter USC numbers (one per line):")
usc_numbers = [x.strip() for x in usc_input.splitlines() if x.strip()] if usc_input else []
if "usc" in st.secrets and not usc_numbers:
    usc_numbers = st.secrets["usc"]["numbers"]

specific_usc = st.text_input("Fetch only this USC (optional):")
add_to_list = st.button("Add to Bills List")

if specific_usc:
    if add_to_list:
        if specific_usc not in usc_numbers:
            usc_numbers.append(specific_usc)
    else:
        usc_numbers = [specific_usc]

# --- Headers (cookie optional) ---
headers = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Content-Type": "application/x-www-form-urlencoded",
    "Origin": "https://tgsouthernpower.org",
    "Referer": "https://tgsouthernpower.org/onlinebillenquiry",
}
if "headers" in st.secrets and st.secrets["headers"].get("cookie"):
    headers["Cookie"] = st.secrets["headers"]["cookie"]

def parse_bill_table(soup):
    table = soup.find("table", {"class": "table"})
    rows = table.find_all("tr")
    result = {}
    for i, row in enumerate(rows):
        cols = row.find_all("td")
        ths = row.find_all("th")
        if i == 0:
            result["Consumer Name"] = cols[0].text.strip() if cols else ""
            result["Unique Service Number"] = cols[1].text.strip() if len(cols) > 1 else ""
        elif i == 1:
            result["Service Number"] = cols[0].text.strip() if cols else ""
            result["ERO"] = cols[1].text.strip() if len(cols) > 1 else ""
        elif i == 2:
            result["Address"] = cols[0].text.strip() if cols else ""
            result["Section Name"] = cols[1].text.strip() if len(cols) > 1 else ""
        elif "Arrears" in row.text:
            date_row = rows[i+1]
            date_cols = date_row.find_all("td")
            result["Arrears Date"] = date_cols[0].text.strip() if date_cols else ""
            result["Arrears Amount"] = date_cols[1].text.strip() if len(date_cols) > 1 else ""
        elif "Current Month Bill" in row.text:
            bill_row = rows[i+1]
            bill_cols = bill_row.find_all("td")
            result["Bill Date"] = bill_cols[0].text.strip() if bill_cols else ""
            result["Bill Amount"] = bill_cols[1].text.strip() if len(bill_cols) > 1 else ""
        elif "Total Amount Payable" in row.text:
            payable_row = rows[i+1]
            payable_cols = payable_row.find_all("td")
            result["Due Date"] = payable_cols[0].text.strip() if payable_cols else ""
            result["Due Amount"] = payable_cols[1].text.strip() if len(payable_cols) > 1 else ""
        elif "Total Amount Paid" in row.text:
            paid_row = rows[i+1]
            paid_cols = paid_row.find_all("td")
            result["Paid Date"] = paid_cols[0].text.strip() if paid_cols else ""
            result["Paid Amount"] = paid_cols[1].text.strip() if len(paid_cols) > 1 else ""
    return result

if st.button("Fetch Bills"):
    if not usc_numbers:
        st.warning("Please enter at least one USC number.")
        st.stop()

    results = []
    progress = st.progress(0, text="Loading bills...")
    total = len(usc_numbers)
    with st.spinner("Fetching bills..."):
        for idx, usc in enumerate(usc_numbers):
            url = "https://tgsouthernpower.org/billinginfo"
            data = {
                "inlineRadioOptions": "LT",
                "ukscno": usc,
            }
            try:
                res = requests.post(url, headers=headers, data=data, timeout=10)
                res.raise_for_status()
                soup = BeautifulSoup(res.text, "html.parser")
                bill_info = parse_bill_table(soup)
                bill_info["USC"] = usc
                results.append(bill_info)
            except Exception as e:
                results.append({"USC": usc, "Error": str(e)})
            time.sleep(random.uniform(0.5, 1.5))
            progress.progress((idx + 1) / total, text=f"Loaded {idx + 1} of {total} bills")

    df = pd.DataFrame(results)

    # --- Clean and Format Columns ---
    for col in ["Due Amount", "Paid Amount", "Bill Amount", "Arrears Amount"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.replace(",", "").str.replace("₹", "").str.strip()
            df[col] = pd.to_numeric(df[col], errors="coerce")
    for date_col in ["Due Date", "Paid Date", "Bill Date", "Arrears Date"]:
        if date_col in df.columns:
            df[date_col] = pd.to_datetime(df[date_col], errors="coerce", dayfirst=True)

    today = pd.Timestamp.today()

    # --- Overdue Calculation ---
    overdue_mask = (
        (df["Due Amount"] > df["Paid Amount"]) &
        (df["Due Date"] < today) &
        (
            df["Paid Date"].isna() | 
            (df["Paid Date"] > df["Due Date"]) | 
            (df["Paid Amount"] < df["Due Amount"])
        )
    )
    pending_mask = (
        (df["Due Amount"] > df["Paid Amount"]) &
        (df["Due Date"] >= today)
    )

    pending_count = pending_mask.sum()
    pending_total = df.loc[pending_mask, "Due Amount"].sum()
    overdue_count = overdue_mask.sum()
    overdue_total = df.loc[overdue_mask, "Due Amount"].sum()

    st.subheader("🔔 Bill Payment Summary")
    st.write(f"**Bills Pending (before due date):** {pending_count}")
    st.write(f"**Total Pending Amount:** ₹ {pending_total:,.2f}")
    st.write(f"**Bills Overdue (after due date):** {overdue_count}")
    st.write(f"**Total Overdue Amount:** ₹ {overdue_total:,.2f}")

    # --- Highlight Overdue Bills ---
    def highlight_alert(row):
        return ['background-color: #ffcccc' if overdue_mask.iloc[row.name] else '' for _ in row]

    st.dataframe(df.style.apply(highlight_alert, axis=1), use_container_width=True)

    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button("⬇ Download CSV", csv, "usc_bills.csv", "text/csv")
