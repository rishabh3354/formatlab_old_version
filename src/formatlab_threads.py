import os
import time
from PyQt5 import QtCore
from PyQt5.QtCore import pyqtSignal
from psutil import pid_exists
from helper import run_ffmpeg_command, save_download_info
from formatlab_scripts import get_download_path, process_video, process_audio
from constant import SCALE_VIDEO, AUDIO_CHANNELS_MAPPING_REVERSE

PRODUCT_NAME = "FORMAT_LAB"


class ProcessVideo(QtCore.QThread):
    meta_data_signal = pyqtSignal(dict)

    def __init__(self, input_video, location, parent=None):
        super(ProcessVideo, self).__init__(parent)
        self.input_video = input_video
        self.location = location

    def run(self):
        video_meta_data = process_video(self.input_video, self.location)
        self.meta_data_signal.emit(video_meta_data)


class ProcessAudio(QtCore.QThread):
    meta_data_signal = pyqtSignal(dict)

    def __init__(self, input_audio, location, parent=None):
        super(ProcessAudio, self).__init__(parent)
        self.input_audio = input_audio
        self.location = location

    def run(self):
        audio_meta_data = process_audio(self.input_audio, self.location)
        self.meta_data_signal.emit(audio_meta_data)


class ConvertVideo(QtCore.QThread):
    change_value = pyqtSignal(dict)
    finished = pyqtSignal(dict)
    error = pyqtSignal(dict)
    no_error = pyqtSignal(str)
    after_kill = pyqtSignal(str)

    def __init__(self, context, parent=None):
        super(ConvertVideo, self).__init__(parent)
        self.main_obj = context.get("main")
        self.input_video_path = context.get("video_path", "")
        self.title = context.get("title", "")
        self.format_type = context.get("format_type", "video")
        self.input_audio_bitrate = context.get("input_audio_bitrate", "")
        self.audio_bitrate = context.get("audio_bitrate", "")
        self.input_format = context.get("input_format", "mp4")
        self.input_quality = context.get("input_quality")
        self.input_fps = context.get("input_fps")
        self.output_format = context.get("formats", "mp4")
        self.quality = context.get("quality", "144p")
        self.fps = context.get("fps", "30")
        self.location = context.get("location", "")
        if self.format_type == "video":
            self.output_folder = get_download_path(self.location, download_video_path=True)
        else:
            self.output_folder = get_download_path(self.location, download_audio_path=True)
        self.a_v_quality = str(10 - context.get("audio_video_quality", 5))
        if self.output_format != "same as source":
            self.final_output_format = self.output_format
        else:
            self.final_output_format = self.input_format
        if self.quality == "same as source":
            self.quality = self.input_quality
        if self.fps == "same as source":
            self.fps = self.input_fps
        if self.audio_bitrate == "same as source":
            self.audio_bitrate = self.input_audio_bitrate
        if self.format_type == "video":
            self.output_video_path = f'{self.output_folder}/{self.title}_{self.quality}_' \
                                     f'{self.fps}fps_{context.get("audio_video_quality", 5)}pts.{self.final_output_format}'
        else:
            self.output_video_path = f'{self.output_folder}/{self.title}_{self.audio_bitrate}kbps.{self.final_output_format}'

        self.save_data_info = {
            "title_show": context.get("show_title", ""),
            "title_safe": context.get("title", ""),
            "length": context.get("duration", ""),
            "size": context.get("size", ""),
            "resolution": self.quality,
            "bitrate": self.audio_bitrate,
            "type": self.format_type,
            "fps": self.fps,
            "a_v_quality": context.get("audio_video_quality", 5),
            "subtype": self.final_output_format,
        }

        # thread control flags
        self.is_paused = False
        self.is_killed = False

    def run(self):
        if not os.path.isfile(self.output_video_path):
            self.no_error.emit("no_error")
            self.main_obj.ui.progress_bar.setRange(0, 0)
            self.progress_convert()
        else:
            self.error.emit({"error": "File Already Exists", "output_folder": self.output_folder,
                             "output_video_path": self.output_video_path, "title": self.title
                             })

    def get_ffmpeg_input_cmd(self):
        cmd = ['ffmpeg', '-i', self.input_video_path]

        if self.format_type == "video":
            if self.quality != self.input_quality:
                scale = SCALE_VIDEO.get(self.quality)
                cmd.extend(['-vf', 'scale={0}'.format(scale), '-preset', 'slow', '-crf', '18'])
            if self.fps != self.input_fps:
                fps = self.fps
                if fps == '15' and self.final_output_format in ["mpg", "mpeg"]:
                    # condition mpeg, mpg 15 fps not supported, so skip fps here!
                    pass
                else:
                    cmd.extend(['-r', fps])
            if self.final_output_format != "webm":
                cmd.extend(['-q:v', self.a_v_quality, '-q:a', self.a_v_quality])
            cmd.append(self.output_video_path)
        else:
            cmd.extend(['-b:a', '320000'])
            if self.final_output_format == "pcm":
                cmd.extend(["-f", "s16le", "-acodec", "pcm_s16le"])
            cmd.extend(["-vn", self.output_video_path])

        return cmd

    def progress_convert(self):
        try:
            progress_dict = {"progress": 0,
                             "total_size": 100,
                             "output_video_path": self.output_video_path,
                             "output_folder": self.output_folder,
                             "type": self.format_type,
                             "output_format": self.final_output_format,
                             "title": self.title,
                             "is_killed": self.is_killed,
                             }

            ffmpeg_cmd = self.get_ffmpeg_input_cmd()

            for progress, pid in run_ffmpeg_command(ffmpeg_cmd):
                progress_dict["progress"] = progress
                while self.is_paused:
                    time.sleep(0.5)
                    if pid_exists(pid.pid):
                        pid.suspend()
                    if self.is_killed:
                        self.terminate()
                        self.after_kill.emit(self.output_video_path)
                        break

                if pid_exists(pid.pid):
                    pid.resume()

                if self.is_killed:
                    if pid_exists(pid.pid):
                        pid.kill()
                    self.terminate()
                    self.after_kill.emit(self.output_video_path)
                    break
                if progress == 100:
                    self.finished.emit(progress_dict)
                    break
                else:
                    self.change_value.emit(progress_dict)

            save_download_info(self.save_data_info, self.output_folder, self.output_video_path, self.location, self.format_type)

        except Exception as e:
            self.error.emit({"error": str(e), "output_folder": self.output_folder,
                             "output_video_path": self.output_video_path
                             })
            pass

    def pause(self):
        self.is_paused = True

    def resume(self):
        self.is_paused = False

    def kill(self):
        self.is_killed = True


