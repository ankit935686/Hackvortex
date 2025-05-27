from django.shortcuts import render
from django.http import JsonResponse
from django.db.models import Avg
from django.db.models.functions import TruncHour
from django.utils import timezone
from datetime import datetime, timedelta
import serial
import json
import os
import requests
from django.conf import settings
from .models import SmokeData

# Global variable to store the serial connection
arduino_serial = None

def initialize_serial():
    global arduino_serial
    # Try to get COM port from environment variable, default to COM3
    com_ports = [os.getenv('ARDUINO_COM_PORT', 'COM3')]
    # Add common COM ports to try
    com_ports.extend(['COM4', 'COM5', 'COM6'])
    
    for port in com_ports:
        try:
            if arduino_serial is None:
                arduino_serial = serial.Serial(port, 9600, timeout=1)
                print(f"Successfully connected to {port}")
                break
        except Exception as e:
            print(f"Error trying to connect to {port}: {e}")
            continue

def landing_page(request):
    return render(request, 'arduinofeature/landing.html')

def smoke_monitor(request):
    return render(request, 'arduinofeature/smoke_monitor.html')

def get_smoke_data(request):
    global arduino_serial
    
    try:
        if arduino_serial is None:
            initialize_serial()
            
        if arduino_serial and arduino_serial.is_open:
            # Read the line from Arduino
            line = arduino_serial.readline().decode('utf-8').strip()
            print(f"Raw data from Arduino: {line}")  # Debug print
            
            # Parse the smoke value - handle various formats
            smoke_value = 0
            if line.startswith("Smoke:"):
                # Standard format: "Smoke: 123"
                try:
                    smoke_value = int(line.split(":")[1].strip())
                except:
                    print("Error parsing standard format")
            elif ":" in line:
                # Alternative format: "e: 123" or any other prefix with colon
                try:
                    smoke_value = int(line.split(":")[1].strip())
                except:
                    print("Error parsing alternative format")
            elif line.isdigit():
                # Just a number
                try:
                    smoke_value = int(line)
                except:
                    print("Error parsing numeric format")
            else:
                # Try to extract any number from the string
                import re
                numbers = re.findall(r'\d+', line)
                if numbers:
                    try:
                        smoke_value = int(numbers[0])
                    except:
                        print("Error parsing extracted number")
                else:
                    # No valid number found, use latest data from database
                    latest = SmokeData.objects.order_by('-timestamp').first()
                    if latest:
                        smoke_value = latest.smoke_level
                        print(f"Using latest database value: {smoke_value}")
            
            print(f"Parsed smoke value: {smoke_value}")  # Debug print
            
            # Determine status based on smoke level
            if smoke_value < 230:
                status = 'Safe'
            elif smoke_value < 500:
                status = 'Warning'
            else:
                status = 'Danger'
            
            print(f"Determined status: {status}")  # Debug print
            
            # Store the data if we have a valid smoke value
            if smoke_value > 0:
                smoke_data = SmokeData.objects.create(
                    smoke_level=smoke_value,
                    status=status.lower()
                )
                print(f"Stored data in database: {smoke_data}")  # Debug print
            
            # Return all necessary data
            return JsonResponse({
                'smoke_level': smoke_value,
                'status': status,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })
            
    except Exception as e:
        print(f"Error reading from serial: {e}")  # Debug print
    
    # Return most recent data from database if available
    try:
        latest = SmokeData.objects.order_by('-timestamp').first()
        if latest:
            if latest.status == 'safe':
                status = 'Safe'
            elif latest.status == 'warning':
                status = 'Warning'
            else:
                status = 'Danger'
                
            return JsonResponse({
                'smoke_level': latest.smoke_level,
                'status': status,
                'timestamp': latest.timestamp.strftime('%Y-%m-%d %H:%M:%S')
            })
    except Exception as e:
        print(f"Error retrieving latest data: {e}")
    
    # Return default values if there's an error
    return JsonResponse({
        'smoke_level': 0,
        'status': 'Unknown',
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })

