import math
import os
import subprocess
import ffmpeg
from helper import get_time_format, get_download_path
from constant import ALL_VIDEO_RESOLUTIONS


def process_video(input_video, location):
    from helper import safe_string
    from helper import humanbytes
    from helper import select_format_data_video

    context = dict()
    try:
        probe_obj = ffmpeg.probe(input_video)
        streams = probe_obj.get("streams", [])[0]
        audio_streams = probe_obj.get("streams", [])[1]
        ff_format = probe_obj.get("format", {})

        context["file_name"] = ff_format.get("filename", "N/A")
        context["size"] = humanbytes(ff_format.get("size", "N/A"))
        context["duration"] = get_time_format(int(float(ff_format.get("duration", 0))))
        context["format"] = ff_format.get('format_long_name', 'N/A')
        context["input_audio_bitrate"] = str(int(float(audio_streams.get("bit_rate", "128000")) / 1000))
        context["quality"] = f'{streams.get("height", "720")}p' + ' ' + \
                             (ALL_VIDEO_RESOLUTIONS.get(f'{streams.get("height", "720")}p'))
        if streams.get("r_frame_rate", 25) == ["0/0", "", 0, "0", None, ]:
            context["frame"] = math.ceil(eval(streams.get("r_frame_rate", 25)))
        else:
            context["frame"] = 25

        context["more_info"] = {
            "Codec Full Name": streams.get("codec_long_name", "N/A"),
            "Codec Type": streams.get("codec_type", "N/A"),
            "Resolution": f'{streams.get("height", "N/A")} * {streams.get("width", "N/A")}',
            "Bit Rate": streams.get("bit_rate", "N/A"),
            "Bits Per Sample": streams.get("bits_per_raw_sample", "N/A"),
            "NB Frames": streams.get("nb_frames", "N/A"),
            "Display Aspect Ratio": streams.get("display_aspect_ratio", "N/A"),
            "Sample Aspect Ratio": streams.get("sample_aspect_ratio", "N/A"),
            "Color Range": streams.get("color_range", "N/A"),
            "Color Space": streams.get("color_space", "N/A"),
            "Color Transfer": streams.get("color_transfer", "N/A"),
            "Color Primaries": streams.get("color_primaries", "N/A"),
            "Chroma Location": streams.get("chroma_location", "N/A"),
        }

        context["format_data"] = select_format_data_video(f'{streams.get("height", "720")}p',
                                                          context["frame"], context["input_audio_bitrate"])
        context["more_info_str"] = "More Video Details:\n\n"
        for heading, values in zip(context["more_info"].keys(), context["more_info"].values()):
            context["more_info_str"] += f"{heading} : {values}\n\n"

        file_name, extension = os.path.splitext(str(input_video))
        context["title"] = safe_string(file_name.split("/")[-1])
        context["title_show"] = file_name.split("/")[-1]
        context["title_show_full"] = str(input_video).split("/")[-1]
        context["thumbnail_path"] = save_thumbnail_for_video(input_video, f'{get_download_path(location, thumbnail=True)}/{context["title"]}.jpg')
        context["status"] = True
    except Exception as e:
        print(e)
        context["status"] = False

    return context


def process_audio(input_audio, location):
    from helper import safe_string
    from helper import humanbytes
    from helper import select_format_data_audio

    context = dict()
    try:
        probe_obj = ffmpeg.probe(input_audio)
        streams = probe_obj.get("streams", [])[0]
        ff_format = probe_obj.get("format", {})

        context["file_name"] = ff_format.get("filename", "N/A")
        context["size"] = humanbytes(ff_format.get("size", "N/A"))
        context["format"] = streams.get("codec_name", "N/A")
        context["duration"] = get_time_format(int(float(ff_format.get("duration", 0))))
        context["codec"] = streams.get("codec_name", "N/A")
        context["bitrate"] = str(int(float(streams.get("bit_rate", "128000")) / 1000))

        if streams.get("channels", "2") == ["", 0, "0", None]:
            context["input_channel"] = str(streams.get("channels", "2"))
        else:
            context["input_channel"] = "2"

        context["more_info"] = {
            "Codec Full Name": streams.get("codec_long_name", "N/A"),
            "Codec Type": streams.get("codec_type", "N/A"),
            "Bit Rate": streams.get("bit_rate", "N/A"),
            "Channels": streams.get("channels", "N/A"),
            "Channel Layout": streams.get("channel_layout", "N/A"),
            "Sample Fmt": streams.get("sample_fmt", "N/A"),
        }

        context["format_data"] = select_format_data_audio(context["bitrate"])

        context["more_info_str"] = "More Audio Details:\n\n"
        for heading, values in zip(context["more_info"].keys(), context["more_info"].values()):
            context["more_info_str"] += f"{heading} : {values}\n\n"

        file_name, extension = os.path.splitext(str(input_audio))
        context["title"] = safe_string(file_name.split("/")[-1])
        context["title_show"] = file_name.split("/")[-1]
        context["title_show_full"] = str(input_audio).split("/")[-1]
        context["thumbnail_path"] = save_thumbnail_for_audio(input_audio, f'{get_download_path(location, thumbnail=True)}/{context["title"]}.jpg')
        context["status"] = True

    except Exception as e:
        print(e)
        context["status"] = False

    return context


def save_thumbnail_for_video(input_video, thumbnail_path):
    stock_image = ":/myresource/resource/video_thumbnail.png"
    t_path = thumbnail_path
    try:
        subprocess.getoutput(f'ffmpeg -i {input_video} -ss 00:00:02.000 -vf "scale=500:400" -vframes 1 {thumbnail_path} -y')
        if os.path.isfile(t_path):
            return t_path
        else:
            return stock_image
    except Exception:
        return stock_image


def save_thumbnail_for_audio(input_audio, thumbnail_path):
    stock_image = ":/myresource/resource/audio_thumbnail.png"
    t_path = thumbnail_path
    try:
        result = subprocess.getoutput(f'ffmpeg -i {input_audio} -an -vcodec copy {thumbnail_path} -y')
        if os.path.isfile(t_path):
            return t_path
        else:
            return stock_image
    except Exception:
        return stock_image
