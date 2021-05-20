import os, argparse
import freesound
from pydub import AudioSegment
from pythonosc.udp_client import SimpleUDPClient

# Freesound config
FREESOUND_API_KEY = '15dab96ed5a596aaba386b2bade17c8c5a5a68a2'  # Please replace by your own Freesound API key
FILES_DIR = './sounds'  # Place where to store the downloaded files. It will be relative to the current folder.
FREESOUND_STORE_METADATA_FIELDS = ['id', 'name', 'username', 'previews', 'license', 'tags']  # Freesound metadata properties to store
# OSC config
IP = "127.0.0.1"
PORT = 1240

freesound_client = freesound.FreesoundClient()
freesound_client.set_token(FREESOUND_API_KEY)

# Define some util functions
def query_freesound(query, filter = 'duration:[0 TO 10]', num_results=1):
    """Queries freesound with the given query and filter values.
    If no filter is given, a default filter is added to only get sounds shorter than 10 seconds.
    """
    pager = freesound_client.text_search(
        query = query,
        filter = filter,
        fields = ','.join(FREESOUND_STORE_METADATA_FIELDS),
        group_by_pack = 1,
        page_size = num_results
    )
    return [sound for sound in pager]

def retrieve_sound_preview(sound, directory):
    """Download the high-quality OGG sound preview of a given Freesound sound object to the given directory.
    """
    return freesound.FSRequest.retrieve(
        sound.previews.preview_hq_ogg,
        freesound_client,
        os.path.join(directory, sound.previews.preview_hq_ogg.split('/')[-1])
    )

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="""
    Freesound previews retriever from the command line. Downloads the first result of a given query with a maximum duration of 10 seconds.
    """)
    parser.add_argument('query', type=str, help='text query for freesound')
    args = parser.parse_args()

    # Create folder if it doesn't exist
    if not os.path.exists(FILES_DIR): os.mkdir(FILES_DIR)

    # Text query for freesound
    sounds = query_freesound(args.query)

    # Do anything else only if query got a result
    if len(sounds)==0:
        print('Your query returned no results.')
    else:
        last_wav = '' # aux string
        # Download the ogg preview
        for count, sound in enumerate(sounds):
            print('Downloading sound with id {0} [{1}/{2}]'.format(sound.id, count + 1, len(sounds)))
            retrieve_sound_preview(sound, FILES_DIR)

        # Convert downloaded file to wav format
        for file in os.listdir(FILES_DIR):
            filepath= os.path.join(FILES_DIR, file)
            if file.endswith('.ogg'):
                ogg = AudioSegment.from_ogg(filepath).set_sample_width(2) # setting bit depth to 16 bits (2 bytes) –Pd doesn't read it properly otherwise
                ogg.export(filepath[:-4]+'.wav', format="wav") # export as wav file
                os.remove(filepath) # delete ogg file
                last_wav = filepath[:-4]+'.wav'
        
        # Delete sound from previous query –comment if you want to preserve all files (only most recent query gets loaded in Pd)
        # for file in os.listdir(FILES_DIR):
        #     if file.endswith('.wav') and file != os.path.basename(last_wav):
        #         os.remove(os.path.join(FILES_DIR, file))
    
        # Send OSC message to Pd when the process has finished
        client = SimpleUDPClient(IP, PORT)
        client.send_message('/downloaded', last_wav)