class ConvertAudio(QtCore.QThread):
    change_value = pyqtSignal(dict)
    finished = pyqtSignal(dict)
    error = pyqtSignal(dict)
    no_error = pyqtSignal(str)
    after_kill = pyqtSignal(str)

    def __init__(self, context, parent=None):
        super(ConvertAudio, self).__init__(parent)
        self.main_obj = context.get("main")
        self.title = context.get("title", "")
        self.input_audio_path = context.get("audio_path", "")
        self.input_format = context.get("input_format", "")
        self.input_bitrate = context.get("input_bitrate", "")
        self.output_format = context.get("formats", "mp3")
        self.output_bitrate = context.get("bitrate", "128")
        self.location = context.get("location", "")

        self.input_channel = context.get("input_channel", "2")
        self.output_channel = context.get("output_channel", "2")

        if self.output_channel == "same as source":
            self.output_channel = self.input_channel

        self.output_folder = get_download_path(self.location, download_audio_path=True)
        if self.output_format != "same as source":
            self.final_output_format = self.output_format
        else:
            self.final_output_format = self.input_format

        if self.output_bitrate == "same as source":
            self.output_bitrate = self.input_bitrate

        self.output_channel_show_name = str(AUDIO_CHANNELS_MAPPING_REVERSE.get(self.output_channel, "stereo")).lower()
        self.output_audio_path = f'{self.output_folder}/{self.title}_{self.output_bitrate}kbps_' \
                                 f'{self.output_channel_show_name}.' \
                                 f'{self.final_output_format}'

        self.save_data_info = {
            "title_show": context.get("show_title", ""),
            "title_safe": context.get("title", ""),
            "length": context.get("duration", ""),
            "size": context.get("size", ""),
            "resolution": "N/A",
            "bitrate": self.output_bitrate,
            "type": "audio",
            "fps": "N/A",
            "a_v_quality": "N/A",
            "subtype": self.final_output_format,
            "audio_channel": self.output_channel_show_name,
        }

        # thread control flags
        self.is_paused = False
        self.is_killed = False

    def run(self):
        if not os.path.isfile(self.output_audio_path):
            self.no_error.emit("no_error")
            self.main_obj.ui.progress_bar.setRange(0, 0)
            self.progress_convert()
        else:
            self.error.emit({"error": "File Already Exists", "output_folder": self.output_folder,
                             "output_audio_path": self.output_audio_path, "title": self.title
                             })

    def get_ffmpeg_input_cmd(self):
        cmd = ['ffmpeg', '-i', self.input_audio_path]

        cmd.extend(['-b:a', '{0}000'.format(self.output_bitrate)])

        if self.final_output_format == "pcm":
            cmd.extend(["-f", "s16le", "-acodec", "pcm_s16le"])

        cmd.extend(["-vn"])
        cmd.extend(["-ac", self.output_channel])
        cmd.extend([self.output_audio_path])

        return cmd

    def progress_convert(self):
        try:
            progress_dict = {"progress": 0,
                             "total_size": 100,
                             "output_audio_path": self.output_audio_path,
                             "output_folder": self.output_folder,
                             "output_format": self.final_output_format,
                             "title": self.title,
                             "is_killed": self.is_killed,
                             }

            ffmpeg_cmd = self.get_ffmpeg_input_cmd()

            for progress, pid in run_ffmpeg_command(ffmpeg_cmd):
                progress_dict["progress"] = progress
                while self.is_paused:
                    time.sleep(0.5)
                    if pid_exists(pid.pid):
                        pid.suspend()
                    if self.is_killed:
                        self.terminate()
                        self.after_kill.emit(self.output_video_path)
                        break

                if pid_exists(pid.pid):
                    pid.resume()

                if self.is_killed:
                    if pid_exists(pid.pid):
                        pid.kill()
                    self.terminate()
                    self.after_kill.emit(self.output_video_path)
                    break
                if progress == 100:
                    self.finished.emit(progress_dict)
                    break
                else:
                    self.change_value.emit(progress_dict)

            save_download_info(self.save_data_info, self.output_folder, self.output_audio_path, self.location, "audio")

        except Exception as e:
            self.error.emit({"error": str(e), "output_folder": self.output_folder,
                             "output_audio_path": self.output_audio_path
                             })
            pass

    def pause(self):
        self.is_paused = True

    def resume(self):
        self.is_paused = False

    def kill(self):
        self.is_killed = True
