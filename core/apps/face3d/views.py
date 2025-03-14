from django.shortcuts import render, redirect
import os
import cv2
import numpy as np
import base64
import json
import face_recognition
import mediapipe as mp
from django.contrib.auth import login, authenticate
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.files.base import ContentFile
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password
from .models import CustomUser

# Initialize MediaPipe FaceMesh for liveness detection
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(static_image_mode=True, max_num_faces=1, refine_landmarks=True)

mp_face_detection = mp.solutions.face_detection
face_detector = mp_face_detection.FaceDetection(model_selection=1, min_detection_confidence=0.5)

def get_mediapipe_face_embedding(image):
    """Extract face embedding using MediaPipe"""
    results = face_detector.process(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
    
    if results.detections:
        return [d.location_data.relative_bounding_box for d in results.detections]
    
    return None  # No face found

def home(request):
    return render(request, "home.html")

def decode_base64_image(image_data):
    """Decode a Base64 encoded image and convert it to an OpenCV frame."""
    try:
        image_bytes = base64.b64decode(image_data.split(",")[1])
        np_arr = np.frombuffer(image_bytes, np.uint8)
        return cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    except Exception:
        return None


@csrf_exempt
def verify_liveness(request):
    """Verify if the captured face is live or spoofed using MediaPipe."""
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            image_data = data.get("image")

            # Convert Base64 image to OpenCV format
            frame = decode_base64_image(image_data)
            if frame is None:
                return JsonResponse({"error": "Invalid image format"}, status=400)

            # Convert to RGB for MediaPipe processing
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = face_mesh.process(rgb_frame)

            if results.multi_face_landmarks:
                return JsonResponse({"liveness": True, "message": "Liveness Verified."})

            return JsonResponse({"liveness": False, "message": "Spoof Detected!"})

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

    return JsonResponse({"error": "Invalid request"}, status=400)

def resize_image(image, target_size=(150, 150)):
    """Resize image to reduce processing time"""
    return cv2.resize(image, target_size, interpolation=cv2.INTER_AREA)


@csrf_exempt
def register(request):
    """Handles user registration and face embedding storage."""
    if request.method == "POST":
        try:
            name = request.POST.get("name")
            email = request.POST.get("email")
            password = request.POST.get("password")
            face_image_data = request.POST.get("face_image")

            if not all([name, email, password, face_image_data]):
                return JsonResponse({"error": "All fields are required."}, status=400)

            # Decode Base64 face image
            face_image = decode_base64_image(face_image_data)
            if face_image is None:
                return JsonResponse({"error": "Invalid face image."}, status=400)

            # ✅ Save the image for debugging
            cv2.imwrite("test_captured_face.jpg", face_image)

            # ✅ Convert to RGB
            rgb_frame = cv2.cvtColor(face_image, cv2.COLOR_BGR2RGB)

            # ✅ Resize image for better detection
            rgb_frame = cv2.resize(rgb_frame, (0, 0), fx=1.5, fy=1.5)

            # ✅ Detect faces (Try CNN model)
            face_locations = face_recognition.face_locations(rgb_frame, model="cnn")
            if not face_locations:
                return JsonResponse({"error": "No face detected. Try again with better lighting."}, status=400)

            # Resize the face image before encoding
            resized_face = resize_image(face_image)
            face_encodings = face_recognition.face_encodings(resized_face)

            if not face_encodings:
                return JsonResponse({"error": "Face encoding failed. Try again."}, status=400)

            face_embedding = get_mediapipe_face_embedding(face_image)
            if face_embedding is None:
                return JsonResponse({"error": "No face detected. Try again."}, status=400)

            # ✅ Save face image
            face_path = f"faces/{email}.jpg"
            full_path = os.path.join(settings.MEDIA_ROOT, face_path)
            cv2.imwrite(full_path, face_image)

            # ✅ Save user
            user = CustomUser.objects.create(
                username = email,
                email=email,
                name=name,
                password=make_password(password),
                face_embedding=face_embedding,
                face_image=face_path,  # Save image path
            )

            login(request, user)

            return JsonResponse({"success": True, "redirect": "/dashboard/"})  

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

    return render(request, "register.html")

@csrf_exempt
def login_view(request):
    """Handles user login by verifying credentials first, then redirecting to face verification."""
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            email = data.get("email")
            password = data.get("password")

            if not email or not password:
                return JsonResponse({"error": "Email and password are required."}, status=400)

            user = authenticate(username=email, password=password)

            if user is not None:
                # Store user ID in session for face verification
                request.session["face_verify_user_id"] = user.id
                return JsonResponse({"success": True, "redirect": "/face-verification/"})
            else:
                return JsonResponse({"error": "Invalid email or password."}, status=400)

        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid request format."}, status=400)

    return render(request, "login.html")


def face_verification_page(request):
    """Render the face verification page where the user captures their face."""
    return render(request, "face_verification.html")


@csrf_exempt
def face_verify(request):
    """Face verification after successful credential login."""
    if request.method == "POST":
        try:
            user_id = request.session.get("face_verify_user_id")
            if not user_id:
                return JsonResponse({"error": "Session expired. Please log in again."}, status=403)

            user = CustomUser.objects.get(id=user_id)
            if not user.face_embedding:
                return JsonResponse({"error": "No face data found. Register your face first."}, status=400)

            data = json.loads(request.body)
            image_data = data.get("image")

            # Convert Base64 image to OpenCV format
            face_image = decode_base64_image(image_data)
            if face_image is None:
                return JsonResponse({"error": "Invalid face image."}, status=400)

            # Extract face encoding
            face_encodings = face_recognition.face_encodings(face_image)
            if not face_encodings:
                return JsonResponse({"error": "No face detected. Try again."}, status=400)

            uploaded_encoding = np.array(face_encodings[0])
            stored_encoding = np.array(json.loads(user.face_embedding))

            # Compare faces
            match = face_recognition.compare_faces([stored_encoding], uploaded_encoding, tolerance=0.6)

            if match[0]:  # Successful match
                login(request, user)
                del request.session["face_verify_user_id"]  # Remove session key
                return JsonResponse({"success": True, "message": "Face authentication successful!"})

            return JsonResponse({"error": "Face not recognized. Try again."}, status=401)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

    return JsonResponse({"error": "Invalid request."}, status=400)


@login_required
def dashboard_view(request):
    """Render the dashboard page after successful login and face verification."""
    return render(request, "dashboard.html")
