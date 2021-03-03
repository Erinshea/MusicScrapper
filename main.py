#!/usr/bin/env python3
import log
import configparser
import whatapi
import sys
import os
import re
import subprocess
import json
import cgi

settings = {'Trackers': {}}
to_skip = {}


def main():
    init()
    scrapeFolders()


def init():
    log.info("Trying to load config file config.cfg")
    config = configparser.ConfigParser(interpolation=None)
    config.read("config.cfg")

    # Ensure config file exists and is valid
    if not 'Settings' in config:
        log.error("Invalid config file. It must contains a Settings section. Please refer to config.cfg.example")
        sys.exit()
    
    # Ensure music directory is valid
    settings['MusicDirectory'] = config['Settings']['MusicDirectory']
    if os.path.exists(settings['MusicDirectory']):
        log.success(f"Music directory {settings['MusicDirectory']} found")
    else:
        log.error(f"Music directory {settings['MusicDirectory']} not found")
        sys.exit()

    # Default LogsDirectory value
    settings['LogsDirectory'] = "./logs"
    # Overwrite LogsDirectory value if provided in config
    if 'LogsDirectory' in config:
        settings['LogsDirectory'] = config['Settings']['LogDirectory']

    # If logs directory doesn't exist. Create it
    if not os.path.exists(settings['LogsDirectory']):
        log.warning(f"Logs directory {settings['LogsDirectory']} doesn't exist. Creating it")
        os.mkdir(settings['LogsDirectory'])

    trackers = [tracker for tracker in config.sections() if tracker != "Settings"]        
    
    # List all music trackers to use
    for section in trackers:
        # Fallback name is section name
        name = config.get(section, 'Name', fallback=section)
        log.info(f"Loading {name} tracker settings")
        
        settings['Trackers'][section] = {
            'name': section
        }

        # Ensure config is correct
        if not 'URL' in config[section]:
            log.error(f"Section {section} is invalid. URL of the tracker must be provided")
            sys.exit()
        URL = config[section]['URL']

        #############################################
        #####  TORRENT DIRECTORY INITIALISATION #####
        #############################################
        torrent_directory = "./torrents/" + section
        if 'TorrentDirectory' in config[section]:
            torrent_directory = config[section]['TorrentDirectory']

        # If torrent directory doesn't exists. Create it
        if not os.path.exists(torrent_directory):
            log.warning(f"{torrent_directory} doesn't exist. Creating it")
            os.makedirs(torrent_directory)
        settings['Trackers'][section]['TorrentDirectory'] = torrent_directory

        #############################################
        #####     LOG FILES  INITIALISATION     #####
        #############################################
        settings['Trackers'][section]['logs'] = {
            'FoundOn': open(os.path.join(settings['LogsDirectory'], f"FoundOn{section}.log"), "a+"),
            'NotFoundOn': open(os.path.join(settings['LogsDirectory'], f"NotFoundOn{section}.log"), "a+"),
            'FoundHereButNotOn': {}
        }


        settings['Trackers'][section]['IgnoreAlreadyFound'] = True
        if 'IgnoreAlreadyFound' in config[section]:
            settings['Trackers'][section]['IgnoreAlreadyFound'] = True if config[section]['IgnoreAlreadyFound'] else False
            settings['Trackers'][section]['logs']['FoundOn'].seek(0)
            to_skip[section] = [line.strip() for line in settings['Trackers'][section]['logs']['FoundOn'].readlines()]
            
        settings['Trackers'][section]['IgnoreAlreadyNotFound'] = True
        if 'IgnoreAlreadyNotFound' in config[section]:
            settings['Trackers'][section]['IgnoreAlreadyNotFound'] = True if config[section]['IgnoreAlreadyNotFound'] else False
            settings['Trackers'][section]['logs']['NotFoundOn'].seek(0)
            to_skip[section] += [line.strip() for line in settings['Trackers'][section]['logs']['NotFoundOn'].readlines()]

        for tracker in trackers:
            if tracker != section:
                settings['Trackers'][section]['logs']['FoundHereButNotOn'][tracker] = open(os.path.join(settings['LogsDirectory'], f"FoundOn{section}ButNotOn{tracker}.log"), "a")


        #############################################
        #####   API CONNECTION INITIALISATION   #####
        #############################################
        # Set config for Throttler
        NumberOfRequests = 5
        PerXSeconds = 10

        if 'NumberOfRequests' in config[section]:
            NumberOfRequests = int(config[section]['NumberOfRequests'])
        if 'PerXSeconds' in config[section]:
            PerXSeconds = int(config[section]['PerXSeconds'])

        throttler = whatapi.Throttler(num_requests=NumberOfRequests, per_seconds=PerXSeconds)
        log.info(f"Setting up throttler at {NumberOfRequests} every {PerXSeconds} maximum")

        # Check wether the authentication will use API Token or username / password
        if 'ApiToken' in config[section]:
            log.info(f"{name} tracker connection will use API Token authentication")
            apiToken = config[section]['ApiToken']
            settings['Trackers'][section]['api'] = whatapi.WhatAPI(apiKey=apiToken, server=URL, throttler=throttler)

        elif 'Username' in config[section] and 'Password' in config[section]:
            log.warning(f"{name} tracker connection will use username / password combination for authentication\nThis can lead to some errors if some endpoints are only accessible with API token. Use at your own risks")
            username = config[section]['Username']
            password = config[section]['Password']
            settings['Trackers'][section]['api'] = whatapi.WhatAPI(username=username, password=password, server=URL, throttler=throttler)

        else:
            log.error("Missing credentials for connection to the tracker")
            sys.exit()
        
        log.success(f"Successfuly connected to {name}")
            
