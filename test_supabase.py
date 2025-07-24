from supabase import create_client, Client
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Supabase setup
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(supabase_url, supabase_key)

def add_test_email():
    """Add the test email to Supabase"""
    try:
        email = "reriyin946@dosonex.com"
        
        # Check if email already exists
        result = supabase.table("subscriptions").select("id").eq("email", email).execute()
        
        if len(result.data) == 0:
            # Add the email
            insert_result = supabase.table("subscriptions").insert({"email": email}).execute()
            print(f"✅ Successfully added email: {email}")
            print(f"Subscription ID: {insert_result.data[0]['id']}")
        else:
            print(f"📧 Email {email} already exists in database")
            
        # Get all emails to verify
        all_emails = supabase.table("subscriptions").select("email").execute()
        print(f"📊 Total emails in database: {len(all_emails.data)}")
        for entry in all_emails.data:
            print(f"  - {entry['email']}")
            
    except Exception as e:
        print(f"❌ Error adding email: {e}")

def test_connection():
    """Test the Supabase connection"""
    try:
        result = supabase.table("subscriptions").select("id").limit(1).execute()
        print("✅ Supabase connection successful!")
        return True
    except Exception as e:
        print(f"❌ Supabase connection failed: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Testing Supabase Connection and Adding Email...")
    print("=" * 50)
    
    if test_connection():
        add_test_email()
        
    print("\n🎯 Now you can run the main script to test email sending:")
    print("python extractor.py") 