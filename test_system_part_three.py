import time
import sys
from pathlib import Path

# ייבוא הלקוח שלנו
from client.client import GeminiExplainerClient

def run_tests():
    print("--- Starting System Test ---")
    
    # אתחול הלקוח
    client = GeminiExplainerClient(base_url="http://127.0.0.1:5000")
    
    # בחירת קובץ לבדיקה
    test_file = Path("test_presentation.pptx")
    
    if not test_file.exists():
        print(f"Error: Please place a valid PowerPoint file named '{test_file.name}' in this directory to run the tests.")
        sys.exit(1)
        
    # --- טסט 1: העלאה אנונימית ---
    print("\n1. Testing Anonymous Upload...")
    uid_anon = client.upload(str(test_file))
    print(f"   Success! Anonymous UID generated: {uid_anon}")
    
    # --- טסט 2: העלאה עם אימייל ---
    test_email = "pro_user@example.com"
    print(f"\n2. Testing Upload with Email ({test_email})...")
    uid_email = client.upload(str(test_file), email=test_email)
    print(f"   Success! Email UID generated: {uid_email}")
    
    # --- טסט 3: בדיקת סטטוס לפי UID ---
    print("\n3. Testing Status Check by UID...")
    status_anon = client.status(uid=uid_anon)
    print(f"   Status for {uid_anon}: '{status_anon.status}'")
    
    # --- טסט 4: בדיקת סטטוס לפי אימייל ושם קובץ ---
    print("\n4. Testing Status Check by Email & Filename...")
    status_email = client.status(filename=test_file.name, email=test_email)
    print(f"   Status for {test_email}'s '{test_file.name}': '{status_email.status}'")
    
    # מוודאים שקיבלנו זמני העלאה מה-DB
    print(f"   Upload Time recorded: {status_email.upload_time}")
    
    # --- טסט 5: המתנה לסיום העיבוד (Polling) ---
    print("\n5. Waiting for the Explainer to finish processing the anonymous file...")
    print("   (Make sure 'api/app.py' and 'explainer/explainer.py' are running!)")
    
    max_retries = 50 # ננסה 15 פעמים (קצת יותר מדקה)
    for i in range(max_retries):
        current_status = client.status(uid=uid_anon)
        
        if current_status.is_done():
            print(f"\n   Processing DONE!")
            print(f"   Finish Time: {current_status.finish_time}")
            
            # הדפסת התחלת ההסבר (כדי לא להציף את המסך)
            explanation_preview = str(current_status.explanation)[:150]
            print(f"   Explanation Preview: {explanation_preview}...\n")
            break
            
        elif current_status.status == "failed":
            print(f"\n   Processing FAILED! Error Message: {current_status.error_message}")
            break
            
        else:
            print(f"   Current status: '{current_status.status}'... checking again in 5 seconds.")
            time.sleep(5)
    else:
        print("\n   Timeout reached! The Explainer might not be running or is taking too long.")
        
    print("--- Tests Completed ---")

if __name__ == "__main__":
    run_tests()
