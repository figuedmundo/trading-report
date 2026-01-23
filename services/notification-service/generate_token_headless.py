import os
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# If modifying these scopes, delete the file token.pickle.
SCOPES = ["https://www.googleapis.com/auth/gmail.send"]


def main():
    creds = None
    token_path = "token.pickle"

    if os.path.exists(token_path):
        try:
            with open(token_path, "rb") as token:
                creds = pickle.load(token)
        except Exception as e:
            print(f"Warning: Could not read existing token: {e}")

    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Refreshing expired token...")
            try:
                creds.refresh(Request())
            except Exception as e:
                print(f"Refresh failed: {e}. Initiating new login.")
                creds = None

        if not creds:
            if not os.path.exists("credentials.json"):
                print("ERROR: credentials.json not found!")
                print("Please ensure 'credentials.json' is in the current directory.")
                return

            print("\n=== GOOGLE AUTHENTICATION ===")
            print("1. Copy the URL below.")
            print("2. Paste it into your browser.")
            print("3. Login and authorize the app.")
            print("4. Copy the code provided by Google.")
            print("5. Paste the code back here.")
            print("=============================\n")

            # Use the newer console flow logic manually since run_console is deprecated
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)

            # 1. Generate the authorization URL
            # prompt='consent' forces a refresh token to be returned
            auth_url, _ = flow.authorization_url(prompt="consent")

            print(f"Please visit this URL to authorize this application: {auth_url}")
            print("\n")

            # 2. Get the authorization code from the user
            code = input("Enter the authorization code: ")

            # 3. Exchange the code for credentials
            flow.fetch_token(code=code)
            creds = flow.credentials

        # Save the credentials for the next run
        print(f"\nSaving credentials to {token_path}...")
        with open(token_path, "wb") as token:
            pickle.dump(creds, token)
        print("Success! token.pickle created/updated.")


if __name__ == "__main__":
    main()
