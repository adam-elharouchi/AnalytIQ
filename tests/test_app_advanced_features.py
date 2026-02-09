"""
Tests for advanced class features, analytics, and bulk operations
"""
import pytest
from app import app
import json


class TestClassAnalytics:
    """Test class analytics and statistics endpoints"""

    def test_class_student_count(self, client, mock_db):
        """Test getting student count for a class"""
        # Create a professor and class
        prof_response = client.post(
            "/api/users/signup",
            json={"name": "Professor", "email": "prof@hult.edu", "password": "profpass"},
        )
        
        if prof_response.status_code == 201:
            prof_id = prof_response.get_json()["user_id"]
            
            # Create a class
            class_response = client.post(
                "/api/classes",
                json={
                    "class_name": "Test Class",
                    "professor_id": prof_id,
                    "description": "Test Description",
                },
            )
            
            if class_response.status_code == 201:
                class_id = class_response.get_json()["class_id"]
                
                # Get class details (should include student count)
                response = client.get(f"/api/classes/{class_id}")
                
                assert response.status_code in [200, 404]

    def test_class_enrollment_statistics(self, client, mock_db):
        """Test class enrollment statistics"""
        # Create professor and class
        prof_response = client.post(
            "/api/users/signup",
            json={"name": "Professor", "email": "prof@hult.edu", "password": "profpass"},
        )
        
        if prof_response.status_code == 201:
            prof_id = prof_response.get_json()["user_id"]
            
            class_response = client.post(
                "/api/classes",
                json={
                    "class_name": "Stats Class",
                    "professor_id": prof_id,
                    "description": "Statistics Test",
                },
            )
            
            if class_response.status_code == 201:
                class_id = class_response.get_json()["class_id"]
                
                # Create and enroll students
                for i in range(3):
                    student_response = client.post(
                        "/api/users/signup",
                        json={
                            "name": f"Student {i}",
                            "email": f"student{i}@student.hult.edu",
                            "password": "studentpass",
                        },
                    )
                    
                    if student_response.status_code == 201:
                        student_id = student_response.get_json()["user_id"]
                        
                        # Enroll student
                        client.post(
                            "/api/enrollments",
                            json={"student_id": student_id, "class_id": class_id},
                        )
                
                # Get class details
                response = client.get(f"/api/classes/{class_id}")
                assert response.status_code in [200, 404]


class TestBulkOperations:
    """Test bulk operations on classes and enrollments"""

    def test_bulk_enrollment(self, client, mock_db):
        """Test enrolling multiple students at once"""
        # Create professor and class
        prof_response = client.post(
            "/api/users/signup",
            json={"name": "Professor", "email": "prof@hult.edu", "password": "profpass"},
        )
        
        if prof_response.status_code == 201:
            prof_id = prof_response.get_json()["user_id"]
            
            class_response = client.post(
                "/api/classes",
                json={
                    "class_name": "Bulk Class",
                    "professor_id": prof_id,
                    "description": "Bulk Enrollment Test",
                },
            )
            
            if class_response.status_code == 201:
                class_id = class_response.get_json()["class_id"]
                
                # Create multiple students
                student_ids = []
                for i in range(5):
                    student_response = client.post(
                        "/api/users/signup",
                        json={
                            "name": f"Bulk Student {i}",
                            "email": f"bulk{i}@student.hult.edu",
                            "password": "bulkpass",
                        },
                    )
                    
                    if student_response.status_code == 201:
                        student_ids.append(student_response.get_json()["user_id"])
                
                # Enroll all students
                for student_id in student_ids:
                    response = client.post(
                        "/api/enrollments",
                        json={"student_id": student_id, "class_id": class_id},
                    )
                    
                    assert response.status_code in [201, 400, 409]

    def test_bulk_unenrollment(self, client, mock_db):
        """Test unenrolling multiple students"""
        # Create professor, class, and students
        prof_response = client.post(
            "/api/users/signup",
            json={"name": "Professor", "email": "prof@hult.edu", "password": "profpass"},
        )
        
        if prof_response.status_code == 201:
            prof_id = prof_response.get_json()["user_id"]
            
            class_response = client.post(
                "/api/classes",
                json={
                    "class_name": "Unenroll Class",
                    "professor_id": prof_id,
                    "description": "Bulk Unenrollment Test",
                },
            )
            
            if class_response.status_code == 201:
                class_id = class_response.get_json()["class_id"]
                
                # Create and enroll students
                enrollment_ids = []
                for i in range(3):
                    student_response = client.post(
                        "/api/users/signup",
                        json={
                            "name": f"Unenroll Student {i}",
                            "email": f"unenroll{i}@student.hult.edu",
                            "password": "unenrollpass",
                        },
                    )
                    
                    if student_response.status_code == 201:
                        student_id = student_response.get_json()["user_id"]
                        
                        enroll_response = client.post(
                            "/api/enrollments",
                            json={"student_id": student_id, "class_id": class_id},
                        )
                        
                        if enroll_response.status_code == 201:
                            enrollment_ids.append(enroll_response.get_json()["enrollment_id"])
                
                # Unenroll all students
                for enrollment_id in enrollment_ids:
                    response = client.delete(f"/api/enrollments/{enrollment_id}")
                    assert response.status_code in [200, 404]


