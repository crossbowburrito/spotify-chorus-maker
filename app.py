from dotenv import load_dotenv
import requests
import os
from collections import Counter
import time
import random
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from spotipy.oauth2 import SpotifyOAuth
from mido import MidiFile, MidiTrack, Message
from bs4 import BeautifulSoup
from pytube import YouTube
import time


load_dotenv()

# Spotify API credentials
CLIENT_ID = os.environ['SPOTIFY_CLIENT_ID']
CLIENT_SECRET = os.environ['SPOTIFY_CLIENT_SECRET']

#get token
def get_access_token():
    """
    Get an access token from the Spotify API.

    Returns:
        str: The access token.
    """
    url = 'https://accounts.spotify.com/api/token'
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
    }
    data = {
        'grant_type': 'client_credentials',
    }
    response = requests.post(url, headers=headers, data=data, auth=(CLIENT_ID, CLIENT_SECRET))
    response.raise_for_status()  # Raise an error for bad responses
    response_json = response.json()
    return response_json['access_token']

def get_standard_key(key):
    """Convert keys to standard sharp notation."""
    key_mapping = {
        'C♯/D♭': 'C#',
        'D♯/E♭': 'Eb',
        'F♯/G♭': 'F#',
        'G♯/A♭': 'Ab',
        'A♯/B♭': 'Bb',
    }
    return key_mapping.get(key, key)


def chord_to_midi(key, chord_name):
    """Convert chord name to a list of MIDI note numbers."""
    return CHORD_DICT[key].get(chord_name, [])


def generate_midi_file(key, progression, filename="generated_song.mid"):
    mid = MidiFile()
    track = MidiTrack()
    mid.tracks.append(track)

    for chord in progression:
        key_standard = get_standard_key(key)  # Convert the key to standard notation
        midi_notes = chord_to_midi(key_standard, chord)  # Use the standardized key to get MIDI notes
        for note in midi_notes:
            track.append(Message('note_on', note=note, velocity=64, time=0))
        # Let the chord play for 480 ticks (a whole note in our case)
        for note in midi_notes:
            track.append(Message('note_off', note=note, velocity=64, time=480))

    mid.save(filename)



client_credentials_manager = SpotifyClientCredentials(client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)

#parse spotify link
def parse_spotify_link(link):
    """Parse Spotify link to get type and id."""
    parts = link.split('/')
    if 'playlist' in parts:
        return 'playlist', parts[-1].split('?')[0]
    else:
        raise ValueError("Invalid Spotify link")