def get_chart_data(request):
    # Get the time range from request or default to last 10 minutes
    time_range = request.GET.get('range', '10m')
    
    end_time = timezone.now()
    
    # Set the time range based on the parameter
    if time_range == '1h':
        start_time = end_time - timedelta(hours=1)
        interval = 'minute'
    elif time_range == '6h':
        start_time = end_time - timedelta(hours=6)
        interval = 'minute'
    elif time_range == '24h':
        start_time = end_time - timedelta(hours=24)
        interval = 'hour'
    elif time_range == '7d':
        start_time = end_time - timedelta(days=7)
        interval = 'day'
    elif time_range == 'all':
        # Get all data
        start_time = timezone.make_aware(datetime(2000, 1, 1))  # Far in the past
        interval = 'day'
    else:  # Default to 10 minutes
        start_time = end_time - timedelta(minutes=10)
        interval = 'minute'
    
    # Get data points for the selected time range
    data_points = SmokeData.objects.filter(
        timestamp__range=(start_time, end_time)
    ).order_by('timestamp')
    
    # Calculate statistics
    stats = {
        'avg': round(data_points.aggregate(Avg('smoke_level'))['smoke_level__avg'] or 0, 1),
        'min': data_points.order_by('smoke_level').first().smoke_level if data_points.exists() else 0,
        'max': data_points.order_by('-smoke_level').first().smoke_level if data_points.exists() else 0,
        'count': data_points.count(),
        'safe_count': data_points.filter(status='safe').count(),
        'warning_count': data_points.filter(status='warning').count(),
        'danger_count': data_points.filter(status='danger').count(),
    }

    # Format data for the chart, with special handling for large datasets
    if time_range == 'all' and data_points.count() > 500:
        # If there are too many points, sample the data to prevent browser performance issues
        sample_size = 500
        total_points = data_points.count()
        step = max(1, total_points // sample_size)
        
        # Sample the data
        sampled_points = [data_points[i] for i in range(0, total_points, step)]
        
        chart_data = {
            'labels': [data.timestamp.strftime('%Y-%m-%d %H:%M') for data in sampled_points],
            'values': [float(data.smoke_level) for data in sampled_points],
            'statuses': [data.status for data in sampled_points],
            'stats': stats,
            'time_range': time_range,
            'sampled': True,
            'original_count': total_points,
            'sample_count': len(sampled_points)
        }
    else:
        # Regular formatting for smaller datasets
        chart_data = {
            'labels': [data.timestamp.strftime('%H:%M:%S' if interval in ['minute'] else '%H:%M' if interval == 'hour' else '%m-%d') 
                     for data in data_points],
            'values': [float(data.smoke_level) for data in data_points],
            'statuses': [data.status for data in data_points],
            'stats': stats,
            'time_range': time_range
        }
    
    return JsonResponse(chart_data)

def graphical_data(request):
    # Get the time range from request or default to all data
    time_range = request.GET.get('range', 'all')  # Changed default from '10m' to 'all'
    
    end_time = timezone.now()
    
    # Set the time range based on the parameter
    if time_range == '1h':
        start_time = end_time - timedelta(hours=1)
    elif time_range == '6h':
        start_time = end_time - timedelta(hours=6)
    elif time_range == '24h':
        start_time = end_time - timedelta(hours=24)
    elif time_range == '7d':
        start_time = end_time - timedelta(days=7)
    elif time_range == 'all':
        # Get all data
        start_time = timezone.make_aware(datetime(2000, 1, 1))  # Far in the past
    else:  # Default to 10 minutes
        start_time = end_time - timedelta(minutes=10)
    
    # Get data points for the selected time range
    data_points = SmokeData.objects.filter(
        timestamp__range=(start_time, end_time)
    ).order_by('timestamp')
    
    # Get total count of records for information
    total_count = SmokeData.objects.count()
    
    # Calculate statistics
    stats = {
        'avg': round(data_points.aggregate(Avg('smoke_level'))['smoke_level__avg'] or 0, 1),
        'min': data_points.order_by('smoke_level').first().smoke_level if data_points.exists() else 0,
        'max': data_points.order_by('-smoke_level').first().smoke_level if data_points.exists() else 0,
        'count': data_points.count(),
        'total_count': total_count,  # Add total count to stats
        'safe_count': data_points.filter(status='safe').count(),
        'warning_count': data_points.filter(status='warning').count(),
        'danger_count': data_points.filter(status='danger').count(),
    }
    
    # Sample the data if there are too many points for initial load
    if time_range == 'all' and data_points.count() > 500:
        # If there are too many points, sample the data to prevent browser performance issues
        sample_size = 500
        total_points = data_points.count()
        step = max(1, total_points // sample_size)
        
        # Sample the data
        sampled_points = [data_points[i] for i in range(0, total_points, step)]
        
        chart_data = {
            'labels': [data.timestamp.strftime('%Y-%m-%d %H:%M') for data in sampled_points],
            'values': [float(data.smoke_level) for data in sampled_points],
            'statuses': [data.status for data in sampled_points],
            'stats': stats,
            'time_range': time_range,
            'sampled': True,
            'original_count': total_points,
            'sample_count': len(sampled_points)
        }
    else:
        # Format data for the chart
        chart_data = {
            'labels': [data.timestamp.strftime('%H:%M:%S') for data in data_points],
            'values': [float(data.smoke_level) for data in data_points],
            'statuses': [data.status for data in data_points],
            'stats': stats,
            'time_range': time_range
        }
    
    return render(request, 'arduinofeature/graphical_data.html', {
        'chart_data': json.dumps(chart_data)
    })

def ai_suggestion(request):
    """
    Render the AI suggestion page
    """
    return render(request, 'arduinofeature/ai_suggestion.html')

def get_ai_suggestions(request):
    """
    Generate air quality improvement suggestions using Gemini API based on smoke data
    """
    try:
        # Get the last 24 hours of data
        end_time = timezone.now()
        start_time = end_time - timedelta(hours=24)
        
        # Get smoke data from the last 24 hours
        smoke_data = SmokeData.objects.filter(
            timestamp__range=(start_time, end_time)
        ).order_by('-timestamp')
        
        # Calculate average smoke level
        avg_smoke_level = smoke_data.aggregate(Avg('smoke_level'))['smoke_level__avg']
        if avg_smoke_level is None:
            avg_smoke_level = 0
        avg_smoke_level = round(avg_smoke_level, 1)
        
        # Get most common status
        status_counts = {
            'safe': smoke_data.filter(status='safe').count(),
            'warning': smoke_data.filter(status='warning').count(),
            'danger': smoke_data.filter(status='danger').count()
        }
        
        most_common_status = max(status_counts, key=status_counts.get) if smoke_data.exists() else 'unknown'
        
        # Get the hourly trend to see if air quality is improving or worsening
        hourly_data = smoke_data.annotate(
            hour=TruncHour('timestamp')
        ).values('hour').annotate(
            avg_level=Avg('smoke_level')
        ).order_by('hour')
        
        # Determine trend
        trend = 'stable'
        if len(hourly_data) > 1:
            first_hour = hourly_data.first()['avg_level'] if hourly_data.exists() else 0
            last_hour = hourly_data.last()['avg_level'] if hourly_data.exists() else 0
            
            if last_hour > first_hour:
                trend = 'worsening'
            elif last_hour < first_hour:
                trend = 'improving'
        
        # Prepare data for Gemini AI
        prompt = f"""
        Based on the following smoke monitoring data:
        - Average smoke level over the last 24 hours: {avg_smoke_level} PPM
        - Most common air quality status: {most_common_status}
        - Air quality trend: {trend}
        
        Please provide 3-5 personalized suggestions on how to improve and maintain better air quality. 
        For each suggestion, include a title and a detailed description explaining why it's effective.
        
        Format your response as a JSON object with the following structure:
        {{
            "suggestions": [
                {{
                    "title": "Short descriptive title",
                    "description": "Detailed explanation of the suggestion"
                }},
                ...
            ]
        }}
        
        Only return the JSON object, nothing else.
        """
        
        # Try to get Gemini API key from settings or environment variable
        api_key = getattr(settings, 'GEMINI_API_KEY', os.getenv('GEMINI_API_KEY'))
        
        if not api_key:
            # If no API key is available, return dummy suggestions for testing
            suggestions = generate_dummy_suggestions(avg_smoke_level, most_common_status, trend)
        else:
            # Call Gemini API
            response = call_gemini_api(prompt, api_key)
            
            try:
                # Parse the response to extract JSON
                suggestions = extract_json_from_response(response)
            except Exception as e:
                print(f"Error parsing Gemini response: {e}")
                suggestions = generate_dummy_suggestions(avg_smoke_level, most_common_status, trend)
        
        # Return the data as JSON
        return JsonResponse({
            'avg_smoke_level': avg_smoke_level,
            'status': most_common_status,
            'trend': trend,
            'suggestions': suggestions
        })
        
    except Exception as e:
        print(f"Error generating AI suggestions: {e}")
        return JsonResponse({
            'avg_smoke_level': 0,
            'status': 'unknown',
            'trend': 'unknown',
            'suggestions': generate_dummy_suggestions(0, 'unknown', 'unknown')
        })

def call_gemini_api(prompt, api_key):
    """
    Call Gemini API with the given prompt
    """
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent"
    
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": api_key
    }
    
    data = {
        "contents": [{
            "parts": [{
                "text": prompt
            }]
        }]
    }
    
    response = requests.post(url, headers=headers, json=data)
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Gemini API error: {response.status_code} - {response.text}")
        return None

def extract_json_from_response(response):
    """
    Extract JSON object from Gemini API response
    """
    if not response:
        return []
    
    try:
        text = response.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '')
        
        # Find JSON object within text (it might be surrounded by markdown code blocks)
        import re
        json_match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
        
        if json_match:
            json_text = json_match.group(1)
        else:
            # If no markdown code block, try to get the whole text as JSON
            json_text = text
        
        # Parse JSON
        data = json.loads(json_text)
        return data.get('suggestions', [])
    except Exception as e:
        print(f"Error extracting JSON from Gemini response: {e}")
        return []

