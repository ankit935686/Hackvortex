from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .models import Discussion, Comment
from django.views.decorators.csrf import csrf_exempt
import json

# Create your views here.

@login_required
def discussions_view(request):
    discussions = Discussion.objects.all().order_by('-created_at')
    return render(request, 'discussion/discussions.html', {'discussions': discussions})

@login_required
@csrf_exempt
def create_discussion(request):
    if request.method == 'POST':
        try:
            title = request.POST.get('title')
            content = request.POST.get('content')
            latitude = request.POST.get('latitude')
            longitude = request.POST.get('longitude')
            location_name = request.POST.get('location_name')
            
            discussion = Discussion.objects.create(
                user=request.user,
                title=title,
                content=content,
                latitude=latitude,
                longitude=longitude,
                location_name=location_name
            )

            if 'image' in request.FILES:
                discussion.image = request.FILES['image']
                discussion.save()

            return JsonResponse({'success': True, 'discussion_id': discussion.id})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@login_required
@csrf_exempt
def add_comment(request, discussion_id):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            content = data.get('content')
            discussion = get_object_or_404(Discussion, id=discussion_id)
            
            comment = Comment.objects.create(
                user=request.user,
                discussion=discussion,
                content=content
            )

            return JsonResponse({
                'success': True,
                'comment_id': comment.id,
                'username': comment.user.username,
                'content': comment.content,
                'created_at': comment.created_at.strftime("%B %d, %Y %I:%M %p")
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})
