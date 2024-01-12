import tkinter as tk
import tkinter.filedialog as filedialog
import os


class CustomFolderDialog(tk.Toplevel):
    def __init__(self, master=None, **options):
        super().__init__(master, **options)
        self.geometry("400x200")

        self.folder_path = tk.StringVar()
        self.folder_name = tk.StringVar()
        self.folder_name.set("NewFolder")  # Default folder name

        tk.Label(self, text="Select Directory:").pack()
        self.directory_entry = tk.Entry(self, textvariable=self.folder_path, width=100)
        self.directory_entry.pack()

        self.browse_button = tk.Button(self, text="Browse Folders", command=self.browse_directory)
        self.browse_button.pack()
        self.folder_confirm_button = tk.Button(self, text="Confirm selected directory", command=self.confirm_directory)
        self.folder_confirm_button.pack()

        tk.Label(self, text="Enter Folder Name:").pack()
        self.folder_name_entry = tk.Entry(self, textvariable=self.folder_name, width=100)
        self.folder_name_entry.pack()

        self.folder_create_button = tk.Button(self, text="Create New Folder", command=self.create_new_folder)
        self.folder_create_button.pack()
        self.new_folder_path=tk.StringVar()



    def browse_directory(self):
        directory = filedialog.askdirectory()
        if directory:
            self.folder_path.set(directory)
        self.lift()
        self.deiconify()

    def create_new_folder(self):
        directory = self.folder_path.get()
        folder_name = self.folder_name.get()

        if not folder_name:  # If folder name is empty, use default name "New Folder"
            folder_name = "NewFolder"

        if directory:
            new_folder_path = os.path.join(directory, folder_name)
            try:
                os.makedirs(new_folder_path)
                self.new_folder_path.set(new_folder_path)
                self.folder_path.set(new_folder_path)
                print(f"Folder '{folder_name}' created at: {new_folder_path}")
            except OSError as e:
                print(f"Failed to create folder: {e}")
        else:
            print("Please select a directory.")
    def confirm_directory(self):
        directory = self.folder_path.get()
        if directory:
            self.new_folder_path.set(directory)
            self.folder_path.set(directory)
            print(f"Save directory set to: {directory}")
            self.destroy()
        else:
            print("Please select a directory.")