def scrapeFolders(): 
    log.info(f"Search for folders in {settings['MusicDirectory']}")

    directories = os.listdir(settings['MusicDirectory'])
    index = 1

    for directory in directories:
        dir_path = os.path.join(settings['MusicDirectory'], directory)

        if os.path.isdir(dir_path):
            log.info(f"({index} / {len(directories)}) Looking into {dir_path}")
            index = index + 1

            dir_content = os.listdir(dir_path)
            dir_size = getDirectorySize(dir_path)

            skip = {}
            for tracker in settings['Trackers']:
                skip[tracker] = True if dir_path in to_skip[tracker] else False

            # If we can't get directory size, then skip it
            if dir_size == -1:
                log.warning("Invalid directory size. Skipping")
                continue

            # Only flac files
            flac_files = [file for file in dir_content if re.search('.flac$', file)]

            # If dir has no flac files, it might contains subdirectories with flac files (when they are multiple CDs for example)
            if not flac_files:
                log.warning("No FLAC files found at the root of the folder. Searching into sub folders")
                subdirectories = [subdir for subdir in dir_content if os.path.isdir(os.path.join(dir_path, subdir))]

                for subdir in subdirectories:
                    subdir_path = os.path.join(dir_path, subdir)
                    subdir_flac_files = [file for file in os.listdir(subdir_path) if re.search('.flac$', file)]

                    if subdir_flac_files:
                        flac_files = [os.path.join(subdir, file) for file in subdir_flac_files]
                        break
            
            # If they are still no flac files found, skip directory
            if not flac_files:
                log.warning("No flac files found in the directory. Skipping")
                continue

            

            # Find files metadatas
            flac_file = os.path.join(dir_path, flac_files[0])
            torrent_id = {}
            metadatas = getFlacMetadatas(flac_file)

            # Try to find torrent with album name
            for tracker in settings['Trackers']:
                if skip[tracker]:
                    log.warning(f"Skipping search for tracker {tracker} since it has already been searched for")
                    continue

                for search_type in ['album', 'performer']:
                    if search_type not in metadatas:
                        log.warning(f"No {search_type} metadata found for this album")
                        continue
                    
                    search_result = searchTorrent(metadatas=metadatas, tracker=tracker, dir_size=dir_size, search_type=search_type)
                    if search_result != -1:
                        torrent_id[tracker] = search_result
                        log.info(f"{search_type.capitalize()} {metadatas[search_type]} found on {tracker}. ID : {search_result}")
                        # If album is found, no need to try to find it with performer
                        break
                    else:
                        log.info(f"{search_type.capitalize()} {metadatas[search_type]} not found on {tracker}")

            # Download part
            for tracker in settings['Trackers']:                
                if skip[tracker]:
                    log.warning(f"Skipping download for tracker {tracker} since it has already been found")
                    continue

                if tracker in torrent_id:
                    # Download torrent file
                    r = settings['Trackers'][tracker]['api'].get_torrent(torrent_id=torrent_id[tracker], full_response=True)
                    _, header_params = cgi.parse_header(r.headers['Content-Disposition'])
                    torrent_filename = str(torrent_id[tracker]) + ".torrent"
                    if 'filename' in header_params:
                        torrent_filename = header_params['filename']
                    torrent_path = os.path.join(settings['Trackers'][tracker]['TorrentDirectory'], torrent_filename)
                    f = open(torrent_path, "wb")                   
                    f.write(r.content)
                    f.close()

                    log.success(f"{torrent_filename} successfuly downloaded on {tracker}")
                    # Logging
                    log_file = settings['Trackers'][tracker]['logs']['FoundOn']
                    log_file.write(dir_path + "\n")
                    log_file.flush()

                    for other_tracker in settings['Trackers']:
                        if other_tracker != tracker and other_tracker not in torrent_id:
                            log_file = settings['Trackers'][tracker]['logs']['FoundHereButNotOn'][other_tracker]
                            log_file.write(str(torrent_id[tracker]) + "\n")
                            log_file.flush()
                else: 
                    log_file = settings['Trackers'][tracker]['logs']['NotFoundOn']                   
                    log_file.write(dir_path + "\n")
                    log_file.flush()
            
