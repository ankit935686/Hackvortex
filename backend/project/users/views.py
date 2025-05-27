from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.models import User
from django.contrib import messages
from .models import UserProfile, Complaint, Notification, TrafficReport
import requests
from django.conf import settings
from datetime import datetime, timedelta
import json
from django.core.serializers.json import DjangoJSONEncoder
from django.contrib.auth.decorators import login_required
import random
import math
from django.http import JsonResponse
import google.generativeai as genai
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from geopy.distance import geodesic
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

# List of Google Maps API keys for rotation/fallback
GOOGLE_MAPS_API_KEYS = [
    'AIzaSyB8Qpd8drt-Fnvd-rCNnky370uxspTjfXY',
    'AIzaSyAKM4O1T2X3hPTh70yNj5hASOjQ5U_uqCA',
    'AIzaSyCFWAdIGgCKB4KnNnTNSNMcVOshwW2cdVM',
    'AIzaSyBYzXj5wF4L6mChyyc5xwfb2QT1QEZ9VN8'
]

def get_google_maps_api_key():
    """Return a random Google Maps API key for load balancing."""
    return random.choice(GOOGLE_MAPS_API_KEYS)

def try_google_maps_request(endpoint, params):
    """Try each API key until one works for Google Maps API requests."""
    # Shuffle the keys to balance load
    keys = GOOGLE_MAPS_API_KEYS.copy()
    random.shuffle(keys)
    
    for api_key in keys:
        try:
            params['key'] = api_key
            response = requests.get(endpoint, params=params, timeout=5)
            
            # Check if response is valid
            if response.status_code == 200:
                data = response.json()
                if 'error_message' not in data and data.get('status') != 'REQUEST_DENIED':
                    logger.info(f"Successfully used Google Maps API key: {api_key[:10]}...")
                    return data
            
            logger.warning(f"API key {api_key[:10]}... failed: {response.status_code}")
        except Exception as e:
            logger.error(f"Error with API key {api_key[:10]}...: {str(e)}")
    
    # If all keys fail, return None
    logger.error("All Google Maps API keys failed")
    return None

# Context processor for adding unread notifications to all templates
def notifications_processor(request):
    context = {}
    if request.user.is_authenticated:
        unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
        context['unread_notifications_count'] = unread_count
        
        # Add Google Maps API key to all templates
        context['google_maps_api_key'] = get_google_maps_api_key()
        
    return context

# Create your views here.

def landing_page(request):
    return render(request, 'users/landing.html')

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid username or password')
    
    return render(request, 'users/login.html')

def signup_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists')
            return render(request, 'users/signup.html')
        
        # Create user
        user = User.objects.create_user(username=username, password=password)
        UserProfile.objects.create(user=user)
        
        # Log user in
        login(request, user)
        return redirect('dashboard')
        
    return render(request, 'users/signup.html')

@login_required
def dashboard_view(request):
    # Get unread notifications count for the navbar
    unread_notifications_count = Notification.objects.filter(user=request.user, is_read=False).count()
    
    try:
        # Fetch current weather data
        api_key = '00e0ddaa0cd9030ecc625b32a507f9e8'
        city = 'Mumbai'  # You can make this dynamic based on user's location
        
        # Current weather
        weather_url = f'https://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric'
        weather_response = requests.get(weather_url)
        current_weather = weather_response.json()
        
        # 7-day forecast
        forecast_url = f'https://api.openweathermap.org/data/2.5/forecast?q={city}&appid={api_key}&units=metric'
        forecast_response = requests.get(forecast_url)
        forecast_data = forecast_response.json()
        
        context = {
            'unread_notifications_count': unread_notifications_count,
            'current_weather': {
                'temp': round(current_weather['main']['temp']),
                'feels_like': round(current_weather['main']['feels_like']),
                'humidity': current_weather['main']['humidity'],
                'wind_speed': current_weather['wind']['speed'],
                'description': current_weather['weather'][0]['description'].capitalize(),
                'icon': current_weather['weather'][0]['icon'],
            },
            'forecast': forecast_data['list'][:8],  # Next 24 hours (3-hour intervals)
            'daily_forecast': forecast_data['list'][::8][:5],  # 5-day forecast
        }
    except Exception as e:
        # Fallback data if API fails
        context = {
            'unread_notifications_count': unread_notifications_count,
            'error': str(e)
        }
    
    return render(request, 'users/dashboard.html', context)

