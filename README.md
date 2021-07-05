# iTunesToSonos
Simple Python script to export chosen playlists and their music from iTunes - intended for sharing with Sonos, but uses industry standard formats

Still very work-in-progress - only shared to help diagnose issues with Unicode characters via StackOverflow.  Hope to have resolved and share fully working code very soon...



Note that the choice of exporting to .wpl format playlists is deliberate, as it seems to be the only playlist format supported by Sonos which also supports Unicode characters, i.e. non-alphanumeric characters in filenames.

See https://stackoverflow.com/questions/54914463/unicode-playlists-for-sonos-from-python for more details on the Unicode challenge, and solution.
