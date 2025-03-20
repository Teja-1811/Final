from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

from django.http import HttpResponse
from django.conf.urls import handler404

def favicon_view(request):
    return HttpResponse(status=204)

handler404 = "apps.face3d.views.custom_404_view" 


urlpatterns = [
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path("login/", views.login_view, name="login"),
    path("face-verification/", views.face_verification_page, name="face_verification"),
    path("face-verify/", views.face_verify, name="face_verify"),
    path("dashboard/", views.dashboard_view, name="dashboard"),  # Add dashboard page
    path("logout/", views.logout_view, name="logout"),  # Logout route
] 
urlpatterns += [path('favicon.ico', favicon_view)]

urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)