@login_required
def air_quality_view(request):
    return render(request, 'users/air_quality.html')

def get_wind_direction(degrees):
    directions = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']
    index = round(degrees / (360 / len(directions))) % len(directions)
    return directions[index]

def get_health_advice(aqi):
    if aqi <= 50:
        return "Air quality is good. Perfect for outdoor activities!"
    elif aqi <= 100:
        return "Air quality is moderate. Sensitive individuals should limit prolonged outdoor exposure."
    else:
        return "Air quality is unhealthy. Avoid outdoor activities if possible."

def generate_heatmap_data(base_aqi=50):
    """Generate realistic heatmap data with irregular pollution patterns"""
    # Mumbai coordinates
    base_lat = 19.0760
    base_lng = 72.8777
    
    # Define pollution hotspots with more varied locations and intensities
    hotspots = [
        {'lat': 19.0178, 'lng': 72.8478, 'intensity': 1.8, 'radius': 0.03},  # Dharavi (larger impact)
        {'lat': 19.1176, 'lng': 72.8791, 'intensity': 1.4, 'radius': 0.04},  # BKC (business district)
        {'lat': 19.0895, 'lng': 72.8656, 'intensity': 1.6, 'radius': 0.025}, # Sion (traffic junction)
        {'lat': 19.0596, 'lng': 72.8295, 'intensity': 1.3, 'radius': 0.035}, # Mahim
        {'lat': 19.0219, 'lng': 72.8347, 'intensity': 1.7, 'radius': 0.045}, # Worli Industrial
        {'lat': 19.0344, 'lng': 72.8686, 'intensity': 1.5, 'radius': 0.03},  # Chembur
        {'lat': 19.0549, 'lng': 72.8435, 'intensity': 1.2, 'radius': 0.02},  # Random pocket
        {'lat': 19.1024, 'lng': 72.8535, 'intensity': 1.4, 'radius': 0.025}, # Random pocket
    ]
    
    # Add some random temporary hotspots (simulating traffic jams, temporary industrial activity, etc.)
    num_temp_hotspots = random.randint(3, 6)
    for _ in range(num_temp_hotspots):
        lat_offset = random.uniform(-0.05, 0.05)
        lng_offset = random.uniform(-0.05, 0.05)
        hotspots.append({
            'lat': base_lat + lat_offset,
            'lng': base_lng + lng_offset,
            'intensity': random.uniform(1.1, 1.4),
            'radius': random.uniform(0.01, 0.03)
        })
    
    heatmap_data = []
    points_per_hotspot = 15  # Number of points to generate around each hotspot
    
    # Generate irregular points around each hotspot
    for hotspot in hotspots:
        for _ in range(points_per_hotspot):
            # Create random angle and distance from hotspot
            angle = random.uniform(0, 2 * math.pi)
            distance = random.uniform(0, hotspot['radius'])
            
            # Calculate point position
            lat = hotspot['lat'] + (distance * math.cos(angle))
            lng = hotspot['lng'] + (distance * math.sin(angle))
            
            # Calculate weight based on distance from hotspot
            distance_factor = 1 - (distance / hotspot['radius'])
            base_weight = distance_factor * hotspot['intensity']
            
            # Add randomness for more natural look
            random_factor = random.uniform(0.7, 1.3)
            weight = min(1.0, base_weight * random_factor)
            
            # Scale weight based on current AQI
            weight = weight * (base_aqi / 100)
            
            if weight > 0.1:  # Only add significant pollution points
                heatmap_data.append({
                    'location': {'lat': lat, 'lng': lng},
                    'weight': weight
                })
    
    # Add some scattered background pollution
    num_background_points = 50
    for _ in range(num_background_points):
        lat = base_lat + random.uniform(-0.06, 0.06)
        lng = base_lng + random.uniform(-0.06, 0.06)
        weight = random.uniform(0.1, 0.3) * (base_aqi / 100)
        
        heatmap_data.append({
            'location': {'lat': lat, 'lng': lng},
            'weight': weight
        })
    
    return heatmap_data