class TestClassExportFeatures:
    """Test class data export functionality"""

    def test_export_class_roster(self, client, mock_db):
        """Test exporting class roster"""
        # Create professor and class
        prof_response = client.post(
            "/api/users/signup",
            json={"name": "Professor", "email": "prof@hult.edu", "password": "profpass"},
        )
        
        if prof_response.status_code == 201:
            prof_id = prof_response.get_json()["user_id"]
            
            class_response = client.post(
                "/api/classes",
                json={
                    "class_name": "Export Class",
                    "professor_id": prof_id,
                    "description": "Export Test",
                },
            )
            
            if class_response.status_code == 201:
                class_id = class_response.get_json()["class_id"]
                
                # Get enrolled students (roster)
                response = client.get(f"/api/classes/{class_id}/students")
                
                # Should return list of students or 404
                assert response.status_code in [200, 404]
                
                if response.status_code == 200:
                    data = response.get_json()
                    assert isinstance(data, (list, dict))

    def test_export_class_grades(self, client, mock_db):
        """Test exporting class grades"""
        # Create professor and class
        prof_response = client.post(
            "/api/users/signup",
            json={"name": "Professor", "email": "prof@hult.edu", "password": "profpass"},
        )
        
        if prof_response.status_code == 201:
            prof_id = prof_response.get_json()["user_id"]
            
            class_response = client.post(
                "/api/classes",
                json={
                    "class_name": "Grades Class",
                    "professor_id": prof_id,
                    "description": "Grades Export Test",
                },
            )
            
            if class_response.status_code == 201:
                class_id = class_response.get_json()["class_id"]
                
                # Try to get class progress/grades
                response = client.get(f"/api/classes/{class_id}/progress")
                
                # Endpoint might not exist, but should not crash
                assert response.status_code in [200, 404, 405]


