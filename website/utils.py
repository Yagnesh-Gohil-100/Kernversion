import os
import cv2
import fitz
import numpy as np
from PIL import Image
from django.conf import settings

def preprocess_image(image):
    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Apply Gaussian blur to the entire image
    blurred = cv2.GaussianBlur(gray, (9, 9), 0)
    
    # Adaptive thresholding on blurred image
    thresh = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 21, 5)

    # Morphological closing to connect broken parts of characters
    closing_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, closing_kernel)

    # Apply erosion to separate vertical lines
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    eroded = cv2.erode(closed, kernel, iterations=1)
    
    return eroded

def enlarge_image(image, scale_factor=3):
    enlarged_image = cv2.resize(image, (0, 0), fx=scale_factor, fy=scale_factor, interpolation=cv2.INTER_LANCZOS4)
    return enlarged_image

def enhance_quality(image):
    sharpened = cv2.filter2D(image, -1, np.array([[-1, -1, -1], [-1,  9, -1], [-1, -1, -1]]))
    denoised = cv2.fastNlMeansDenoisingColored(sharpened, None, 10, 10, 7, 21)
    return denoised

def create_mapping(coordinates, aspect_ratio_threshold, is_row=True):
    mapping = []
    number = 1

    if not coordinates:
        return mapping

    for i, (page_num, x, y, w, h) in enumerate(coordinates):
        if is_row:
            if h / w > aspect_ratio_threshold:
                continue
            coord = y
            size = h
        else:
            # if h / w > aspect_ratio_threshold:
            #     continue
            if w / h > aspect_ratio_threshold and w > 14 and h < 8:  
                continue
            coord = x
            size = w

        if i == 0:
            upper_limit = coord + int(size / 2)
            lower_limit = coord
            mapping.append((number, lower_limit, upper_limit))
        elif mapping and coord > mapping[-1][2]:
            number += 1
            lower_limit = coord
            upper_limit = coord + int(size / 2)
            mapping.append((number, lower_limit, upper_limit))
        else:
            upper_limit = max(mapping[-1][2], coord + int(size / 2))
            mapping[-1] = (number, mapping[-1][1], upper_limit)

    return mapping

def assign_number(coord, mapping):
    for num, lower_limit, upper_limit in mapping:
        if lower_limit <= coord <= upper_limit:
            return num
    return -1

def extract_alphabets(pdf_path, output_folder, aspect_ratio_threshold=3):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    pdf_document = fitz.open(pdf_path)
    coordinates = []

    for page_num in range(len(pdf_document)):
        page = pdf_document.load_page(page_num)
        page_image = page.get_pixmap()
        np_page_image = np.frombuffer(page_image.samples, dtype=np.uint8).reshape((page_image.height, page_image.width, page_image.n))

        processed_image = preprocess_image(np_page_image)

        contours, _ = cv2.findContours(processed_image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            coordinates.append((page_num, x, y, w, h))

    if not coordinates:
        print("No contours found.")
        return

    coordinates_sorted_by_y = sorted(coordinates, key=lambda item: item[2])

    row_mapping = create_mapping(coordinates_sorted_by_y, aspect_ratio_threshold, is_row=True)

    print("Row mapping:", row_mapping)

    for page_num, x, y, w, h in coordinates:
        if h / w > aspect_ratio_threshold:
            continue

        row_num = assign_number(y, row_mapping)

        if row_num == -1:
            continue

        alphabet_region = np_page_image[y:y+h, x:x+w]
        enlarged_region = enlarge_image(alphabet_region)
        enhanced_region = enhance_quality(enlarged_region)

        if w<6 and h<6:
            continue

        base_filename = f"{page_num}_row{row_num}_x{x}_y{y}_w{w}_h{h}"
        counter = 1
        filename = f"{base_filename}.png"
        while os.path.exists(os.path.join(output_folder, filename)):
            filename = f"{base_filename}_{counter}.png"
            counter += 1

        alphabet_image = Image.fromarray(enhanced_region)
        alphabet_image.save(os.path.join(output_folder, filename))
    
    return coordinates, row_mapping

def extract_rows(pdf_path, row_mapping, output_folder, padding=10):
    """
    Extract rows from the PDF as images using row_mapping.
    """
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    pdf_document = fitz.open(pdf_path)
    row_images = []

    # Sort row_mapping by lower_limit to ensure proper order
    row_mapping = sorted(row_mapping, key=lambda x: x[1])

    for page_num in range(len(pdf_document)):
        page = pdf_document.load_page(page_num)
        page_image = page.get_pixmap()
        np_page_image = np.frombuffer(page_image.samples, dtype=np.uint8).reshape((page_image.height, page_image.width, page_image.n))

        for i, (row_num, lower_limit, upper_limit) in enumerate(row_mapping):
            # Calculate the height of the row
            row_height = upper_limit - lower_limit

            # Calculate the ending y coordinate
            end_y = lower_limit + 2 * row_height

            # Ensure the end_y does not exceed the image height
            end_y = min(end_y, np_page_image.shape[0])

            # Check if the next row exists and adjust end_y to avoid overlap
            if i < len(row_mapping) - 1:
                next_lower_limit = row_mapping[i + 1][1]
                next_upper_limit = row_mapping[i + 1][2]
                if end_y > next_lower_limit and next_upper_limit - next_lower_limit > 1:
                    end_y = next_lower_limit

            # Skip if the row is empty or invalid
            if lower_limit >= end_y:
                print(f"Skipping empty row {row_num}: lower_limit ({lower_limit}) >= end_y ({end_y})")
                continue

            # Extract the row from the page image
            row_image = np_page_image[lower_limit:end_y, :]

            # Convert RGB to grayscale if necessary
            if len(row_image.shape) == 3:  # If RGB, convert to grayscale
                row_image = cv2.cvtColor(row_image, cv2.COLOR_RGB2GRAY)

            # Ensure the image is 2D (grayscale)
            if len(row_image.shape) != 2:
                raise ValueError(f"Unexpected image shape: {row_image.shape}")

            # Add padding to the row image
            padded_row_image = np.pad(row_image, ((padding, padding), (0, 0)), mode='constant', constant_values=255)

            # Convert to PIL image
            pil_row_image = Image.fromarray(padded_row_image)

            # Save the row image
            row_image_filename = f"row_{row_num}.png"
            row_image_path = os.path.join(output_folder, row_image_filename)
            pil_row_image.save(row_image_path)

            # Store the relative path for the template
            relative_path = os.path.relpath(row_image_path, settings.MEDIA_ROOT)
            row_images.append((row_num, relative_path))

    return row_images