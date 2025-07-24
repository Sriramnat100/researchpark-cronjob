from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import pandas as pd, time
from datetime import date, timedelta
from dotenv import load_dotenv
import os
from send_email import Email
from supabase import create_client, Client
import hashlib
from datetime import datetime




class ExtractListings:

    def __init__(self):
        
        load_dotenv()

        #time sensitive
        self.URL = "https://researchpark.illinois.edu/work-here/careers/"
        self.today_formated = self.formated(date.today())
        self.yesterday_formated = self.formated(date.today() - timedelta(days=1))

        # Supabase setup
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("ANON_KEY")
        self.supabase: Client = create_client(supabase_url, supabase_key)

        #emails
        self.email_password = os.getenv("EMAIL_PASSWORD")



    #Code for formatting everything
    def formated(self,date):
        formatted = f"{date.month}.{date.day}.{str(date.year)[-2:]}"
        return formatted

    
    def formatmsg(self, val):
        if val:
            final_message = ""
            for job in val:
                final_message += (
                    f"📌 {job['title']}\n"
                    f"🏢 Company: {job['company']}\n"
                    f"📅 Posted: {job['date_posted']}\n"
                    f"🔗 Link: {job['link']}\n"
                    f"{'-'*50}\n"
                )
        else:
            final_message = "No new job listings found."
        
        return final_message


    #All the hash related stuff
    def get_job_hash(self, job):
        combo = f"{job['title']}|{job['company']}|{job['link']}"
        return hashlib.sha256(combo.encode()).hexdigest()

    def has_been_sent(self, job):
        try:
            h = self.get_job_hash(job)
            result = self.supabase.table("jobs").select("id").eq("job_hash", h).execute()
            return len(result.data) > 0
        except Exception as e:
            print(f"Error checking if job has been sent: {e}")
            return False

    def mark_as_sent(self, job):
        try:
            h = self.get_job_hash(job)
            # First, insert the job into the jobs table
            job_data = {
                "title": job['title'],
                "company": job['company'],
                "link": job['link'],
                "date_posted": job['date_posted'],
                "job_hash": h
            }
            job_result = self.supabase.table("jobs").insert(job_data).execute()
            
            if job_result.data:
                job_id = job_result.data[0]['id']
                # Get all subscriptions
                subscriptions = self.supabase.table("subscriptions").select("id").execute()
                
                # Batch insert sent_events for all subscriptions
                if subscriptions.data:
                    sent_events = [
                        {
                            "job_id": job_id,
                            "subscription_id": subscription['id']
                        }
                        for subscription in subscriptions.data
                    ]
                    self.supabase.table("sent_events").insert(sent_events).execute()
        except Exception as e:
            print(f"Error marking job as sent: {e}")

    # def add_email(self, email):
    #     try:
    #         # Check if email already exists
    #         result = self.supabase.table("subscriptions").select("id").eq("email", email).execute()
    #         if len(result.data) == 0:
    #             print(f"Adding email: {email}")
    #             self.supabase.table("subscriptions").insert({"email": email}).execute()
    #             return True
    #         else:
    #             print(f"Email {email} already exists")
    #             return False
    #     except Exception as e:
    #         print(f"Error adding email: {e}")
    #         return False

    # def remove_email(self, email):
    #     """Remove an email subscription"""
    #     try:
    #         result = self.supabase.table("subscriptions").delete().eq("email", email).execute()
    #         if result.data:
    #             print(f"Removed email: {email}")
    #             return True
    #         else:
    #             print(f"Email {email} not found")
    #             return False
    #     except Exception as e:
    #         print(f"Error removing email: {e}")
    #         return False

    def get_all_emails(self):
        try:
            result = self.supabase.table("subscriptions").select("email").execute()
            return [entry["email"] for entry in result.data]
        except Exception as e:
            print(f"Error getting emails: {e}")
            return []

    # def get_subscription_count(self):
    #     """Get the total number of email subscriptions"""
    #     try:
    #         result = self.supabase.table("subscriptions").select("id", count="exact").execute()
    #         return result.count if result.count is not None else 0
    #     except Exception as e:
    #         print(f"Error getting subscription count: {e}")
    #         return 0

    # def get_recent_jobs_count(self, days=7):
    #     """Get count of jobs scraped in the last N days"""
    #     try:
    #         from datetime import datetime, timedelta
    #         cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
    #         result = self.supabase.table("jobs").select("id", count="exact").gte("scraped_at", cutoff_date).execute()
    #         return result.count if result.count is not None else 0
    #     except Exception as e:
    #         print(f"Error getting recent jobs count: {e}")
    #         return 0

    def test_connection(self):
        """Test the Supabase connection"""
        try:
            # Simple test - try to get emails
            result = self.supabase.table("subscriptions").select("id").limit(1).execute()
            print(f"✅ Supabase connection successful.")
            return True
        except Exception as e:
            print(f"❌ Supabase connection failed: {e}")
            return False


    #Getting the lists of the jobs on the website
    def getListings(self):
        with sync_playwright() as p:
            #Launches a headless chromium browser
            browser = p.chromium.launch(headless=True)

            #opens a new tab and then goes to the URL that I give it for research park
            page = browser.new_page()
            page.goto(self.URL, timeout=60000)

            #Wait's until One job listing is posted 
            page.wait_for_selector("li.job-listing")

            # Scroll until everything is loaded
            prev_height = 0

            #Keeps scrolling until reaches end of the page
            while True:
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(1)
                curr_height = page.evaluate("document.body.scrollHeight")
                if curr_height == prev_height:
                    break
                prev_height = curr_height

            #Grabbing full page's HTML 
            soup = BeautifulSoup(page.content(), "html.parser")
            browser.close()

        # Parse jobs
        rows = []

        for card in soup.select("li.job-listing"):
            try:

                #Everything in title
                title_tag = card.select_one(".title-sec a")
                title = title_tag.get_text(strip=True)
                link = title_tag["href"]
                date = card.select_one(".posted-on").get_text(strip=True).replace("Posted", "")
                full_title_sec = card.select_one(".title-sec").get_text(strip=True)
                company = full_title_sec.replace(title, "").strip()



                if (str(date) == self.today_formated or str(date) == self.yesterday_formated):
                    
                    # Convert date string to proper date format for PostgreSQL
                    try:
                        # Parse the date string (e.g., "1.15.24") to a proper date
                        date_parts = date.split('.')
                        month = int(date_parts[0])
                        day = int(date_parts[1])
                        year = 2000 + int(date_parts[2])  # Assuming 20xx years
                        parsed_date = f"{year}-{month:02d}-{day:02d}"
                    except:
                        parsed_date = date  # Fallback to original if parsing fails
                    
                    rows.append({
                        "title": title,
                        "company": company,
                        "date_posted": parsed_date,
                        "link": link,
                    })

                else:
                    break
            except Exception as e:
                print(f"Skipping a card due to error: {e}")


        return rows
    
    def sendEmails(self):
        print(f"Starting job scraping at {datetime.now()}")
        
        #Getting the recent jobs from the listings
        jobs = self.getListings()
        print(f"Found {len(jobs)} recent job listings")
        
        to_send = []

        #Checking if jobs have been sent before
        for job in jobs:
            if not self.has_been_sent(job):
                to_send.append(job)
                self.mark_as_sent(job)
        
        email_list = self.get_all_emails()
        print(f"Found {len(email_list)} email subscribers")

        #If there are any new jobs go ahead and send them
        if (to_send):
            print(f"Sending {len(to_send)} new jobs to {len(email_list)} subscribers")
            emaildraft = self.formatmsg(to_send)    
            emailer = Email(self.email_password)

            for address in email_list:
                emailer.send_email("kingicydiamond@gmail.com", address, "Research Park Internship Drop", emaildraft)
                print(f"Email successfully sent to {address}")
        else:
            print("No new jobs to send")



if __name__ == "__main__":
    tester = ExtractListings()
    
    # Test connection first
    if tester.test_connection():
        tester.sendEmails()
    else:
        print("Failed to connect to Supabase. Exiting.")

   




