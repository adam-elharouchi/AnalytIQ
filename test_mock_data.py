#!/usr/bin/env python3
"""
Mock Data Generator for Testing
Creates mock data for testing without requiring database connection
"""

import json
from datetime import datetime, timedelta
import random
import string

def generate_class_code():
    """Generate a random 6-character class code"""
    letters = ''.join(random.choices(string.ascii_uppercase, k=3))
    numbers = ''.join(random.choices(string.digits, k=3))
    return letters + numbers

def generate_user_id():
    """Generate a random user ID"""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=12))

# Mock Professor Data
mock_professors = [
    {
        "user_id": "prof001",
        "name": "Dr. Sarah Johnson",
        "email": "sarah.johnson@hult.edu",
        "role": "professor"
    },
    {
        "user_id": "prof002",
        "name": "Prof. Michael Chen",
        "email": "michael.chen@faculty.hult.edu",
        "role": "professor"
    }
]

# Mock Student Data
mock_students = [
    {
        "user_id": "stud001",
        "name": "John Doe",
        "email": "john.doe@student.hult.edu",
        "role": "student"
    },
    {
        "user_id": "stud002",
        "name": "Jane Smith",
        "email": "jane.smith@student.hult.edu",
        "role": "student"
    },
    {
        "user_id": "stud003",
        "name": "Alex Brown",
        "email": "alex.brown@student.hult.edu",
        "role": "student"
    }
]

# Mock Classes
mock_classes = [
    {
        "class_id": "ABC123",
        "name": "Business Analytics 101",
        "description": "Introduction to Business Analytics and Data-Driven Decision Making",
        "professor_id": "prof001",
        "professor_name": "Dr. Sarah Johnson",
        "created_at": (datetime.now() - timedelta(days=30)).isoformat(),
        "student_count": 2,
        "chapter_count": 3,
        "exercise_count": 8
    },
    {
        "class_id": "XYZ789",
        "name": "Advanced Data Science",
        "description": "Advanced techniques in data science and machine learning",
        "professor_id": "prof002",
        "professor_name": "Prof. Michael Chen",
        "created_at": (datetime.now() - timedelta(days=15)).isoformat(),
        "student_count": 1,
        "chapter_count": 2,
        "exercise_count": 5
    }
]

# Mock Chapters
mock_chapters = [
    {
        "chapter_id": "chap001",
        "class_id": "ABC123",
        "title": "Chapter 1: Introduction to Analytics",
        "description": "Basic concepts and foundations of business analytics",
        "chapter_number": 1,
        "pdf_filename": "Chapter_1_Introduction.pdf",
        "created_at": (datetime.now() - timedelta(days=25)).isoformat(),
        "exercise_count": 3
    },
    {
        "chapter_id": "chap002",
        "class_id": "ABC123",
        "title": "Chapter 2: Data Collection and Preparation",
        "description": "Methods for collecting and preparing data for analysis",
        "chapter_number": 2,
        "pdf_filename": "Chapter_2_Data_Collection.pdf",
        "created_at": (datetime.now() - timedelta(days=20)).isoformat(),
        "exercise_count": 3
    },
    {
        "chapter_id": "chap003",
        "class_id": "ABC123",
        "title": "Chapter 3: Statistical Analysis",
        "description": "Statistical methods for data analysis",
        "chapter_number": 3,
        "pdf_filename": "Chapter_3_Statistical_Analysis.pdf",
        "created_at": (datetime.now() - timedelta(days=15)).isoformat(),
        "exercise_count": 2
    }
]