def generate_dummy_suggestions(avg_level, status, trend):
    """
    Generate dummy suggestions when API is not available
    """
    suggestions = []
    
    if status == 'safe':
        suggestions = [
            {
                "title": "Maintain Regular Ventilation",
                "description": "Continue maintaining good ventilation in your space by opening windows for 15-20 minutes daily, even in cold weather. This ensures a consistent flow of fresh air."
            },
            {
                "title": "Keep Air-Purifying Plants",
                "description": "Consider adding more air-purifying plants like Spider Plants, Peace Lilies, or Snake Plants to naturally filter air pollutants and maintain good air quality."
            },
            {
                "title": "Regular HVAC Maintenance",
                "description": "Keep up with regular maintenance of your ventilation systems, including changing filters every 3 months to ensure clean air circulation."
            }
        ]
    elif status == 'warning':
        suggestions = [
            {
                "title": "Increase Ventilation Immediately",
                "description": "Open windows in opposite sides of your space to create cross-ventilation, which can quickly reduce smoke levels by up to 50% within 30 minutes."
            },
            {
                "title": "Use Air Purifiers with HEPA Filters",
                "description": "Deploy air purifiers with HEPA filters in the most frequently used areas of your home or workspace to capture smoke particles as small as 0.3 microns."
            },
            {
                "title": "Check for Sources of Smoke",
                "description": "Investigate potential sources of smoke such as faulty appliances, overheating electronics, or nearby cooking areas, and address these issues promptly."
            },
            {
                "title": "Reduce Indoor Combustion Activities",
                "description": "Minimize activities that produce smoke, such as burning candles, using fireplaces, or smoking indoors. Consider alternative options for these activities."
            }
        ]
    else:  # danger or unknown
        suggestions = [
            {
                "title": "Evacuate if Necessary",
                "description": "If smoke levels remain dangerously high, consider temporarily relocating until the source of the problem is identified and resolved, especially if you have respiratory conditions."
            },
            {
                "title": "Professional Air Quality Assessment",
                "description": "Hire a professional to conduct a thorough air quality assessment to identify specific pollutants and their sources in your environment."
            },
            {
                "title": "Install Industrial-Grade Air Filtration",
                "description": "Consider installing high-capacity air filtration systems designed specifically for removing smoke and other harmful particulates from indoor air."
            },
            {
                "title": "Seal Leaks and Entry Points",
                "description": "Identify and seal gaps around windows, doors, and other potential entry points to prevent outdoor pollutants from entering your space."
            },
            {
                "title": "Create Clean Air Zones",
                "description": "Designate certain rooms as 'clean air zones' with concentrated air purification efforts, especially bedrooms where you spend 6-8 hours sleeping."
            }
        ]
    
    return suggestions
