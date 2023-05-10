from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.contrib.auth.models import User


#category table where we list all the categories of products
class Category(models.Model):
    name = models.CharField(max_length=50)

    def __str__(self):
    	return self.name

#brand table where we list all the brands of products
class Brand(models.Model):
	name = models.CharField(max_length=50)

	def __str__(self):
		return self.name	

#this is the master table for products
class Product(models.Model):
    name = models.CharField(max_length=100)
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, related_name='products_by_brand')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products_by_category')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    quantity = models.IntegerField(default=0)
    rating = models.FloatField(null=True)
    image = models.ImageField(upload_to='images/', null=True, blank=True)

    def __str__(self):
    	return self.name

class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    price = models.FloatField()

    def subtotal(self):
        return self.quantity * self.price