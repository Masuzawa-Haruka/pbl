from django.shortcuts import render, get_object_or_404
from django.db.models import Q
from .models import Book


def get_search_context(request):
    books = Book.objects.all()

    keyword = request.GET.get("keyword", "").strip()
    category = request.GET.get("category", "").strip()
    campus = request.GET.get("campus", "").strip()
    sort = request.GET.get("sort", "newest").strip()

    if keyword:
        books = books.filter(
            Q(title__icontains=keyword)
            | Q(author__icontains=keyword)
        )

    if category:
        books = books.filter(category=category)

    if campus:
        books = books.filter(campus=campus)

    if sort == "price_low":
        books = books.order_by("price", "-created_at")
    elif sort == "price_high":
        books = books.order_by("-price", "-created_at")
    else:
        books = books.order_by("-created_at")

    return {
        "books": books,
        "keyword": keyword,
        "selected_category": category,
        "selected_campus": campus,
        "selected_sort": sort,
        "categories": Book.CATEGORY_CHOICES,
        "campuses": Book.CAMPUS_CHOICES,
    }


def index(request):
    return render(request, 'main/search.html', get_search_context(request))


def search(request):
    return render(request, 'main/search.html', get_search_context(request))


def listing_form(request):

    if request.method == 'POST':
        book = Book(

            title=request.POST.get('title'),
            author=request.POST.get('author'),
            price=request.POST.get('price'),
            category=request.POST.get('category'),
            campus=request.POST.get('campus'),
            condition=request.POST.get('condition'),     
            
        )
        book.save()

        return render(request, 'main/listing_form.html', {'success': True})
        

    return render(request, 'main/listing_form.html')


def inbox(request):
    return render(request, 'main/inbox.html')


def mypage(request):
    return render(request, 'main/mypage.html')


def book_detail(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    return render(request, 'main/book_detail.html', {'book': book})


def login(request):
    return render(request, 'main/login.html')
