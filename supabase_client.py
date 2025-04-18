import os
from supabase import create_client, Client
import pytz
from datetime import datetime

# Get Supabase credentials from environment variables
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

def get_supabase_client() -> Client:
    """Get a Supabase client instance."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError("Supabase credentials not found in environment variables")
    
    return create_client(SUPABASE_URL, SUPABASE_KEY)

def add_subscriber(email: str, mode: str) -> dict:
    """Add a new subscriber to the database.
    
    Args:
        email: The subscriber's email address
        mode: Either 'immediate' or 'daily'
        
    Returns:
        The created subscriber data
    """
    client = get_supabase_client()
    
    # Check if subscriber already exists
    existing = client.table("subscribers").select("*").eq("email", email).execute()
    
    if existing.data:
        # Update existing subscriber
        result = client.table("subscribers").update({"mode": mode}).eq("email", email).execute()
        return {"success": True, "data": result.data[0], "status": "updated"}
    
    # Add new subscriber
    result = client.table("subscribers").insert({"email": email, "mode": mode}).execute()
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
