import threading
import os
import subprocess
import random
import tkinter as tk
import moviepy.editor as mpe
from tkinter import filedialog, messagebox, Label, Button, Entry, Listbox, END, Tk, IntVar, Checkbutton
import datetime
import shutil
import tempfile
from moviepy.editor import *
from moviepy.editor import VideoFileClip, concatenate_videoclips


all_errors = ""
video_processing_thread = None

def run_ffmpeg_command(command):
    global all_errors
    try:
        result = subprocess.run(command, shell=True, capture_output=True)
        if result.returncode != 0:
            error_message = f"FFmpeg命令执行失败！\n错误信息：{result.stderr.decode('utf-8', errors='replace')}"
            save_ffmpeg_log(error_message)
            all_errors += error_message + "\n"
    except Exception as e:
        error_message = f"在运行FFmpeg命令时发生错误！\n错误信息：{str(e)}"
        save_ffmpeg_log(error_message)
        all_errors += error_message + "\n"


def get_ffmpeg_version():
    command = "ffmpeg -version"
    result = subprocess.check_output(command, shell=True, text=True)
    return result.strip()

def get_system_info():
    command = "systeminfo"
    result = subprocess.check_output(command, shell=True, text=True)
    return result.strip()

def get_file_permissions(file_path):
    file_stat = os.stat(file_path)
    return oct(file_stat.st_mode)[-3:]

def get_output_folder_permissions(output_folder):
    file_stat = os.stat(output_folder)
    return oct(file_stat.st_mode)[-3:]

def get_media_info(file_path):
    command = f'ffprobe -v error -show_entries format=duration,height,width,bit_rate,frame_rate -of default=noprint_wrappers=1:nokey=1 "{file_path}"'
    result = subprocess.check_output(command, shell=True, text=True)
    media_info = {}
    for line in result.split("\n"):
        if ":" in line:
            key, value = line.split(":", maxsplit=1)
            media_info[key.strip()] = value.strip()
    return media_info

def save_ffmpeg_log(error_message):
    log_folder = os.path.join(os.path.dirname(__file__), "log")
    if not os.path.exists(log_folder):
        os.makedirs(log_folder)
    
    log_file = os.path.join(log_folder, f"ffmpeg_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.log")
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"当前时间：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"FFmpeg版本：{get_ffmpeg_version()}\n")
        f.write(f"错误信息：{error_message}\n\n")


def get_output_file_name(output_folder, base_name):
    return os.path.join(output_folder, f"{base_name}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.mp4")

def show_error_message():
    global all_errors

    if all_errors:
        error_message = "\n".join(all_errors)
        messagebox.showerror("错误", f"出现了一些错误：\n{error_message}")
        return False
    else:
        return True

