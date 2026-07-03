from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('search/', views.search, name='search'),
    path('listing/new/', views.listing_form, name='listing_form'),
    path('inbox/', views.inbox, name='inbox'),
    path('mypage/', views.mypage, name='mypage'),
    path('login/', views.login, name='login'),
]
