from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import traceback
from pymongo import MongoClient
import os
from bson.objectid import ObjectId
from student.utils import *
# Update the MongoClient to use the provided connection string
client = MongoClient("mongodb+srv://ihub:ihub@test-portal.lcgyx.mongodb.net/test_portal_db?retryWrites=true&w=majority")
db = client["test_portal_db"]  # Ensure this matches the database name in your connection string
questions_collection = db['Coding_Questions_Library']
final_questions_collection = db['finalQuestions']
coding_assessments_collection = db['coding_assessments']
coding_report_collection = db['coding_report']

PROBLEMS_FILE_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'Frontend', 'public', 'json', 'questions.json')
