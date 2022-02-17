import re

ALL_VIDEO_RESOLUTIONS = {'144p': 'LD', '240p': 'LD', '360p': 'SD', '480p': 'SD',
                         '720p': 'HD', '1080p': 'FHD', '1440p': '2K', '2160p': '4K', '4320p': '8K'}

POPULAR_VIDEO_FORMAT = ['mp4', 'mov', 'wmv', 'avi', 'flv', 'f4v', 'mkv', 'webm', 'mpeg', 'm2ts', 'mpg', 'asf', 'swf']
VALID_INPUT_VIDEO_FORMAT = ['ogg', 'rmvb', 'wmv', 'm4v', 'vro', 'm2v', 'webm', 'mpeg', 'tp', 'mpg', 'ts',
                            'm2ts', 'mpeg4', 'm2p', 'mkv', '3gp2', 'mpeg2', 'mod', 'tod', 'mxf', 'swf',
                            'mts', '3gp', 'dvr-ms', 'mov', 'amv', '3gpp', 'mpv', 'avi', 'ogv', 'dat',
                            'flv', 'mp4', 'vob', 'ogm', 'qt', 'avs', 'asf', 'mpe', 'rm', 'trp', 'm1v',
                            'f4v', 'm2t', '3g2', 'nsv', 'dv', 'divx']

FPS_LIST = ['15', '25', '30', '60']

AUDIO_BITRATE_LIST = ['64', '128', '160', '256', '320']
AUDIO_BITRATE_LIST_MAP = {"64": "Low", "128": "Standard", "160": "Good", "256": "Best", "320": "Super"}

POPULAR_AUDIO_FORMAT = ['mp3', 'm4a', 'wav', 'wma', 'aac', 'ogg', 'pcm', 'aiff', 'flac']
VALID_INPUT_AUDIO_FORMAT = ['mp3', 'm4a', 'wav', 'wma', 'aac', 'ogg', 'pcm', 'aiff', 'flac']

AUDIO_CHANNELS = ["Mono", "Stereo"]
AUDIO_CHANNELS_MAPPING = {"Mono": "1", "Stereo": "2"}
AUDIO_CHANNELS_MAPPING_REVERSE = {"1": "Mono", "2": "Stereo"}

AFTER_PLAYBACK = {"Loop Play": "loop_play", "Stop And Quit": "stop_and_quit"}

AFTER_PLAYBACK_REVERSE = {"loop_play": "Loop Play", "stop_and_quit": "Stop And Quit"}

SCALE_VIDEO = {'144p': '256:144', '240p': '426:240', '360p': '480:360', '480p': '640:480',
               '720p': '1280:720', '1080p': '1920:1080', '1440p': '2560:1440', '2160p': '3840:2160',
               '4320p': '7680:4320'}

QUALITY_MAP = {
    0: "Super",
    1: "Super",
    2: "Super",
    3: "Best",
    4: "Best",
    5: "Average",
    6: "Average",
    7: "Low",
    8: "Low",
    9: "Very Low",
    10: "Very Low",
}

FREQUENCY_MAPPER = {1: 0.2, 2: 0.4, 3: 0.6, 4: 1.0, 5: 2.0, 6: 3.0}

DUR_REGEX = re.compile(
    r"Duration: (?P<hour>\d{2}):(?P<min>\d{2}):(?P<sec>\d{2})\.(?P<ms>\d{2})"
)
TIME_REGEX = re.compile(
    r"out_time=(?P<hour>\d{2}):(?P<min>\d{2}):(?P<sec>\d{2})\.(?P<ms>\d{2})"
)