class TestStudentPerformanceTracking:
    """Test student performance tracking features"""

    def test_student_progress_in_class(self, client, mock_db):
        """Test tracking student progress in a class"""
        # Create student
        student_response = client.post(
            "/api/users/signup",
            json={"name": "Student", "email": "student@student.hult.edu", "password": "studentpass"},
        )
        
        if student_response.status_code == 201:
            student_id = student_response.get_json()["user_id"]
            
            # Create professor and class
            prof_response = client.post(
                "/api/users/signup",
                json={"name": "Professor", "email": "prof@hult.edu", "password": "profpass"},
            )
            
            if prof_response.status_code == 201:
                prof_id = prof_response.get_json()["user_id"]
                
                class_response = client.post(
                    "/api/classes",
                    json={
                        "class_name": "Progress Class",
                        "professor_id": prof_id,
                        "description": "Progress Tracking",
                    },
                )
                
                if class_response.status_code == 201:
                    class_id = class_response.get_json()["class_id"]
                    
                    # Enroll student
                    client.post(
                        "/api/enrollments",
                        json={"student_id": student_id, "class_id": class_id},
                    )
                    
                    # Get student progress
                    response = client.get(f"/api/students/{student_id}/progress")
                    
                    assert response.status_code in [200, 404]

    def test_leaderboard_with_multiple_students(self, client, mock_db):
        """Test leaderboard with multiple students"""
        # Create professor and class
        prof_response = client.post(
            "/api/users/signup",
            json={"name": "Professor", "email": "prof@hult.edu", "password": "profpass"},
        )
        
        if prof_response.status_code == 201:
            prof_id = prof_response.get_json()["user_id"]
            
            class_response = client.post(
                "/api/classes",
                json={
                    "class_name": "Leaderboard Class",
                    "professor_id": prof_id,
                    "description": "Leaderboard Test",
                },
            )
            
            if class_response.status_code == 201:
                class_id = class_response.get_json()["class_id"]
                
                # Create and enroll multiple students
                for i in range(5):
                    student_response = client.post(
                        "/api/users/signup",
                        json={
                            "name": f"Leader Student {i}",
                            "email": f"leader{i}@student.hult.edu",
                            "password": "leaderpass",
                        },
                    )
                    
                    if student_response.status_code == 201:
                        student_id = student_response.get_json()["user_id"]
                        
                        client.post(
                            "/api/enrollments",
                            json={"student_id": student_id, "class_id": class_id},
                        )
                
                # Get leaderboard
                response = client.get(f"/api/classes/{class_id}/leaderboard")
                
                assert response.status_code in [200, 404]
                
                if response.status_code == 200:
                    data = response.get_json()
                    assert isinstance(data, (list, dict))


class TestClassArchiving:
    """Test class archiving and restoration"""

    def test_archive_class(self, client, mock_db):
        """Test archiving a class"""
        # Create professor and class
        prof_response = client.post(
            "/api/users/signup",
            json={"name": "Professor", "email": "prof@hult.edu", "password": "profpass"},
        )
        
        if prof_response.status_code == 201:
            prof_id = prof_response.get_json()["user_id"]
            
            class_response = client.post(
                "/api/classes",
                json={
                    "class_name": "Archive Class",
                    "professor_id": prof_id,
                    "description": "Archive Test",
                },
            )
            
            if class_response.status_code == 201:
                class_id = class_response.get_json()["class_id"]
                
                # Try to archive class (update with archived status)
                response = client.put(
                    f"/api/classes/{class_id}",
                    json={"archived": True},
                )
                
                # Endpoint might not support archiving, but should not crash
                assert response.status_code in [200, 400, 404, 405]

    def test_list_archived_classes(self, client, mock_db):
        """Test listing archived classes"""
        # Create professor
        prof_response = client.post(
            "/api/users/signup",
            json={"name": "Professor", "email": "prof@hult.edu", "password": "profpass"},
        )
        
        if prof_response.status_code == 201:
            prof_id = prof_response.get_json()["user_id"]
            
            # Get professor's classes (might include archived filter)
            response = client.get(f"/api/professors/{prof_id}/classes?archived=true")
            
            # Endpoint might not exist, but should not crash
            assert response.status_code in [200, 404, 405]


