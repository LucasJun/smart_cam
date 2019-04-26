from django.urls import path
from. import views

urlpatterns = [
    path('', views.index, name='index'),
    path('video_feed', views.video_feed, name='video_feed'),
    path('adjust', views.adjust, name='adjust'),
    path('setting', views.setting, name='setting'),
    path('manual', views.manual, name='manual'),
    path('about', views.about, name='about'),
]