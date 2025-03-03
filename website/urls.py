from django.urls import path
from . import views

urlpatterns = [    
    path('', views.home, name='home'),
    path('process-pdf/', views.process_pdf, name='process_pdf'),
    path('user-edit/', views.user_edit, name='user_edit'),
]