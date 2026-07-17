from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("login/", views.login, name="login"),
    path("logout/", views.logout, name="logout"),
    path("signup/", views.signup, name="signup"),
    path("activate/<uidb64>/<token>/", views.activate, name="activate"),
    path("search/", views.search, name="search"),
    path("listing/new/", views.listing_form, name="listing_form"),
    path("book/<int:book_id>/", views.book_detail, name="book_detail"),
    path("book/<int:book_id>/like/", views.toggle_like, name="toggle_like"),
    path("book/<int:book_id>/consult/", views.start_consultation, name="start_consultation"),
    path("book/<int:book_id>/chat/", views.chat, name="chat"),
    path("book/<int:book_id>/evaluate/", views.evaluate_trade, name="evaluate_trade"),
    path("book/<int:book_id>/cancel/", views.cancel_trade, name="cancel_trade"),
    path("book/<int:book_id>/edit/", views.edit_book, name="edit_book"),
    path("inbox/", views.inbox, name="inbox"),
    path("mypage/", views.mypage, name="mypage"),
    path("mypage/edit/", views.edit_profile, name="edit_profile"),
    path("help/", views.help_contact, name="help_contact"),
    path("terms/", views.terms, name="terms"),
]
