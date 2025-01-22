from django.urls import path
from . import views, views_auto, views_user
from . import views_contest
from .views_contest import *
from . import views

urlpatterns = [
    path('contestdetails/', views_contest.saveDetails, name='save_details'),
    path('userinfo/', views_contest.saveUserInfo, name='save_user_info'),  # New endpoint
    # path('api/contests/', get_contests, name='get_contests'),
    path('api/contests/delete/<str:contest_id>/', delete_contest, name='delete_contest'),
    path('api/start_test/', start_test, name='start_test'),
    path('api/save_coding_report/', save_coding_report, name='save_coding_report'),
    path('api/finish_test/', finish_test, name='finish_test'),
    path('api/start_mcqtest/', start_mcqtest, name='start_mcqtest'),
    # path('api/finish_mcqtest/', finish_mcqTest, name='finish_mcqtest'),
    path("api/contests/stats/<str:contest_id>/", contest_stats, name="contest_stats"),
    path("api/contests/<str:contest_id>/students/", contest_students, name="contest_students"),
    path('questions/', views_user.fetch_Questions, name='questions'),
    path('saveQuestions/', views_user.fetch_and_save_questions, name= 'saveInFrontend'),

]