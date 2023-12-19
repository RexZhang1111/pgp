import threading
import os
import subprocess
import random
import tkinter as tk
from tkinter import filedialog, messagebox, Label, Button, Entry, Listbox, END, Tk, IntVar, Checkbutton
import datetime
import shutil
import tempfile
from moviepy.editor import VideoFileClip, concatenate_videoclips, vfx
from moviepy.video.fx.all import speedx, lum_contrast, resize, fadein, fadeout
import moviepy.editor as mp

output_duration = 0

def add_files():
    files = filedialog.askopenfilenames(title="选择视频文件", filetypes=[("视频文件", "*.mp4;*.avi;*.mkv")])
    for file in files:
        videos_listbox.insert(tk.END, file)

def remove_file():
    selected_indices = videos_listbox.curselection()
    for index in reversed(selected_indices):
        videos_listbox.delete(index)

def select_output_folder():
    output_folder = filedialog.askdirectory(title="选择输出文件夹")
    output_folder_entry.delete(0, tk.END)
    output_folder_entry.insert(0, output_folder)
    
def show_error_message(message):
    messagebox.showerror("错误", message)

def check_import_info():
    # 检查剪切秒数是否为正整数
    cut_seconds_str = cut_seconds_entry.get().strip()
    if not cut_seconds_str:
        messagebox.showerror("错误", "剪切秒数不能为空！")
        return False
    try:
        cut_seconds = int(cut_seconds_str)
    except ValueError:
        messagebox.showerror("错误", "剪切秒数必须是一个整数！")
        return False
    if cut_seconds <= 0:
        messagebox.showerror("错误", "剪切秒数必须是正整数！")
        return False

    # 检查输出持续时间是否为正整数
    output_duration_str = output_duration_entry.get().strip()
    if not output_duration_str:
        messagebox.showerror("错误", "输出持续时间不能为空！")
        return False
    try:
        output_duration = int(output_duration_str)
    except ValueError:
        messagebox.showerror("错误", "输出持续时间必须是一个整数！")
        return False
    if output_duration <= 0:
        messagebox.showerror("错误", "输出持续时间必须是正整数！")
        return False

    # 检查剪辑数量是否为正整数
    clip_count_str = clip_count_entry.get().strip()
    if not clip_count_str:
        messagebox.showerror("错误", "剪辑数量不能为空！")
        return False
    try:
        clip_count = int(clip_count_str)
    except ValueError:
        messagebox.showerror("错误", "剪辑数量必须是一个整数！")
        return False
    if clip_count <= 0:
        messagebox.showerror("错误", "剪辑数量必须是正整数！")
        return False

    # 检查是否有视频文件被选中
    videos_listbox_files = videos_listbox.get(0, END)
    if not videos_listbox_files:
        messagebox.showerror("错误", "请至少选择一个视频文件！")
        return False

    # 检查输出文件夹是否存在
    output_folder = output_folder_entry.get().strip()
    if not output_folder:
        messagebox.showerror("错误", "请先选择一个输出文件夹！")
        return False
    if not os.path.exists(output_folder):
        messagebox.showerror("错误", f"输出文件夹不存在：{output_folder}！")

    return True
    
def get_output_folder():
    output_folder = output_folder_entry.get().strip()
    return output_folder

