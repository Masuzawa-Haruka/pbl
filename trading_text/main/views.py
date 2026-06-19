from django.shortcuts import render


def index(request):
    return render(request, 'main/search.html')


def search(request):
    return render(request, 'main/search.html')


def listing_form(request):
    return render(request, 'main/listing_form.html')


def inbox(request):
    return render(request, 'main/inbox.html')


def mypage(request):
    return render(request, 'main/mypage.html')
