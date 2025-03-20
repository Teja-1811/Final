from django.shortcuts import render, redirect
from django.core.mail import send_mail
import os
import cv2
import numpy as np
import base64
import json
import face_recognition
from django.contrib.auth import login, authenticate, logout
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password
from django.contrib import messages
from django.conf import settings

from .models import CustomUser

def home(request):
    return render(request, "home.html")

def decode_base64_image(image_data):
    try:
        image_bytes = base64.b64decode(image_data.split(",")[1])
        np_arr = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        return image if image is not None else None
    except Exception as e:
        print("❌ Error decoding image:", e)
        return None

@csrf_exempt
def register(request):
    if request.method == "POST":
        try:
            if request.content_type == "application/json":
                data = json.loads(request.body)
                fname = data.get("fname")
                lname = data.get("lname")
                email = data.get("email")
                password = data.get("password")
                image_data = data.get("image")  # Base64 image from frontend
            else:
                fname = request.POST.get("fname")
                lname = request.POST.get("lname")
                email = request.POST.get("email")
                password = request.POST.get("password")
                image_data = request.POST.get("face_image")  # Base64 image from frontend
            
            if not all([fname, lname, email, password, image_data]):
                return JsonResponse({"error": "All fields are required."}, status=400)

            face_image = decode_base64_image(image_data)
            if face_image is None:
                return JsonResponse({"error": "Invalid image format!"}, status=400)

            # Encode face
            rgb_frame = cv2.cvtColor(face_image, cv2.COLOR_BGR2RGB)
            face_encodings = face_recognition.face_encodings(rgb_frame)
            if not face_encodings:
                return JsonResponse({"error": "Face encoding failed. Please try again."}, status=400)
            
            face_embedding = json.dumps(face_encodings[0].tolist())
            
            user = CustomUser.objects.create(
                username=email,
                email=email,
                first_name=fname,
                last_name=lname,
                password=make_password(password),
                face_embedding=face_embedding
            )

            messages.success(request, "Registration successful. Please log in.")
            return redirect("home")
        
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

    return render(request, "register.html")

@csrf_exempt
def login_view(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            email = data.get("email")
            password = data.get("password")
            
            user = authenticate(username=email, password=password)
            if user is not None:
                # print(f"✅ User Logged In: {user.email}")
                # print(f"🆔 User ID: {user.id}")
                # print(f"👤 Name: {user.first_name} {user.last_name}")
                request.session["face_verify_user_id"] = user.id
                return JsonResponse({"success": True, "redirect": "/face-verification/"})
            else:
                user = CustomUser.objects.filter(email = email)
                if len(user) == 1:
                    send_mail(
                    "Login Attempt Failed",
                    f"Hello,\n\nThere was a failed login attempt using your email: {email}. If this wasn't you, please secure your account.",
                    "your-email@example.com",
                    [email],
                    fail_silently=False,
                )
                return JsonResponse({"error": "Invalid email or password."}, status=400)
        
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid request format."}, status=400)
    
    return render(request, "login.html")

@csrf_exempt
def face_verify(request):
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
            face_image = decode_base64_image(image_data)
            
            if face_image is None:
                return JsonResponse({"error": "Invalid face image."}, status=400)
            
            uploaded_encoding = np.array(face_recognition.face_encodings(face_image)[0])
            stored_encoding = np.array(json.loads(user.face_embedding))
            
            match = face_recognition.compare_faces([stored_encoding], uploaded_encoding, tolerance=0.6)
            
            if match[0]:
                login(request, user)
                print(f"Face Verified: {user.email}, Name: {user.first_name} {user.last_name}")
                send_mail(
                    "Login Successful",
                    f"Hello {user.first_name},\n\nYour account was successfully logged in.",
                    "bhanuteja18112001@gmail.com",
                    [user.email],
                    fail_silently=False,
                )
                return JsonResponse({
                    "success": True,
                    "message": "Face authentication successful!",
                    "username": f"{user.first_name} {user.last_name}"
                })
            send_mail(
                    "Login Attempt Failed",
                    f"Hello,\n\nThere was a failed login attempt using your email: {user.email}. If this wasn't you, please secure your account.",
                    "your-email@example.com",
                    [user.email],
                    fail_silently=False,
                )
            return JsonResponse({"error": "Face not recognized. Try again."}, status=401)
        
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    
    return JsonResponse({"error": "Invalid request."}, status=400)

@csrf_exempt
def logout_view(request):
    logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect("/")

@login_required
def dashboard_view(request):
    user_id = request.session.get("face_verify_user_id")
    
    user = CustomUser.objects.get(id=user_id)  # Fetch user details
    return render(request, "dashboard.html", {"user": user})

def face_verification_page(request):
    return render(request, "face_verification.html")
