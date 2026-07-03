from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('signup/', views.signup, name='signup'),
    path('login/', views.login, name='login'),
    path('logout/', views.logout, name='logout'),
    path('search/', views.search, name='search'),
    path('book/<int:book_id>/', views.book_detail, name='book_detail'),
    path('book/<int:book_id>/favorite/', views.toggle_favorite, name='toggle_favorite'),
    path('book/<int:book_id>/transaction/start/', views.start_transaction, name='start_transaction'),
    path('listing/new/', views.listing_form, name='listing_form'),
    path('inbox/', views.inbox, name='inbox'),
    path('transactions/<int:transaction_id>/', views.transaction_detail, name='transaction_detail'),
    path('mypage/', views.mypage, name='mypage'),
]
