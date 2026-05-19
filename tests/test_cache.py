from datetime import datetime, timedelta

from md_leads.cache import SQLiteCache


def test_cache_miss_then_hit(tmp_path):
    db = tmp_path / "cache.db"
    cache = SQLiteCache(db, ttl_days=30)
    assert cache.is_recent("Frizeria X", "+373 22 000 000") is False
    cache.mark_seen("Frizeria X", "+373 22 000 000")
    assert cache.is_recent("Frizeria X", "+373 22 000 000") is True


def test_cache_phone_none_uses_name_only(tmp_path):
    cache = SQLiteCache(tmp_path / "c.db", ttl_days=30)
    cache.mark_seen("X", None)
    assert cache.is_recent("X", None) is True


def test_cache_expired_when_older_than_ttl(tmp_path):
    cache = SQLiteCache(tmp_path / "c.db", ttl_days=30)
    cache.mark_seen("X", "+1", seen_at=datetime.now() - timedelta(days=40))
    assert cache.is_recent("X", "+1") is False


def test_cache_stats(tmp_path):
    cache = SQLiteCache(tmp_path / "c.db", ttl_days=30)
    cache.mark_seen("A", "+1")
    cache.mark_seen("B", "+2")
    stats = cache.stats()
    assert stats["total"] == 2
    assert stats["recent"] == 2


def test_cache_clear(tmp_path):
    cache = SQLiteCache(tmp_path / "c.db", ttl_days=30)
    cache.mark_seen("A", "+1")
    cache.clear()
    assert cache.stats()["total"] == 0
