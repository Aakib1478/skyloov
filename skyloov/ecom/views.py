from django.contrib.auth.models import User
from rest_framework.views import APIView
from rest_framework.response import Response
from .serializers import UserSerializer, LoginSerializer, ProductSearchSerializer
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.contrib.auth import authenticate
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import IsAuthenticated
from .models import Product, Brand, Category, Cart, CartItem
from rest_framework import generics, mixins, viewsets, permissions, filters, status
from rest_framework.pagination import LimitOffsetPagination
from django_filters.rest_framework import DjangoFilterBackend
from .filter import ProductFilter
from django.shortcuts import get_object_or_404, render
from django.contrib import messages
from django.conf import settings
from django.core.files.images import ImageFile
import threading
import os
from skyloov.tasks import send_welcome_email

#this API is use to create the user
class AddUser(APIView):
	@swagger_auto_schema(
    request_body=openapi.Schema(
        type='object',
        properties={
            'username': openapi.Schema(type='string'),
            'email': openapi.Schema(type='string'),
            'password': openapi.Schema(type='string')
        	}
    	)
	)
	def post(self, request):
		serializer = UserSerializer(data=request.data)
		if serializer.is_valid():
			serializer.save()
			send_welcome_email.apply_async(args=[user.id], eta=timezone.now() + timedelta(days=1))
			return Response({'message': 'User added successfully'}, status=200)
		else:
			return Response(serializer.errors, status=400)


#this API will authenticate the user detials and generate the token that can be used to authentication
class LoginView(APIView):
	@swagger_auto_schema(
	request_body=openapi.Schema(
		type='object',
		properties={
			'username': openapi.Schema(type='string'),
			'password': openapi.Schema(type='string')
			}
		)
	)
	def post(self, request):
		username = request.data.get('username')
		password = request.data.get('password')
		    
		# Check if username and password are provided
		if not (username and password):
			return Response({'error': 'Please provide both username and password.'}, status=400)

		# Authenticate the user
		user = authenticate(request, username=username, password=password)
		if not user:
				return Response({'error': 'Invalid credentials.'}, status=401)

		# Generate JWT token
		refresh = RefreshToken.for_user(user)
		return Response({'access_token': str(refresh.access_token)})


class ProductViewSet(
    mixins.ListModelMixin,
    viewsets.GenericViewSet):
	
	permission_classes = (permissions.IsAuthenticated,)
	pagination_class = LimitOffsetPagination
	serializer_class = ProductSearchSerializer
	queryset = Product.objects.all()
	filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
	filter_class = ProductFilter
	search_fields = ['name']

	@swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                name='min_price',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_INTEGER,
                description='Minimum price for filtering Products'
            ),
            openapi.Parameter(
                name='max_price',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_INTEGER,
                description='Maximum price for filtering  Products'
            ),
            openapi.Parameter(
                name='category',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                description='Category for filtering Products'
            ),
            openapi.Parameter(
                name='brand',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                description='Brand for filtering Products'
            ),
            openapi.Parameter(
			    name='created_at_min',
			    in_=openapi.IN_QUERY,
			    type=openapi.TYPE_STRING,
			    format='date-time',
			    description='Filter Products by creation date/time'
			),
			openapi.Parameter(
			    name='created_at_max',
			    in_=openapi.IN_QUERY,
			    type=openapi.TYPE_STRING,
			    format='date-time',
			    description='Filter Products by creation date/time'
			),
        ]
    )

	def list(self, request, *args, **kwargs):
		return super().list(request, *args, **kwargs)

	def get_queryset(self):
		queryset = super().get_queryset()
		min_price = self.request.query_params.get('min_price')
		max_price = self.request.query_params.get('max_price')
		category_param = self.request.query_params.get('category')
		if category_param:
			# Filter Category objects by name and get their IDs
			category_ids = Category.objects.filter(name=category_param).values_list('id', flat=True)
			# Filter Products by the Category IDs
			queryset = queryset.filter(category__in=category_ids)
		brand_param = self.request.query_params.get('category')
		if brand_param:
			# Filter Brand objects by name and get their IDs
			brand_ids = Brand.objects.filter(name=brand_param).values_list('id', flat=True)
			# Filter Products by the Brand IDs
			queryset = queryset.filter(brand__in=brand_ids)

		created_at_min = self.request.query_params.get('created_at_min')
		created_at_max = self.request.query_params.get('created_at_max')
		# Filter by created_at range
		if created_at_min:
			created_at_min_dt = datetime.datetime.strptime(created_at_min, '%Y-%m-%dT%H:%M:%S.%fZ').replace(tzinfo=timezone.utc)
			queryset = queryset.filter(created_at__gte=created_at_min_dt)
		if created_at_max:
			created_at_max_dt = datetime.datetime.strptime(created_at_max, '%Y-%m-%dT%H:%M:%S.%fZ').replace(tzinfo=timezone.utc)
			queryset = queryset.filter(created_at__lte=created_at_max_dt)
		#logic to search product on the basis of price range 
		if min_price and max_price:
			queryset = queryset.filter(price__range=(min_price, max_price))
		elif min_price:
			queryset = queryset.filter(price__gte=min_price)
		elif max_price:
			queryset = queryset.filter(price__lte=max_price)
		return queryset

