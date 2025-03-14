from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

from django.http import HttpResponse

def favicon_view(request):
    return HttpResponse(status=204)


urlpatterns = [
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('verify-liveness/', views.verify_liveness, name='verify_liveness'),
    #path("register/success/<str:username>/", views.register_success, name="register_success"),
    path("login/", views.login_view, name="login"),
    path("face-verification/", views.face_verification_page, name="face_verification"),
    path("face-verify/", views.face_verify, name="face_verify"),
    path("dashboard/", views.dashboard_view, name="dashboard"),  # Add dashboard page
] 
urlpatterns += [path('favicon.ico', favicon_view)]

urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)