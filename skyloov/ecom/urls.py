from django.urls import path
from .views import AddUser, LoginView, ProductSearchView, ProductViewSet, CartView
from rest_framework import routers

router = routers.SimpleRouter()
router.register(r'product-search', ProductViewSet)
urlpatterns = [
    path('add_user/', AddUser.as_view(), name='add_user'),
    path('login/', LoginView.as_view(), name='login_user'),
    path('cart/', CartView.as_view(), name='Cart')

] + router.urls