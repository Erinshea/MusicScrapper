# Music Scrapper

Music Scrapper is a script for automating music search on music trackers given a folder with music inside.

# How does it work ?

The script will go through every folders inside your music folder (which can be changed in config file). If the folder contains a flac file, it will try to find the corresponding torrent with the album name or the performer name. Size is used to ensure that the match is good.
The torrent is then downloaded and put in ./torrents folder (can be changed in config)

Additionaly, if multiple trackers are specified, when a torrent is found on one tracker but not another, his torrent id is put into a file (.logs/FoundOn...ButNotOn...) so you can use a tool (for example [RedCurry](https://gitlab.com/_mclovin/redcurry)) to upload it on other trackers :)

# Usage

```
# It will not work with issaczafuta's module as it was not compatible with API token
python -m pip install git+https://github.com/Erinshea/whatapi.git
python main.py
```

# Configuration

Please use ./config.cfg.example as a reference. The config file name must be ./config.cfg in order to work

## Settings
That section is mandatory. The name of the section **MUST** be Settings

- **MusicDirectory** : Directory where the script will look for music folders
- **LogsDirectory** (Optional) : Directory where logs should be stored. Default value is *./logs*

## Trackers
Each tracker must have his own section. Section name doesn't really matters, it will only be used for logging matters. You use full tracker name or tracker abbreviation

- **Name** (Optional) : Name of the tracker for logging purposes. Default *section_name*
- **URL** : URL of the tracker. The script has only been tested with HTTPS
- **ApiToken** : Api Token for authentication. This is the prefered method of authentication, please use it, really.
- **Username** & **Password** : Credentials for user/password authentication. Please do not use
- **TorrentDirectory** (Optional) : Folder where .torrent files will be downloaded. Default *./torrents*
- **NumberOfRequests** & **PerXSeconds** (Optional) : Max NumberOfRequests to do every PerXSeconds. Default *5 requests every 10 seconds*
- **IgnoreAlreadyFound** (Optional) : Ignore folder that have been put in FoundOn... log file (which mean they have been found on tracker and downloaded). Default *True*
- **IgnoreAlreadyNotFound** (Optional) : Ignore folder that have been put in NotFoundOn... log file (which mean they have been searched for on tracker and not found). Default *True*