# Extract all metadatas from a given flac
def getFlacMetadatas(file_path=None):
    if file_path is None:
        log.warning("Empty file_path parameter passed to getFlacMetadatas()")
        return {
            'returncode': -1,
            'message': "Empty file_path parameter"
        }

    log.info(f"Extracting metadatas from : {file_path} ")
    completed_process = subprocess.run(["mediainfo", "--Output=JSON", file_path], capture_output=True)
    if completed_process.returncode == 0:
        try:
            metadatas = json.loads(completed_process.stdout)
        except ValueError:
            return {
                'returncode': -1,
                'message': "Could not parse metadatas JSON"
            }

        try:
            track_infos = metadatas['media']['track'][0]
        except AttributeError:
            return {
                'returncode': -1,
                'message': "Couldn't load track metadatas"
            }
        
        if 'Album' not in track_infos and 'Title' in track_infos:
            track_infos['Album'] = track_infos['Title']
        else:
            track_infos['Album'] = None

        if 'Album_Performer' not in track_infos and 'Performer' in track_infos:
            track_infos['Album_Performer'] = track_infos['Performer']
        elif 'Album_Performer' not in track_infos and 'Composer' in track_infos:
            track_infos['Album_Performer'] = track_infos['Composer']
        else:
            track_infos['Album_Performer'] = None

        return {
            'returncode': 0,
            'album': track_infos['Album'],
            'performer': track_infos['Album_Performer']
        }
    else:
        return {
            'returncode': completed_process.returncode
        }

def getDirectorySize(dir_path=None):
    if dir_path is None:
        log.warning("Empty dir_path parameter passed to getDirectorySize()")
        return -1

    escaped_path = dir_path.replace('$', '\\$')
    # Get folder content size without the size of the folder themselves (as it is done when torrent size is calculated)
    size = subprocess.check_output(f"find \"{escaped_path}\" -type f -exec stat -c \"%s\" {{}} \; | awk '{{s+=$1}} END {{print s}}'", shell=True)
    return int(size)

def searchTorrent(metadatas=None, tracker=None, dir_size=None, search_type='album'):
    if metadatas is None or tracker is None or dir_size is None:
        log.warning("Missing parameter parameter in searchAlbum()")
        return -1

    if search_type != 'album' and search_type != 'performer':
        log.error("search_type allowed are only 'album' or 'performer' in searchTorrent()")
        return -1
    
    output = settings['Trackers'][tracker]['api'].request('browse', searchstr=metadatas[search_type])

    for result in output['response']['results']:
        if 'torrents' in result:
            for torrent in result['torrents']:
                if torrent['size'] == dir_size:
                    return torrent['torrentId']
    return -1
    
main()