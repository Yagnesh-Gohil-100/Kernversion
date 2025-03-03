from django.shortcuts import render, redirect
from django.conf import settings
import os
from .utils import extract_alphabets, extract_rows  # Import your PDF processing function
from django.http import HttpResponse, FileResponse
import fitz

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

        # Extract PDF images using PyMuPDF
        pdf_images_folder = os.path.join(pdf_folder, 'pdf_images')
        os.makedirs(pdf_images_folder, exist_ok=True)
        pdf_document = fitz.open(upload_path)
        pdf_images = []

        for page_num in range(len(pdf_document)):
            page = pdf_document.load_page(page_num)
            page_image = page.get_pixmap()
            image_path = os.path.join(pdf_images_folder, f"page_{page_num + 1}.png")
            page_image.save(image_path)
            pdf_images.append(os.path.relpath(image_path, settings.MEDIA_ROOT))

        # Process the PDF
        output_folder = os.path.join(pdf_folder, 'segmented_images')
        coordinates, row_mapping = extract_alphabets(upload_path, output_folder)

        # Extract rows as images
        row_images_folder = os.path.join(pdf_folder, 'row_images')
        row_images = extract_rows(upload_path, row_mapping, row_images_folder)

        # Save the results to the session
        request.session['coordinates'] = coordinates
        request.session['row_mapping'] = row_mapping
        request.session['row_images'] = row_images
        request.session['pdf_images'] = pdf_images

        return redirect('user_edit')  # Redirect to the user_edit page

    return redirect('home')  # Redirect back to home if there's an error

def user_edit(request):
    # Retrieve row images and PDF images from the session
    row_images = request.session.get('row_images', [])
    pdf_images = request.session.get('pdf_images', [])

    # Add MEDIA_URL prefix to row image paths and PDF image paths
    row_images = [(row_num, f"{settings.MEDIA_URL}{row_image_path}") for row_num, row_image_path in row_images]
    pdf_images = [f"{settings.MEDIA_URL}{pdf_image}" for pdf_image in pdf_images]

    return render(request, 'website/user_edit.html', {
        'row_images': row_images,
        'pdf_images': pdf_images,
    })

def save_user_input(request):
    if request.method == 'POST':
        # Process user input for each row
        for row_num, _ in request.session.get('row_images', []):
            row_type = request.POST.get(f"row_{row_num}_type")
            print(f"Row {row_num} classified as: {row_type}")
            # Save the classification to the database or session as needed

        # Redirect to the next step (e.g., convert to kern format)
        return redirect('convert_to_kern')

    return HttpResponse("Invalid request")

def convert_to_kern(request):
    return render(request, 'website/converted_kern.html')
