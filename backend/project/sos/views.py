from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import google.generativeai as genai
import requests
from .models import EmergencyRequest
import json
import logging
import random

logger = logging.getLogger(__name__)

GEMINI_API_KEY = 'AIzaSyC3ekNJCildP0PuU5rPYZKdCtwmaYS3S50'
GOOGLE_MAPS_API_KEY = 'AIzaSyAKM4O1T2X3hPTh70yNj5hASOjQ5U_uqCA'
GOOGLE_MAPS_API_KEYS = [
    'AIzaSyAKM4O1T2X3hPTh70yNj5hASOjQ5U_uqCA',
    'AIzaSyCFWAdIGgCKB4KnNnTNSNMcVOshwW2cdVM',
    'AIzaSyBYzXj5wF4L6mChyyc5xwfb2QT1QEZ9VN8',
    'AIzaSyB8Qpd8drt-Fnvd-rCNnky370uxspTjfXY',
    # Add any additional API keys here
]

def get_working_maps_api_key(latitude, longitude, facility_type):
    """
    Try each API key until finding one that works for the Places API request.
    Returns tuple of (working_key, response_data) or (None, None) if no keys work.
    """
    base_url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    
    for api_key in GOOGLE_MAPS_API_KEYS:
        try:
            params = {
                'location': f"{latitude},{longitude}",
                'radius': '5000',  # 5km radius
                'type': facility_type,
                'key': api_key
            }
            
            response = requests.get(base_url, params=params)
            data = response.json()
            
            if response.status_code == 200 and data.get('status') != 'OVER_QUERY_LIMIT':
                return api_key, data
                
        except Exception as e:
            logger.error(f"Error with Maps API key {api_key}: {str(e)}")
            continue
            
    return None, None

@login_required
def emergency_assistance(request):
    # Get a Google Maps API key using the rotation mechanism
    api_key = get_working_maps_api_key(19.0760, 72.8777, 'hospital')[0]
    if not api_key:
        api_key = GOOGLE_MAPS_API_KEYS[0]  # Fallback to the first key if all failed
        
    return render(request, 'sos/emergency.html', {'google_maps_api_key': api_key})

@login_required
@csrf_exempt
def submit_emergency(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            emergency_type = data.get('emergency_type')
            description = data.get('description')
            latitude = data.get('latitude')
            longitude = data.get('longitude')

            # Configure Gemini API
            genai.configure(api_key=GEMINI_API_KEY)
            model = genai.GenerativeModel('gemini-1.5-flash')

            # Generate AI response with error handling
            try:
                prompt = f"Emergency situation: {emergency_type}. Details: {description}. Provide a calm, helpful response with immediate steps to take."
                response = model.generate_content(prompt)
                ai_response = response.text
            except Exception as e:
                logger.error(f"Gemini API error: {str(e)}")
                ai_response = "I apologize, but I'm having trouble generating a response. Please contact emergency services immediately if this is a serious situation."

            # Find nearest facility using Google Places API with key rotation
            facility_type = 'hospital' if emergency_type == 'MEDICAL' else 'fire_station' if emergency_type == 'FIRE' else 'police'
            
            # Get a working API key and response
            working_key, places_response_data = get_working_maps_api_key(latitude, longitude, facility_type)
            
            # Process the response
            if working_key and places_response_data:
                results = places_response_data.get('results', [])
                if results:
                    nearest = results[0]
                    nearest_facility = {
                        'name': nearest['name'],
                        'address': nearest.get('vicinity', ''),
                        'latitude': nearest['geometry']['location']['lat'],
                        'longitude': nearest['geometry']['location']['lng']
                    }
                else:
                    nearest_facility = None
            else:
                nearest_facility = None
                logger.error("Could not find a working Google Maps API key")

            # Save emergency request
            emergency = EmergencyRequest.objects.create(
                user=request.user,
                emergency_type=emergency_type,
                description=description,
                latitude=latitude,
                longitude=longitude,
                ai_response=ai_response,
                nearest_facility=nearest_facility
            )

            return JsonResponse({
                'success': True,
                'ai_response': ai_response,
                'nearest_facility': nearest_facility
            })

        except Exception as e:
            logger.error(f"Emergency submission error: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)

    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=400)
