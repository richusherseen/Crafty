from django.shortcuts import render,redirect
from django.views.generic import TemplateView,View,CreateView,ListView
from customer.models import ContactUs
from customer.forms import RegisterForm,LoginForm,UserUpdateForm,ProfileUpdateForm,CheckOutForm
from django.contrib.auth.models import User,auth
from django.contrib.auth import login,authenticate,logout
from product.models import *
from .models import Profile
from django.http import HttpResponse,JsonResponse
import json
import datetime


class HomeView(View):
	form_class = LoginForm
	form_class2 = RegisterForm
	model = User
	
	def get(self,request):
		
		form_class = LoginForm() 
		form_class2 = RegisterForm()      
		template_name = 'index.html'
		products = Offer.objects.all()
		
		# categories = CategoryModel.objects.all()
		if request.user.is_authenticated:
			categories = CategoryModel.objects.all()
			customer = request.user
			order, created = Order.objects.get_or_create(customer=customer,complete=False)
			cartItems = order.get_cart_items
		else:
			categories = CategoryModel.objects.all()
			items=[]
			order = {'get_cart_total':0,'get_cart_items':0,'shipping':False}
			cartItems = order['get_cart_items']
		
		context = {
			'form':form_class,
			'form2':form_class2,
			'products':products,
			'cartItems':cartItems,
			'categories':categories
		}
		return render(request,template_name,context)
	
	def post(self,request):
		
		form2 = self.form_class2(request.POST)
		if form2.is_valid():
			password=request.POST.get('password')
			user = User.objects.create(username = request.POST.get('username'))
			user.set_password(password)
			user.save()
			return redirect('/')
		
		form = self.form_class(request.POST)
		if form.is_valid():
			username = request.POST.get('username')
			password = request.POST.get('password')
			user = auth.authenticate(username=username,password=password)
			if user is not None:
				login(request,user)
				if user.is_superuser:
					return render(request,"admin.html")
				if user.is_staff:
					return render(request,'vendor.html')
				else:
					if request.user.is_authenticated:
						customer=request.user
						order, created = Order.objects.get_or_create(customer=customer,complete=False)
						cartItems=order.get_cart_items
					else:
						order ={'get_cart_total':0,'get_cart_items':0,'shipping':False}
						cartItems=order['get_cart_items']
					products = ProductModel.objects.all()
					context = {
						
						'products':products,
						'cartItems':cartItems
					}
					return render(request,'index.html',context)

			else:
				return redirect('home_page')

#function for add to cart
def updateItem(request):
	
	data = json.loads(request.body)
	productId = data['productId']
	action = data['action']
	customer = request.user
	product = ProductModel.objects.get(id=productId)
	vendor = product.vendor
	order, created = Order.objects.get_or_create(customer=customer,complete=False)
	order.vendor_id = vendor
	order.save()
	
	orderItem, created = OrderItem.objects.get_or_create(order=order,product=product)

	if action == 'add':
		orderItem.quantity = (orderItem.quantity + 1)
	elif action == 'remove':
		orderItem.quantity = (orderItem.quantity - 1)

	orderItem.save()

	if orderItem.quantity <=0:
		orderItem.delete()
	


	return JsonResponse('Item was added' , safe=False) 

class ProfieView(View):
	
	def get(self,request):
		
		profiles = Profile.objects.get(user = request.user.id)
		customer = request.user
		order, created = Order.objects.get_or_create(customer=customer,complete=False)
		cartItems = order.get_cart_items

		context={
		'cartItems':cartItems,
		'profiles':profiles
		
		}
		return render(request,'profile.html',context)

class EditProfile(View):

	def get(self,request):
		
		u_form = UserUpdateForm(instance=request.user)
		p_form = ProfileUpdateForm(instance=request.user.profile)

		context={

			'u_form': u_form,
			'p_form': p_form
		}

		return render(request,'edit_profile.html',context)

	def post(self,request):

		u_form = UserUpdateForm(request.POST,instance=request.user)
		p_form = ProfileUpdateForm(request.POST,request.FILES,
		instance=request.user.profile)
		print(p_form)
		if u_form.is_valid() and p_form.is_valid():


			u_form.save()
			p_form.save()
			
			return redirect('profile')


def logout_view(request):
    logout(request)
    return redirect('/')

class CartView(View):

	def get(self,request):
		
		customer=request.user
		order, created = Order.objects.get_or_create(customer=customer,complete=False)
		items=order.orderitem_set.all()
		cartItems=order.get_cart_items
		context={
			'cartItems':cartItems,
			'items':items,
			'order':order,
		}
		return render(request,'cart.html',context)

def contact(request):
	if request.method == 'POST':
		name = request.POST['name']
		email = request.POST['email']
		subject = request.POST['subject']
		message = request.POST['message']
		
		feedback = ContactUs.objects.create(name=name,email=email,subject=subject,message=message)
		

	return render(request,'contact us.html')


class CheckOutView(View):
	form_class = CheckOutForm
	def get(self,request):
		form_class=CheckOutForm()
		customer=request.user
		order, created = Order.objects.get_or_create(customer=customer,complete=False)
		items=order.orderitem_set.all()
		cartItems=order.get_cart_items
		
		context={
			
			'cartItems':cartItems,
			'items':items,
			'order':order,
			'form':form_class
		}
		
		return render(request,'checkout.html',context)


def processOrder(request):
    transaction_id=datetime.datetime.now().timestamp()
    data =json.loads(request.body)
    if request.user.is_authenticated:
        customer=request.user
        order, created = Order.objects.get_or_create(customer=customer,complete=False)
        total= float(data['form']['total'])
        order.transaction_id = transaction_id

        if total == order.get_cart_total:
            order.complete = True
        order.save()
        if order.shipping == True:
            ShippingAdress.objects.create(
                customer=customer,
                order=order,
                address=data['shipping']['address'],
                city=data['shipping']['city'],
                state=data['shipping']['state'],
                zipcode=data['shipping']['zipcode'],
            )
            # print(ShippingAdress.address)

    else:
        print("user is not logged in")
    return JsonResponse('Payment complete' , safe=False) 


class OrderListView(View):

    def get(self,request):
        customer=request.user
        # print(customer)
        order=Order.objects.filter(customer=customer,complete=True)
        items =[]
        for i in order:
            details=OrderItem.objects.filter(order=i,product__isnull=False)
            for j in details:
                items.append(j)

        context ={
			"items":items,
			"order":order,
			# "cartItems":cartItems,

    	}


        return render(request,'order_view.html',context)

def product_list_based_on_category(request,category_id):
	if request.user.is_authenticated:
			product_cate = ProductModel.objects.filter(product_category = category_id)
			customer = request.user
			order, created = Order.objects.get_or_create(customer=customer,complete=False)
			cartItems=order.get_cart_items
			
	else:
		product_cate = ProductModel.objects.filter(product_category = category_id)
		order = {'get_cart_total':0,'get_cart_items':0,'shipping':False}
		cartItems = order['get_cart_items']
	
	context = {
		'product_cate':product_cate,
		'cartItems':cartItems,
		
	}
	return render(request,'category_based_list.html',context)