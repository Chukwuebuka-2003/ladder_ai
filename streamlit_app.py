import streamlit as st
import requests
import json
from streamlit_option_menu import option_menu
from datetime import datetime

FASTAPI_URL = "http://localhost:8000"


# Authentication Functions
def login_user(email, password):
    """
    Attempt to authenticate a user by POSTing credentials to the backend /login endpoint.
    
    Sends a POST request with the provided email and password to FASTAPI_URL + "/login".
    On success returns the parsed JSON response (typically containing an access token and user info).
    On network/request errors or when the response is not valid JSON, displays an error message via Streamlit and returns None.
    
    Parameters:
        email (str): User email address used for authentication.
        password (str): User password.
    
    Returns:
        dict | None: Parsed JSON response on success, or None if the request failed or the response could not be decoded.
    """
    try:
        response = requests.post(f"{FASTAPI_URL}/login", json={"email": email, "password": password})
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Login failed: {e}")
        return None
    except json.JSONDecodeError:
        st.error("Invalid response from server. Please try again.")
        return None


def signup_user(email, password, username):
    """
    Create a new user account by POSTing username, email, and password to the backend /signup endpoint.
    
    Parameters:
        email (str): User email address sent in the request body.
        password (str): User password sent in the request body.
        username (str): Desired username sent in the request body.
    
    Returns:
        dict or None: Parsed JSON response from the server on success; None if the HTTP request fails or the response contains invalid JSON.
    
    Side effects:
        Displays a Streamlit error message when the request fails or the response cannot be parsed.
    """
    try:
        response = requests.post(f"{FASTAPI_URL}/signup",
                                 json={"username": username, "email": email, "password": password})
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Signup failed: {e}")
        return None
    except json.JSONDecodeError:
        st.error("Server returned invalid JSON. Please contact support.")
        return None


def verify_otp(email, otp):
    """
    Verify a one-time password (OTP) for the given email by calling the backend /verify-otp endpoint.
    
    Parameters:
        email (str): The user's email address to verify.
        otp (str | int): The OTP/code provided by the user.
    
    Returns:
        dict | None: Parsed JSON response from the server on success; None if the request fails or the response is invalid.
    
    Side effects:
        Displays user-facing error messages using Streamlit's st.error on network/request failures or invalid JSON responses.
    """
    try:
        response = requests.post(f"{FASTAPI_URL}/verify-otp", json={"email": email, "code": otp})
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"OTP verification failed: {e}")
        return None
    except json.JSONDecodeError:
        st.error("Invalid response from server during OTP verification.")
        return None


# --- API Request Helper ---
def make_api_request(method, endpoint, data=None):
    """
    Send an HTTP request to the backend API and return the parsed JSON response.
    
    Builds the full URL from FASTAPI_URL and the provided endpoint, attaches an
    Authorization header when a session token exists, and dispatches the request
    using the specified HTTP method. On success returns the decoded JSON object;
    on failure returns None.
    
    Parameters:
        method (str): HTTP method name (e.g., "GET", "POST", "PUT", "DELETE").
        endpoint (str): API path appended to FASTAPI_URL (must begin with '/').
        data (dict|None): Payload for the request. Used as query params for GET and
            as JSON body for POST/PUT. Ignored for DELETE.
    
    Returns:
        dict|list|None: Parsed JSON response from the server, or None on error.
    
    Side effects:
        - If a 401 Unauthorized is returned while a session token exists, clears
          authentication-related session state keys (token, logged_in,
          user_email_for_otp, otp_verification_pending), shows a warning, and
          triggers a Streamlit rerun to force re-authentication.
        - Displays user-facing error messages via Streamlit on request or JSON
          parsing failures.
    """
    headers = {}
    if st.session_state.get("token"):
        headers["Authorization"] = f"Bearer {st.session_state.token}"

    try:
        full_url = f"{FASTAPI_URL}{endpoint}"
        if method.upper() == "GET":
            response = requests.get(full_url, headers=headers, params=data)
        elif method.upper() == "POST":
            response = requests.post(full_url, json=data, headers=headers)
        elif method.upper() == "PUT":
            response = requests.put(full_url, json=data, headers=headers)
        elif method.upper() == "DELETE":
            response = requests.delete(full_url, headers=headers)
        else:
            st.error(f"Unsupported HTTP method: {method}")
            return None

        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        if 'response' in locals() and response.status_code == 401 and st.session_state.get("token"):
            st.warning("Your session has expired. Please log in again.")
            st.session_state.token = None
            st.session_state.logged_in = False
            for key in ["user_email_for_otp", "otp_verification_pending"]:
                st.session_state.pop(key, None)
            st.rerun()
        else:
            st.error(f"API request failed: {e}")
        return None
    except json.JSONDecodeError:
        st.error("Received an invalid JSON response from the server.")
        return None


