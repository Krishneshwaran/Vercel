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

@csrf_exempt
def compileCode(request):
    if request.method == "POST":
        
        # PROBLEMS_FILE_PATH = filepath.get_filepath()
        
        # print('PROBLEMS_FILE_PATH:',PROBLEMS_FILE_PATH)

        data = json.loads(request.body)
        user_code = data.get('user_code', '')
        language = data.get('language', '')
        problem_id = data.get('problem_id', 0)

        test_case = 'samples'
        response = compile.compilecode(PROBLEMS_FILE_PATH, problem_id, user_code, test_case, language)
        print(user_code)
        return response

    return JsonResponse({"error": "Invalid request method."}, status=405)

@csrf_exempt
def compileHidden(request):
    if request.method == "POST":

        # PROBLEMS_FILE_PATH = filepath.get_filepath()

        # print('PROBLEMS_FILE_PATH:',PROBLEMS_FILE_PATH)

        data = json.loads(request.body)
        user_code = data.get('user_code', '')
        language = data.get('language', '')
        problem_id = data.get('problem_id', 0)

        test_case = 'hidden_samples'
        response = compile.compilecode(PROBLEMS_FILE_PATH, problem_id, user_code, test_case, language)
        return response

    return JsonResponse({"error": "Invalid request method."}, status=405)
    
@csrf_exempt
def userInput(request):
    if request.method == 'POST':
        try:
            print("Received POST request")  # Debugging log to check if this line executes

            csv_file = request.FILES.get('file')
            if not csv_file:
                print("No file provided")  # Debugging log for file presence
                return JsonResponse({'error': 'No file provided'}, status=400)

            # Convert CSV to JSON format
            data = []
            reader = csv.DictReader(csv_file.read().decode('utf-8').splitlines())
            print("CSV read successfully")  # Debugging log to check CSV reading

            for row in reader:
                formatted_row = {
                    "id": int(row.get("id", 0)),  # Assuming 'id' field exists in CSV
                    "title": row.get("title", ""),
                    "role": row.get("role", "").split(','),  # Assuming 'role' is a comma-separated list in CSV
                    "level": row.get("level", ""),
                    "problem_statement": row.get("problem_statement", ""),
                    "samples": eval(row.get("samples", "[]")),  # Assuming samples are stored as a JSON array string
                    "hidden_samples": eval(row.get("hidden_samples", "[]"))  # Assuming hidden_samples are stored as a JSON array string
                }
                data.append(formatted_row)
            
            print("Data formatted:", data)  # Log the data to check if it's formatted correctly

            # Append to MongoDB
            temp_questions_collection.update_one(
                {},
                {'$push': {'problems': {'$each': data}}},
                upsert=True
            )
            print("Data inserted into MongoDB successfully")  # Debug log for database update
            return JsonResponse({'message': 'File uploaded and appended to MongoDB successfully'}, status=201)

        except Exception as e:
            print("An error occurred while processing the file:", str(e))
            traceback.print_exc()
            return JsonResponse({'error': str(e)}, status=500)

    print("Invalid request method")  # Debugging log if method is not POST
    return JsonResponse({'error': 'Invalid request method'}, status=405)



@csrf_exempt
def selectedProblems(request):
    if request.method == "POST":
        try:
            # Parse the incoming JSON data
            data = json.loads(request.body)
            selected_ids = data.get('selected', [])

            # Define the directory and file paths
            directory = 'compile/jsonfiles'
            questions_file = os.path.join(directory, 'questions.json')
            selected_file = os.path.join(directory, 'selected.json')

            # Load the questions.json file
            if not os.path.exists(questions_file):
                return JsonResponse({"error": "questions.json not found."}, status=404)

            with open(questions_file, 'r') as f:
                questions_data = json.load(f)

            # Filter the problems based on the selected IDs
            filtered_problems = [
                problem for problem in questions_data.get('problems', [])
                if problem['id'] in selected_ids
            ]

            # Save the filtered problems to selected.json
            with open(selected_file, 'w') as f:
                json.dump({'selected_problems': filtered_problems}, f, indent=4)

            return JsonResponse({"message": "Selected problems saved successfully", "file": selected_file}, status=200)
        
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Invalid request method."}, status=405)

