from django.shortcuts import render
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.contrib.auth.hashers import check_password, make_password
from rest_framework.exceptions import AuthenticationFailed
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime, timedelta, timezone
import logging
import json
from .utils import *
import jwt


import random
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import string
from django.core.mail import send_mail
from django.conf import settings

from pymongo import MongoClient
from .utils import *
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime, timezone

client = MongoClient('mongodb+srv://krish:krish@assessment.ar5zh.mongodb.net/')
db = client['test_portal_db']
assessments_collection = db['coding_assessments']
staff_collection = db['staff']
mcq_collection = db['MCQ_Assessment_Data']



logger = logging.getLogger(__name__)

JWT_SECRET = 'test'
JWT_ALGORITHM = "HS256"

def generate_tokens_for_staff(staff_user):
    """
    Generate tokens for authentication. Modify this with JWT implementation if needed.
    """
    access_payload = {
        'staff_user': str(staff_user),
        'exp': datetime.utcnow() + timedelta(minutes=600),  # Access token expiration
        'iat': datetime.utcnow(),
    }

    # Encode the token
    token = jwt.encode(access_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return {'jwt': token}

logger = logging.getLogger(__name__)

@api_view(["POST"])
@permission_classes([AllowAny])
def staff_login(request):
    try:
        data = request.data
        email = data.get("email")
        password = data.get("password")

        # Validate input
        if not email or not password:
            logger.warning(f"Login failed: Missing email or password")
            return Response(
                {"error": "Email and password are required"},
                status=400
            )

        # Fetch staff user from MongoDB
        staff_user = db['staff'].find_one({"email": email})
        if not staff_user:
            logger.warning(f"Login failed: User with email {email} not found")
            return Response({"error": "Invalid email or password"}, status=401)

        # Check password hash
        stored_password = staff_user.get("password")
        if not check_password(password, stored_password):
            logger.warning(f"Login failed: Incorrect password for {email}")
            return Response({"error": "Invalid email or password"}, status=401)

        # Generate tokens
        staff_id = str(staff_user["_id"])
        tokens = generate_tokens_for_staff(staff_id)

        # Create response
        response = Response({
            "message": "Login successful",
            "tokens": tokens,
            "staffId": staff_id,
            "name": staff_user.get("full_name"),
            "email": staff_user.get("email"),
            "department": staff_user.get("department"),
            "collegename": staff_user.get("collegename"),
        }, status=200)

        # Set secure cookie for JWT
        response.set_cookie(
            key='jwt',
            value=tokens['jwt'],
            httponly=True,
            samesite='Lax',
            path="/",      # Ensure the cookie is sent for all routes
            secure=os.getenv("ENV") == "production",
            max_age=1 * 24 * 60 * 60  # 1 day expiration
        )

        logger.info(f"Login successful for staff: {email}")
        
        return response

    except Exception as e:
        logger.error(f"Error during staff login: {str(e)}")
        return Response(
            {"error": "Something went wrong. Please try again later."},
            status=500
        )

#forgot password
def generate_reset_token():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=20))

@api_view(["POST"])
@permission_classes([AllowAny])
def forgot_password(request):
    try:
        email = request.data.get('email')

        # Check if the email exists in the system
        user = staff_collection.find_one({"email": email})
        if not user:
            return Response({"error": "Email not found"}, status=400)

        # Generate reset token and store it
        reset_token = generate_reset_token()

        # Store token in the database with expiration time (e.g., 1 hour)
        expiration_time = datetime.utcnow() + timedelta(hours=1)
        staff_collection.update_one(
            {"email": email},
            {"$set": {"password_reset_token": reset_token, "password_reset_expires": expiration_time}}
        )

        # Send the reset token via email (you can customize the email content)
        send_mail(
            'Password Reset Request',
            f'Use this token to reset your password: {reset_token}',
            settings.DEFAULT_FROM_EMAIL,
            [email],
        )

        return Response({"message": "Password reset link sent to your email"}, status=200)

    except Exception as e:
        return Response({"error": str(e)}, status=500)

