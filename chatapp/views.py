from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required

def login_register_view(request):
    error_message = None  # To store error messages

    if request.method == 'POST':
        # Check which form was submitted using 'tab'
        if 'login' in request.POST:
            # Handle login form
            username = request.POST.get('user')
            password = request.POST.get('pass')
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('chat_view')
            else:
                error_message = "Invalid username or password."
        
        elif 'register' in request.POST:
            # Handle registration form
            username = request.POST.get('user')
            password = request.POST.get('pass')
            repeat_password = request.POST.get('repeat_pass')
            email = request.POST.get('email')
            
            # Check if passwords match
            if password != repeat_password:
                error_message = "Passwords do not match."
            else:
                # Check if the username or email already exists
                if User.objects.filter(username=username).exists():
                    error_message = "Username already taken."
                elif User.objects.filter(email=email).exists():
                    error_message = "Email already in use."
                else:
                    # Create a new user
                    user = User.objects.create_user(username=username, password=password, email=email)
                    login(request, user)
                    return redirect('chat_view')
    
    return render(request, 'login.html', {'error_message': error_message})


@login_required
def home_view(request):
    # This view is protected, so it requires the user to be logged in
    return render(request, 'home.html', {'username': request.user.username})

@login_required
def logout_view(request):
    logout(request)
    return redirect('login_register')


from django.shortcuts import render
from django.conf import settings
from django.contrib.auth.decorators import login_required
import google.generativeai as genai
import pylast
import re

# Configure the Google Generative AI API
genai.configure(api_key=settings.GENAI_API_KEY)

# Configure the Last.fm API
API_KEY = settings.API_KEY
API_SECRET = settings.API_SECRET
USERNAME = 'dasjhjhads'
PASSWORD_HASH = pylast.md5(settings.PASSWORD)

network = pylast.LastFMNetwork(api_key=API_KEY, api_secret=API_SECRET, username=USERNAME, password_hash=PASSWORD_HASH)

generation_config = {
    "temperature": 1,
    "top_p": 0.95,
    "top_k": 0,
    "max_output_tokens": 8192,
}

safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
]

model = genai.GenerativeModel(
    model_name="gemini-1.5-pro-latest",
    generation_config=generation_config,
    system_instruction="You are Tenor, an empathetic and insightful chatbot designed to suggest music exactly in this format [Track: track_name] [Artist: artist_name] no ** shouldnt be there, based on the user's mood and emotions. You analyze the user's emotions through a series of thoughtful and engaging questions, such as asking how they are feeling, what they are doing, and other deep, open-ended inquiries. Your goal is to understand the user's emotional state without directly asking for music recommendations, mood, or emotions. Based on your analysis, you then suggest 5 appropriate musics that resonates with their feelings in the format [Track: track_name] [Artist: artist_name].",
    # safety_settings=safety_settings
)

def extract_music_from_response(response):
    # Define regex pattern to extract song and artist details
    pattern = r'\[Track: (.*?)\] \[Artist: (.*?)\]'
    matches = re.findall(pattern, response)
    
    songs = []
    for match in matches:
        song = {'track': match[0], 'artist': match[1]}
        songs.append(song)
    return songs

@login_required
def chat_view(request):
    if 'conversation' not in request.session:
        request.session['conversation'] = []

    user_input = request.POST.get('user_input')
    song_recommendations = []

    if user_input:
        request.session['conversation'].append({'role': 'user', 'parts': [user_input]})
        request.session.modified = True

        convo = model.start_chat(history=request.session['conversation'])
        convo.send_message(user_input)

        response = convo.last.text
        request.session['conversation'].append({'role': 'model', 'parts': [response]})
        request.session.modified = True

        # Extract song recommendations from the response
        songs = extract_music_from_response(response)
        for song in songs:
            try:
                track = network.get_track(song['artist'], song['track'])
                album = track.get_album()
                album_cover = album.get_cover_image() if album else None

                song_recommendations.append({
                    'name': track.title,
                    'artist': track.artist.name,
                    'url': track.get_url() + '?autostart',
                    'tags': track.get_top_tags(),
                    'thumbnail': album_cover,
                    'description': track.get_wiki_content(),
                    'youtube_link': get_youtube_link(track)
                })
            except pylast.WSError:
                continue

    return render(request, 'chat.html', {
        'conversation': request.session['conversation'],
        'username': request.user.username,
        'song_recommendations': song_recommendations
    })

def get_youtube_link(track):
    # This function should return the YouTube link of the track if available.
    # You can implement it by using additional APIs or data sources.
    # For now, we will return a placeholder string.
    return "https://www.youtube.com/results?search_query=" + track.artist.name + " " + track.title
