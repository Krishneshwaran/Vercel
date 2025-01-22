from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import os
from .additional import compile, csvtojson, filepath
from .models import FileUploadProblems
import csv
import traceback
from pymongo import MongoClient


# Update the MongoClient to use the provided connection string
client = MongoClient("mongodb+srv://ihub:ihub@test-portal.lcgyx.mongodb.net/test_portal_db?retryWrites=true&w=majority")
db = client["test_portal_db"]  # Ensure this matches the database name in your connection string
temp_questions_collection = db['tempQuestions']
mcq_report_collection = db['mcqReports']

PROBLEMS_FILE_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'Frontend', 'public', 'json', 'questions.json')

