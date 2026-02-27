"""
Milestone 1 Validation Script
Проверяет критерии готовности Milestone 1
"""

def test_config_loading():
    """Test config loading."""
    print("✅ Testing Config Loading...")
    try:
        from config.settings import Settings
        settings = Settings()
        
        # Test profile loading
        profile = settings.load_profile()
        assert profile is not None, "Profile не загружен"
        assert profile.name is not None, "Profile.name не установлен"
        print(f"   ✓ Profile loaded: {profile.name}")
        
        # Test scoring rules loading
        rules = settings.load_scoring_rules()
        assert rules is not None, "Scoring rules не загружены"
        assert 'scoring' in rules, "Ключ 'scoring' не найден"
        assert rules['scoring']['max_points']['tfidf_similarity'] == 35
        print(f"   ✓ Scoring rules loaded: TF-IDF max = {rules['scoring']['max_points']['tfidf_similarity']}")
        
        # Test tech dictionary loading
        tech_dict = settings.load_tech_dictionary()
        assert tech_dict is not None, "Tech dictionary не загружен"
        assert len(tech_dict) > 0, "Tech dictionary пустой"
        print(f"   ✓ Tech dictionary loaded: {len(tech_dict)} categories")
        
        return True
    except Exception as e:
        print(f"   ✗ FAILED: {e}")
        return False


def test_pydantic_models():
    """Test Pydantic models validation."""
    print("\n✅ Testing Pydantic Models...")
    try:
        from models.job import Job
        from datetime import datetime
        
        job = Job(
            id="test-milestone-1",
            title="Full Stack Engineer",
            company="Test GmbH",
            location="Berlin",
            remote_type="Remote",
            contract_type="Festanstellung",
            url="https://example.com/job",
            description="This is a test job description for validation purposes.",
            posted_date=datetime.now(),
            source="validation"
        )
        
        assert job.remote_type == "Remote"
        assert job.title == "Full Stack Engineer"
        print(f"   ✓ Job model created: {job.title} at {job.company}")
        
        # Test Job methods
        age = job.get_age_days()
        assert age == 0, f"Age should be 0, got {age}"
        print(f"   ✓ Job.get_age_days() works: {age} days")
        
        is_fresh = job.is_fresh(max_age_days=7)
        assert is_fresh is True
        print(f"   ✓ Job.is_fresh() works: {is_fresh}")
        
        # Test Profile model
        from models.profile import Profile
        profile = Profile(
            name="Test User",
            roles=["Backend Developer"],
            skills={"languages": ["Python", "C#"]},
            preferences={"remote": "100%", "min_score": 65},
            profile_text="Experienced backend developer with expertise in Python, C# and modern web frameworks"
        )
        
        min_score = profile.get_min_score()
        assert min_score == 65
        print(f"   ✓ Profile.get_min_score() works: {min_score}")
        
        is_remote = profile.is_remote_preferred()
        assert is_remote is True
        print(f"   ✓ Profile.is_remote_preferred() works: {is_remote}")
        
        return True
    except Exception as e:
        print(f"   ✗ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_logger():
    """Test logger setup."""
    print("\n✅ Testing Logger...")
    try:
        from utils.logger import setup_logging, get_logger
        
        # Setup logging
        setup_logging(log_level="INFO", log_to_file=False)
        
        # Get logger
        logger = get_logger("validation")
        logger.info("Test message from validation script")
        print("   ✓ Logger initialized and message logged")
        
        return True
    except Exception as e:
        print(f"   ✗ FAILED: {e}")
        return False


def test_cache_manager():
    """Test cache manager."""
    print("\n✅ Testing Cache Manager...")
    try:
        from cache.manager import CacheManager
        import tempfile
        
        # Create cache with temp directory
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheManager(cache_dir=tmpdir, ttl_hours=1, enabled=True)
            
            # Test set/get
            cache.set("test_key", {"data": "value"}, ttl_hours=24)
            result = cache.get("test_key")
            assert result is not None, "Cache.get() returned None"
            assert result["data"] == "value", f"Expected 'value', got {result['data']}"
            print(f"   ✓ Cache set/get works: {result}")
            
            # Test exists
            exists = cache.exists("test_key")
            assert exists is True
            print(f"   ✓ Cache.exists() works: {exists}")
            
            # Test stats
            stats = cache.get_stats()
            assert stats["enabled"] is True
            print(f"   ✓ Cache stats: {stats}")
            
            cache.close()
        
        return True
    except Exception as e:
        print(f"   ✗ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_rate_limiter():
    """Test rate limiter."""
    print("\n✅ Testing Rate Limiter...")
    try:
        from utils.rate_limiter import RateLimiter
        import time
        
        # Create rate limiter with 0.5s delay
        limiter = RateLimiter(min_delay_seconds=0.5)
        
        # Make first request
        start = time.time()
        limiter.wait("test_source")
        
        # Make second request (should delay)
        limiter.wait("test_source")
        elapsed = time.time() - start
        
        # Should take at least 0.5 seconds
        assert elapsed >= 0.5, f"Expected delay >= 0.5s, got {elapsed:.2f}s"
        print(f"   ✓ Rate limiter works: {elapsed:.2f}s delay")
        
        # Test stats
        stats = limiter.get_stats("test_source")
        assert stats["total_requests"] == 2
        print(f"   ✓ Rate limiter stats: {stats['total_requests']} requests")
        
        return True
    except Exception as e:
        print(f"   ✗ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all validation tests."""
    print("=" * 60)
    print("Milestone 1 Validation")
    print("=" * 60)
    
    results = []
    
    # Run tests
    results.append(("Config Loading", test_config_loading()))
    results.append(("Pydantic Models", test_pydantic_models()))
    results.append(("Logger", test_logger()))
    results.append(("Cache Manager", test_cache_manager()))
    results.append(("Rate Limiter", test_rate_limiter()))
    
    # Summary
    print("\n" + "=" * 60)
    print("Validation Summary")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{name:.<50} {status}")
    
    print("=" * 60)
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 Milestone 1 Validation SUCCESSFUL!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Check errors above.")
        return 1


if __name__ == "__main__":
    exit(main())
