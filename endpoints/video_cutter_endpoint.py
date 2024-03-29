import __init__
import time
from watchdog.events import FileSystemEventHandler, FileCreatedEvent
import os
from concurrent.futures import ProcessPoolExecutor
import cv2
from argparse import ArgumentParser
from utils import constants as c, os_utils, general_utils
from utils.flask_child import FuseNode
from utils.general_utils import init_start_function_thread


class VideoHandler(FileSystemEventHandler):
    def __init__(self, source_folder, dest_folder):
        self.source_folder = source_folder
        self.dest_folder = dest_folder
        self.videoExecutor = ProcessPoolExecutor(max_workers=cutter_max_workers)

    def on_created(self, event):
        if os_utils.check_there_is_enough_free_space():
            if not event.is_directory and event.src_path.endswith('.webm'):
                self.videoExecutor.submit(VideoHandler.process_video, event.src_path)
        else:
            app.logger.warning(f"There is not enough space to cut video {event.src_path} on screenshots")

    # TODO: to test. I have a theory that yt-dlp sometimes renames chunks into final file, so on modify is needed
    def on_modified(self, event):
        if not event.is_directory and event.src_path.endswith('.webm'):
            self.videoExecutor.submit(VideoHandler.process_video, event.src_path)

    @staticmethod
    def cut_video_into_screenshots(video_path):
        video_base = os.path.basename(video_path)
        cap = cv2.VideoCapture(video_path)
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        frame_count = 0
        index = 0
        i = 1
        # 5400 = 1.5 * 60 * 60
        if total_frames / fps >= 5400:
            app.logger.warn(f"Video {video_base} lasts more than 1.5 hours, Freezes may occur")
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            frame_count += 1
            if i % fps == 0:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=10, minSize=(50, 50),
                                                      flags=cv2.CASCADE_SCALE_IMAGE)
                if len(faces) > 0:
                    for (x, y, w, h) in faces:
                        crop_img = frame[y:y + h, x:x + w]
                        cv2.imwrite(f"{screenshots_folder_name}/{video_base}_{str(index)}.jpg", crop_img)
                        index += 1

            if frame_count % (180 * fps) == 0:
                current_time = int(cap.get(cv2.CAP_PROP_POS_MSEC) / 1000)
                app.logger.info(
                    f"Processed {frame_count}/{total_frames} frames, {current_time} seconds out of {int(total_frames / fps)} seconds; ({video_base})")
            i += 1

        cap.release()
        app.logger.info(f"Releasing {video_base}; Trying to delete it")
        if os.path.exists(video_path):
            os.remove(video_path)

    @staticmethod
    def process_video(video_path):
        basename = os.path.basename(video_path)
        app.logger.info(f"Cutting {basename} into screenshots")
        VideoHandler.cut_video_into_screenshots(video_path)


yt_dlp_used_playlists_file_path = c.temporary_files_folder_full_path + '//yt_dlp_used_playlists.txt'
videos_folder_name = c.temporary_files_folder_full_path + '//ytdlp_videos'
screenshots_folder_name = c.temporary_files_folder_full_path + '//ytlpd_screenshots'
archives_folder_name = c.temporary_files_folder_full_path + '//ytlpd_archives'
theshold_of_videos_to_panic = 1_000
cutter_max_workers = 1
# face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
face_cascade = cv2.CascadeClassifier(c.resources_folder_full_path+"//yt_downloader_models//lbpcascade_frontalface.xml")

parser = ArgumentParser()
app = FuseNode(__name__, arg_parser=parser)


def recreate_image_harvester_files_and_folders():
    if not os.path.exists(yt_dlp_used_playlists_file_path):
        open(yt_dlp_used_playlists_file_path, "w")
    if not os.path.exists(videos_folder_name):
        os.makedirs(videos_folder_name)
    if not os.path.exists(screenshots_folder_name):
        os.makedirs(screenshots_folder_name)
    if not os.path.exists(archives_folder_name):
        os.makedirs(archives_folder_name)


def process_existing_videos():
    app.logger.info(f"Processing existing videos")
    existing_files = []
    for filename in os.listdir(videos_folder_name):
        file_path = os.path.join(videos_folder_name, filename)
        if os.path.isfile(file_path):
            existing_files.append(file_path)
    amount_of_videos = len(existing_files)
    ind = 0
    for existing_file in existing_files:
        app.logger.info(f"Existing video No. {ind}/{amount_of_videos} sent to videoExecutor Process Pool")
        event = FileCreatedEvent(existing_file)
        video_handler.on_created(event)
        ind += 1
        if ind % theshold_of_videos_to_panic == 0:
            app.logger.warning(
                f"There is currently too big amount of videos ({len(existing_files)}), video cutting is slowed down, "
                f"as well as it is recommended to avoid sending requests to the module")
            time.sleep(180)


def watch_video_folder():
    if os_utils.is_linux_running():
        from watchdog.observers.inotify import InotifyObserver
        observer = InotifyObserver()
    else:
        from watchdog.observers import Observer
        observer = Observer()
    observer.schedule(video_handler, videos_folder_name, recursive=False)
    observer.start()
    init_start_function_thread(process_existing_videos)


def give_recreated_files_and_folders_permissions():
    # TODO NOTE if the problem persists with the files,
    # refer here to create folders/files already with needed permissions
    # https://stackoverflow.com/questions/5231901/permission-problems-when-creating-a-dir-with-os-makedirs-in-python/67723702#67723702
    if os_utils.is_linux_running():
        # this might *need* sudo, even tho as service it is root already
        command = f"cd {c.temporary_files_folder_full_path} && chmod ugo+rwx *"
        general_utils.run_cmd_command_and_wait_response(command)


if __name__ == "__main__":
    recreate_image_harvester_files_and_folders()
    give_recreated_files_and_folders_permissions()
    video_handler = VideoHandler(videos_folder_name, screenshots_folder_name)
    init_start_function_thread(watch_video_folder)
    app.run()