@login_required
def air_quality(request):
    api_key = '2b108f32-6919-4e95-98ba-31b26be32dcc'  # Replace with your actual API key
    city = 'Mumbai'  # Default city
    state = 'Maharashtra'
    country = 'India'
    
    # Get unread notifications count for the navbar
    unread_notifications_count = Notification.objects.filter(user=request.user, is_read=False).count()
    
    try:
        # Make API request to IQAir
        url = f'http://api.airvisual.com/v2/city?city={city}&state={state}&country={country}&key={api_key}'
        response = requests.get(url)
        data = response.json()
        
        if data['status'] == 'success':
            current = data['data']['current']
            
            # Generate time labels for the last 24 hours
            time_labels = [(datetime.now() - timedelta(hours=x)).strftime('%H:%M') 
                          for x in range(24, -1, -1)]
            
            # Sample data for charts
            aqi_history = [current['pollution']['aqius'] + x for x in range(-12, 13)]
            temperatures = [current['weather']['tp'] + x for x in range(-5, 6)]
            
            context = {
                'aqi': current['pollution']['aqius'],
                'temperature': current['weather']['tp'],
                'humidity': current['weather']['hu'],
                'city': city,
                'country': country,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'lat': 19.0760,
                'lng': 72.8777,
                'heatmap_data': json.dumps(generate_heatmap_data(current['pollution']['aqius']), cls=DjangoJSONEncoder),
                'pollutant_levels': json.dumps([
                    current['pollution'].get('pm25', 30),
                    current['pollution'].get('pm10', 50),
                    current['pollution'].get('o3', 40),
                    current['pollution'].get('no2', 25),
                    current['pollution'].get('so2', 15),
                    current['pollution'].get('co', 20)
                ]),
                'weather_times': json.dumps(time_labels, cls=DjangoJSONEncoder),
                'temperatures': json.dumps(temperatures, cls=DjangoJSONEncoder),
                'aqi_levels': json.dumps(aqi_history, cls=DjangoJSONEncoder),
                'trend_labels': json.dumps(time_labels, cls=DjangoJSONEncoder),
                'trend_data': json.dumps(aqi_history, cls=DjangoJSONEncoder),
                'wind_speed': current['weather'].get('ws', 0),
                'wind_degree': current['weather'].get('wd', 0),
                'wind_direction': get_wind_direction(current['weather'].get('wd', 0)),
                'health_advice': get_health_advice(current['pollution']['aqius']),
                'unread_notifications_count': unread_notifications_count,
            }
            
            return render(request, 'users/air_quality.html', context)
            
    except Exception as e:
        # Fallback data in case of API failure
        context = {
            'aqi': 50,
            'temperature': 20,
            'humidity': 60,
            'city': city,
            'country': country,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'lat': 19.0760,
            'lng': 72.8777,
            'heatmap_data': json.dumps([]),  # Empty array as fallback
            'pollutant_levels': json.dumps([30, 50, 40, 25, 15, 20]),
            'weather_times': json.dumps([]),
            'temperatures': json.dumps([]),
            'aqi_levels': json.dumps([]),
            'trend_labels': json.dumps([]),
            'trend_data': json.dumps([]),
            'wind_speed': 0,
            'wind_degree': 0,
            'wind_direction': 'N',
            'health_advice': 'Unable to fetch air quality data.',
            'error': str(e),
            'unread_notifications_count': unread_notifications_count,
        }
        
    return render(request, 'users/air_quality.html', context)

