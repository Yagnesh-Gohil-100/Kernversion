from django.shortcuts import render, redirect
from django.conf import settings
import os
from .utils import extract_alphabets  # Import your PDF processing function

# Create your views here.

def home(request):
    return render(request, 'website/home.html')

def process_pdf(request):
    if request.method == 'POST' and 'pdf' in request.FILES:
        # Get the uploaded file
        uploaded_file = request.FILES['pdf']

        # Create a unique folder for the user and PDF
        user_folder = f"user_{request.user.id}"  # Folder for the user
        pdf_name = uploaded_file.name.replace('.pdf', '')  # Remove .pdf extension
        pdf_folder = os.path.join(settings.MEDIA_ROOT, user_folder, pdf_name)  # Folder for the PDF

        # Save the uploaded PDF directly in the pdf_folder
        upload_path = os.path.join(pdf_folder, uploaded_file.name)
        os.makedirs(pdf_folder, exist_ok=True)  # Create the folder if it doesn't exist
        with open(upload_path, 'wb+') as destination:
            for chunk in uploaded_file.chunks():
                destination.write(chunk)

        # Process the PDF
        output_folder = os.path.join(pdf_folder, 'segmented_images')
        coordinates, row_mapping = extract_alphabets(upload_path, output_folder)

        # Save the results (coordinates and row_mapping) to the session
        request.session['coordinates'] = coordinates
        request.session['row_mapping'] = row_mapping
        request.session['output_folder'] = output_folder

        return redirect('user_edit')  # Redirect to the success page

    return redirect('home')  # Redirect back to home if there's an error

def user_edit(request):
    return render(request, 'website/user_edit.html')
