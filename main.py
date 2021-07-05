import os
import shutil
import json
import unicodedata


def main():
    # TODO: Check that tracks in export folder are needed, optionally clean up those not associated with a playlist

    settings_file = 'settings.json'
    settings = {}

    # Load Settings File
    try:
        with open(os.path.join(os.path.dirname(__file__), settings_file), 'r') as settings_handle:
            settings = json.load(settings_handle)
    except IOError:
        print('First Run! Please provide basic configuration information to start:')

    # Check for and if needed request path to playlists
    if 'playlist_path' not in settings:
        while True:
            input_text = input('Enter full path to folder containing .m3u8 Playlists to export: ')
            if os.path.isdir(input_text):
                settings['playlist_path'] = input_text
                break
            else:
                print('Path invalid or folder not found!  Please try again... (or ctrl+c to quit)')

    # Check for and if needed request the Export Path
    if 'export_path' not in settings:
        while True:
            print('The export path can be either local or on a network drive.  However, network drives must be mounted')
            print('before they can be used within this script.  A sub-folder will be created for Media.')
            print('Playlists will be added to the root of the folder.')
            print('On Mac OS X, network folders can be referenced via "/Volumes/[DriveName]/[FolderName]"')
            print('On Mac OS X, removable drives can be referenced via "/Volumes/[DriveName]"')
            input_text = input('Enter full path to your export folder:')
            if os.path.isdir(input_text):
                settings['export_path'] = input_text
                break
            else:
                print('Path invalid or folder not found!  Please try again... (or ctrl+c to quit)')

    # Save config data back to file
    with open(os.path.join(os.path.dirname(__file__), settings_file), 'w') as settings_handle:
        json.dump(settings, settings_handle, indent=2, sort_keys=True)

    # Get the list of Playlists from the folder
    if not os.path.isdir(settings['playlist_path']):
        print(f'Playlists folder ({settings["playlist_path"]}) does not exist - exiting!')
        exit()
    playlists = [x for x in os.listdir(settings['playlist_path']) if x.lower().endswith(".m3u8")]

    # Open each playlist in turn
    for playlist in playlists:

        playlist_name = playlist[0:playlist.find('.')]

        print(f'Exporting {playlist_name} Playlist...')

        playlist_file = open(os.path.join(settings['playlist_path'], playlist))
        playlist_lines = playlist_file.readlines()

        # Generate the new playlist (wpl format)
        playlist_wpl_media = ''
        playlist_wpl_count = 0
        playlist_wpl_duration = 0   # In seconds...

        # Read through the playlist, getting the list of tracks from it
        playlist_tracks = []
        this_track_duration = 0
        for line in playlist_lines:
            # Each track is split across two lines - we need the duration from the 1st line, and the path from the 2nd
            if line.startswith('#EXTINF:'):
                this_track_duration = int(line[line.find(':')+1:line.find(',')])
            elif not line.startswith('#'):
                # Save the track to our list - note that we're expecting an absolute path to the track
                playlist_tracks.append(line.strip())
                playlist_wpl_duration += this_track_duration
                this_track_duration = 0

        for track in playlist_tracks:
            # Get just the artist/album/track part of the track's path
            artist_album_track = track[track.rfind('/', 0, track.rfind('/', 0, track.rfind('/')))+1:]
            # Create the full path to export this track to
            export_path = os.path.join(settings['export_path'], 'Media', artist_album_track)
            # Create the path formatted appropriately for the playlist: NFC Normalized, and replaced special characters
            playlist_path = unicodedata.normalize('NFC', f'Media/{artist_album_track}').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')

            # Add this track's details to the WPL playlist
            playlist_wpl_count += 1
            playlist_wpl_media += f'            <media src="{playlist_path}"/>\n'

            # Check if file already exists, and if not then copy over (making folder if needed, and reporting progress)
            if not os.path.isfile(export_path):
                os.makedirs(os.path.dirname(export_path), exist_ok=True)
                print(f'  Copying {artist_album_track}...')
                shutil.copyfile(track, export_path)

        # Once added all tracks to the playlist, get path and make folder for saving WPL file to disk
        pl_dest_path = os.path.join(settings['export_path'], playlist_name + '.wpl')
        os.makedirs(os.path.dirname(pl_dest_path), exist_ok=True)

        # Create and write the wpl file
        with open(pl_dest_path, 'wb') as playlist_file:

            # Generate start and end of the playlist
            prefix = ('<?wpl version="1.0"?>\n' +
                      '<smil>\n' +
                      '    <head>\n' +
                      '        <title>' + playlist_name + '</title>\n' +
                      '        <meta name="Generator" content="https://github.com/dwalker-uk/iTunesToSonos"/>\n' +
                      '        <meta name="ItemCount" content="' + str(playlist_wpl_count) + '"/>\n' +
                      '        <meta name="TotalDuration" content="' + str(playlist_wpl_duration) + '"/>\n' +
                      '    </head>\n' +
                      '    <body>\n' +
                      '        <seq>\n')
            suffix = ('        </seq>\n' +
                      '    </body>\n' +
                      '</smil>')

            # Write the playlist to file, using ascii with xml character replacement encoding
            playlist_file.write(prefix.encode('ascii', 'xmlcharrefreplace'))
            playlist_file.write(playlist_wpl_media.encode('ascii', 'xmlcharrefreplace'))
            playlist_file.write(suffix.encode('ascii', 'xmlcharrefreplace'))

        print('"%s" Playlist Export Complete!' % playlist_name)


if __name__ == "__main__":
    main()