# Mock Exercises
mock_exercises = [
    {
        "exercise_id": "ex001",
        "chapter_id": "chap001",
        "class_id": "ABC123",
        "title": "Load California Housing Dataset",
        "description": "Load the California Housing dataset using sklearn and display basic information",
        "difficulty": "easy",
        "solution_code": "from sklearn.datasets import fetch_california_housing\nimport pandas as pd\n\nhousing = fetch_california_housing()\ndf = pd.DataFrame(housing.data, columns=housing.feature_names)\nprint(df.head())\nprint(df.info())",
        "exercise_number": 1
    },
    {
        "exercise_id": "ex002",
        "chapter_id": "chap001",
        "class_id": "ABC123",
        "title": "Data Exploration",
        "description": "Explore the dataset by computing basic statistics and visualizing distributions",
        "difficulty": "medium",
        "solution_code": "import matplotlib.pyplot as plt\nimport seaborn as sns\n\n# Basic statistics\nprint(df.describe())\n\n# Visualizations\nplt.figure(figsize=(12, 8))\ndf.hist(bins=50, figsize=(12, 8))\nplt.show()",
        "exercise_number": 2
    },
    {
        "exercise_id": "ex003",
        "chapter_id": "chap001",
        "class_id": "ABC123",
        "title": "Correlation Analysis",
        "description": "Analyze correlations between features in the dataset",
        "difficulty": "medium",
        "solution_code": "import numpy as np\n\n# Compute correlation matrix\ncorr_matrix = df.corr()\nprint(corr_matrix)\n\n# Visualize correlations\nsns.heatmap(corr_matrix, annot=True, cmap='coolwarm')\nplt.show()",
        "exercise_number": 3
    }
]

# Mock Progress Data
mock_progress = [
    {
        "user_id": "stud001",
        "exercise_id": "ex001",
        "class_exercise_id": "ex001",
        "class_id": "ABC123",
        "exercise_title": "Load California Housing Dataset",
        "best_score": 85,
        "best_accuracy": 95.5,
        "total_attempts": 2,
        "completed": True,
        "last_completed_at": (datetime.now() - timedelta(days=5)).isoformat()
    },
    {
        "user_id": "stud001",
        "exercise_id": "ex002",
        "class_exercise_id": "ex002",
        "class_id": "ABC123",
        "exercise_title": "Data Exploration",
        "best_score": 72,
        "best_accuracy": 88.0,
        "total_attempts": 3,
        "completed": True,
        "last_completed_at": (datetime.now() - timedelta(days=3)).isoformat()
    },
    {
        "user_id": "stud002",
        "exercise_id": "ex001",
        "class_exercise_id": "ex001",
        "class_id": "ABC123",
        "exercise_title": "Load California Housing Dataset",
        "best_score": 90,
        "best_accuracy": 98.0,
        "total_attempts": 1,
        "completed": True,
        "last_completed_at": (datetime.now() - timedelta(days=4)).isoformat()
    }
]

# Mock Enrollments
mock_enrollments = [
    {
        "class_id": "ABC123",
        "student_id": "stud001",
        "student_name": "John Doe",
        "student_email": "john.doe@student.hult.edu",
        "enrolled_at": (datetime.now() - timedelta(days=28)).isoformat()
    },
    {
        "class_id": "ABC123",
        "student_id": "stud002",
        "student_name": "Jane Smith",
        "student_email": "jane.smith@student.hult.edu",
        "enrolled_at": (datetime.now() - timedelta(days=25)).isoformat()
    },
    {
        "class_id": "XYZ789",
        "student_id": "stud001",
        "student_name": "John Doe",
        "student_email": "john.doe@student.hult.edu",
        "enrolled_at": (datetime.now() - timedelta(days=10)).isoformat()
    }
]

def export_mock_data():
    """Export all mock data to JSON files"""
    data = {
        "professors": mock_professors,
        "students": mock_students,
        "classes": mock_classes,
        "chapters": mock_chapters,
        "exercises": mock_exercises,
        "progress": mock_progress,
        "enrollments": mock_enrollments
    }
    
    with open("mock_data.json", "w") as f:
        json.dump(data, f, indent=2)
    
    print("✅ Mock data exported to mock_data.json")
    print(f"   - {len(mock_professors)} professors")
    print(f"   - {len(mock_students)} students")
    print(f"   - {len(mock_classes)} classes")
    print(f"   - {len(mock_chapters)} chapters")
    print(f"   - {len(mock_exercises)} exercises")
    print(f"   - {len(mock_progress)} progress records")
    print(f"   - {len(mock_enrollments)} enrollments")

if __name__ == "__main__":
    export_mock_data()
