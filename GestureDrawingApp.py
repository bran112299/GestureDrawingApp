import os
import random
import time
import tkinter as tk
from tkinter import filedialog, ttk
from PIL import Image, ImageTk, ImageOps, ImageFilter

class GestureDrawingApp:
	def __init__(self, root, image_folder=".", interval=60):
		self.root = root
		self.root.title("Gesture Drawing Slideshow")
		self.root.geometry("800x600")  # Initial window size
		self.root.protocol("WM_DELETE_WINDOW", self.exit_program)  # Handle "X" button exit

		self.root.bind("<Configure>", self.on_resize) # Bind the window resize event to update the image size
		self.resize_flag = False  # Control flag for resizing
		self.resize_after_id = None

		self.interval = interval
		self.remaining_time = interval
		self.shadow_threshold = 85
		self.highlight_threshold = 170


		self.countdown_after_id = None  # ID of the root.after() call to stop it when necessary

		self.image_folder = image_folder
		self.image_paths = self.load_images(self.image_folder)
		self.current_image_index = 0
		self.current_image = None

		self.is_running = False
		self.is_paused = False
		self.is_toned = False

		self.new_image = False
		self.last_width = root.winfo_width()
		self.last_height = root.winfo_height()

		self.init_ui()

	def init_ui(self):
		# Create UI layout frames
		self.image_frame = tk.Frame(root)
		self.image_frame.pack(fill="both", expand=True)

		time_control_frame = tk.Frame(self.image_frame)
		time_control_frame.pack(side="right", anchor="n")

		self.control_frame = tk.Frame(root)
		self.control_frame.pack(side="bottom", fill="x", pady=10)

		self.timer_remaining_label = tk.Label(self.image_frame, text="", font=("Arial", 16))
		self.timer_remaining_label.pack(anchor="n")

		# Time label
		self.time_label = tk.Label(time_control_frame, text="Time")
		self.time_label.pack()  # Center-align the label

		# Timer slider
		self.timer_slider = tk.Scale(time_control_frame, from_=180, to=5, resolution=5, orient="vertical", command=self.update_timer)
		self.timer_slider.set(self.interval)
		self.timer_slider.pack(padx=(0,25))

		# Image label
		self.image_label = tk.Label(self.image_frame)
		self.image_label.pack(fill="both", expand=True)

		# Pause indicator label
		self.pause_label = tk.Label(root, text="PAUSED", fg="blue", font=("Arial", 16), cursor="hand2")
		self.pause_label.bind("<Button-1>", self.toggle_pause)
		self.pause_label.place_forget()

		# Control buttons
		self.start_button = tk.Button(self.control_frame, text="Start", command=self.start_or_unpause)
		self.start_button.pack(side="left", padx=10)

		self.back_button = tk.Button(self.control_frame, text="Back", command=lambda: self.reset_slideshow(True, -1))
		self.back_button.pack(side="left", padx=10)

		self.forward_button = tk.Button(self.control_frame, text="Forward", command= lambda: self.reset_slideshow(True, 1))
		self.forward_button.pack(side="left", padx=10)

		self.pause_button = tk.Button(self.control_frame, text="Pause", command=self.toggle_pause)
		self.pause_button.pack(side="left", padx=10)

		self.tone_label = tk.Label(self.control_frame, text="Tone:")
		self.tone_label.pack(side="left", padx=10)
		self.tone_options = ["Off", 2, 3]  # Tone options
		self.tone_combobox = ttk.Combobox(self.control_frame, values=self.tone_options, state="readonly", width=5)
		self.tone_combobox.pack(side="left", padx=10)
		self.tone_combobox.bind("<<ComboboxSelected>>", self.toggle_tone)

		self.folder_button = tk.Button(self.control_frame, text="Load Folder", command=self.load_folder)
		self.folder_button.pack(side="left", padx=10)

		# self.time_label = tk.Label(self.control_frame, text=f"shadow_threshold")
		# self.time_label.pack(side="left", padx=10)
		self.shadow_threshold_slider = tk.Scale(self.control_frame, from_=0, to=255, resolution=5, orient="horizontal", command=self.update_shadow)
		self.shadow_threshold_slider.set(self.shadow_threshold)
		self.shadow_threshold_slider.pack(side="left", padx=10)

		self.highlight_threshold_slider = tk.Scale(self.control_frame, from_=0, to=255, resolution=5, orient="horizontal", command=self.update_highlight)
		self.highlight_threshold_slider.set(self.highlight_threshold)
		self.highlight_threshold_slider.pack(side="left", padx=10)


	def load_folder(self):
		"""Open a file dialog to select a new folder and load images from it."""
		folder_selected = filedialog.askdirectory()
		if folder_selected:
			self.image_folder = folder_selected
			self.image_paths = self.load_images(self.image_folder)
			self.current_image_index = 0  # Reset index for new folder
			self.show_image(self.current_image_index)
			self.pause_slideshow()

	def load_images(self, folder):
		"""Recursively load all images from the specified folder and subfolders."""
		image_extensions = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tiff"}
		image_paths = []
		for root, _, files in os.walk(folder):
			for file in files:
				if file.lower().endswith(tuple(image_extensions)):
					image_paths.append(os.path.join(root, file))
		random.shuffle(image_paths)
		return image_paths

	def on_resize(self, event):
		def handle_resize():
			# Check if the window size has actually changed
			width = self.root.winfo_width()
			height = self.root.winfo_height()
			if width != self.last_width or height != self.last_height:
				self.last_width = width
				self.last_height = height
				print("Window resized to", width, height)
				self.show_image(self.current_image_index)

		if self.resize_after_id:
			self.root.after_cancel(self.resize_after_id)
		self.resize_after_id = self.root.after(200, handle_resize)

	def toggle_pause(self, event=None):
		"""Toggle the pause state."""
		if self.is_paused:
			self.is_paused = False
			self.pause_label.place_forget()
			self.run_slideshow()  # Unpause and resume slideshow
		else:
			self.pause_slideshow()

	def toggle_tone(self, event=None):
		"""Toggle the pause state."""
		self.is_toned = not self.is_toned
		self.show_image(self.current_image_index)  # Refresh the current image

	def show_image(self, index):
		def tone_conversion(image):
			shadow_threshold = self.shadow_threshold   # 60-75 for pronounced 85-100 for shadow subtle
			highlight_threshold = self.highlight_threshold  # 170-255 for highlights, 180-200 more bright
			toned_image = None
			width, height = image.size
			min_dimension = min(width, height)  # Use the smaller dimension for proportional blur
			blur_radius = min(min_dimension / 1000, 3)  # Adjust the factor (100 is arbitrary and can be changed)
			try:
				tone_setting = int(self.tone_combobox.get())
				image = image.convert("L")
				contrast_image = ImageOps.autocontrast(image, cutoff=2)  # Adjust 'cutoff' for desired contrast level
				print(min_dimension)
				print(blur_radius)
				smooth_image = contrast_image.filter(ImageFilter.GaussianBlur(radius=blur_radius))

				if tone_setting == 2:
					toned_image = smooth_image.point(lambda p: 50 if p < shadow_threshold else 150)
				elif tone_setting == 3:
					# Mode 1
					toned_image = smooth_image.point(lambda p: 50 if p < shadow_threshold else 150 if p < highlight_threshold else 255)
					# Mode 2
					# three_tone_image = contrast_image.point(lambda p: 40 if p < shadow_threshold else 130 if p < highlight_threshold else 240)
				return toned_image
			except:
				return image




		"""Display an image in the Tkinter window."""
		if 0 <= index < len(self.image_paths):
			img = tone_conversion(Image.open(self.image_paths[index]))
			window_width = self.last_width
			window_height = self.last_height
			padding = 150

			available_width = window_width
			available_height = window_height - padding
			aspect_ratio = img.width / img.height

			# Scale image to fit within the available space while maintaining aspect ratio
			if available_width / available_height > aspect_ratio:
				# Scale by height if the available space is too tall
				new_height = available_height
				new_width = int(aspect_ratio * new_height)
			else:
				# Scale by width if the available space is too wide
				new_width = available_width
				new_height = int(new_width / aspect_ratio)

			# Resize the image while maintaining aspect ratio
			img = img.resize((new_width, new_height), Image.LANCZOS)
			self.current_image = ImageTk.PhotoImage(img)
			self.image_label.config(image=self.current_image)

	def start_or_unpause(self):
		"""Start the slideshow or unpause it if it's already running."""
		if not self.is_running: self.start_slideshow()
		elif self.is_paused:
			self.toggle_pause()
			if self.remaining_time != self.interval:
				self.remaining_time = self.interval
		else:
			self.image_paths = self.load_images(self.image_folder)
			self.reset_slideshow()

	def start_slideshow(self):
		"""Start the slideshow."""
		self.is_running = True
		self.is_paused = False
		self.pause_label.place_forget()
		self.remaining_time = self.interval
		self.update_remaining_time()
		# self.show_next_image()
		self.run_slideshow()  # Start the slideshow loop

	def run_slideshow(self):
		"""Run the slideshow with the specified interval."""
		if self.is_running and not self.is_paused:
			if self.new_image:
				self.show_next_image()
				self.remaining_time = self.interval  # Reset timer to interval duration
				self.new_image = False
			self.countdown()

	def countdown(self):
		"""Decrement remaining time and update the timer display."""
		if self.remaining_time > 0 and not self.is_paused:
			self.remaining_time -= 0.1
			self.update_remaining_time()
			self.countdown_after_id = self.root.after(100, self.countdown)  # Call countdown again after 100ms
		elif self.remaining_time <= 0:
			self.new_image = True  # Reset new_image to trigger next image change
			self.root.after(0, self.run_slideshow)  # Call countdown again after 100ms

	def update_remaining_time(self):
		"""Update the remaining time display."""
		self.timer_remaining_label.config(text=f"{abs(self.remaining_time):.1f}")

	def pause_slideshow(self):
		"""Pause the slideshow, displaying a Pause message."""
		self.is_paused = True
		self.pause_label.place(x=10, y=10)  # Show at top-left corner
		self.update_remaining_time()

	def reset_slideshow(self, pause=False, index_direction=0):
		"""Reset the slideshow and stop any existing countdown."""
		self.is_running = True
		self.is_paused = False
		self.new_image = False
		self.pause_label.place_forget()
		self.remaining_time = self.interval
		self.update_remaining_time()
		self.show_next_image(pause, index_direction)

		if self.countdown_after_id is not None:
			self.root.after_cancel(self.countdown_after_id)

		self.run_slideshow()  # Use root.after to handle the slideshow loop

	def update_timer(self, value):
		"""Update the interval timer from the slider and pause the slideshow."""
		self.interval = int(value)
		self.pause_slideshow()

	def update_shadow(self, value):
		self.shadow_threshold = int(value)
		self.show_image(self.current_image_index)



	def update_highlight(self, value):
		self.highlight_threshold = int(value)
		self.show_image(self.current_image_index)


	def show_next_image(self, pause=False, index=1):
		if pause:
			self.toggle_pause()
		if self.image_paths:
			self.current_image_index = (self.current_image_index + index) % len(self.image_paths)
			self.show_image(self.current_image_index)

	def exit_program(self):
		self.root.quit()  # Gracefully quit the Tkinter app

if __name__ == "__main__":
	root = tk.Tk()
	app = GestureDrawingApp(root)
	root.mainloop()
