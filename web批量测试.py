import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import requests
from concurrent.futures import ThreadPoolExecutor
import time
import csv
import webbrowser

class WebRequester:
    def __init__(self, master):
        self.master = master
        master.title("Web批量请求器-XM")
        master.geometry("1200x900")
        # 颜色
        self.color_config = {
            "success": "#e6ffe6",
            "warning": "#fff3e6",
            "error": "#ffe6e6"
        }
        # 界面
        self.create_widgets()
        self.running = False
        self.executor = None
        self.futures = []

    def create_widgets(self):
        # URL输入
        url_frame = ttk.LabelFrame(self.master, text="请求设置")
        url_frame.pack(padx=10, pady=5, fill="x")

        ttk.Label(url_frame, text="URL列表（每行一个）:").grid(row=0, column=0, sticky="w", columnspan=7)
        self.url_text = tk.Text(url_frame, height=8)
        self.url_text.grid(row=1, column=0, columnspan=7, sticky="ew")

        # get-post选择
        ttk.Label(url_frame, text="方法:").grid(row=2, column=0, sticky="w")
        self.method = tk.StringVar(value="GET")
        ttk.Combobox(url_frame, textvariable=self.method, values=["GET", "POST"], width=8).grid(row=2, column=1,
                                                                                                sticky="w")
        # 并发数设置
        ttk.Label(url_frame, text="并发数:").grid(row=2, column=2, sticky="w", padx=5)
        self.concurrency = tk.IntVar(value=5)
        ttk.Spinbox(url_frame, from_=1, to=50, textvariable=self.concurrency, width=5).grid(row=2, column=3, sticky="w")
        # 超时设置
        ttk.Label(url_frame, text="超时(s):").grid(row=2, column=4, sticky="w", padx=5)
        self.timeout = tk.DoubleVar(value=10)
        ttk.Entry(url_frame, textvariable=self.timeout, width=5).grid(row=2, column=5, sticky="w")

        # 请求间隔
        ttk.Label(url_frame, text="间隔(ms):").grid(row=2, column=6, sticky="w", padx=5)
        self.interval = tk.IntVar(value=0)
        ttk.Entry(url_frame, textvariable=self.interval, width=7).grid(row=2, column=7, sticky="w")
        # POST
        ttk.Label(url_frame, text="POST数据:").grid(row=3, column=0, sticky="w", pady=(10, 0))
        self.post_data_text = tk.Text(url_frame, height=4)
        self.post_data_text.grid(row=4, column=0, columnspan=7, sticky="ew", pady=(0, 5))

        # 按钮
        self.start_btn = ttk.Button(url_frame, text="开始请求", command=self.toggle_requests)
        self.start_btn.grid(row=2, column=8, padx=5)
        self.export_btn = ttk.Button(url_frame, text="导出结果", command=self.export_results)
        self.export_btn.grid(row=2, column=9, padx=5)
        # 进度
        self.progress_label = ttk.Label(url_frame, text="准备就绪")
        self.progress_label.grid(row=2, column=10, padx=10)
        # 结果
        result_frame = ttk.LabelFrame(self.master, text="请求结果（双击可跳转网页）")
        result_frame.pack(padx=10, pady=5, fill="both", expand=True)
        columns = ("url", "status", "time")
        self.result_tree = ttk.Treeview(result_frame, columns=columns, show="headings")
        self.result_tree.heading("url", text="URL")
        self.result_tree.heading("status", text="状态码/错误", anchor="center")
        self.result_tree.heading("time", text="响应时间(ms)", anchor="center")
        self.result_tree.column("url", width=700, anchor="w")
        self.result_tree.column("status", width=200, anchor="center")
        self.result_tree.column("time", width=150, anchor="center")
        # 颜色
        for tag, color in self.color_config.items():
            self.result_tree.tag_configure(tag, background=color)
        # 滚动条
        scroll_y = ttk.Scrollbar(result_frame, orient="vertical", command=self.result_tree.yview)
        scroll_x = ttk.Scrollbar(result_frame, orient="horizontal", command=self.result_tree.xview)
        self.result_tree.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)
        # 布局
        self.result_tree.grid(row=0, column=0, sticky="nsew")
        scroll_y.grid(row=0, column=1, sticky="ns")
        scroll_x.grid(row=1, column=0, sticky="ew")
        result_frame.grid_rowconfigure(0, weight=1)
        result_frame.grid_columnconfigure(0, weight=1)
        # 绑定双击事件
        self.result_tree.bind("<Double-1>", self.open_url)
    def toggle_requests(self):
        if self.running:
            self.stop_requests()
        else:
            self.start_requests()
    def start_requests(self):
        urls = self.url_text.get("1.0", tk.END).strip().split('\n')
        urls = [url.strip() for url in urls if url.strip()]
        urls = list(dict.fromkeys(urls))

        if not urls:
            messagebox.showwarning("警告", "请输入至少一个URL")
            return

        self.result_tree.delete(*self.result_tree.get_children())
        self.running = True
        self.start_btn.config(text="停止请求")
        self.executor = ThreadPoolExecutor(max_workers=self.concurrency.get())
        self.futures = []

        total = len(urls)
        self.progress_label.config(text=f"0/{total}")

        for idx, url in enumerate(urls):
            future = self.executor.submit(self.worker, url, idx + 1)
            self.futures.append(future)

        self.master.after(100, self.update_results)

    def worker(self, url, task_id):
        try:
            # 请求间隔控制
            time.sleep(self.interval.get() / 1000)

            method = self.method.get()
            data = self.post_data_text.get("1.0", tk.END).strip() if method == "POST" else None
            headers = {'Content-Type': 'application/json'}

            start_time = time.time()
            response = requests.request(
                method,
                url,
                data=data,
                headers=headers,
                timeout=self.timeout.get()
            )
            elapsed_time = round((time.time() - start_time) * 1000, 2)
            return (url, response.status_code, elapsed_time)
        except Exception as e:
            return (url, str(e), 0)

    def update_results(self):
        current_futures = self.futures.copy()
        completed = 0

        for future in current_futures:
            if future.done():
                try:
                    url, status, elapsed = future.result()
                    tag = self.get_status_tag(status)
                    self.result_tree.insert("", "end", values=(url, status, elapsed), tags=(tag,))
                except Exception as e:
                    self.result_tree.insert("", "end", values=(url, str(e), 0), tags=("error",))
                finally:
                    self.futures.remove(future)
                    completed += 1

        total = len(current_futures)
        if total > 0:
            self.progress_label.config(text=f"{completed}/{total} ({completed / total:.0%})")

        if self.running and self.futures:
            self.master.after(100, self.update_results)
        else:
            self.stop_requests()

    def get_status_tag(self, status):
        if isinstance(status, int):
            if 200 <= status < 300:
                return "success"
            elif 400 <= status < 500:
                return "warning"
            else:
                return "error"
        return "error"

    def stop_requests(self):
        self.running = False
        self.start_btn.config(text="开始请求")
        if self.executor:
            self.executor.shutdown(wait=False)
        self.progress_label.config(text="已停止")
        messagebox.showinfo("提示", "请求已终止")

    def export_results(self):
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv")]
        )
        if not file_path:
            return

        try:
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["URL", "状态码/错误", "响应时间(ms)"])
                for item in self.result_tree.get_children():
                    values = self.result_tree.item(item, 'values')
                    writer.writerow(values)
            messagebox.showinfo("成功", f"结果已导出到：{file_path}")
        except Exception as e:
            messagebox.showerror("错误", f"导出失败：{str(e)}")

    def open_url(self, event):
        selected = self.result_tree.selection()
        if selected:
            item = selected[0]
            url = self.result_tree.item(item, 'values')[0]
            if url.startswith(('http://', 'https://')):
                webbrowser.open(url)
            else:
                messagebox.showwarning("警告", "无效的URL格式")


if __name__ == "__main__":
    root = tk.Tk()
    app = WebRequester(root)
    root.mainloop()