@login_required
def traffic(request):
    """
    Enhanced traffic view with weather, routes, and conditions
    """
    # Get unread notifications count for the navbar
    unread_notifications_count = Notification.objects.filter(user=request.user, is_read=False).count()
    
    try:
        # Fetch weather data (using OpenWeatherMap API as example)
        weather_api_key = '84ec4bbce24409d1400e5157f252b79d'  # Replace with your API key
        weather_url = f'http://api.openweathermap.org/data/2.5/weather?q=Mumbai&appid={weather_api_key}'
        weather_response = requests.get(weather_url)
        weather_data = weather_response.json()

        # Process weather conditions that affect traffic
        weather_impact = {
            'severity': 'low',
            'description': 'Normal driving conditions',
            'alerts': []
        }

        if weather_data.get('weather'):
            condition = weather_data['weather'][0]['main'].lower()
            if 'rain' in condition:
                weather_impact = {
                    'severity': 'high',
                    'description': 'Heavy rain affecting visibility',
                    'alerts': ['Reduce speed', 'Maintain safe distance', 'Use headlights']
                }
            elif 'fog' in condition:
                weather_impact = {
                    'severity': 'high',
                    'description': 'Foggy conditions reducing visibility',
                    'alerts': ['Use fog lights', 'Reduce speed', 'Extra caution at intersections']
                }
            elif 'snow' in condition:
                weather_impact = {
                    'severity': 'severe',
                    'description': 'Snowy conditions affecting road safety',
                    'alerts': ['Avoid unnecessary travel', 'Use snow chains', 'Maintain safe distance']
                }

        # Sample traffic incidents data (in production, use real-time API)
        traffic_incidents = [
            {
                'type': 'accident',
                'location': {'lat': 34.0522, 'lng': -118.2437},
                'severity': 'high',
                'description': 'Multi-vehicle collision',
                'estimated_delay': '30 mins'
            },
            {
                'type': 'construction',
                'location': {'lat': 34.0622, 'lng': -118.2537},
                'severity': 'medium',
                'description': 'Road maintenance',
                'estimated_delay': '15 mins'
            }
        ]

        # Route recommendations based on current conditions
        route_recommendations = {
            'fastest': {
                'name': 'Highway 101',
                'estimated_time': '25 mins',
                'distance': '15.5 miles',
                'congestion_level': 'moderate'
            },
            'safest': {
                'name': 'Local Route via Main St',
                'estimated_time': '35 mins',
                'distance': '14.2 miles',
                'congestion_level': 'low'
            },
            'eco_friendly': {
                'name': 'Hybrid Route',
                'estimated_time': '30 mins',
                'distance': '14.8 miles',
                'congestion_level': 'low'
            }
        }

        context = {
            'api_key': 'AIzaSyAKM4O1T2X3hPTh70yNj5hASOjQ5U_uqCA',
            'weather_impact': weather_impact,
            'traffic_incidents': json.dumps(traffic_incidents),
            'route_recommendations': route_recommendations,
            'current_weather': {
                'temperature': round((weather_data.get('main', {}).get('temp', 273.15) - 273.15), 1),
                'condition': weather_data.get('weather', [{}])[0].get('main', 'Unknown'),
                'visibility': weather_data.get('visibility', 10000) / 1000,  # Convert to km
                'wind_speed': weather_data.get('wind', {}).get('speed', 0)
            },
            'unread_notifications_count': unread_notifications_count,
        }

    except Exception as e:
        # Fallback data if API calls fail
        context = {
            'api_key': 'AIzaSyAKM4O1T2X3hPTh70yNj5hASOjQ5U_uqCA',
            'weather_impact': {'severity': 'unknown', 'description': 'Weather data unavailable', 'alerts': []},
            'traffic_incidents': '[]',
            'route_recommendations': {},
            'current_weather': {
                'temperature': 20,
                'condition': 'Unknown',
                'visibility': 10,
                'wind_speed': 0
            },
            'error': str(e),
            'unread_notifications_count': unread_notifications_count,
        }

    return render(request, 'users/traffic.html', context)