@api_view(["POST"])
@permission_classes([AllowAny])
def reset_password(request):
    try:
        email = request.data.get('email')
        token = request.data.get('token')
        new_password = request.data.get('password')

        # Find the user by email and validate token
        user = staff_collection.find_one({"email": email})
        if not user or user.get('password_reset_token') != token:
            return Response({"error": "Invalid token"}, status=400)

        # Check if token is expired
        if datetime.utcnow() > user.get('password_reset_expires'):
            return Response({"error": "Token has expired"}, status=400)

        # Hash the new password
        hashed_password = make_password(new_password)

        # Update the user's password and clear the reset token
        staff_collection.update_one(
            {"email": email},
            {"$set": {"password": hashed_password, "password_reset_token": None, "password_reset_expires": None}}
        )

        return Response({"message": "Password reset successful"}, status=200)

    except Exception as e:
        return Response({"error": str(e)}, status=500)

@api_view(["POST"])
@permission_classes([AllowAny])  # Allow signup without authentication
def staff_signup(request):
    """
    Signup view for staff
    """
    try:
        # Extract data from request
        data = request.data
        staff_user = {
            "email": data.get("email"),
            "password": make_password(data.get("password")),
            "full_name": data.get("name"),
            "department": data.get("department"),
            "collegename": data.get("collegename"),
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }

        # Validate required fields
        required_fields = ["email", "password", "name", "department", "collegename"]
        missing_fields = [field for field in required_fields if not data.get(field)]
        if missing_fields:
            return Response(
                {"error": f"Missing required fields: {', '.join(missing_fields)}"},
                status=400,
            )

        # Check if email already exists
        if db['staff'].find_one({"email": staff_user["email"]}):
            return Response({"error": "Email already exists"}, status=400)

        # Insert staff profile into MongoDB
        db['staff'].insert_one(staff_user)
        return Response({"message": "Signup successful"}, status=201)

    except Exception as e:
        logger.error(f"Error during staff signup: {e}")
        return Response(
            {"error": "Something went wrong. Please try again later."}, status=500
        )

def str_to_datetime(date_str):
    if not date_str or date_str == 'T':
        # If the date string is empty or just contains 'T', return None or raise an error
        raise ValueError(f"Invalid datetime format: {date_str}")

    try:
        # Try parsing the full datetime format (with seconds)
        return datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%S')
    except ValueError:
        try:
            # If there's no seconds, try parsing without seconds
            return datetime.strptime(date_str, '%Y-%m-%dT%H:%M')
        except ValueError:
            # If both parsing methods fail, raise an error
            raise ValueError(f"Invalid datetime format: {date_str}")

from bson import ObjectId

