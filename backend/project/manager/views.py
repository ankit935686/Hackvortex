from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth import get_user_model
from users.models import Complaint, Notification
from django.http import JsonResponse, HttpResponse
from django.db.models import Q, Count
from datetime import datetime, timedelta
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from io import BytesIO
from django.utils import timezone
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags

# Create your views here.

def signup_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        email = request.POST['email']
        password1 = request.POST['password1']
        password2 = request.POST['password2']

        if password1 != password2:
            messages.error(request, "Passwords don't match!")
            return redirect('manager:signup')

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists!")
            return redirect('manager:signup')

        user = User.objects.create_user(username=username, email=email, password=password1)
        # Authenticate the user first, then login
        authenticated_user = authenticate(request, username=username, password=password1)
        if authenticated_user is not None:
            login(request, authenticated_user)
            messages.success(request, "Registration successful!")
            return redirect('manager:dashboard')

    return render(request, 'manager/signup.html')

def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            messages.success(request, "Login successful!")
            return redirect('manager:dashboard')
        else:
            messages.error(request, "Invalid username or password!")
            
    return render(request, 'manager/login.html')

def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect('manager:login')

@login_required
def dashboard_view(request):
    return render(request, 'manager/dashboard.html')

@login_required
def profile_view(request):
    return render(request, 'manager/dashboard.html')  # You can create a separate profile template later

@login_required
def smoke_monitor_redirect(request):
    return redirect('arduinofeature:smoke_monitor')

@login_required
def complaints_view(request):
    complaints = Complaint.objects.all().order_by('-created_at')
    return render(request, 'manager/complaints.html', {'complaints': complaints})

@login_required
def update_complaint_status(request):
    if request.method == 'POST':
        try:
            complaint_id = request.POST.get('complaint_id')
            new_status = request.POST.get('status')
            
            complaint = Complaint.objects.get(id=complaint_id)
            old_status = complaint.status
            complaint.status = new_status
            complaint.save()
            
            # Prepare email content
            context = {
                'user': complaint.user,
                'complaint_title': complaint.title,
                'complaint_type': complaint.complaint_type,
                'old_status': old_status,
                'new_status': new_status,
                'description': complaint.description,
                'created_at': complaint.created_at,
                'updated_at': complaint.updated_at,
            }
            
            # Render email content from template
            html_message = render_to_string('manager/emails/complaint_status_update.html', context)
            plain_message = strip_tags(html_message)
            
            # Send email
            send_mail(
                subject=f'Complaint Status Update - {complaint.title}',
                message=plain_message,
                from_email=None,  # Uses DEFAULT_FROM_EMAIL from settings
                recipient_list=[complaint.user.email],
                html_message=html_message,
                fail_silently=False,
            )
            
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@login_required
def filter_complaints(request):
    complaints = Complaint.objects.all()
    
    # Filter by type
    complaint_type = request.GET.get('type')
    if complaint_type:
        complaints = complaints.filter(complaint_type=complaint_type)
    
    # Filter by status
    status = request.GET.get('status')
    if status:
        complaints = complaints.filter(status=status)
    
    # Filter by date range
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    if date_from:
        complaints = complaints.filter(created_at__gte=date_from)
    if date_to:
        complaints = complaints.filter(created_at__lte=date_to)
    
    # Order by latest first
    complaints = complaints.order_by('-created_at')
    
    # Prepare the data for JSON response
    complaints_data = [{
        'id': c.id,
        'title': c.title,
        'complaint_type': c.complaint_type,
        'description': c.description[:50] + '...' if len(c.description) > 50 else c.description,
        'latitude': c.latitude,
        'longitude': c.longitude,
        'status': c.status,
        'user': c.user.username,
        'created_at': c.created_at.strftime('%b %d, %Y %H:%M'),
        'image': c.image.url if c.image else None
    } for c in complaints]
    
    return JsonResponse({
        'success': True,
        'complaints': complaints_data
    })