#fetch artist genre
def fetch_artist_genre(access_token, artist_id):
    """
    Fetch the genre of an artist from the Spotify API.

    Args:
        access_token (str): The access token.
        artist_id (str): The artist's ID.

    Returns:
        list: A list of genres associated with the artist.
    """
    url = f'https://api.spotify.com/v1/artists/{artist_id}'
    headers = {
        'Authorization': f'Bearer {access_token}',
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    response_json = response.json()
    return response_json['genres']

#fetch songs
def fetch_songs(access_token):
    """
    Fetch the songs from the Spotify API.

    Args:
        access_token (str): The access token.

    Returns:
        list: A list of dictionaries containing the song data.
    """
    url = f'https://api.spotify.com/v1/playlists/{playlist_id}/tracks?limit=50'
    headers = {
        'Authorization': f'Bearer {access_token}',
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    response_json = response.json()
    global songs
    songs = []
    global track_ids
    track_ids = []
    for i, item in enumerate(response_json['items']):
        if i <= 50:
            track = item['track']
            track_ids.append(track['id'])
            song = {
                'id': track['id'],
                'name': track['name'],
                'artist': track['artists'][0]['name'],
                'album': track['album']['name'],
                'release_date': track['album']['release_date'],
                'popularity': track['popularity'],
                'duration_ms': track['duration_ms'],
                'position': i + 1,
            }
            artist_id = track['artists'][0]['id']
            song_genre = fetch_artist_genre(access_token, artist_id)
            song['genre'] = song_genre
            songs.append(song)
            i+=1
        else:
            break

    # Get audio features of the tracks in bulk
    audio_features_url = f'https://api.spotify.com/v1/audio-features'
    audio_features_response = requests.get(audio_features_url, headers=headers, params={'ids': ','.join(track_ids)})
    audio_features_response.raise_for_status()
    audio_features_list = audio_features_response.json()['audio_features']
    for song, features in zip(songs, audio_features_list):
        song.update(features)

    return songs

#calculate difference
def calculate_difference(song, generated_song):
    bpm_diff = abs(song['tempo'] - generated_song['tempo'])
    energy_diff = abs((song['energy'] - generated_song['energy'])/2)
    # Add more differences as needed (e.g., genre, time signature)
    
    total_diff = bpm_diff + energy_diff
    return total_diff


def get_drum_audio(query):
    
    
    base_url = "https://www.youtube.com/results?search_query="
    search_url = base_url + query.replace(" ", "+")
    
    response = requests.get(search_url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Find all video links from the search results
    videos = soup.find_all("a", href=True, class_="yt-uix-tile-link")
    
    # Return the first video URL
    if videos:
        video_url = "https://www.youtube.com" + videos[0]["href"]
        yt = YouTube(video_url)
        try:
            stream_audio = yt.streams.get_audio_only()
            stream_audio.download(filename= '{video_title}.wav')        
        except Exception as e:
            print(f"An error occurred: {e}")

            
    
    return None




#dictionaries
key_dict = {
    0: 'C',
    1: 'C♯/D♭',
    2: 'D',
    3: 'D♯/E♭',
    4: 'E',
    5: 'F',
    6: 'F♯/G♭',
    7: 'G',
    8: 'G♯/A♭',
    9: 'A',
    10: 'A♯/B♭',
    11: 'B',
}


major_chord_progressions = [
    ['I', 'IV', 'V', 'IV'],
    ['I', 'V', 'vi', 'IV'],
    ['ii', 'V', 'I'],
    ['I', 'vi', 'ii', 'V'],
    ['I', 'IV', 'ii', 'V'],
    ['I', 'iii', 'IV', 'V'],
    ['I', 'IV', 'I', 'V'],
    ['I', 'V', 'IV', 'V'],
    ['I', 'vi', 'IV', 'V', 'IV'],
    ['I', 'IV', 'V', 'vi'],
    ['ii7', 'V7', 'I7'],
    ['I', 'vi', 'IV', 'V'],
    ['I', 'V', 'vi', 'iii', 'IV', 'I', 'IV', 'V'],
    ['IV', 'V', 'iii', 'vi'],
    ['I', 'bVII', 'I'],
]

minor_chord_progressions = [
    ['i', 'iv', 'v', 'i'],
    ['i', 'VI', 'III', 'VII'],
    ['i', 'iv', 'VII', 'i'],
    ['i', 'iv', 'v', 'VII'],
    ['i', 'VI', 'iv', 'VII'],
    ['i', 'v', 'iv', 'i'],
    ['i', 'VII', 'VI', 'v'],
    ['i', 'iv', 'i', 'v'],
    ['i', 'VI', 'VII', 'i'],
    ['i', 'iv', 'VI', 'VII'],
    ['i', 'ii˚', 'v', 'i'],
    ['i', 'bVI', 'bIII', 'bVII'],
    ['i', 'bVII', 'bVI', 'bVII', 'i'],
    ['i', 'bVII', 'bVI', 'V7'],
]


major_weights = [
    10,  # ['I', 'IV', 'V', 'IV'] - Classic blues progression
    9,   # ['I', 'V', 'vi', 'IV'] - One of the most common in pop music
    8,   # ['ii', 'V', 'I'] - Common in jazz
    7,   # ['I', 'vi', 'ii', 'V'] - Another common jazz progression
    6,   # ['I', 'IV', 'ii', 'V']
    5,   # ['I', 'iii', 'IV', 'V']
    7,   # ['I', 'IV', 'I', 'V']
    6,   # ['I', 'V', 'IV', 'V']
    5,   # ['I', 'vi', 'IV', 'V', 'IV']
    4,   # ['I', 'IV', 'V', 'vi']
    7,   # ['ii7', 'V7', 'I7'] - Common 2-5-1 jazz progression with sevenths
    9,   # ['I', 'vi', 'IV', 'V'] - Another very common pop progression
    3,   # ['I', 'V', 'vi', 'iii', 'IV', 'I', 'IV', 'V']
    4,   # ['IV', 'V', 'iii', 'vi']
    2    # ['I', 'bVII', 'I']
]

minor_weights = [
    8,   # ['i', 'iv', 'v', 'i'] - Classic minor progression
    7,   # ['i', 'VI', 'III', 'VII']
    9,   # ['i', 'iv', 'VII', 'i'] - Common in flamenco and some pop songs
    6,   # ['i', 'iv', 'v', 'VII']
    5,   # ['i', 'VI', 'iv', 'VII']
    7,   # ['i', 'v', 'iv', 'i']
    6,   # ['i', 'VII', 'VI', 'v']
    8,   # ['i', 'iv', 'i', 'v']
    7,   # ['i', 'VI', 'VII', 'i']
    5,   # ['i', 'iv', 'VI', 'VII']
    9,   # ['i', 'ii˚', 'v', 'i'] - Classic minor with diminished ii
    4,   # ['i', 'bVI', 'bIII', 'bVII']
    3,   # ['i', 'bVII', 'bVI', 'bVII', 'i']
    2    # ['i', 'bVII', 'bVI', 'V7']
]


CHORD_DICT = {
    'Ab': {
        'I': [68, 72, 75],
        'ii': [70, 73, 77],
        'iii': [72, 75, 79],
        'IV': [73, 77, 80],
        'V': [75, 79, 82],
        'vi': [77, 80, 84],
        'vii°': [79, 82, 85],
        'ii7': [70, 73, 77, 80],
        'V7': [75, 79, 82, 85],
        'I7': [68, 72, 75, 78],
        'bVII': [67, 70, 73],
        'bIII': [71, 75, 78],
        'bVI': [65, 68, 72],
        'i': [68, 71, 75],
        'iv': [73, 76, 80],
        'v': [75, 78, 82],
        'VII': [77, 80, 83],
        'VI': [76, 80, 83],
        'III': [72, 75, 79]
    },

        'A': {
        'I': [69, 73, 76],
        'ii': [71, 74, 78],
        'iii': [73, 76, 80],
        'IV': [74, 78, 81],
        'V': [76, 80, 83],
        'vi': [78, 81, 85],
        'vii°': [80, 83, 86],
        'ii7': [71, 74, 78, 81],
        'V7': [76, 80, 83, 86],
        'I7': [69, 73, 76, 79],
        'bVII': [68, 71, 74],
        'bIII': [72, 76, 79],
        'bVI': [66, 69, 73],
        'i': [69, 72, 76],
        'iv': [74, 77, 81],
        'v': [76, 79, 83],
        'VII': [78, 81, 84],
        'VI': [77, 81, 84],
        'III': [73, 76, 80]
    },
    'Bb': {
        'I': [70, 74, 77],
        'ii': [72, 75, 79],
        'iii': [74, 77, 81],
        'IV': [75, 79, 82],
        'V': [77, 81, 84],
        'vi': [79, 82, 86],
        'vii°': [81, 84, 87],
        'ii7': [72, 75, 79, 82],
        'V7': [77, 81, 84, 87],
        'I7': [70, 74, 77, 80],
        'bVII': [69, 72, 75],
        'bIII': [73, 77, 80],
        'bVI': [67, 70, 74],
        'i': [70, 73, 77],
        'iv': [75, 78, 82],
        'v': [77, 80, 84],
        'VII': [79, 82, 85],
        'VI': [78, 82, 85],
        'III': [74, 77, 81]
    },

    'B': {
        'I': [71, 75, 78],
        'ii': [73, 76, 80],
        'iii': [75, 78, 82],
        'IV': [76, 80, 83],
        'V': [78, 82, 85],
        'vi': [80, 83, 87],
        'vii°': [82, 85, 88],
        'ii7': [73, 76, 80, 83],
        'V7': [78, 82, 85, 88],
        'I7': [71, 75, 78, 81],
        'bVII': [70, 73, 76],
        'bIII': [74, 78, 81],
        'bVI': [68, 71, 75],
        'i': [71, 74, 78],
        'iv': [76, 79, 83],
        'v': [78, 81, 85],
        'VII': [80, 83, 86],
        'VI': [79, 83, 86],
        'III': [75, 78, 82]
    },

    'C': {
        'I': [60, 64, 67],
        'ii': [62, 65, 69],
        'iii': [64, 67, 71],
        'IV': [65, 69, 72],
        'V': [67, 71, 74],
        'vi': [69, 72, 76],
        'vii°': [71, 74, 77],
        'ii7': [62, 65, 69, 72],
        'V7': [67, 71, 74, 77],
        'I7': [60, 64, 67, 70],
        'bVII': [59, 62, 65],
        'bIII': [63, 67, 70],
        'bVI': [57, 60, 64],
        'i': [60, 63, 67],
        'iv': [65, 68, 72],
        'v': [67, 70, 74],
        'VII': [69, 72, 75],
        'VI': [68, 72, 75],
        'III': [64, 67, 71]
    },

    'C#': {
            'I': [61, 65, 68],
            'ii': [63, 66, 70],
            'iii': [65, 68, 72],
            'IV': [66, 70, 73],
            'V': [68, 72, 75],
            'vi': [70, 73, 77],
            'vii°': [72, 75, 78],
            'ii7': [63, 66, 70, 73],
            'V7': [68, 72, 75, 78],
            'I7': [61, 65, 68, 71],
            'bVII': [60, 63, 66],
            'bIII': [64, 68, 71],
            'bVI': [58, 61, 65],
            'i': [61, 64, 68],
            'iv': [66, 69, 73],
            'v': [68, 71, 75],
            'VII': [70, 73, 76],
            'VI': [69, 73, 76],
            'III': [65, 68, 72]
        },
    'D': {
        'I': [62, 66, 69],
        'ii': [64, 67, 71],
        'iii': [66, 69, 73],
        'IV': [67, 71, 74],
        'V': [69, 73, 76],
        'vi': [71, 74, 78],
        'vii°': [73, 76, 79],
        'ii7': [64, 67, 71, 74],
        'V7': [69, 73, 76, 79],
        'I7': [62, 66, 69, 72],
        'bVII': [61, 64, 67],
        'bIII': [65, 69, 72],
        'bVI': [59, 62, 66],
        'i': [62, 65, 69],
        'iv': [67, 70, 74],
        'v': [69, 72, 76],
        'VII': [71, 74, 77],
        'VI': [70, 74, 77],
        'III': [66, 69, 73]
    },
    'Eb': {
        'I': [63, 67, 70],
        'ii': [65, 68, 72],
        'iii': [67, 70, 74],
        'IV': [68, 72, 75],
        'V': [70, 74, 77],
        'vi': [72, 75, 79],
        'vii°': [74, 77, 80],
        'ii7': [65, 68, 72, 75],
        'V7': [70, 74, 77, 80],
        'I7': [63, 67, 70, 73],
        'bVII': [62, 65, 68],
        'bIII': [66, 70, 73],
        'bVI': [60, 63, 67],
        'i': [63, 66, 70],
        'iv': [68, 71, 75],
        'v': [70, 73, 77],
        'VII': [72, 75, 78],
        'VI': [71, 75, 78],
        'III': [67, 70, 74]
    },
    'E': {
        'I': [64, 68, 71],
        'ii': [66, 69, 73],
        'iii': [68, 71, 75],
        'IV': [69, 73, 76],
        'V': [71, 75, 78],
        'vi': [73, 76, 80],
        'vii°': [75, 78, 81],
        'ii7': [66, 69, 73, 76],
        'V7': [71, 75, 78, 81],
        'I7': [64, 68, 71, 74],
        'bVII': [63, 66, 69],
        'bIII': [67, 71, 74],
        'bVI': [61, 64, 68],
        'i': [64, 67, 71],
        'iv': [69, 72, 76],
        'v': [71, 74, 78],
        'VII': [73, 76, 79],
        'VI': [72, 76, 79],
        'III': [68, 71, 75]
    },    
    'F': {
        'I': [65, 69, 72],
        'ii': [67, 70, 74],
        'iii': [69, 72, 76],
        'IV': [70, 74, 77],
        'V': [72, 76, 79],
        'vi': [74, 77, 81],
        'vii°': [76, 79, 82],
        'ii7': [67, 70, 74, 77],
        'V7': [72, 76, 79, 82],
        'I7': [65, 69, 72, 75],
        'bVII': [64, 67, 70],
        'bIII': [68, 72, 75],
        'bVI': [62, 65, 69],
        'i': [65, 68, 72],
        'iv': [70, 73, 77],
        'v': [72, 75, 79],
        'VII': [75, 79, 82],
        'VI': [73, 77, 80],
        'III': [69, 72, 76]
    },    

    'F#': {
        'I': [66, 70, 73],
        'ii': [68, 71, 75],
        'iii': [70, 73, 77],
        'IV': [71, 75, 78],
        'V': [73, 77, 80],
        'vi': [75, 78, 82],
        'vii°': [77, 80, 83],
        'ii7': [68, 71, 75, 78],
        'V7': [73, 77, 80, 83],
        'I7': [66, 70, 73, 76],
        'bVII': [65, 68, 71],
        'bIII': [69, 73, 76],
        'bVI': [63, 66, 70],
        'i': [66, 69, 73],
        'iv': [71, 74, 78],
        'v': [73, 76, 80],
        'VII': [75, 78, 81],
        'VI': [74, 78, 81],
        'III': [70, 73, 77]
    },
    
    'G': {
        'I': [67, 71, 74],
        'ii': [69, 72, 76],
        'iii': [71, 74, 78],
        'IV': [72, 76, 79],
        'V': [74, 78, 81],
        'vi': [76, 79, 83],
        'vii°': [78, 81, 84],
        'ii7': [69, 72, 76, 79],
        'V7': [74, 78, 81, 84],
        'I7': [67, 71, 74, 77],
        'bVII': [66, 69, 72],
        'bIII': [70, 74, 77],
        'bVI': [64, 67, 71],
        'i': [67, 70, 74],
        'iv': [72, 75, 79],
        'v': [74, 77, 81],
        'VII': [76, 79, 82],
        'VI': [75, 79, 82],
        'III': [71, 74, 78]
    }



    # Add other keys as needed
}



#gather data from songs
def gather_data():

    no_maj = 0
    no_min = 0
    no_4 = 0
    no_other = 0
    total_bpm = 0
    total_energy = 0
    total_songs = 0
    total_time = 0
    global keys
    global modes
    global time_signatures
    global bpms
    global energies
    global genres
    keys = []
    modes = []
    time_signatures = []
    bpms = []
    energies = []
    genres = []
    times = []
    retries = 3
    backoff_factor = 2

    for _ in range(retries):
        try:
            
            print(f"Loading...")
            access_token = get_access_token()
            songs = fetch_songs(access_token)
            for song in songs:
                total_songs += 1
                print(f"{total_songs}. {song['name']} by {song['artist']}")

                key = song['key']
                key_note = key_dict[key]
                keys.append(key_note)

                if song['mode'] == 1:
                    mode = 'Major'                    
                    no_maj += 1
                else:
                    mode = 'Minor'
                    no_min += 1
                
                modes.append(mode)

                mins = int((song['duration_ms'] / 60000))
                secs = int(((song['duration_ms'] / 1000) % 60))

                genres.extend(song['genre'])


                print(f"{round(song['tempo'])} BPM, {key_note} {mode}, {song['time_signature']}/4, Energy: {song['energy']}, length: {mins} mins {secs} secs \n")
                


                

                time_signatures.append(song['time_signature'])
                if song['time_signature'] == 4:
                    no_4 += 1
                else:
                    no_other += 1

                bpms.append(round(song['tempo']))
                total_bpm += song['tempo']
                energies.append(song['energy'])
                total_energy += song['energy']
                times.append(song['duration_ms'])
                total_time += song['duration_ms']


                
        except requests.exceptions.RequestException as e:
            print(f"Error: {e}")
            if _ < retries - 1:  # Don't sleep on the last attempt
                sleep_duration = backoff_factor * (_ + 1)
                print(f"Retrying in {sleep_duration} seconds...")
                time.sleep(sleep_duration)
            else:
                print("Max retries reached. Exiting.")
                break

        average_bpm = round(total_bpm / total_songs)
        average_energy = total_energy / total_songs
        global key_counts
        global mode_counts
        key_counts = Counter(keys)
        most_common_key = key_counts.most_common(1)
        mode_counts = Counter(modes)
        most_common_mode = mode_counts.most_common(1)
        global time_signature_counts
        global genre_counts
        global bpm_counts
        global energy_counts
        time_signature_counts = Counter(time_signatures)
        genre_counts = Counter(genres)
        global most_common_genre
        most_common_genre = genre_counts.most_common(1)[0][0]
        bpm_counts = Counter(bpms)
        energy_counts = Counter(energies)
        total_mins = int((total_time / total_songs) / 60000)
        total_secs = int(((total_time / total_songs) / 1000) % 60)

        

        # Generate a list of all parameters with their frequencies
        global all_keys
        global all_modes
        global all_time_signatures
        global all_bpms
        global all_energies
        global all_genres

        all_keys = [key for key, count in key_counts.items() for _ in range(count)]
        all_modes = [mode for mode, count in mode_counts.items() for _ in range(count)]
        all_time_signatures = [time_signature for time_signature, count in time_signature_counts.items() for _ in range(count)]
        all_bpms = [bpm for bpm, count in bpm_counts.items() for _ in range(count)]
        all_energies = [energy for energy, count in energy_counts.items() for _ in range(count)]
        all_genres = [genre for genre, count in genre_counts.items() for _ in range(count)]
        most_common_genre = genre_counts.most_common(1)[0][0]
        break

def get_recommendations(target_tempo, target_energy, target_time_signature):
    
    popular_genres = ['pop', 'rap', 'rock', 'country']  # Adjust this list based on your preference
    seed_genres = [most_common_genre] + popular_genres[:4]  # Take the first 4 genres from the popular_genres list
    
    
    # Get a set of recommendations from Spotify using the seed genres
    recommendations = sp.recommendations(target_tempo=target_tempo, target_energy=target_energy, seed_genres=seed_genres, limit=50)

    filtered_tracks = []

    for track in recommendations['tracks']:
        track_id = track['id']
        audio_features = sp.audio_features(track_id)[0]

        # Check time signature
        if audio_features['time_signature'] == target_time_signature:
            # Check energy
            if abs(audio_features['energy'] - target_energy) <= 1.3:
                # Check BPM
                if target_tempo - 30 <= audio_features['tempo'] <= target_tempo + 30:
                    filtered_tracks.append(track)
  
    # Sort the tracks based on BPM closeness
    sorted_tracks = sorted(filtered_tracks, key=lambda x: abs(sp.audio_features(x['id'])[0]['energy'] - target_energy))
    return sorted_tracks[:3],   # Return top 3 tracks


# Generate 10 songs worth of parameters




if __name__ == '__main__':
    playlist_id = input(f'Enter Spotify playlist link: ')
    playlist_type, playlist_id = parse_spotify_link(playlist_id)
    if playlist_type != 'playlist':
        raise ValueError("Only Spotify playlist links are supported.")
    playlist_name = sp.playlist(playlist_id)['name']
    print(f"Fetching songs from playlist {playlist_name}...")
    gather_data()
    for i in range(10):
        song_key = random.choice(all_keys)
        song_mode = random.choice(all_modes)
        song_tempo = random.choice(all_bpms)
        song_time_signature = random.choice(all_time_signatures)
        song_energy = random.choice(all_energies)
        song_genre = random.choice(all_genres)
        selected_progression = []
        if song_mode.endswith('Major'):
            selected_progression = random.choices(major_chord_progressions, weights=major_weights, k=1)[0]
        elif song_mode.endswith('Minor'):
            selected_progression = random.choices(minor_chord_progressions, weights=minor_weights, k=1)[0]
        
        # Define the generated_song dictionary
        generated_song = {
            'tempo': song_tempo,
            'energy': song_energy
            # Add more parameters as needed
        }

        access_token = get_access_token()
        tracks = fetch_songs(access_token)

        differences = []
        for track in tracks:
            audio_features = sp.audio_features(track['id'])[0]
            diff = calculate_difference(audio_features, generated_song)
            differences.append((track, diff))

        # Sort the songs by difference
        sorted_songs = sorted(differences, key=lambda x: x[1])
        recommended_tracks = get_recommendations(song_tempo, song_energy, song_time_signature)







        print(f'Song {i+1}:')
        print(f'Key: {song_key} {song_mode}')
        print(f'Tempo: {song_tempo}')
        print(f'Time Signature: {song_time_signature}/4')
        print(f'Energy: {song_energy}')
        print(f'Genre: {song_genre}')
        print(f'Chord Progression: {selected_progression}')
        midi_filename = f"generated_song_{i+1}.mid"
        generate_midi_file(song_key, selected_progression, midi_filename)
        print(f"MIDI file generated: {midi_filename}")
        print(f"Top songs to consider for drum inspiration from Spotify's library:")
        
        if recommended_tracks:
            for j, track in enumerate(recommended_tracks):
                print(f"{j+1}. {track['name']} by {track['artists'][0]['name']}")
        else:
            print("No recommendations found for this song.")