@login_required
def complaints_view(request):
    # Get unread notifications count for the navbar
    unread_notifications_count = Notification.objects.filter(user=request.user, is_read=False).count()
    
    context = {
        'google_maps_api_key': 'AIzaSyAKM4O1T2X3hPTh70yNj5hASOjQ5U_uqCA',
        'unread_notifications_count': unread_notifications_count,
    }
    return render(request, 'users/complaints.html', context)

@login_required
def submit_complaint(request):
    if request.method == 'POST':
        try:
            # Get form data
            title = request.POST.get('title')
            description = request.POST.get('description')
            image = request.FILES.get('image')
            latitude = float(request.POST.get('latitude'))
            longitude = float(request.POST.get('longitude'))
            complaint_type = request.POST.get('complaint_type')

            # Configure Gemini API
            genai.configure(api_key='AIzaSyC3ekNJCildP0PuU5rPYZKdCtwmaYS3S50')
            model = genai.GenerativeModel('gemini-1.5-flash')

            # Generate AI classification
            prompt = f"Classify this urban issue: Title: {title}. Description: {description}. Choose from these categories: Pothole, Water Leak, Broken Signal, Garbage, or Other. Also provide a brief analysis."
            response = model.generate_content(prompt)
            ai_classification = response.text

            # Create complaint with the user-selected type
            complaint = Complaint.objects.create(
                user=request.user,
                title=title,
                description=description,
                image=image,
                latitude=latitude,
                longitude=longitude,
                ai_classification=ai_classification,
                complaint_type=complaint_type
            )

            return JsonResponse({'success': True})

        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@login_required
def get_complaints(request):
    complaint_type = request.GET.get('type', 'ALL')
    
    if complaint_type == 'ALL':
        complaints = Complaint.objects.all()
    else:
        complaints = Complaint.objects.filter(complaint_type=complaint_type)
    
    complaints_data = [{
        'title': c.title,
        'description': c.description,
        'image': c.image.url if c.image else None,
        'latitude': c.latitude,
        'longitude': c.longitude,
        'status': c.status,
        'created_at': c.created_at.strftime('%Y-%m-%d %H:%M:%S')
    } for c in complaints]
    
    return JsonResponse({'complaints': complaints_data})

@require_http_methods(["GET", "POST"])
def logout_view(request):
    logout(request)
    return redirect('landing')

@login_required
def notifications_view(request):
    # Get all notifications for the user
    notifications = Notification.objects.filter(user=request.user)
    
    # Get unread notifications count
    unread_notifications_count = notifications.filter(is_read=False).count()
    
    context = {
        'notifications': notifications,
        'unread_notifications_count': unread_notifications_count
    }
    
    return render(request, 'users/notifications.html', context)

