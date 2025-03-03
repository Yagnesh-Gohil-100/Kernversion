from django.urls import path
from . import views

urlpatterns = [    
    path('', views.home, name='home'),
    path('process-pdf/', views.process_pdf, name='process_pdf'),
    path('user-edit/', views.user_edit, name='user_edit'),
    path('save_user_input/', views.save_user_input, name='save_user_input'),
    path('convert_to_kern/', views.convert_to_kern, name='convert_to_kern'),
]