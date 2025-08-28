# Electricity Bills Dashboard

> **License:** This project is licensed under the GNU Affero General Public License v3.0 (AGPLv3). See [LICENSE](LICENSE) for details.

A Streamlit dashboard to fetch and display electricity bill payment details for multiple USC numbers from the TGSPDCL portal.

## Features

- **Password protected:** Only authorized users can access the dashboard.
- **USC input:** Enter multiple USC numbers (one per line) or fetch a specific USC.
- **Progress indicator:** Shows progress while bills are being fetched.
- **Random delay:** Adds a short random delay between requests to avoid failures.
- **Bill summary:** Displays pending and overdue bills, with totals.
- **Overdue highlighting:** Unpaid bills after due date are highlighted in red.
- **CSV download:** Download all bill details as a CSV file.

## Usage

1. **Configure secrets:**
   - Add your password and optionally a default USC list in `.streamlit/secrets.toml`:
     ```
     [auth]
     password = "your_password"

     [usc]
     numbers = [ "222233344", ...]
     ```

2. **Run the app:**
   ```
   streamlit run app.py
   ```

3. **On the dashboard:**
   - Enter your password to unlock.
   - Enter USC numbers (one per line) or use the "Fetch only this USC" field.
   - Click **Fetch Bills**.
   - View bill details, summary, and download CSV.

## Notes

- The app fetches bill details from [https://tgsouthernpower.org/billinginfo](https://tgsouthernpower.org/billinginfo).
- Overdue bills are determined by comparing due date, paid date, and amounts.
- If you encounter issues, check your secrets configuration and network connectivity.
