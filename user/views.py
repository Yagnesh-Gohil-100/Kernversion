from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from .forms import SignUpForm  

def login_user(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            messages.success(request, "You have been successfully logged in...")
            return redirect('home')  # Redirect to the homepage
        else:
            messages.success(request, "Whoops! An error occurred during login. Please try again...")
            return redirect('login')
    return render(request, 'user/login.html', {})

def logout_user(request):
    logout(request)
    messages.success(request, "You have been logged out successfully...")
    return redirect('home')  # Redirect to the homepage

def register_user(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data['username']
            password = form.cleaned_data['password1']

            user = authenticate(username=username, password=password)
            login(request, user)
            messages.success(request, "Thank you for registering! You can now start using the website.")
            return redirect('home')  # Redirect to the homepage
        else:
            messages.success(request, "There was an error. Please try again...")
            return redirect('register')
    else:
        form = SignUpForm()
        return render(request, 'user/register.html', {'form': form})
