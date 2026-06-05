from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import F
from .models import Task, Shift
from .forms import TaskForm


@login_required
def home(request):
    user  = request.user
    today = timezone.localdate()

    if request.method == 'POST':
        form = TaskForm(request.POST)
        if form.is_valid():
            task = form.save(commit=False)
            task.user = user
            task.save()
            return redirect('home')
    else:
        form = TaskForm()

    tasks     = Task.objects.filter(user=user, due_date=today)
    completed = tasks.filter(is_completed=True).count()
    total     = tasks.count()
    progress  = int((completed / total) * 100) if total > 0 else 0

    shifts = Shift.objects.filter(user=user, date__gte=today)[:3]

    next_level_xp = user.level * 500
    level_progress = int((user.xp / next_level_xp) * 100) if next_level_xp > 0 else 0

    context = {
        'form':           form,
        'tasks':          tasks,
        'completed':      completed,
        'total':          total,
        'progress':       progress,
        'shifts':         shifts,
        'level_progress': level_progress,
        'next_level_xp':  next_level_xp,
        'xp_remaining':   next_level_xp - user.xp,
        'today':          today,
    }
    return render(request, 'dashboard/home.html', context)


@login_required
def toggle_task(request, task_id):
    if request.method != 'POST':
        return redirect('home')

    task = get_object_or_404(Task, id=task_id, user=request.user)
    user = request.user

    if not task.is_completed:
        task.is_completed = True
        user.__class__.objects.filter(pk=user.pk).update(
            xp=F('xp') + task.xp_reward
        )
    else:
        task.is_completed = False
        user.__class__.objects.filter(pk=user.pk).update(
            xp=F('xp') - task.xp_reward
        )

    # Level yangilash
    user.refresh_from_db()
    user.level = (user.xp // 500) + 1
    user.save(update_fields=['level'])

    task.save()
    return redirect('home')


@login_required
def delete_task(request, task_id):
    if request.method != 'POST':
        return redirect('home')
    task = get_object_or_404(Task, id=task_id, user=request.user)
    if task.is_completed:
        user = request.user
        user.__class__.objects.filter(pk=user.pk).update(
            xp=F('xp') - task.xp_reward
        )
        user.refresh_from_db()
        user.level = (user.xp // 500) + 1
        user.save(update_fields=['level'])
    task.delete()
    return redirect('home')