@login_required
@require_http_methods(["POST"])
def update_location(request):
    """Update user's location in their profile"""
    try:
        data = json.loads(request.body)
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        
        if latitude and longitude:
            # Update user profile with location
            profile, created = UserProfile.objects.get_or_create(user=request.user)
            profile.latitude = latitude
            profile.longitude = longitude
            profile.save()
            
            # Generate notifications based on location (example)
            generate_location_based_notifications(request.user, latitude, longitude)
            
            return JsonResponse({'success': True})
        else:
            return JsonResponse({'success': False, 'error': 'Invalid location data'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
def nearby_incidents(request):
    """Fetch incidents near the user's location"""
    try:
        lat = float(request.GET.get('lat'))
        lng = float(request.GET.get('lng'))
        
        # Get complaints within certain radius (e.g., 10km)
        user_location = (lat, lng)
        max_distance_km = 10
        
        # Get all complaints
        all_complaints = Complaint.objects.all()
        
        # Filter nearby complaints manually with distance calculation
        nearby_complaints = []
        for complaint in all_complaints:
            complaint_location = (complaint.latitude, complaint.longitude)
            distance = geodesic(user_location, complaint_location).kilometers
            
            if distance <= max_distance_km:
                nearby_complaints.append({
                    'id': complaint.id,
                    'title': complaint.title,
                    'description': complaint.description,
                    'type': complaint.get_complaint_type_display(),
                    'status': complaint.status,
                    'distance': distance,
                    'created_at': complaint.created_at.strftime('%Y-%m-%d %H:%M'),
                    'latitude': complaint.latitude,
                    'longitude': complaint.longitude
                })
        
        # Sort by distance
        nearby_complaints.sort(key=lambda x: x['distance'])
        
        return JsonResponse({'success': True, 'incidents': nearby_complaints})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
@require_http_methods(["POST"])
def mark_notification_read(request, notification_id):
    """Mark a notification as read"""
    try:
        notification = Notification.objects.get(id=notification_id, user=request.user)
        notification.is_read = True
        notification.save()
        return JsonResponse({'success': True})
    except Notification.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Notification not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
@require_http_methods(["POST"])
def mark_all_notifications_read(request):
    """Mark all notifications as read for a user"""
    try:
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

def generate_location_based_notifications(user, latitude, longitude):
    """Generate notifications based on user location"""
    # Example: Check air quality in the area
    try:
        # Simulate an air quality API call with random data
        aqi = random.randint(30, 150)
        
        notification_type = 'AIR_QUALITY'
        title = f"Air Quality Alert: {aqi} AQI"
        
        if aqi < 50:
            message = "Air quality in your area is good. Enjoy outdoor activities!"
        elif aqi < 100:
            message = "Moderate air quality in your area. Sensitive individuals should take precautions."
        else:
            message = "Unhealthy air quality detected in your area. Limit outdoor activities."
            
        # Create notification if AQI is concerning (over 75)
        if aqi > 75:
            Notification.objects.create(
                user=user,
                title=title,
                message=message,
                notification_type=notification_type,
                latitude=latitude,
                longitude=longitude
            )
        
        # Check for nearby complaints
        user_location = (latitude, longitude)
        max_distance_km = 2  # Only very close complaints trigger notifications
        
        # Get recent complaints (last 24 hours)
        recent_complaints = Complaint.objects.filter(
            created_at__gte=datetime.now() - timedelta(days=1)
        )
        
        for complaint in recent_complaints:
            complaint_location = (complaint.latitude, complaint.longitude)
            distance = geodesic(user_location, complaint_location).kilometers
            
            if distance <= max_distance_km:
                # Create notification for nearby incident
                Notification.objects.create(
                    user=user,
                    title=f"Nearby {complaint.get_complaint_type_display()}: {complaint.title}",
                    message=f"{complaint.description[:100]}... ({distance:.1f}km from your location)",
                    notification_type='COMPLAINT',
                    latitude=complaint.latitude,
                    longitude=complaint.longitude
                )
                
        # Example: Traffic alert simulation
        if random.random() < 0.3:  # 30% chance of traffic alert
            traffic_messages = [
                "Heavy traffic reported on nearby main roads due to an accident.",
                "Road construction causing delays in your vicinity. Consider alternate routes.",
                "Traffic signal outage reported near your location. Expect delays."
            ]
            
            Notification.objects.create(
                user=user,
                title=f"Traffic Alert Near You",
                message=random.choice(traffic_messages),
                notification_type='TRAFFIC',
                latitude=latitude,
                longitude=longitude
            )
            
    except Exception as e:
        print(f"Error generating notifications: {str(e)}")
        # Fail silently - notifications are non-critical

@login_required
def rain_alerts(request):
    api_key = '00e0ddaa0cd9030ecc625b32a507f9e8'
    city = 'Mumbai'
    
    try:
        # Fetch current weather data
        weather_url = f'https://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric'
        weather_response = requests.get(weather_url)
        current_weather = weather_response.json()
        
        # Fetch forecast data
        forecast_url = f'https://api.openweathermap.org/data/2.5/forecast?q={city}&appid={api_key}&units=metric'
        forecast_response = requests.get(forecast_url)
        forecast_data = forecast_response.json()
        
        # Process rainfall data
        rainfall_data = []
        time_labels = []
        for item in forecast_data['list'][:8]:  # Next 24 hours
            rain_amount = item['rain']['3h'] if 'rain' in item else 0
            rainfall_data.append(rain_amount)
            time_labels.append(datetime.fromtimestamp(item['dt']).strftime('%H:%M'))
        
        # Sample flood zones data (in production, this would come from a database)
        flood_zones = [
            {
                'location': 'Hindmata',
                'risk_level': 'high',
                'description': 'Historical flooding area, high risk during heavy rainfall'
            },
            {
                'location': 'King Circle',
                'risk_level': 'medium',
                'description': 'Moderate flooding risk due to low elevation'
            },
            {
                'location': 'Sion',
                'risk_level': 'high',
                'description': 'Prone to waterlogging during monsoon'
            }
        ]
        
        # Flood zones for map visualization
        flood_zones_geo = [
            {
                'center': {'lat': 19.0760, 'lng': 72.8777},
                'radius': 500,
                'color': '#ef4444'
            },
            {
                'center': {'lat': 19.0330, 'lng': 72.8597},
                'radius': 300,
                'color': '#f59e0b'
            }
        ]
        
        context = {
            'current_rainfall': current_weather.get('rain', {}).get('1h', 0),
            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'rainfall_data': json.dumps(rainfall_data),
            'time_labels': json.dumps(time_labels),
            'flood_zones': flood_zones,
            'flood_zones_geo': json.dumps(flood_zones_geo),
            'city_lat': 19.0760,
            'city_lng': 72.8777,
            'google_maps_api_key': 'AIzaSyAKM4O1T2X3hPTh70yNj5hASOjQ5U_uqCA',
            'unread_notifications_count': Notification.objects.filter(
                user=request.user, 
                is_read=False
            ).count()
        }
        
    except Exception as e:
        context = {
            'error': str(e),
            'current_rainfall': 0,
            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'rainfall_data': json.dumps([0] * 8),
            'time_labels': json.dumps([]),
            'flood_zones': [],
            'flood_zones_geo': json.dumps([]),
            'city_lat': 19.0760,
            'city_lng': 72.8777,
            'google_maps_api_key': 'AIzaSyAKM4O1T2X3hPTh70yNj5hASOjQ5U_uqCA',
            'unread_notifications_count': Notification.objects.filter(
                user=request.user, 
                is_read=False
            ).count()
        }
    
    return render(request, 'users/rain_alerts.html', context)

@login_required
@require_http_methods(["POST"])
def report_traffic_issue(request):
    try:
        data = json.loads(request.body)
        
        # Validate required fields
        required_fields = ['type', 'description', 'location']
        if not all(field in data for field in required_fields):
            return JsonResponse({'error': 'Missing required fields'}, status=400)
        
        # Create the report
        report = TrafficReport.objects.create(
            type=data['type'],
            description=data['description'],
            latitude=data['location']['lat'],
            longitude=data['location']['lng'],
            reported_by=request.user
        )
        
        return JsonResponse({
            'id': report.id,
            'type': report.type,
            'description': report.description,
            'location': {
                'lat': report.latitude,
                'lng': report.longitude
            },
            'timestamp': report.timestamp.isoformat(),
            'reporter': report.reported_by.username
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@require_http_methods(["GET"])
def get_traffic_reports(request):
    try:
        # Get active reports from the last 24 hours
        time_threshold = timezone.now() - timedelta(hours=24)
        reports = TrafficReport.objects.filter(
            is_active=True,
            timestamp__gte=time_threshold
        )
        
        return JsonResponse({
            'reports': [{
                'id': report.id,
                'type': report.type,
                'description': report.description,
                'location': {
                    'lat': report.latitude,
                    'lng': report.longitude
                },
                'timestamp': report.timestamp.isoformat(),
                'reporter': report.reported_by.username,
                'verified': report.verified
            } for report in reports]
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
@require_http_methods(["POST"])
def verify_report(request, report_id):
    try:
        report = TrafficReport.objects.get(id=report_id)
        report.verified = True
        report.save()
        return JsonResponse({'success': True})
    except TrafficReport.DoesNotExist:
        return JsonResponse({'error': 'Report not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
@require_http_methods(["POST"])
def close_report(request, report_id):
    try:
        report = TrafficReport.objects.get(id=report_id)
        report.is_active = False
        report.save()
        return JsonResponse({'success': True})
    except TrafficReport.DoesNotExist:
        return JsonResponse({'error': 'Report not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def energy_usage(request):
    try:
        # Configure Gemini API
        genai.configure(api_key="AIzaSyC3ekNJCildP0PuU5rPYZKdCtwmaYS3S50")
        model = genai.GenerativeModel('gemini-pro')

        # Enhanced prompt for real-time Mumbai energy data
        prompt = """Generate real-time Mumbai city energy data in JSON format with current timestamp. Include:
        1. Current power demand in MW (realistic for Mumbai, typically between 2800-3500 MW)
        2. Distribution of power sources in percentage:
           - Thermal (coal)
           - Hydro
           - Solar
           - Wind
           - Nuclear
        3. Current day's peak demand in MW
        4. Carbon emissions avoided in tons (last 24 hours)
        5. Renewable energy percentage
        6. Power deficit if any (in MW)
        7. Grid frequency (should be close to 50 Hz)
        8. Power quality index (0-100)

        Make all values realistic for Mumbai's actual power infrastructure and current time of day.
        Return only the JSON data without any explanation."""

        # Generate response and parse JSON
        response = model.generate_content(prompt)
        energy_data = json.loads(response.text)

    except Exception as e:
        # Fallback data with current timestamp
        from datetime import datetime
        energy_data = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'current_demand': 3245,  # Remove string formatting
            'peak_demand': 3567,     # Remove string formatting
            'power_deficit': 0,      # Remove string formatting
            'grid_frequency': 49.98, # Remove string formatting
            'power_quality_index': 95,
            'sources': {
                'Thermal': 55,
                'Hydro': 20,
                'Solar': 15,
                'Wind': 7,
                'Nuclear': 3
            },
            'carbon_saved': 1234,    # Remove string formatting
            'renewable_percentage': 42 # Remove string formatting
        }

    # Prepare time series data for graphs
    current_hour = datetime.now().hour
    hourly_demand = [
        energy_data['current_demand'] * (0.85 + 0.3 * random.random())
        for _ in range(24)
    ]
    
    hourly_labels = [
        f"{(current_hour - x) % 24:02d}:00" 
        for x in range(23, -1, -1)
    ]

    context = {
        'energy_data': energy_data,
        'hourly_demand': json.dumps(hourly_demand),
        'hourly_labels': json.dumps(hourly_labels),
        'error': str(e) if 'e' in locals() else None,
        'unread_notifications_count': Notification.objects.filter(
            user=request.user, 
            is_read=False
        ).count()
    }
    
    return render(request, 'users/energy_usage.html', context)

@login_required
def alerts_view(request):
    """View to display alerts and notifications for the user"""
    # Get all notifications for the current user
    alerts = Notification.objects.filter(user=request.user).order_by('-created_at')
    
    # Get unread notifications count for the navbar
    unread_notifications_count = Notification.objects.filter(user=request.user, is_read=False).count()
    
    return render(request, 'users/alerts.html', {
        'alerts': alerts,
        'unread_notifications_count': unread_notifications_count
    })