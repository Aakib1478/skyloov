from django.contrib.auth.models import User
from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.hashers import make_password
from .models import Product, Brand, Category


#serializer for adding new user and  check if email is already exists or not
class UserSerializer(serializers.ModelSerializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        """
        Check if email address already exists.
        """
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email address already exists.")
        return value

    def create(self, validated_data):
        password = validated_data.pop('password')
        validated_data['password'] = make_password(password)
        user = super().create(validated_data)
        return user


    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password']
        extra_kwargs = {'password': {'write_only': True}}


#to authenticate the user
class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()

    def validate(self, attrs):
        print(attrs['username'])
        print(attrs['password'])
        user = authenticate(username=attrs['username'], password=attrs['password'])
        print(user)
        if not user:
            raise serializers.ValidationError('Invalid username or password.')

        if not user.is_active:
            raise serializers.ValidationError('User account is disabled.')

        return attrs

class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = ('name',)

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ('name',)

class ProductSearchSerializer(serializers.ModelSerializer):
    brand = BrandSerializer()
    category = CategorySerializer()
    min_price = serializers.DecimalField(required=False, decimal_places=2, max_digits=10)
    max_price = serializers.DecimalField(required=False, decimal_places=2, max_digits=10)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['brand'] = data['brand']['name']
        data['category'] = data['category']['name']
        return data

    class Meta:
        model = Product
        fields = ('id','name', 'brand', 'category', 'min_price', 'max_price', 'price')