# --- Helper: Format ISO Date to Readable String ---
def format_date(iso_string):
    """
    Convert an ISO 8601 timestamp string to a human-readable format.
    
    If parsing succeeds, returns a string like "Sep 15, 2025, 10:30 AM".
    If parsing fails, returns the original input unchanged.
    
    Parameters:
        iso_string (str): ISO 8601 datetime string (e.g., "2025-09-15T10:30:00Z" or with timezone offset).
    
    Returns:
        str: Formatted datetime ("Mon DD, YYYY, HH:MM AM/PM") or the original input on parse failure.
    """
    try:
        dt = datetime.fromisoformat(iso_string.replace("Z", "+00:00"))
        return dt.strftime("%b %d, %Y, %I:%M %p")
    except Exception:
        return iso_string



st.set_page_config(page_title="Expense Tracker", layout="wide")

# Initialize session state variables
defaults = {
    "token": None,
    "logged_in": False,
    "current_page": "Login",
    "user_email_for_otp": None,
}
for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val


# --- Sidebar Navigation ---
with st.sidebar:
    if st.session_state.logged_in:
        selected = option_menu(
            menu_title="Expense Tracker",
            options=["Dashboard", "AI Insights", "Logout"],
            icons=["speedometer", "robot", "box-arrow-left"],
            menu_icon="cast",
            default_index=0,
        )
        st.session_state.current_page = selected
    else:
        selected = option_menu(
            menu_title="Expense Tracker",
            options=["Login", "Sign Up", "Verify OTP"],
            icons=["box-arrow-in-right", "person-plus", "key"],
            menu_icon="cast",
            default_index=0,
        )
        st.session_state.current_page = selected


# --- Page Rendering ---
if st.session_state.current_page == "Login":
    st.title("🔐 Login")
    email = st.text_input("Email Address")
    password = st.text_input("Password", type="password")
    if st.button("Log In", type="primary", use_container_width=True):
        if not email or not password:
            st.error("Please enter both email and password.")
        else:
            user_data = login_user(email, password)
            if user_data and 'access_token' in user_data:
                st.session_state.token = user_data['access_token']
                st.session_state.logged_in = True
                st.session_state.current_page = "Dashboard"
                st.success("✅ Logged in successfully!")
                st.rerun()
            else:
                st.error("❌ Invalid credentials or account not verified.")


elif st.session_state.current_page == "Sign Up":
    st.title("📝 Sign Up")
    username = st.text_input("Username")
    email = st.text_input("Email Address")
    password = st.text_input("Password", type="password")

    if st.button("Create Account", type="primary", use_container_width=True):
        if not all([username, email, password]):
            st.error("Please fill in all fields.")
        else:
            signup_response = signup_user(email, password, username)

            if signup_response and isinstance(signup_response, dict):
                message = signup_response.get("message", "")
                if message == "User created. OTP sent.":
                    st.session_state.user_email_for_otp = email
                    st.session_state.current_page = "Verify OTP"
                    st.success("Account created! Check your email for the OTP.")
                    st.rerun()
                elif "access_token" in signup_response:
                    st.session_state.token = signup_response["access_token"]
                    st.session_state.logged_in = True
                    st.session_state.current_page = "Dashboard"
                    st.success("Account created and auto-verified! Welcome!")
                    st.rerun()
                else:
                    st.warning(f"Unexpected response: {message}")
                    st.session_state.current_page = "Login"
                    st.rerun()
            else:
                st.error("Failed to create account. Please try again.")


