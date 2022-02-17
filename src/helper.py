import datetime
import json
import psutil
from PyQt5.QtNetwork import QNetworkConfigurationManager
from typing import Iterator
import getpass
import os
import subprocess
from PyQt5.QtCore import QProcessEnvironment, QStandardPaths
from constant import POPULAR_VIDEO_FORMAT, POPULAR_AUDIO_FORMAT, TIME_REGEX, DUR_REGEX, ALL_VIDEO_RESOLUTIONS, FPS_LIST, \
    AUDIO_BITRATE_LIST, VALID_INPUT_VIDEO_FORMAT, VALID_INPUT_AUDIO_FORMAT, AUDIO_BITRATE_LIST_MAP, AUDIO_CHANNELS
import time
from PyQt5 import QtGui, QtCore


def set_style_for_pause_play_button(self, pause=False):
    if pause:
        self.ui.pause_button.setText("")
        icon9 = QtGui.QIcon()
        icon9.addPixmap(QtGui.QPixmap(":/myresource/resource/pause_new.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.ui.pause_button.setIcon(icon9)
        self.ui.pause_button.setIconSize(QtCore.QSize(25, 25))

    else:
        self.ui.pause_button.setText("")
        icon10 = QtGui.QIcon()
        icon10.addPixmap(QtGui.QPixmap(":/myresource/resource/play.png"), QtGui.QIcon.Normal,
                         QtGui.QIcon.Off)
        self.ui.pause_button.setIcon(icon10)
        self.ui.pause_button.setIconSize(QtCore.QSize(25, 25))


def get_time_format(length):
    time_str = str(time.strftime('%H:%M:%S', time.gmtime(length)))
    if time_str[0:2] == '00':
        return "{0}m:{1}s".format(time_str[3:5], time_str[6:])
    else:
        return "{0}h:{1}m:{0}s".format(time_str[0:2], time_str[3:5], time_str[6:])


def human_format(num):
    magnitude = 0
    while abs(num) >= 1000:
        magnitude += 1
        num /= 1000.0
    # add more suffixes if you need them
    return '%.2f%s' % (num, ['', 'K', 'M', 'G', 'T', 'P'][magnitude])


def save_download_info(save_data_info, download_path, file_path, location_path, download_type):
    try:
        video_info_list = list()
        video_info = dict()
        video_info["download_type"] = download_type
        video_info["title_show"] = save_data_info.get("title_show", "")
        video_info["title_safe"] = save_data_info.get("title_safe", "")
        video_info["length"] = save_data_info.get("length", "")
        video_info["size"] = save_data_info.get("size", "")
        video_info["resolution"] = save_data_info.get("resolution", "")
        video_info["bitrate"] = save_data_info.get("bitrate", "N/A")
        video_info["type"] = save_data_info.get("type", "")
        video_info["audio_channel"] = save_data_info.get("audio_channel", "N/A")

        if download_type in ["audio", "playlist_audio"]:
            video_info["fps"] = "-"
        else:
            video_info["fps"] = save_data_info.get("fps", "")
        video_info["subtype"] = save_data_info.get("subtype", "")
        video_info["download_date"] = datetime.datetime.strftime(datetime.datetime.now(), '%d %b %Y')
        video_info["download_time"] = datetime.datetime.strftime(datetime.datetime.now(), "%H:%M")
        video_info["download_path"] = download_path
        video_info["sort_param"] = str(datetime.datetime.now())
        video_info["file_path"] = file_path
        video_info[
            "thumbnail_path"] = f"{location_path}/FORMAT_LAB/.thumbnails/{save_data_info.get('title_safe', '')}.jpg"

        video_info_list.append(video_info.copy())
        download_data_dir = f'{location_path}/FORMAT_LAB/.downloads'
        prev_saved_data = get_local_download_data(location_path)

        if prev_saved_data:
            prev_saved_data.extend(video_info_list)
            data = json.dumps(prev_saved_data)
        else:
            data = json.dumps(video_info_list)

        os.makedirs(download_data_dir, exist_ok=True)
        file_name = f'{download_data_dir}/download_data.json'
        with open(file_name, "w+") as file:
            file.write(data)

    except Exception as e:
        print(e)
        pass


def save_after_delete(data, location_path):
    try:
        data = json.dumps(data)
        download_data_dir = f'{location_path}/FORMAT_LAB/.downloads'
        os.makedirs(download_data_dir, exist_ok=True)
        file_name = f'{download_data_dir}/download_data.json'
        with open(file_name, "w+") as file:
            file.write(data)
    except Exception as e:
        pass


def get_local_download_data(location_path):
    download_data_dir = f'{location_path}/FORMAT_LAB/.downloads'
    prev_saved_data = []
    try:
        os.makedirs(download_data_dir, exist_ok=True)
        file_name = f'{download_data_dir}/download_data.json'
        user_data_file = open(file_name, "r+")
        data = user_data_file.read()
        prev_saved_data = json.loads(data)
    except Exception as error:
        pass

    return prev_saved_data


def safe_string(input_str):
    from slugify import slugify
    return slugify(input_str)


def select_format_data_video(video_quality, fps_quality, audio_quality):
    all_quality = []
    all_fps = []
    all_audio_bitrate = []
    res_list = list(ALL_VIDEO_RESOLUTIONS.keys())
    POPULAR_VIDEO_FORMAT.sort()
    POPULAR_AUDIO_FORMAT.sort()

    video_format = list(map(lambda x: f"{str(x).upper()} - VIDEO", POPULAR_VIDEO_FORMAT))
    audio_format = list(map(lambda x: f"{str(x).upper()} - AUDIO", POPULAR_AUDIO_FORMAT))

    for count, quality in enumerate(res_list, 1):
        if quality == video_quality:
            all_quality = res_list[0:count]
            break

    if fps_quality > 60:
        all_fps = FPS_LIST
    else:
        for count, quality in enumerate(FPS_LIST, 1):
            if int(quality) >= fps_quality:
                all_fps = FPS_LIST[0:count]
                break

    if len(all_fps) == 0:
        all_fps = ['30']

    if int(audio_quality) > 320:
        all_audio_bitrate = AUDIO_BITRATE_LIST
    else:
        for count, bitrate in enumerate(AUDIO_BITRATE_LIST, 1):
            if int(bitrate) >= int(audio_quality):
                all_audio_bitrate = AUDIO_BITRATE_LIST[0:count]
                break

    if len(all_audio_bitrate) == 0:
        all_audio_bitrate = ['128']

    return [f"{qlty} ({ALL_VIDEO_RESOLUTIONS.get(qlty)})"
            for qlty in all_quality], video_format + audio_format, [f'{fps} FPS' for fps in all_fps], \
           [f'{br} Kbps' for br in all_audio_bitrate]


def select_format_data_audio(audio_quality):
    all_bitrate = []

    if int(audio_quality) > 320:
        all_bitrate = AUDIO_BITRATE_LIST
    else:
        for count, bitrate in enumerate(AUDIO_BITRATE_LIST, 1):
            if int(bitrate) >= int(audio_quality):
                all_bitrate = AUDIO_BITRATE_LIST[0:count]
                break

    if len(all_bitrate) == 0:
        all_bitrate = ['128']

    return list(map(str.upper, POPULAR_AUDIO_FORMAT)), [f'{br} Kbps - {AUDIO_BITRATE_LIST_MAP.get(str(br))}' for br in
                                                        all_bitrate], AUDIO_CHANNELS


def check_internet_connection():
    try:
        if QNetworkConfigurationManager().isOnline():
            return True
    except Exception as e:
        pass
    return False


def humanbytes(byte_str):
    B = float(byte_str)
    KB = float(1024)
    MB = float(KB ** 2)
    GB = float(KB ** 3)
    TB = float(KB ** 4)

    if B < KB:
        return '{0} {1}'.format(B, 'B')
    elif KB <= B < MB:
        return '{0:.2f} KB'.format(B / KB)
    elif MB <= B < GB:
        return '{0:.2f} MB'.format(B / MB)
    elif GB <= B < TB:
        return '{0:.2f} GB'.format(B / GB)
    elif TB <= B:
        return '{0:.2f} TB'.format(B / TB)


def to_ms(s=None, des=None, **kwargs) -> float:
    if s:
        hour = int(s[0:2])
        minute = int(s[3:5])
        sec = int(s[6:8])
        ms = int(s[10:11])
    else:
        hour = int(kwargs.get("hour", 0))
        minute = int(kwargs.get("min", 0))
        sec = int(kwargs.get("sec", 0))
        ms = int(kwargs.get("ms", 0))

    result = (hour * 60 * 60 * 1000) + (minute * 60 * 1000) + (sec * 1000) + ms
    if des and isinstance(des, int):
        return round(result, des)
    return result


def run_ffmpeg_command(cmd: "list[str]") -> Iterator[int]:
    """
    Run an ffmpeg command, trying to capture the process output and calculate
    the duration / progress.
    Yields the progress in percent.
    """
    total_dur = None

    cmd_with_progress = [cmd[0]] + ["-progress", "-", "-nostats"] + cmd[1:]

    stderr = []

    p = subprocess.Popen(
        cmd_with_progress,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=False,
    )

    p_id = psutil.Process(pid=p.pid)

    while True:
        line = p.stdout.readline().decode("utf8", errors="replace").strip()
        if line == "" and p.poll() is not None:
            break
        stderr.append(line.strip())

        if not total_dur and DUR_REGEX.search(line):
            total_dur = DUR_REGEX.search(line).groupdict()
            total_dur = to_ms(**total_dur)
            continue

        if total_dur:
            result = TIME_REGEX.search(line)
            if result:
                elapsed_time = to_ms(**result.groupdict())
                yield int(elapsed_time / total_dur * 100), p_id

    if p.returncode != 0:
        raise RuntimeError(
            "Error running command {}: {}".format(cmd, str("\n".join(stderr)))
        )

    yield 100, p_id


def check_default_location(path):
    try:
        home = str(path).split("/")[1]
        if home == "home":
            return True
        else:
            return False
    except Exception as e:
        return False


def get_downloaded_data_filter(data, filter_type):
    if filter_type == "all_files":
        return data
    else:
        return [item_dict for item_dict in data if item_dict.get("download_type") == filter_type]


def get_valid_video_file(video_file):
    if str(video_file).lower().endswith(tuple(VALID_INPUT_VIDEO_FORMAT)):
        return video_file, False
    else:
        return video_file, True


def get_valid_audio_file(video_file):
    if str(video_file).lower().endswith(tuple(VALID_INPUT_AUDIO_FORMAT)):
        return video_file, False
    else:
        return video_file, True


def get_download_path(location,
                      thumbnail=False,
                      download_video_path=False,
                      download_audio_path=False,
                      ):
    try:
        if location:
            if thumbnail:
                location += '/FORMAT_LAB/.thumbnails'
                os.makedirs(location, exist_ok=True)
            elif download_video_path:
                location += '/FORMAT_LAB/videos'
                os.makedirs(location, exist_ok=True)
            elif download_audio_path:
                location += '/FORMAT_LAB/audio'
                os.makedirs(location, exist_ok=True)
            else:
                location += '/Downloads'
            return location
        else:
            HOME = QProcessEnvironment().systemEnvironment().value('SNAP_REAL_HOME')
            if HOME != '':
                if thumbnail:
                    HOME += '/Downloads/FORMAT_LAB/.thumbnails'
                    os.makedirs(HOME, exist_ok=True)
                elif download_video_path:
                    HOME += '/Downloads/FORMAT_LAB/videos'
                    os.makedirs(HOME, exist_ok=True)
                elif download_audio_path:
                    HOME += '/Downloads/FORMAT_LAB/audio'
                    os.makedirs(HOME, exist_ok=True)
                else:
                    HOME += '/Downloads'
            else:
                HOME = QStandardPaths.writableLocation(QStandardPaths.HomeLocation)
    except Exception as e:
        HOME = QProcessEnvironment().systemEnvironment().value('SNAP_REAL_HOME') + "/Downloads/FORMAT_LAB/"

    return HOME


def get_initial_download_dir():
    try:
        download_path = QProcessEnvironment().systemEnvironment().value('SNAP_REAL_HOME')
        if download_path not in ["", None]:
            download_path = download_path + "/Downloads"
        else:
            username = getpass.getuser()
            if username not in ["", None]:
                download_path = f"/home/{username}/Downloads"
            else:
                download_path = os.environ['HOME']
                if download_path not in ["", None]:
                    download_path = download_path + "/Downloads"
                else:
                    download_path = os.path.expanduser("~") + "/Downloads"
        os.makedirs(download_path, exist_ok=True)
    except Exception as e:
        print("error in getting download path", str(e))
        return "/Downloads"
    return download_path


def get_initial_document_dir():
    try:
        download_path = QProcessEnvironment().systemEnvironment().value('SNAP_REAL_HOME')
        if download_path not in ["", None]:
            download_path = download_path + "/Documents"
        else:
            username = getpass.getuser()
            if username not in ["", None]:
                download_path = f"/home/{username}/Documents"
            else:
                download_path = os.environ['HOME']
                if download_path not in ["", None]:
                    download_path = download_path + "/Documents"
                else:
                    download_path = os.path.expanduser("~") + "/Documents"
        os.makedirs(download_path, exist_ok=True)
    except Exception as e:
        print("error in getting download path", str(e))
        return "/Documents"
    return download_path