def process_videos(cut_seconds, clip_count, output_duration, videos_listbox_files, output_folder):
    global all_errors

    def get_video_duration(file_path):
        video_clip = mp.VideoFileClip(file_path)
        return video_clip.duration

    def get_output_file_name(output_folder, base_name):
        if not output_folder.endswith(os.sep):
            output_folder += os.sep
        output_file = os.path.join(output_folder, f"{base_name}.mp4")
        return output_file

    # 获取当前工作目录
    working_dir = os.getcwd()

    # 检查并初始化临时文件夹
    temp_folder = os.path.join(working_dir, "dsx_temp")

    # 在开始处理新视频之前，先删除临时文件夹（如果存在）
    if os.path.exists(temp_folder):
        shutil.rmtree(temp_folder)

    # 新建一个临时文件夹
    os.makedirs(temp_folder)

    cut_seconds = int(cut_seconds_entry.get())
    output_duration = int(output_duration_entry.get())
    clip_count = int(clip_count_entry.get())
    videos_listbox_files = videos_listbox.get(0, END)

    for i in range(1, clip_count + 1):
        try:
            output_folder = output_folder_entry.get().strip()
            base_name = f"DSx_merged_video_{i}"
            output_file = get_output_file_name(output_folder, base_name)

            clips: list[mp.VideoFileClip] = []
            segment_count = -(-output_duration // cut_seconds)  # 使用进一法计算需要的片段数量

            total_segment_duration = 0
            for j in range(segment_count):
                input_file = random.choice(videos_listbox_files)

                start_second = j * cut_seconds
                end_second = min(start_second + cut_seconds, output_duration)

                video_clip = mp.VideoFileClip(input_file)
                segment_clip = video_clip.subclip(start_second, end_second)

                # 添加以下代码行来确保片段的时长精确等于 cut_seconds，并减小片段之间的时间间隙
                segment_clip = segment_clip.set_duration(cut_seconds)
                if j > 0:
                    segment_clip = segment_clip.set_start(clips[-1].end)

                segment_temp_file = os.path.join(temp_folder, f"temp_{j}.mp4")
                segment_clip.write_videofile(segment_temp_file)

                clips.append(mp.VideoFileClip(segment_temp_file))
                total_segment_duration += cut_seconds

            # 如果所有片段的总时长大于预期的输出时长，截短最后一个片段的时间
            if total_segment_duration > output_duration:
                last_clip_index = len(clips) - 1
                last_clip = clips[last_clip_index]
                excess_duration = total_segment_duration - output_duration
                last_clip = last_clip.set_duration(last_clip.duration - excess_duration)
                clips[last_clip_index] = last_clip

            final_clip = mp.concatenate_videoclips(clips, method="compose")
            final_clip.write_videofile(output_file, fps=30, codec='libx264', bitrate='20000k')

        except Exception as e:
            error_message = str(e)
            show_error_message(error_message)
            break  # 当出现错误时，跳出循环

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

    # 在循环结束后删除临时文件夹
    try:
        shutil.rmtree(temp_folder)
    except Exception as e:
        print(f"Failed to delete the temporary folder '{temp_folder}'. Reason: {e}")

    # 在循环结束后删除临时文件夹
    try:
        shutil.rmtree(temp_folder)
    except Exception as e:
        print(f"Failed to delete the temporary folder '{temp_folder}'. Reason: {e}")
        
def process_all_videos():
    cut_seconds = int(cut_seconds_entry.get())
    clip_count = int(clip_count_entry.get())
    output_duration = int(output_duration_entry.get())
    output_folder = output_folder_entry.get()

    process_videos(None, cut_seconds, clip_count, output_duration, output_folder)

def process_videos_in_thread():
    if not check_import_info():
        return

    cut_seconds = int(cut_seconds_entry.get())
    clip_count = int(clip_count_entry.get())
    output_duration = int(output_duration_entry.get())
    videos_listbox_files = videos_listbox.get(0, END)
    
    output_folder = get_output_folder()  # 添加这一行来获取输出文件夹路径
    thread = threading.Thread(target=process_videos, args=(cut_seconds, clip_count, output_duration, videos_listbox_files, output_folder))
    thread.start()

def process_all_videos_in_thread():
    cut_seconds = int(cut_seconds_entry.get())
    clip_count = int(clip_count_entry.get())
    output_duration = int(output_duration_entry.get())
    output_folder = output_folder_entry.get()

    output_folder = get_output_folder()  # 添加这一行来获取输出文件夹路径
    thread = threading.Thread(target=process_videos, args=(None, cut_seconds, clip_count, output_duration, output_folder))
    thread.start()

def concatenate_segments(segment_files, output_file_name):
    final_clip = concatenate_videoclips([VideoFileClip(file) for file in segment_files])
    final_clip.duration(output_duration)
    final_clip.write_videofile(output_file_name, remove_temp=True)
    
def show_processing_complete_message():
    messagebox.showinfo("完成", "视频处理已完成！")

def stop_threads_and_close_window():
    global temp_folder

    # 停止所有线程（假设你已经在其他地方创建了线程）
    # for thread in thread_list:
    #     thread.join()

    # 删除临时文件夹
    if temp_folder and os.path.exists(temp_folder):
        shutil.rmtree(temp_folder)

    # 关闭窗口
    root.destroy()
    


def save_log_checkbox_changed():
    if save_log_checkbox_var.get():
        # 保存日志到文件的代码
        pass
    else:
        # 不保存日志到文件的代码
        pass


def preset_information():
    cut_seconds_entry.delete(0, tk.END)
    cut_seconds_entry.insert(0, "3")

    output_duration_entry.delete(0, tk.END)
    output_duration_entry.insert(0, "20")

    clip_count_entry.delete(0, tk.END)
    clip_count_entry.insert(0, "3")

    output_folder_entry.delete(0, tk.END)
    output_folder_entry.insert(0, "C:/py/testoutput")

    for i in range(1, 25):
        videos_listbox.insert(tk.END, f"C:/py/testvd/测试视频 ({i}).mp4")

    process_videos_button.config(command=process_videos_in_thread)

if __name__ == "__main__":
    root = tk.Tk()
    root.title("视频合并器")
    root.protocol("WM_DELETE_WINDOW", root.quit)
    # 设置窗口大小和位置
    root.geometry("800x600+100+100")

    # 创建标签和输入框
    cut_seconds_label = tk.Label(root, text="剪切秒数：")
    cut_seconds_label.place(x=50, y=50)
    cut_seconds_entry = tk.Entry(root)
    cut_seconds_entry.place(x=250, y=50, width=100)

    output_duration_label = tk.Label(root, text="片段长度：")
    output_duration_label.place(x=50, y=100)
    output_duration_entry = tk.Entry(root)
    output_duration_entry.place(x=250, y=100, width=100)

    clip_count_label = tk.Label(root, text="片段数量：")
    clip_count_label.place(x=50, y=150)
    clip_count_entry = tk.Entry(root)
    clip_count_entry.place(x=250, y=150, width=100)

    # 创建按钮
    add_files_button = tk.Button(root, text="添加文件", command=add_files)
    add_files_button.place(x=50, y=200, width=100, height=30)
    remove_files_button = tk.Button(root, text="移除文件", command=remove_file)
    remove_files_button.place(x=170, y=200, width=100, height=30)
    select_output_folder_button = tk.Button(root, text="输出路径", command=select_output_folder)
    select_output_folder_button.place(x=290, y=200, width=100, height=30)
    process_videos_button = tk.Button(root, text="处理视频", command=process_videos_in_thread)
    process_videos_button.place(x=410, y=200, width=100, height=30)
    all_process_button = tk.Button(root, text="全面处理", command=process_all_videos_in_thread)
    all_process_button.place(x=530, y=200, width=100, height=30)
    close_button = tk.Button(root, text="关闭程序", command=stop_threads_and_close_window)
    close_button.place(x=650, y=200, width=100, height=30)

    # 创建列表框
    videos_listbox = tk.Listbox(root)
    videos_listbox.place(x=50, y=250, width=700, height=200)

    # 创建输出文件夹输入框
    output_folder_label = tk.Label(root, text="输出路径：")
    output_folder_label.place(x=50, y=470)
    output_folder_entry = tk.Entry(root)
    output_folder_entry.place(x=250, y=470, width=400)

    # 创建保存日志勾选框
    save_log_label = tk.Label(root, text="保存日志到文件：")
    save_log_label.place(x=50, y=510)
    save_log_checkbox_var = tk.IntVar()
    save_log_checkbox = tk.Checkbutton(root, variable=save_log_checkbox_var, onvalue=1, offvalue=0)
    save_log_checkbox.select()
    save_log_checkbox.place(x=250, y=510)
    
    import_button = tk.Button(root, text="填空按钮", command=lambda: preset_information())
    import_button.place(x=50, y=230, width=100, height=30)
    
    


# 初始化变量
temp_folder = ""
clip_count = 0

# 主循环
root.mainloop()
