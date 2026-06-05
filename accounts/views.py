from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from .forms import RegisterForm, LoginForm

def register_view(request):
    form = RegisterForm(request.POST or None)
    if form.is_valid():
        user = form.save()
        login(request, user)
        return redirect('home')
    return render(request, 'accounts/register.html', {'form': form})

def login_view(request):
    form = LoginForm(request, data=request.POST or None)
    if form.is_valid():
        login(request, form.get_user())
        return redirect('home')
    return render(request, 'accounts/login.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('login')