def serialize_object(obj):
    if isinstance(obj, list):
        return [serialize_object(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: serialize_object(value) for key, value in obj.items()}
    elif isinstance(obj, ObjectId):
        return str(obj)
    else:
        return obj


@csrf_exempt
def view_test_details(request, contestId):
    try:
        if request.method == "GET":
            # Fetch the test details using the contestId field
            test_details = assessments_collection.find_one({"contestId": contestId}, {"_id": 0})
            mcq_details = mcq_collection.find_one({"contestId": contestId}, {"_id": 0})

            if test_details or mcq_details:
                # Get the relevant document (either test_details or mcq_details)
                document = test_details if test_details else mcq_details

                # If visible_to exists, fetch student details
                if 'visible_to' in document:
                    students_collection = db['students']
                    report_collection = db['coding_report'] if test_details else db['MCQ_Assessment_report']
                    student_details = []
                    for regno in document['visible_to']:
                        student = students_collection.find_one(
                            {"regno": regno},
                            {"name": 1, "dept": 1, "collegename": 1, "year": 1, "_id": 1}
                        )

                        if student:
                            # Convert ObjectId to string for JSON serialization
                            student['_id'] = str(student['_id'])
                            student_id = student['_id']

                            # Check status in report_collection
                            report = report_collection.find_one({
                                "contest_id": contestId,
                                "students": {"$elemMatch": {"student_id": student_id}}
                            })

                            # Determine status
                            status = 'yet to start'
                            if report:
                                for student_report in report.get('students', []):
                                    if student_report.get('student_id') == student_id:
                                        status = student_report.get('status', 'yet to start')
                                        break

                            student_details.append({
                                "regno": regno,
                                "name": student.get('name'),
                                "dept": student.get('dept'),
                                "collegename": student.get('collegename'),
                                "year": student.get('year'),
                                "studentId": student_id,
                                "status": status
                            })

                    # Add student details to the response
                    document['student_details'] = student_details

                # Serialize the document before returning
                return JsonResponse(serialize_object(document), safe=False)
            else:
                return JsonResponse({"error": "Test not found"}, status=404)


        elif request.method == "PUT":
            try:
                update_data = json.loads(request.body)
                
                # Extract date fields and convert them
                reg_date = update_data['assessmentOverview'].get('registrationStart')
                end_date = update_data['assessmentOverview'].get('registrationEnd')
                created_at = update_data.get('createdAt')
                updated_at = update_data.get('updatedAt')

                # Function to convert a date string to datetime object
                def convert_date(date_str):
                    if not date_str:
                        return None
                    try:
                        # Parse with different formats
                        return datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%S.%f')  # With microseconds
                    except ValueError:
                        try:
                            return datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%S')  # Without microseconds
                        except ValueError:
                            return datetime.strptime(date_str, '%Y-%m-%dT%H:%M')  # Without seconds
                
                # Update the fields in the `update_data` dict
                if reg_date:
                    update_data['assessmentOverview']['registrationStart'] = convert_date(reg_date)
                if end_date:
                    update_data['assessmentOverview']['registrationEnd'] = convert_date(end_date)
                if created_at:
                    update_data['createdAt'] = convert_date(created_at)
                if updated_at:
                    update_data['updatedAt'] = convert_date(updated_at)

                # Check if the update is for 'visible_to'
                if 'newStudent' in update_data:
                    new_student = update_data['newStudent']
                    if not new_student:
                        return JsonResponse({"error": "Student name is required"}, status=400)

                    # Check if it's a coding contest or MCQ assessment based on the contestId
                    test_details = assessments_collection.find_one({"contestId": contestId})
                    mcq_details = mcq_collection.find_one({"contestId": contestId})

                    if test_details:
                        # Add the new student to the 'visible_to' array (if not already present)
                        if "visible_to" not in test_details:
                            test_details["visible_to"] = []

                        # Avoid duplicates
                        if new_student not in test_details["visible_to"]:
                            test_details["visible_to"].append(new_student)

                        # Update the contest in the database
                        updated_test = assessments_collection.update_one(
                            {"contestId": contestId},
                            {"$set": {"visible_to": test_details["visible_to"], **update_data}}
                        )
                        if updated_test.modified_count > 0:
                            return JsonResponse({"message": "Student added successfully"})
                        else:
                            return JsonResponse({"error": "Failed to add student"}, status=400)

                    elif mcq_details:
                        # Add the new student to the 'visible_to' array (if not already present)
                        if "visible_to" not in mcq_details:
                            mcq_details["visible_to"] = []

                        # Avoid duplicates
                        if new_student not in mcq_details["visible_to"]:
                            mcq_details["visible_to"].append(new_student)

                        # Update the MCQ assessment in the database
                        updated_mcq = mcq_collection.update_one(
                            {"contestId": contestId},
                            {"$set": {"visible_to": mcq_details["visible_to"], **update_data}}
                        )
                        if updated_mcq.modified_count > 0:
                            return JsonResponse({"message": "Student added successfully"})
                        else:
                            return JsonResponse({"error": "Failed to add student"}, status=400)
                    else:
                        return JsonResponse({"error": "Test not found"}, status=404)

                else:
                    # Regular update logic for contest details
                    test_details = assessments_collection.find_one({"contestId": contestId})
                    mcq_details = mcq_collection.find_one({"contestId": contestId})

                    if test_details:
                        # Update the fields for the coding contest
                        updated_test = assessments_collection.update_one(
                            {"contestId": contestId},
                            {"$set": update_data}
                        )
                        if updated_test.modified_count > 0:
                            return JsonResponse({"message": "Coding Contest updated successfully"})
                        else:
                            return JsonResponse({"error": "No changes were made to the Coding Contest"}, status=400)
                    elif mcq_details:
                        # Update the fields for the MCQ assessment
                        updated_mcq = mcq_collection.update_one(
                            {"contestId": contestId},
                            {"$set": update_data}
                        )
                        if updated_mcq.modified_count > 0:
                            return JsonResponse({"message": "MCQ Assessment updated successfully"})
                        else:
                            return JsonResponse({"error": "No changes were made to the MCQ Assessment"}, status=400)
                    else:
                        return JsonResponse({"error": "Test not found"}, status=404)

            except Exception as e:
                return JsonResponse({"error": f"Failed to update the test: {str(e)}"}, status=500)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


    
def contest_details(request, contestID):
    """
    Fetch the contest details from MongoDB using the contest_id.
    """
    try:
        # Fetch the contest details from the MongoDB collection using contest_id
        contest_details = assessments_collection.find_one({"contestId": contestID})
        if contest_details:
            return JsonResponse(contest_details, safe=False)
        else:
            return JsonResponse({"error": "Contest not found"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


#Student Counts Fetching 
@api_view(['GET'])
@permission_classes([AllowAny])
def fetch_student_stats(request):
    """
    Fetch total number of students and other student-related statistics
    """
    try:
        students_collection = db['students']
        
        # Total number of students
        total_students = students_collection.count_documents({})
        
        # Optional: Additional statistics you might want to include
        students_by_department = list(students_collection.aggregate([
            {"$group": {
                "_id": "$department",
                "count": {"$sum": 1}
            }}
        ]))
        
        # Optional: Active students (if you have a way to define 'active')
        active_students = students_collection.count_documents({"status": "active"})
        
        return Response({
            "total_students": total_students,
            "students_by_department": students_by_department,
            "active_students": active_students
        })
    
    except Exception as e:
        logger.error(f"Error fetching student stats: {e}")
        return Response({"error": "Something went wrong. Please try again later."}, status=500)

#Admin test
@api_view(['GET'])
@permission_classes([AllowAny])
def fetch_contests(request):
    """
    Fetch contests created by the logged-in admin from MongoDB.
    Filters contests using staff_user from the JWT token.
    """
    try:
        jwt_token = request.COOKIES.get("jwt")
        if not jwt_token:
            raise AuthenticationFailed("Authentication credentials were not provided.")

        # Decode JWT token
        try:
            decoded_token = jwt.decode(jwt_token, 'test', algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            raise AuthenticationFailed("Access token has expired. Please log in again.")
        except jwt.InvalidTokenError:
            raise AuthenticationFailed("Invalid token. Please log in again.")
        
        staff_id = decoded_token.get("staff_user")
        print("Decoded staff_id:", staff_id)

        if not staff_id:
            raise AuthenticationFailed("Invalid token payload.")

        # Connect to the MongoDB collection
        coding_assessments = db['coding_assessments']
        current_time = datetime.utcnow().replace(tzinfo=timezone.utc)
        current_date = current_time.date()

        # Fetch all documents (unfiltered initially)
        contests_cursor = coding_assessments.find()
        contests = []

        # Process and filter the results manually
        for contest in contests_cursor:
            if contest.get("staffId") == staff_id:  # Match staffId
                visible_to_users = contest.get("visible_to", [])  # Fetch the visible_to array
                start_date = contest.get("assessmentOverview", {}).get("registrationStart")
                end_date = contest.get("assessmentOverview", {}).get("registrationEnd")
                # print("Start date:", start_date)
                # print("End date:", end_date)

                # Determine the status of the contest
                if start_date and end_date:
                    start_date_only = start_date.date()
                    end_date_only = end_date.date()
                    if current_date < start_date_only:
                        status = "Upcoming"
                    elif start_date_only <= current_date <= end_date_only:
                        status = "Live"
                    else:
                        status = "Completed"
                else:
                    status = "Upcoming"

                # Append the contest details
                contests.append({
                    "_id": str(contest.get("_id", "")),
                    "contestId": contest.get("contestId", ""),
                    "assessmentName": contest.get("assessmentOverview", {}).get("name", "Unnamed Contest"),
                    "type": "Coding",
                    "category": "Technical",
                    "startDate": contest.get("assessmentOverview", {}).get("registrationStart", "Null"),
                    "endDate": contest.get("assessmentOverview", {}).get("registrationEnd", "Null"),
                    "status": status,
                    "assignedCount": len(visible_to_users),  # Count of users in 'visible_to'
                })


        return Response({
            "contests": contests,
            "total": len(contests)
        })


    except jwt.ExpiredSignatureError:
        return Response({"error": "Token has expired"}, status=401)
    except jwt.InvalidTokenError:
        return Response({"error": "Invalid token"}, status=401)
    except Exception as e:

        logger.error(f"Error fetching contests: {e}")
        return Response({"error": "Something went wrong. Please try again later."}, status=500)

from datetime import datetime, timezone
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.exceptions import AuthenticationFailed
import jwt
from pymongo import MongoClient
from bson import ObjectId
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache

# Assuming db is already initialized
# db = MongoClient().your_database

# Cache for frequently accessed data
@lru_cache(maxsize=128)
def get_completed_count(contest_id):
    report_collection = db['MCQ_Assessment_report']
    report_cursor = report_collection.find({"contest_id": contest_id}, {"students": 1})
    completed_count = 0
    for report in report_cursor:
        completed_count += sum(1 for student in report.get("students", []) if student.get("status", "").lower() == "completed")
    return completed_count

@api_view(['GET'])
@permission_classes([AllowAny])
def fetch_mcq_assessments(request):
    """
    Fetch MCQ assessments based on staff privileges:
    - Admin users (admin="true") can see all assessments
    - Regular staff users can only see their own assessments
    """
    try:
        # Fetch JWT token
        jwt_token = request.COOKIES.get("jwt")
        if not jwt_token:
            raise AuthenticationFailed("Authentication credentials were not provided.")

        # Decode JWT token
        try:
            decoded_token = jwt.decode(jwt_token, 'test', algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            raise AuthenticationFailed("Access token has expired. Please log in again.")
        except jwt.InvalidTokenError:
            raise AuthenticationFailed("Invalid token. Please log in again.")

        staff_id = decoded_token.get("staff_user")
        if not staff_id:
            raise AuthenticationFailed("Invalid token payload.")

        # Check if staff is admin
        staff_collection = db['staff']
        staff_user = staff_collection.find_one({"_id": ObjectId(staff_id)}, {"admin": 1})

        if not staff_user:
            raise AuthenticationFailed("Staff user not found.")

        # Determine if user is admin
        is_admin = staff_user.get("admin") == "true"

        # Set up query based on user type
        mcq_collection = db['MCQ_Assessment_Data']
        query = {} if is_admin else {"staffId": staff_id}
        projection = {
            "_id": 1, "contestId": 1, "assessmentOverview.name": 1, "assessmentOverview.registrationStart": 1,
            "assessmentOverview.registrationEnd": 1, "visible_to": 1, "student_details": 1,
            "testConfiguration.questions": 1, "testConfiguration.duration": 1, "staffId": 1
        }
        assessments_cursor = mcq_collection.find(query, projection).batch_size(100)

        assessments = []
        current_time = datetime.utcnow().replace(tzinfo=timezone.utc)

        def process_assessment(assessment):
            # Add the condition to skip documents without 'visible_to' and 'questions'
            if "visible_to" not in assessment or "questions" not in assessment.get("testConfiguration", {}):
                return None

            # Extract dates
            registration_start = assessment.get("assessmentOverview", {}).get("registrationStart")
            registration_end = assessment.get("assessmentOverview", {}).get("registrationEnd")
            visible_users = assessment.get("visible_to", [])
            student_details = assessment.get("student_details", [])

            # Count student statuses
            yet_to_start_count = sum(1 for student in student_details if student.get("status", "").lower() == "yet to start")

            # Convert string to datetime if needed
            if registration_start:
                if isinstance(registration_start, str):
                    registration_start = datetime.fromisoformat(registration_start)
                if registration_start.tzinfo is None:
                    registration_start = registration_start.replace(tzinfo=timezone.utc)

            if registration_end:
                if isinstance(registration_end, str):
                    registration_end = datetime.fromisoformat(registration_end)
                if registration_end.tzinfo is None:
                    registration_end = registration_end.replace(tzinfo=timezone.utc)

            # Determine status
            if registration_start and registration_end:
                if current_time < registration_start:
                    status = "Upcoming"
                elif registration_start <= current_time <= registration_end:
                    status = "Live"
                elif current_time > registration_end:
                    status = "Completed"
                else:
                    status = "Unknown"
            else:
                status = "Date Unavailable"

            # Fetch completed count using cache
            contest_id = assessment.get("contestId")
            completed_count = get_completed_count(contest_id) if contest_id else 0

            return {
                "_id": str(assessment.get("_id")),
                "contestId": assessment.get("contestId"),
                "name": assessment.get("assessmentOverview", {}).get("name"),
                "registrationStart": registration_start,
                "endDate": registration_end,
                "type": "MCQ",
                "category": "Technical",
                "questions": assessment.get("testConfiguration", {}).get("questions"),
                "duration": assessment.get("testConfiguration", {}).get("duration"),
                "status": status,
                "assignedCount": len(visible_users),
                "completedCount": completed_count,
                "yetToStartCount": yet_to_start_count,
                "createdBy": assessment.get("staffId"),
            }

        with ThreadPoolExecutor() as executor:
            assessments = list(filter(None, executor.map(process_assessment, assessments_cursor)))

        return Response({
            "assessments": assessments,
            "total": len(assessments)
        })

    except Exception as e:
        return Response({"error": str(e)}, status=500)




@api_view(["GET", "PUT"])  # Allow both GET and PUT requests
@permission_classes([AllowAny])
@authentication_classes([])
def get_staff_profile(request):
    """
    GET: Retrieve staff profile using the JWT token.
    PUT: Update staff profile details.
    """
    try:
        jwt_token = request.COOKIES.get("jwt")
        if not jwt_token:
            raise AuthenticationFailed("Authentication credentials were not provided.")

        # Decode JWT token
        try:
            decoded_token = jwt.decode(jwt_token, 'test', algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            raise AuthenticationFailed("Access token has expired. Please log in again.")
        except jwt.InvalidTokenError:
            raise AuthenticationFailed("Invalid token. Please log in again.")
        
        staff_id = decoded_token.get("staff_user")

        if not staff_id:
            raise AuthenticationFailed("Invalid token payload.")

        # Fetch the staff details from MongoDB using ObjectId
        staff = staff_collection.find_one({"_id": ObjectId(staff_id)})

        if not staff:
            return Response({"error": "Staff not found"}, status=404)

        # Handle GET request
        if request.method == "GET":
            staff_details = {
                "name": staff.get("full_name"),
                "email": staff.get("email"),
                "department": staff.get("department"),
                "collegename": staff.get("collegename"),
            }
            return Response(staff_details, status=200)

        # Handle PUT request
        if request.method == "PUT":
            data = request.data  # Extract new data from request body
            updated_data = {}

            # Update fields if they are provided
            if "name" in data:
                updated_data["full_name"] = data["name"]
            if "email" in data:
                updated_data["email"] = data["email"]
            if "department" in data:
                updated_data["department"] = data["department"]
            if "collegename" in data:
                updated_data["collegename"] = data["collegename"]

            if updated_data:
                # Update the document in the database
                staff_collection.update_one(
                    {"_id": ObjectId(staff_id)},
                    {"$set": updated_data}
                )
                return Response({"message": "Profile updated successfully"}, status=200)

            return Response({"error": "No fields provided for update"}, status=400)

    except AuthenticationFailed as auth_error:
        return Response({"error": str(auth_error)}, status=401)
    except Exception as e:
        print(f"Unexpected error: {e}")
        return Response({"error": "An unexpected error occurred"}, status=500)

