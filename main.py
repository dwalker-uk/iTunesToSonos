import plistlib
import os
import shutil
import json
import urllib.parse
from lxml import etree


def main():

    # TODO: Wait max e.g. 10secs for response to keeping selection, otherwise continue anyway.
    # TODO: Check if Playlist ID has changed, even if name stays the same
    # TODO: Check that tracks in export folder are needed, optionally clean up those not associated with a playlist

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
        for name in [x['Name'] for x in settings['playlists'] if x['Export'] is True]:
            print('  - ', name)
        print('And the following Playlists were not: ')
        for name in [x['Name'] for x in settings['playlists'] if x['Export'] is False]:
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
        if itunes_playlist['Name'] not in [x['Name'] for x in settings['playlists']]:
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
    for playlist_name in [x['Name'] for x in settings['playlists'] if x['Export'] is True]:
        print('Exporting "%s" Playlist...' % playlist_name)

        # ElementTree approach...
        wpl_playlist = etree.Element('smil')
        wpl_header = etree.Element('head')
        wpl_body = etree.Element('body')
        wpl_seq = etree.SubElement(wpl_body, 'seq')
        wpl_count = 0

        # String approach (wpl)...
        playlist_wpl_media = ''
        playlist_wpl_count = 0
        playlist_wpl_duration = 0

        # String approach (m3u)...
        playlist_m3u = '#EXTM3U\n'

        itunes_playlist_info = [x for x in itunes_library['Playlists'] if x['Name'] == playlist_name][0]
        for track in itunes_playlist_info['Playlist Items']:
            # Add entry into the playlist
            left = len(itunes_library['Music Folder']) + 6      # +6 takes off iTunes' /Music folder too!

            # String approach (m3u)...
            playlist_m3u += '#EXTINF:%d,%s - %s\n' % (
                itunes_library['Tracks'][str(track['Track ID'])]['Total Time'] / 1000,
                urllib.parse.unquote(itunes_library['Tracks'][str(track['Track ID'])]['Artist']),
                urllib.parse.unquote(itunes_library['Tracks'][str(track['Track ID'])]['Name']))
            playlist_m3u += 'Media/%s\n' % (
                urllib.parse.unquote(itunes_library['Tracks'][str(track['Track ID'])]['Location'][left:]))

            # String approach (wpl)...
            playlist_wpl_count += 1
            playlist_wpl_duration += int(itunes_library['Tracks'][str(track['Track ID'])]['Total Time'] / 1000)
            playlist_wpl_media += '            <media src="Media/%s"/>\n' % (
                urllib.parse.unquote(itunes_library['Tracks'][str(track['Track ID'])]
                                     ['Location'][left:])).replace('&', '&amp;')

            # ElementTree approach...
            wpl_count += 1
            etree.SubElement(wpl_seq, 'media', src='Media/%s' % (
                urllib.parse.unquote(itunes_library['Tracks'][str(track['Track ID'])]['Location'][left:])))

            # Copy the file to the export location, if it's not already there
            # Note all actual file operations need to be unquoted, to remove e.g. %20 instead of space
            # Note for src_path the [7:] slice removes file:// from the front of the path
            src_path = urllib.parse.unquote(itunes_library['Tracks'][str(track['Track ID'])]['Location'][7:])
            dest_path = os.path.join(settings['export_path'],
                                     'Media',
                                     urllib.parse.unquote(itunes_library['Tracks'][str(track['Track ID'])]
                                                          ['Location'][left:]))
            if not os.path.isfile(dest_path):
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                print('  Copying %s - %s...' % (
                    urllib.parse.unquote(itunes_library['Tracks'][str(track['Track ID'])]['Artist']),
                    urllib.parse.unquote(itunes_library['Tracks'][str(track['Track ID'])]['Name'])))
                shutil.copyfile(src_path, dest_path)

        # Once added all tracks to the playlist, save the m3u file out to disk
        # Have been tweaking extension here, depending on which approach I'm trying...
        dest_path = os.path.join(settings['export_path'],
                                 urllib.parse.unquote(itunes_playlist_info['Name']) + 'X5.wpl')
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)

        # ElementTree approach...
        wpl_title = etree.SubElement(wpl_header, 'title')
        wpl_title.text = itunes_playlist_info['Name']
        etree.SubElement(wpl_header, 'meta', name='ItemCount', content=str(playlist_wpl_count))

        with open(dest_path, 'w') as playlist_file:

            # ElementTree approach...
            # wpl_playlist.append(wpl_header)
            # wpl_playlist.append(wpl_body)
            # playlist_file.write(etree.tostring(wpl_playlist, pretty_print=True).decode('utf-8'))

            # String approach (wpl)...
            playlist_file.write('<?wpl version="1.0"?>\n' +
                                '<smil>\n' +
                                '    <head>\n' +
                                '        <title>' + itunes_playlist_info['Name'] + '</title>\n' +
                                '        <meta name="ItemCount" content="' + str(playlist_wpl_count) + '"/>\n' +
                                '    </head>\n' +
                                '    <body>\n' +
                                '        <seq>\n')
            playlist_file.write(playlist_wpl_media)
            playlist_file.write('        </seq>\n +'
                                '    </body>\n' +
                                '</smil>')

        print('"%s" Playlist Export Complete!' % playlist_name)


if __name__ == "__main__":
    main()
