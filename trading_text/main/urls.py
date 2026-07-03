from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('search/', views.search, name='search'),
    path('listing/new/', views.listing_form, name='listing_form'),
    path('inbox/', views.inbox, name='inbox'),
    path('mypage/', views.mypage, name='mypage'),
    path('bookdetail/<int:book_id>/', views.book_detail, name='book_detail'),
]
