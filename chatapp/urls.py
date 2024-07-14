from django.urls import path
from . import views

urlpatterns = [
    path('home/', views.home_view, name='home'),
    path('', views.login_register_view, name='login_register'),
    path('logout/', views.logout_view, name='logout'),
    path('chat/', views.chat_view, name='chat_view'),
]
