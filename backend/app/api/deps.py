from supabase import Client

from app.db.client import get_supabase as _get_supabase


def get_db() -> Client:
    return _get_supabase()