elif st.session_state.current_page == "Verify OTP":
    st.title("🔑 Verify Your Email")
    st.write(f"An OTP has been sent to **{st.session_state.user_email_for_otp}**")
    st.info("Check your inbox (and spam folder) for a 6-digit code.")

    otp_code = st.text_input("Enter OTP Code", placeholder="e.g., 842917", max_chars=6)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Verify OTP", type="primary", use_container_width=True):
            if not otp_code:
                st.error("Please enter the OTP code.")
            else:
                result = verify_otp(st.session_state.user_email_for_otp, otp_code)
                if result and isinstance(result, dict):
                    if "access_token" in result:
                        st.session_state.token = result["access_token"]
                        st.session_state.logged_in = True
                        st.session_state.current_page = "Dashboard"
                        st.success("OTP verified! You are now logged in.")
                        st.rerun()
                    elif "verified" in result.get("message", "").lower() or "success" in result.get("message", "").lower():
                        st.session_state.current_page = "Login"
                        st.success("OTP verified! Please log in now.")
                        st.rerun()
                    else:
                        st.error(f"Verification failed: {result.get('message', 'Unknown error')}")
                else:
                    st.error("Invalid or expired OTP. Please request a new one.")

    with col2:
        if st.button("Resend OTP", type="secondary", use_container_width=True):
            st.warning("Resend functionality requires backend support. Contact admin if needed.")


elif st.session_state.current_page == "Dashboard":
    st.title("📊 Dashboard")

    st.header("Your Expenses")
    expenses = make_api_request("GET", "/expenses/")
    if expenses:

        formatted_expenses = []
        for exp in expenses:
            exp_copy = exp.copy()
            exp_copy["date"] = format_date(exp["date"])
            formatted_expenses.append(exp_copy)
        st.dataframe(formatted_expenses, use_container_width=True)
    else:
        st.write("📭 No expenses found.")

    st.header("➕ Add New Expense")
    with st.form("new_expense_form"):
        description = st.text_input("Description")
        amount = st.number_input("Amount", min_value=0.0, format="%.2f")
        category = st.text_input("Category")

        current_datetime = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        st.caption(f"Date will be set to: {current_datetime}")

        submitted = st.form_submit_button("Add Expense", type="primary")

        if submitted:
            if not description or not category:
                st.error("Description and Category are required.")
            else:

                new_expense_data = {
                    "description": description,
                    "amount": amount,
                    "category": category,
                    "date": current_datetime
                }
                add_response = make_api_request("POST", "/expenses/", data=new_expense_data)
                if add_response:
                    st.success("✅ Expense added successfully!")
                    st.rerun()


elif st.session_state.current_page == "AI Insights":
    st.title("🤖 AI Insights")

    st.header("Spending Analysis")
    col1, col2 = st.columns(2)
    with col1:
        start_date_input = st.date_input("Start Date")
    with col2:
        end_date_input = st.date_input("End Date")

    if st.button("Generate Insights", type="primary"):
        if not start_date_input or not end_date_input:
            st.warning("Please select both start and end dates.")
        else:
            insights_payload = {
                "start_date": f"{start_date_input.isoformat()}T00:00:00Z",
                "end_date": f"{end_date_input.isoformat()}T23:59:59Z",
                "ai_provider": "gemini"
            }
            insights = make_api_request("POST", "/ai/insights/", data=insights_payload)

            if insights:
                if insights.get("anomalies"):
                    st.warning("⚠️ Potential issues found:")
                    for anomaly in insights["anomalies"]:
                        st.write(f"- {anomaly.get('description', 'N/A')}: {anomaly.get('reason', 'No reason provided.')}") # Access specific keys or provide a default error message

                st.subheader("📊 Spending Summary")
                total_spent = insights.get('total_spent', 0.0)
                st.write(f"**Total Spent:** ${total_spent:.2f}")

                top_categories = insights.get('top_categories')
                if top_categories:
                    st.subheader("🔝 Top Categories")

                    if isinstance(top_categories, list):
                        for cat in top_categories:

                            st.write(f"- **{cat.get('category', 'N/A')}**: ${cat.get('amount', 0.0):.2f}")

                else:
                    st.write("No spending data available.")

            else:
                st.error("❌ Failed to generate insights.")


elif st.session_state.current_page == "Logout":
    st.session_state.token = None
    st.session_state.logged_in = False
    st.session_state.current_page = "Login"
    for key in ["user_email_for_otp", "otp_verification_pending"]:
        st.session_state.pop(key, None)
    st.success("✅ Logged out successfully.")
    st.rerun()