@login_required
def export_complaints_pdf(request):
    # Create the HttpResponse object with PDF headers
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(letter))
    
    # Container for the 'Flowable' objects
    elements = []
    
    # Define styles
    styles = getSampleStyleSheet()
    title_style = styles['Heading1']
    subtitle_style = styles['Heading2']
    normal_style = styles['Normal']

    # Add title
    elements.append(Paragraph('Complaints Report', title_style))
    elements.append(Spacer(1, 20))

    # Add summary statistics
    total_complaints = Complaint.objects.count()
    pending_complaints = Complaint.objects.filter(status='PENDING').count()
    in_progress_complaints = Complaint.objects.filter(status='IN_PROGRESS').count()
    resolved_complaints = Complaint.objects.filter(status='RESOLVED').count()

    # Summary Table
    summary_data = [
        ['Summary Statistics'],
        ['Total Complaints', str(total_complaints)],
        ['Pending Complaints', str(pending_complaints)],
        ['In Progress Complaints', str(in_progress_complaints)],
        ['Resolved Complaints', str(resolved_complaints)]
    ]

    summary_table = Table(summary_data)
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 14),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))

    elements.append(summary_table)
    elements.append(Spacer(1, 20))

    # Complaints by Type
    elements.append(Paragraph('Complaints by Type', subtitle_style))
    type_counts = Complaint.objects.values('complaint_type').annotate(
        count=Count('id')
    ).order_by('-count')

    type_data = [['Type', 'Count']]
    type_data.extend([[t['complaint_type'], str(t['count'])] for t in type_counts])

    type_table = Table(type_data)
    type_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))

    elements.append(type_table)
    elements.append(Spacer(1, 20))

    # Recent Complaints Table
    elements.append(Paragraph('Recent Complaints', subtitle_style))
    complaints = Complaint.objects.all().order_by('-created_at')[:10]
    
    complaints_data = [['Title', 'Type', 'Status', 'Submitted By', 'Date']]
    complaints_data.extend([
        [
            c.title,
            c.complaint_type,
            c.status,
            c.user.username,
            c.created_at.strftime('%Y-%m-%d %H:%M')
        ] for c in complaints
    ])

    complaints_table = Table(complaints_data)
    complaints_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))

    elements.append(complaints_table)

    # Build PDF
    doc.build(elements)
    
    # Get the value of the BytesIO buffer and return it
    pdf = buffer.getvalue()
    buffer.close()
    
    # Create the HTTP response
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="complaints_report.pdf"'
    response.write(pdf)
    
    return response

@login_required
def notifications_view(request):
    """View to display the notifications management page"""
    # Get recently sent notifications
    recent_notifications = Notification.objects.filter(
        notification_type='ALERT'
    ).order_by('-created_at')[:10]
    
    return render(request, 'manager/notifications.html', {
        'recent_notifications': recent_notifications
    })

@login_required
def send_notification(request):
    """Send a notification to all citizens via app and email"""
    if request.method == 'POST':
        try:
            notification_type = request.POST.get('notification_type')
            title = request.POST.get('title')
            message = request.POST.get('message')
            priority = request.POST.get('priority', 'normal')
            
            # Get all users
            users = User.objects.all()
            
            # Create notifications and send emails for each user
            for user in users:
                # Create in-app notification
                Notification.objects.create(
                    user=user,
                    title=title,
                    message=message,
                    notification_type=notification_type,
                    is_read=False
                )
                
                # Prepare email content
                context = {
                    'user': user,
                    'title': title,
                    'message': message,
                    'notification_type': notification_type,
                    'priority': priority,
                    'timestamp': timezone.now()
                }
                
                # Render email content from template
                html_message = render_to_string('manager/emails/notification_alert.html', context)
                plain_message = strip_tags(html_message)
                
                # Send email
                send_mail(
                    subject=f'Smart City Alert: {title}',
                    message=plain_message,
                    from_email=None,  # Uses DEFAULT_FROM_EMAIL from settings
                    recipient_list=[user.email],
                    html_message=html_message,
                    fail_silently=True  # Set to True to prevent email errors from breaking the notification process
                )
            
            messages.success(request, f"Notification '{title}' sent successfully to {users.count()} users via app and email.")
            return redirect('manager:notifications')
            
        except Exception as e:
            messages.error(request, f"Error sending notification: {str(e)}")
            return redirect('manager:notifications')
    
    return redirect('manager:notifications')