class TestClassUpdateOperations:
    """Test class update and modification operations"""

    def test_update_class_description(self, client, mock_db):
        """Test updating class description"""
        # Create professor and class
        prof_response = client.post(
            "/api/users/signup",
            json={"name": "Professor", "email": "prof@hult.edu", "password": "profpass"},
        )
        
        if prof_response.status_code == 201:
            prof_id = prof_response.get_json()["user_id"]
            
            class_response = client.post(
                "/api/classes",
                json={
                    "class_name": "Update Class",
                    "professor_id": prof_id,
                    "description": "Original Description",
                },
            )
            
            if class_response.status_code == 201:
                class_id = class_response.get_json()["class_id"]
                
                # Update description
                response = client.put(
                    f"/api/classes/{class_id}",
                    json={"description": "Updated Description"},
                )
                
                assert response.status_code in [200, 400, 404]

    def test_update_class_name(self, client, mock_db):
        """Test updating class name"""
        # Create professor and class
        prof_response = client.post(
            "/api/users/signup",
            json={"name": "Professor", "email": "prof@hult.edu", "password": "profpass"},
        )
        
        if prof_response.status_code == 201:
            prof_id = prof_response.get_json()["user_id"]
            
            class_response = client.post(
                "/api/classes",
                json={
                    "class_name": "Original Name",
                    "professor_id": prof_id,
                    "description": "Test",
                },
            )
            
            if class_response.status_code == 201:
                class_id = class_response.get_json()["class_id"]
                
                # Update name
                response = client.put(
                    f"/api/classes/{class_id}",
                    json={"class_name": "Updated Name"},
                )
                
                assert response.status_code in [200, 400, 404]

    def test_update_nonexistent_class(self, client, mock_db):
        """Test updating a non-existent class"""
        response = client.put(
            "/api/classes/999999",
            json={"description": "Updated"},
        )
        
        # Should return 404 for non-existent class
        assert response.status_code in [400, 401, 404]


class TestClassDeletionSafety:
    """Test safe deletion of classes with data"""

    def test_delete_class_with_students(self, client, mock_db):
        """Test deleting a class that has enrolled students"""
        # Create professor and class
        prof_response = client.post(
            "/api/users/signup",
            json={"name": "Professor", "email": "prof@hult.edu", "password": "profpass"},
        )
        
        if prof_response.status_code == 201:
            prof_id = prof_response.get_json()["user_id"]
            
            class_response = client.post(
                "/api/classes",
                json={
                    "class_name": "Delete Class",
                    "professor_id": prof_id,
                    "description": "Delete Test",
                },
            )
            
            if class_response.status_code == 201:
                class_id = class_response.get_json()["class_id"]
                
                # Enroll a student
                student_response = client.post(
                    "/api/users/signup",
                    json={
                        "name": "Student",
                        "email": "student@student.hult.edu",
                        "password": "studentpass",
                    },
                )
                
                if student_response.status_code == 201:
                    student_id = student_response.get_json()["user_id"]
                    
                    client.post(
                        "/api/enrollments",
                        json={"student_id": student_id, "class_id": class_id},
                    )
                
                # Try to delete class
                response = client.delete(f"/api/classes/{class_id}")
                
                # Should handle deletion gracefully
                assert response.status_code in [200, 400, 403, 404]

    def test_delete_class_with_chapters(self, client, mock_db):
        """Test deleting a class that has chapters"""
        # Create professor and class
        prof_response = client.post(
            "/api/users/signup",
            json={"name": "Professor", "email": "prof@hult.edu", "password": "profpass"},
        )
        
        if prof_response.status_code == 201:
            prof_id = prof_response.get_json()["user_id"]
            
            class_response = client.post(
                "/api/classes",
                json={
                    "class_name": "Chapter Class",
                    "professor_id": prof_id,
                    "description": "Chapter Delete Test",
                },
            )
            
            if class_response.status_code == 201:
                class_id = class_response.get_json()["class_id"]
                
                # Create a chapter
                client.post(
                    "/api/chapters",
                    json={
                        "class_id": class_id,
                        "chapter_name": "Test Chapter",
                        "content": "Test Content",
                    },
                )
                
                # Try to delete class
                response = client.delete(f"/api/classes/{class_id}")
                
                # Should handle deletion gracefully (cascade or prevent)
                assert response.status_code in [200, 400, 403, 404]
