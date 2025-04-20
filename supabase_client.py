import os
from supabase import create_client, Client
import pytz
from datetime import datetime
import random

# Get Supabase credentials from environment variables
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Collection of Bamba facts for the enhanced subscription
BAMBA_FACTS = [
    "Bamba was first produced in Israel in 1964 by the Osem company.",
    "Bamba is made from peanut butter-flavored puffed corn and contains 50% peanuts.",
    "Studies suggest early exposure to peanut products like Bamba may help prevent peanut allergies in children.",
    "Bamba is the best-selling snack in Israel, with 90% of Israeli families buying it regularly.",
    "The Bamba Baby, the brand's mascot since 1992, is a diapered baby with red hair.",
    "Bamba contains no preservatives, food coloring, or artificial flavors.",
    "The original Bamba factory is located in Holon, Israel.",
    "Over 1 million bags of Bamba are produced daily.",
    "Sweet Bamba varieties include strawberry, halva, and nougat flavors.",
    "In Israel, Bamba is often a baby's first solid food."
]

def get_random_bamba_fact():
    """Return a random fact about Bamba."""
    return random.choice(BAMBA_FACTS)

def get_supabase_client() -> Client:
    """Get a Supabase client instance."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError("Supabase credentials not found in environment variables")
    
    return create_client(SUPABASE_URL, SUPABASE_KEY)

def add_subscriber(email: str, preferences: dict) -> dict:
    """Add a new subscriber to the database.
    
    Args:
        email: The subscriber's email address
        preferences: Dictionary containing subscriber preferences:
            - mode: Either 'immediate' or 'daily'
            - product_size_preference: '25g', '100g', or 'both'
            - store_preference: 'dianella', 'mirrabooka', or 'both'
            - notify_on_change_only: True or False
            - include_facts: True or False
        
    Returns:
        The created subscriber data
    """
    client = get_supabase_client()
    
    # Check if subscriber already exists
    existing = client.table("subscribers").select("*").eq("email", email).execute()
    
    # Set default values for any missing preferences
    preferences.setdefault("mode", "immediate")
    preferences.setdefault("product_size_preference", "both")
    preferences.setdefault("store_preference", "both")
    preferences.setdefault("notify_on_change_only", False)
    preferences.setdefault("include_facts", False)
    
    # Prepare subscriber data
    subscriber_data = {
        "email": email,
        "mode": preferences["mode"],
        "product_size_preference": preferences["product_size_preference"],
        "store_preference": preferences["store_preference"],
        "notify_on_change_only": preferences["notify_on_change_only"],
        "include_facts": preferences["include_facts"]
    }
    
    if existing.data:
        # Update existing subscriber
        result = client.table("subscribers").update(subscriber_data).eq("email", email).execute()
        return {"success": True, "data": result.data[0], "status": "updated"}
    
    # Add new subscriber
    result = client.table("subscribers").insert(subscriber_data).execute()
    return {"success": True, "data": result.data[0], "status": "created"}

def get_subscribers(mode=None):
    """Get all subscribers, optionally filtered by mode.
    
    Args:
        mode: Optional filter for notification mode ('immediate' or 'daily')
        
    Returns:
        List of subscriber data
    """
    client = get_supabase_client()
    query = client.table("subscribers").select("*")
    
    if mode:
        query = query.eq("mode", mode)
        
    result = query.execute()
    return result.data

def get_awst_time():
    """Get current time in Australian Western Standard Time (AWST)."""
    utc_now = datetime.now(pytz.utc)
    awst = pytz.timezone('Australia/Perth')  # Perth uses AWST
    return utc_now.astimezone(awst)

def is_within_operating_hours(config):
    """Check if current AWST time is within operating hours."""
    awst_now = get_awst_time()
    hour = awst_now.hour
    return config["operating_hours"]["start"] <= hour < config["operating_hours"]["end"]
