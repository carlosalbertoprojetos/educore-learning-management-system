from django.urls import path

from .views import forum, thread, reply_correct, reply_incorrect

app_name = 'forum'


urlpatterns = [
    path('', forum, name='forum_index'),
    path('tag/<str:tag>/', forum, name='index_tagged'),
    path('reply/<int:pk>/correct/', reply_correct, name='reply_correct'),
    path('reply/<int:pk>/incorrect/', reply_incorrect, name='reply_incorrect'),
    path('thread/<slug:slug>/', thread, name='thread'),
]
