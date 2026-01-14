"""
Test script for Phase 1: Role Detection
Tests the role detection logic without requiring database connection
"""
import sys
import os

# Add app.py to path to import detect_role_from_email
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_role_detection():
    """Test the role detection function"""
    from app import detect_role_from_email
    
    test_cases = [
        # (email, expected_role)
        ('professor@hult.edu', 'professor'),
        ('john.doe@hult.edu', 'professor'),
        ('teacher@faculty.hult.edu', 'professor'),
        ('student@student.hult.edu', 'student'),
        ('jane.smith@student.hult.edu', 'student'),
        ('unknown@example.com', 'student'),  # Default
        ('', 'student'),  # Empty email
        (None, 'student'),  # None email
    ]
    
    print("Testing Role Detection Logic")
    print("=" * 50)
    
    passed = 0
    failed = 0
    
    for email, expected_role in test_cases:
        try:
            result = detect_role_from_email(email)
            if result == expected_role:
                print(f"✓ PASS: {email or 'None'} -> {result}")
                passed += 1
            else:
                print(f"✗ FAIL: {email or 'None'} -> {result} (expected {expected_role})")
                failed += 1
        except Exception as e:
            print(f"✗ ERROR: {email or 'None'} -> Exception: {e}")
            failed += 1
    
    print("=" * 50)
    print(f"Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("\n✅ All role detection tests passed!")
        return True
    else:
        print(f"\n❌ {failed} test(s) failed")
        return False

if __name__ == "__main__":
    success = test_role_detection()
    sys.exit(0 if success else 1)
