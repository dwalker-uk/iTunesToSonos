import plistlib
import os
import shutil
import json
import urllib.parse
import unicodedata


def main():

    # TODO: Wait max e.g. 10secs for response to keeping selection, otherwise continue anyway.
    # TODO: Check if Playlist ID has changed, even if name stays the same
    # TODO: Check that tracks in export folder are needed, optionally clean up those not associated with a playlist
    # TODO: Need to test whether playlist has been deleted - assumes it does so gives out of range error

    settings_file = 'settings.json'
    settings = {}
    itunes_library = {}

    # Load Settings File
    try:
        with open(os.path.join(os.path.dirname(__file__), settings_file), 'r') as settings_handle:
            settings = json.load(settings_handle)
    except IOError:
        print('First Run! Please provide basic configuration information to start:')

    # Check for and if needed request iTunes Library Path
    if 'itunes_path' not in settings:
        while True:
            input_text = input('Enter full path to iTunes Music Library.xml: ')
            if os.path.isfile(input_text):
                settings['itunes_path'] = input_text
                break
            else:
                print('Path invalid or file not found!  Please try again... (or ctrl+c to quit)')

    # Check for and if needed request the Export Path
    if 'export_path' not in settings:
        while True:
            print('The export path can be either local or on a network drive.  However, network drives must be mounted')
            print('before they can be used within this script.  Sub-folders will be created for Media and Playlists.')
            print('(On Mac OS X, network folders can be referenced via "/Volumes/[DriveName]/[FolderName]")')
            input_text = input('Enter full path to your export folder:')
            if os.path.isdir(input_text):
                settings['export_path'] = input_text
                break
            else:
                print('Path invalid or folder not found!  Please try again... (or ctrl+c to quit)')

    # Read in the iTunes Library File
    try:
        with open(settings['itunes_path'], 'rb') as itunes_handle:
            itunes_library = plistlib.load(itunes_handle)
    except IOError:
        print('Unable to read iTunes Library - check the path is correct!')
        exit()

    # Get the playlists stored in settings, and ask if user wants to change the selection
    if 'playlists' not in settings:
        settings['playlists'] = []
    else:
        print('On your previous run, the following Playlists were exported: ')
        for name in [pl['Name'] for pl in settings['playlists'] if pl['Export'] is True]:
            print('  - ', name)
        print('And the following Playlists were not: ')
        for name in [pl['Name'] for pl in settings['playlists'] if pl['Export'] is False]:
            print('  - ', name)
        while True:
            keep_selection = input('Do you want to keep this selection? (y/n)  ' +
                                   'Note that you will still be prompted for any new playlists!: ')
            if keep_selection in ('y', 'Y'):
                break
            elif keep_selection in ('n', 'N'):
                settings['playlists'].clear()
                break
            else:
                print('Error - enter y or n.  Please try again, or ctrl+c to quit.')

    # Get actual playlists from iTunes, and ask about any that are new
    for itunes_playlist in itunes_library['Playlists']:

        # Deal with new (or renamed) playlists
        if itunes_playlist['Name'] not in [pl['Name'] for pl in settings['playlists']]:
            while True:
                should_include = input('New playlist "%s" - do you want to export? (y/n) ' % itunes_playlist['Name'])
                if should_include in ('y', 'Y'):
                    should_inc_bool = True
                    break
                elif should_include in ('n', 'N'):
                    should_inc_bool = False
                    break
                else:
                    print('Error - enter y or n.  Please try again, or ctrl+c to quit.')
            settings['playlists'].append({'Name': itunes_playlist['Name'],
                                          'PPID': itunes_playlist['Playlist Persistent ID'],
                                          'Export': should_inc_bool})

    # Save config data back to file
    with open(os.path.join(os.path.dirname(__file__), settings_file), 'w') as settings_handle:
        json.dump(settings, settings_handle, indent=2, sort_keys=True)

    # Do the export for each selected playlist
    for playlist_name in [pl['Name'] for pl in settings['playlists'] if pl['Export'] is True]:
        print('Exporting "%s" Playlist...' % playlist_name)

        # String approach (wpl)...
        playlist_wpl_media = ''
        playlist_wpl_count = 0
        playlist_wpl_duration = 0

        itunes_playlist_info = [x for x in itunes_library['Playlists'] if x['Name'] == playlist_name][0]
        for track in itunes_playlist_info['Playlist Items']:

            # Translate filename into correct formats - important process:
            #  1. Calculate the length of iTunes path to strip, in order to make the path relative
            #  2. Get the relative path to the file, by stripping the iTunes path and adding Media/ instead
            #  3. Remove iTunes library's url encoding, e.g. %20 is used instead of space
            #  4. Normalise the unicode string, using NFC form (i.e a single composed character for an accented letter)
            #  5. Replace &, <, >, " characters - note don't need to replace ' as will use double quotes in XML
            left = len(itunes_library['Music Folder']) + 6      # +6 takes off iTunes' /Music folder too!
            t_path_relative = 'Media/' + itunes_library['Tracks'][str(track['Track ID'])]['Location'][left:]
            t_path_unquoted = urllib.parse.unquote(t_path_relative)
            t_path_norm = unicodedata.normalize('NFC', t_path_unquoted)
            t_path = t_path_norm.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')

            # Add this track's details to the wpl file
            playlist_wpl_count += 1
            playlist_wpl_duration += int(itunes_library['Tracks'][str(track['Track ID'])]['Total Time'] / 1000)
            playlist_wpl_media += '            <media src="%s"/>\n' % t_path

            # Get the paths for source and destination for the actual file copy
            # Note all actual file operations need to be unquoted, to remove e.g. %20 instead of space - but don't
            # need to normalise or replace XML characters
            # Note for src_path the [7:] slice removes file:// from the front of the path - not needed on Mac
            src_path = urllib.parse.unquote(itunes_library['Tracks'][str(track['Track ID'])]['Location'][7:])
            dest_path = urllib.parse.unquote(
                                    os.path.join(settings['export_path'],
                                                 'Media',
                                                 itunes_library['Tracks'][str(track['Track ID'])]['Location'][left:]))

            # Check if file already exists, and if not then copy over (making folder if needed, and reporting progress)
            if not os.path.isfile(dest_path):
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                print('  Copying %s - %s...' % (
                    itunes_library['Tracks'][str(track['Track ID'])]['Artist'],
                    itunes_library['Tracks'][str(track['Track ID'])]['Name']))
                shutil.copyfile(src_path, dest_path)

        # Once added all tracks to the playlist, get path and make folder for saving wpl file to disk
        pl_dest_path = os.path.join(settings['export_path'],
                                    urllib.parse.unquote(itunes_playlist_info['Name']) + '.wpl')
        os.makedirs(os.path.dirname(pl_dest_path), exist_ok=True)

        # Create and write the wpl file
        with open(pl_dest_path, 'wb') as playlist_file:

            # Generate start and end of the playlist
            prefix = ('<?wpl version="1.0"?>\n' +
                      '<smil>\n' +
                      '    <head>\n' +
                      '        <title>' + itunes_playlist_info['Name'] + '</title>\n' +
                      '        <meta name="Generator" content="https://github.com/dwalker-uk/iTunesToSonos"/>\n' +
                      '        <meta name="ItemCount" content="' + str(playlist_wpl_count) + '"/>\n' +
                      '        <meta name="TotalDuration" content="' + str(playlist_wpl_duration) + '"/>\n' +
                      '    </head>\n' +
                      '    <body>\n' +
                      '        <seq>\n')
            suffix = ('        </seq>\n +'
                      '    </body>\n' +
                      '</smil>')

            # Write the playlist to file, using ascii with xml character replacement encoding
            playlist_file.write(prefix.encode('ascii', 'xmlcharrefreplace'))
            playlist_file.write(playlist_wpl_media.encode('ascii', 'xmlcharrefreplace'))
            playlist_file.write(suffix.encode('ascii', 'xmlcharrefreplace'))

        print('"%s" Playlist Export Complete!' % playlist_name)


if __name__ == "__main__":
    main()
