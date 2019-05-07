from django.urls import path
from. import views

urlpatterns = [
    path('', views.index, name='index'),
    path('video_feed', views.video_feed, name='video_feed'),
    path('adjust', views.adjust, name='adjust'),
    path('manual', views.manual, name='manual'),
    path('about', views.about, name='about'),
    # ajax
    # path('ajax_status_table', views.ajax_status_table, name='ajax_status_table'),
]