class CartView(APIView):
	permission_classes = (permissions.IsAuthenticated,)
    def get(self, request):
        cart, created = Cart.objects.get_or_create(user=request.user.id)
        cart_items = cart.cartitem_set.all()
        context = {
            'cart_items': cart_items,
            'cart_total': sum(item.subtotal() for item in cart_items),
        }
        return render(request, 'cart.html', context)
    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                name='product_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_INTEGER,
                description='id of Product'
            ),
            openapi.Parameter(
                name='action',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                description='action for cart add, delete'
            ),
        ]
    )
    def post(self, request):
        cart, created = Cart.objects.get_or_create(user=request.user.id)
        product_id = request.POST.get('product_id')
        action = request.POST.get('action')
        product = get_object_or_404(Product, id=product_id)
        cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product, price=product.price)

        if action == 'add':
            cart_item.quantity += 1
            messages.success(request, f'{product.name} added to your cart.')
        elif action == 'remove':
            cart_item.quantity -= 1
            if cart_item.quantity <= 0:
                cart_item.delete()
                messages.success(request, f'{product.name} removed from your cart.')
        elif action == 'clear':
            cart.cartitem_set.all().delete()
            messages.success(request, 'Cart cleared.')
        
        cart_item.save()
        return self.get(request)

class ImageProcessor:
    def __init__(self, product_id, image_file):
        self.product_id = product_id
        self.image_file = image_file
    
    def process(self):
        product = Product.objects.get(id=self.product_id)
        # create different size of the image
        sizes = {
            'thumbnail': (100, 100),
            'medium': (300, 300),
            'full': None,
        }
        for size_name, size in sizes.items():
            if size is None:
                image_data = self.image_file.read()
            else:
                image = ImageFile(self.image_file)
                image.open()
                image.thumbnail(size)
                image_data = image.getvalue()

            # save the resized image data to the product
            filename, ext = os.path.splitext(self.image_file.name)
            filename = f'{filename}_{size_name}{ext}'
            product.image_sizes.save(filename, ImageFile(image_data))

class ImageProcessor:
    def __init__(self, product_id, image_file):
        self.product_id = product_id
        self.image_file = image_file
    
    def process(self):
        # get the product instance
        product = Product.objects.get(id=self.product_id)
        # generate the different sizes of the image
        sizes = {
            'thumbnail': (100, 100),
            'medium': (300, 300),
            'full': None,
        }
        for size_name, size in sizes.items():
            # generate the resized image data
            if size is None:
                image_data = self.image_file.read()
            else:
                image = ImageFile(self.image_file)
                image.open()
                image.thumbnail(size)
                image_data = image.getvalue()
            # save the resized image data to the product instance
            filename, ext = os.path.splitext(self.image_file.name)
            filename = f'{filename}_{size_name}{ext}'
            product.image_sizes.save(filename, ImageFile(image_data))

class ProductCreateView(APIView):
	permission_classes = (permissions.IsAuthenticated,)
    def post(self, request, format=None):
        serializer = ProductSerializer(data=request.data)
        if serializer.is_valid():
            # get the product data from the serializer
            product_data = serializer.validated_data
            # check if an existing product should be updated
            product_id = request.data.get('id')
            if product_id is not None:
                try:
                    product = Product.objects.get(id=product_id)
                    product.name = product_data.get('name', product.name)
                    product.description = product_data.get('description', product.description)
                    product.save()
                except Product.DoesNotExist:
                    return Response({'error': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)
            else:
                # create a new Product instance with the product data
                product = Product.objects.create(name=product_data['name'], category=product_data['category'], brand=product_data['brand'], \
                	price=product_data['price'], quantity=product_data['quantity'])
            # get the uploaded image data from the request
            image_data = request.FILES.get('image')
            if image_data is not None:
                # validate the image data (optional)
                # ...
                # save the image data to the product instance
                product.image.save(image_data.name, image_data)
                # process the image in a separate thread
                image_processor = ImageProcessor(product.id, image_data)
                threading.Thread(target=image_processor.process).start()
            # return a response with the serialized data of the created/updated product instance
            serializer = ProductSerializer(product)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)