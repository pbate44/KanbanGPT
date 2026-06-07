
from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .helpers import max_boards_for_user
from frontend.models import Board


@login_required
def dashboard(request):
    boards = list(Board.objects.filter(owner=request.user).order_by('-updated_at'))
    max_boards = max_boards_for_user(request.user)

    return render(request, 'dashboard.html', {
        'boards':      boards,
        'max_boards':  max_boards,
        'is_premium':  request.user.profile.is_premium(),
        'board_count': len(boards),
    })