def do_video_processing():
    global all_errors, clip_count
    # 获取当前工作目录
    working_dir = os.getcwd()

    # 检查并初始化临时文件夹
    temp_folder = os.path.join(working_dir, "dxs_temp")

    # 在开始处理新视频之前，先删除临时文件夹（如果存在）
    if os.path.exists(temp_folder):
        shutil.rmtree(temp_folder)

    # 新建一个临时文件夹
    os.makedirs(temp_folder)
        
        # 检查剪切秒数是否为正整数
    cut_seconds_str = cut_seconds_entry.get().strip()
    if not cut_seconds_str:
        messagebox.showerror("错误", "剪切秒数不能为空！")
        return
    try:
        cut_seconds = int(cut_seconds_str)
    except ValueError:
        messagebox.showerror("错误", "剪切秒数必须是一个整数！")
        return
    if cut_seconds <= 0:
        messagebox.showerror("错误", "剪切秒数必须是正整数！")
        return

    # 检查输出持续时间是否为正整数
    output_duration_str = output_duration_entry.get().strip()
    if not output_duration_str:
        messagebox.showerror("错误", "输出持续时间不能为空！")
        return
    try:
        output_duration = int(output_duration_str)
    except ValueError:
        messagebox.showerror("错误", "输出持续时间必须是一个整数！")
        return
    if output_duration <= 0:
        messagebox.showerror("错误", "输出持续时间必须是正整数！")
        return

    # 检查剪辑数量是否为正整数
    clip_count_str = clip_count_entry.get().strip()
    if not clip_count_str:
        messagebox.showerror("错误", "剪辑数量不能为空！")
        return
    try:
        clip_count = int(clip_count_str)
    except ValueError:
        messagebox.showerror("错误", "剪辑数量必须是一个整数！")
        return
    if clip_count <= 0:
        messagebox.showerror("错误", "剪辑数量必须是正整数！")
        return

    # 检查是否有视频文件被选中
    videos_listbox_files = videos_listbox.get(0, END)
    if not videos_listbox_files:
        messagebox.showerror("错误", "请至少选择一个视频文件！")
        return

    # 检查输出文件夹是否存在
    output_folder = output_folder_entry.get().strip()
    if not output_folder:
        messagebox.showerror("错误", "请先选择一个输出文件夹！")
        return
    if not os.path.exists(output_folder):
        messagebox.showerror("错误", f"输出文件夹不存在：{output_folder}！")

    def format_time(seconds):
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        remaining_seconds = seconds % 60

        return f"{hours:02d}:{minutes:02d}:{remaining_seconds:06.3f}"

    videos_listbox_files = videos_listbox.get(0, END)
    total_video_length = sum([get_video_duration(file) for file in videos_listbox_files])
    
    i = 1
    while i <= clip_count:
        try:
            output_folder = output_folder_entry.get().strip()
            base_name = f"DSX_merged_video_{i}"
            output_file = get_output_file_name(output_folder, base_name)
            
            clips: list[VideoFileClip] = []
            segment_start_times = [i * cut_seconds for i in range(output_duration // cut_seconds + (output_duration % cut_seconds > 0))]
            random.shuffle(segment_start_times)
            
            command_segments = []

            for j in range(len(segment_start_times)):
                input_file = random.choice(videos_listbox_files)

                start_second = segment_start_times[j]
                end_second = min(start_second + cut_seconds, output_duration) # 如果output_duration不是cut_seconds的整数倍，则最后一段可能不足cut_seconds秒
                formatted_start_time = format_time(start_second)
                formatted_end_time = format_time(end_second)
                segment_temp_file = os.path.join(temp_folder, f"temp_{j}.mp4")
                ffmpeg_command = f"ffmpeg -i \"{input_file}\" -ss {formatted_start_time} -to {formatted_end_time} -vf scale=1920:1086 -c:v h264 -c:a aac -b:v 20000k -an -avoid_negative_ts 1 \"{segment_temp_file}\""
                
                print(f"Running command: {ffmpeg_command}")
                run_ffmpeg_command(ffmpeg_command)

                command_segment = f"-i \"{segment_temp_file}\""
                command_segments.append(command_segment)
                clips.append(VideoFileClip(segment_temp_file))
            
            final_clip = concatenate_videoclips(clips)
            final_clip.write_videofile(output_file, fps=30, codec='libx264', bitrate='20000k')

        finally:
            # 删除临时文件夹中的所有文件
            for filename in os.listdir(temp_folder):
                file_path = os.path.join(temp_folder, filename)
                try:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                except Exception as e:
                    print(f"Failed to delete {file_path}. Reason: {e}")

        show_error_message()
        i += 1

    # 在循环结束后删除临时文件夹
    try:
        shutil.rmtree(temp_folder)
    except Exception as e:
        print(f"Failed to delete the temporary folder '{temp_folder}'. Reason: {e}")

def process_videos_threaded():
    video_processing_thread = threading.Thread(target=do_video_processing)
    video_processing_thread.start()
    
    
def add_files():
    file_names = filedialog.askopenfilenames(filetypes=[("视频文件", "*.mp4")])
    videos_listbox.insert(END, *file_names)

def remove_file():
    selection = videos_listbox.curselection()
    if selection:
        videos_listbox.delete(selection)

def select_output_folder():
    global temp_folder
    temp_folder = filedialog.askdirectory()
    output_folder_entry.delete(0, END)
    output_folder_entry.insert(0, temp_folder)

def get_video_duration(file_path):
    command = f'ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "{file_path}"'
    result = subprocess.check_output(command, shell=True, text=True)
    video_duration = float(result.strip())
    return video_duration

def process_all_videos():
    global all_errors, clip_count

    # 获取当前工作目录
    working_dir = os.getcwd()

    # 检查并初始化临时文件夹
    temp_folder = os.path.join(working_dir, "dxs_temp")

    # 在开始处理新视频之前，先删除临时文件夹（如果存在）
    if os.path.exists(temp_folder):
        shutil.rmtree(temp_folder)

    # 新建一个临时文件夹
    os.makedirs(temp_folder)
        
    # 检查剪切秒数是否为正整数
    cut_seconds_str = cut_seconds_entry.get().strip()
    if not cut_seconds_str:
        messagebox.showerror("错误", "剪切秒数不能为空！")
        return
    try:
        cut_seconds = int(cut_seconds_str)
    except ValueError:
        messagebox.showerror("错误", "剪切秒数必须是一个整数！")
        return
    if cut_seconds <= 0:
        messagebox.showerror("错误", "剪切秒数必须是正整数！")
        return

    # 检查输出持续时间是否为正整数
    output_duration_str = output_duration_entry.get().strip()
    if not output_duration_str:
        messagebox.showerror("错误", "输出持续时间不能为空！")
        return
    try:
        output_duration = int(output_duration_str)
    except ValueError:
        messagebox.showerror("错误", "输出持续时间必须是一个整数！")
        return
    if output_duration <= 0:
        messagebox.showerror("错误", "输出持续时间必须是正整数！")
        return

    # 检查剪辑数量是否为正整数
    clip_count_str = clip_count_entry.get().strip()
    if not clip_count_str:
        messagebox.showerror("错误", "剪辑数量不能为空！")
        return
    try:
        clip_count = int(clip_count_str)
    except ValueError:
        messagebox.showerror("错误", "剪辑数量必须是一个整数！")
        return
    if clip_count <= 0:
        messagebox.showerror("错误", "剪辑数量必须是正整数！")
        return

    # 检查是否有视频文件被选中
    videos_listbox_files = videos_listbox.get(0, END)
    if not videos_listbox_files:
        messagebox.showerror("错误", "请至少选择一个视频文件！")
        return

    # 检查输出文件夹是否存在
    output_folder = output_folder_entry.get().strip()
    if not output_folder:
        messagebox.showerror("错误", "请先选择一个输出文件夹！")
        return
    if not os.path.exists(output_folder):
        messagebox.showerror("错误", f"输出文件夹不存在：{output_folder}！")

    def format_time(seconds):
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        remaining_seconds = seconds % 60

        return f"{hours:02d}:{minutes:02d}:{remaining_seconds:06.3f}"

    videos_listbox_files = videos_listbox.get(0, END)
    total_video_length = sum([get_video_duration(file) for file in videos_listbox_files])

    i = 1
    while i <= clip_count:
        try:
            output_folder = output_folder_entry.get().strip()
            base_name = f"DSB_merged_video_{i}"
            output_file = get_output_file_name(output_folder, base_name)

            clips: list[VideoFileClip] = []
            segment_start_times = [i * cut_seconds for i in range(output_duration // cut_seconds + (output_duration % cut_seconds > 0))]
            random.shuffle(segment_start_times)

            command_segments = []

            for j in range(len(segment_start_times)):
                input_file = random.choice(videos_listbox_files)

                start_second = segment_start_times[j]
                end_second = min(start_second + cut_seconds, output_duration) # 如果output_duration不是cut_seconds的整数倍，则最后一段可能不足cut_seconds秒
                formatted_start_time = format_time(start_second)
                formatted_end_time = format_time(end_second)
                segment_temp_file = os.path.join(temp_folder, f"temp_{j}.mp4")
                ffmpeg_command = f"ffmpeg -i \"{input_file}\" -ss {formatted_start_time} -to {formatted_end_time} -vf scale=1920:1086 -c:v h264 -c:a aac -b:v 20000k -an -avoid_negative_ts 1 \"{segment_temp_file}\""

                print(f"Running command: {ffmpeg_command}")
                run_ffmpeg_command(ffmpeg_command)

                command_segment = f"-i \"{segment_temp_file}\""
                command_segments.append(command_segment)
                clips.append(VideoFileClip(segment_temp_file))

                # 随机选择文件水平翻转
                if random.random() < 0.5:
                    flipped_clip = clips[-1].fx(vfx.flip_h)
                    clips.append(flipped_clip)

                # 随机选择文件抽丢弃1帧
                if random.random() < 0.5:
                    dropped_frames_clip = clips[-1].subclip(clips[-1].duration - 1, clips[-1].duration)
                    clips.append(dropped_frames_clip)

                # 随机选择文件改变对比度
                if random.random() < 0.5:
                    contrast_change = random.uniform(-0.2, 0.2)
                    contrast_clip = clips[-1].fx(colorx.change_contrast, contrast_change)
                    clips.append(contrast_clip)

                # 随机选择文件加速0.01
                if random.random() < 0.5:
                    speedup_factor = 1 + random.uniform(0.0, 0.01)
                    speedup_clip = clips[-1].speedx(speedup_factor)
                    clips.append(speedup_clip)

        finally:
            # 删除临时文件夹中的所有文件
            for filename in os.listdir(temp_folder):
                file_path = os.path.join(temp_folder, filename)
                try:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                except Exception as e:
                    print(f"Failed to delete {file_path}. Reason: {e}")

        show_error_message()
        i += 1

    final_clip = concatenate_videoclips(clips)
    final_clip.write_videofile(output_file, fps=30, codec='libx264', bitrate='20000k')

    # 在循环结束后删除临时文件夹
    try:
        shutil.rmtree(temp_folder)
    except Exception as e:
        print(f"Failed to delete the temporary folder '{temp_folder}'. Reason: {e}")

    show_error_message()
    i += 1

def stop_threads_and_close_window():
    # 强制停止所有线程（如果你有多个线程，请在此处列出它们）
    if video_processing_thread is not None:
        video_processing_thread.join()

    # 删除名为 dxs_temp 的临时文件夹
    temp_folder_to_delete = "dxs_temp"
    if os.path.exists(temp_folder_to_delete):
        try:
            shutil.rmtree(temp_folder_to_delete)
        except Exception as e:
            print(f"Failed to delete the temporary folder '{temp_folder_to_delete}'. Reason: {e}")

    # 关闭窗口
    root.destroy()

if __name__ == "__main__":
   # 创建主窗口
    root = tk.Tk()
    root.title("我是一只猪")
    root.protocol("WM_DELETE_WINDOW", root.quit)
    # 设置窗口大小和位置
    root.geometry("800x600+100+100")

    # 创建标签和输入框
    cut_seconds_label = tk.Label(root, text="剪切秒数：")
    cut_seconds_label.place(x=50, y=50)
    cut_seconds_entry = tk.Entry(root)
    cut_seconds_entry.place(x=200, y=50)

    output_duration_label = tk.Label(root, text="输出持续时间：")
    output_duration_label.place(x=50, y=90)
    output_duration_entry = tk.Entry(root)
    output_duration_entry.place(x=200, y=90)

    clip_count_label = tk.Label(root, text="剪辑数量：")
    clip_count_label.place(x=50, y=130)
    clip_count_entry = tk.Entry(root)
    clip_count_entry.place(x=200, y=130)

    # 创建按钮
    add_files_button = tk.Button(root, text="添加文件", command=add_files)
    add_files_button.place(x=50, y=170, width=100, height=30)
    remove_files_button = tk.Button(root, text="移除文件", command=remove_file)
    remove_files_button.place(x=160, y=170, width=100, height=30)
    select_output_folder_button = tk.Button(root, text="选择输出文件夹", command=select_output_folder)
    select_output_folder_button.place(x=270, y=170, width=100, height=30)
    process_videos_button = tk.Button(root, text="处理视频", command=process_videos_threaded)
    process_videos_button.place(x=380, y=170, width=100, height=30)
    all_process_button = tk.Button(root, text="全面处理", command=process_all_videos)
    all_process_button.place(x=490, y=170, width=100, height=30)
    close_button = tk.Button(root, text="关闭", command=lambda: stop_threads_and_close_window())
    close_button.place(x=600, y=170, width=100, height=30)

    # 创建列表框
    videos_listbox = tk.Listbox(root)
    videos_listbox.place(x=50, y=210, width=700, height=200)

    # 创建输出文件夹输入框
    output_folder_label = tk.Label(root, text="输出文件夹：")
    output_folder_label.place(x=50, y=420)
    output_folder_entry = tk.Entry(root)
    output_folder_entry.place(x=200, y=420, width=550)

    # 创建保存日志勾选框
    save_log_label = tk.Label(root, text="保存日志到文件：")
    save_log_label.place(x=50, y=460)
    save_log_checkbox_var = tk.IntVar()
    save_log_checkbox = tk.Checkbutton(root, variable=save_log_checkbox_var, onvalue=1, offvalue=0)
    save_log_checkbox.select()
    save_log_checkbox.place(x=200, y=460)
    
    process_videos_button.config(command=process_videos_threaded)


# 初始化变量
temp_folder = ""
clip_count = 0

# 主循环
root.mainloop()

