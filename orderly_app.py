import customtkinter as ctk
import tkinter.filedialog
import os
from customtkinter import CTkInputDialog
from send2trash import send2trash


# --- Application Configuration ---
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")


# --- Main Application Class ---
class OrderlyApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # --- Window Setup ---
        self.title("Orderly - by Project Curator")
        self.geometry("800x600")
        self.minsize(600, 450)
        self.selected_folder = None

        # --- Main Layout ---
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=10)
        # --- NEW: Frame for Actions (Open, Delete, etc.) ---
        self.actions_frame = ctk.CTkFrame(self)
        self.actions_frame.grid(row=2, column=0, padx=10, pady=(5, 10), sticky="ew")

        # --- NEW: Status Bar for feedback messages ---
        self.status_bar = ctk.CTkLabel(self, text="Welcome to Orderly! Select a folder to begin.", anchor="w")
        self.status_bar.grid(row=3, column=0, padx=10, pady=(5, 10), sticky="ew")

        self.open_button = ctk.CTkButton(self.actions_frame, text="Open File", command=self.open_selected_file)
        self.open_button.pack(side="left", padx=10, pady=5)

        self.delete_button = ctk.CTkButton(self.actions_frame, text="Delete File", fg_color="#D32F2F", hover_color="#B71C1C", command=self.delete_selected_file)
        self.delete_button.pack(side="left", padx=10, pady=5)

        # --- Top Frame for Search Controls ---
        self.search_frame = ctk.CTkFrame(self)
        self.search_frame.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="ew")
        self.search_frame.grid_columnconfigure(1, weight=1)

        self.select_folder_button = ctk.CTkButton(self.search_frame, text="Select Folder",
                                                  command=self.select_folder_and_search)
        self.select_folder_button.grid(row=0, column=0, padx=10, pady=10)

        self.search_entry = ctk.CTkEntry(self.search_frame, placeholder_text="Enter keyword to search for...")
        self.search_entry.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

        # --- Add this new label ---
        self.selected_folder_label = ctk.CTkLabel(self.search_frame, text="No folder selected.", text_color="gray", anchor="w")
        self.selected_folder_label.grid(row=1, column=0, columnspan=2, padx=10, pady=(0, 10), sticky="ew")

        # --- Bottom Frame for Displaying Results ---
        self.results_frame = ctk.CTkFrame(self)
        self.results_frame.grid(row=1, column=0, padx=10, pady=(5, 10), sticky="nsew")
        self.results_frame.grid_columnconfigure(0, weight=1)
        self.results_frame.grid_rowconfigure(0, weight=1)

        self.results_list = ctk.CTkScrollableFrame(self.results_frame, label_text="Found Files")
        self.results_list.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")

    # --- Core Functions (Methods) ---
    def select_folder_and_search(self):
        """
        Opens a dialog to select a folder, stores the path, and updates the UI.
        """
        folder_path = tkinter.filedialog.askdirectory(title="Select a Folder to Search")

        if not folder_path:
            self.selected_folder = None
            # Update label to show cancellation
            self.selected_folder_label.configure(text="No folder selected.", text_color="gray")
            print("Folder selection cancelled.")
            return

        self.selected_folder = folder_path
        # --- UPDATE THE LABEL HERE ---
        self.selected_folder_label.configure(text=f"Searching in: {self.selected_folder}",
                                             text_color=("black", "white"))

        self.search_entry.bind("<Return>", self.trigger_search)
        print(f"Selected folder: {self.selected_folder}")
        print("Folder selected. Type a keyword and press Enter to search.")

    def trigger_search(self, event=None):
        """
        Gets the keyword, launches the search, and displays results as selectable buttons.
        """
        if not self.selected_folder:
            self.update_status("No folder selected. Please select a folder first.", color="red")
            self.select_folder_and_search()
            return

        keyword = self.search_entry.get()
        if not keyword:
            self.update_status("Search keyword is empty. Please enter a keyword.", color="red")
            return

        self.update_status(f"Searching for '{keyword}' in {os.path.basename(self.selected_folder)}...")
        self.results_list.update()  # Force UI to update before long search

        for widget in self.results_list.winfo_children():
            widget.destroy()

        matching_files = self.perform_search(self.selected_folder, keyword)

        if not matching_files:
            self.update_status(f"No files found containing '{keyword}'.", color="red")
            label = ctk.CTkLabel(self.results_list, text="No matching files found.")
            label.pack(padx=10, pady=5, anchor="w")
        else:
            self.found_files_map = {}
            self.file_buttons = []
            self.selected_file_button = None

            for file_path in matching_files:
                filename_only = os.path.basename(file_path)
                self.found_files_map[filename_only] = file_path

                file_button = ctk.CTkButton(self.results_list, text=filename_only, fg_color="transparent",
                                            text_color=("black", "white"), anchor="w")
                file_button.configure(command=lambda btn=file_button: self.select_file(btn))
                file_button.pack(fill="x", padx=5, pady=2)
                self.file_buttons.append(file_button)

            self.update_status(f"Search complete. Found {len(matching_files)} file(s).", color="green")

    def select_file(self, button_to_select):
        """
        Highlights the selected file button. Allows de-selecting by clicking again.
        """
        if self.selected_file_button == button_to_select:
            self.selected_file_button.configure(fg_color="transparent")
            self.selected_file_button = None
            self.update_status("File de-selected.")
            return

        if self.selected_file_button:
            self.selected_file_button.configure(fg_color="transparent")

        button_to_select.configure(fg_color=("#3B8ED0", "#1F6AA5"))
        self.selected_file_button = button_to_select
        self.update_status(f"Selected: {self.selected_file_button.cget('text')}")


    def open_selected_file(self):
        """
        Opens the currently selected file using the default system application.
        """
        if not self.selected_file_button:
            self.update_status("No file selected to open. Please select a file first.", color="red")
            return

        selected_filename = self.selected_file_button.cget("text")
        file_path_to_open = self.found_files_map.get(selected_filename)

        if file_path_to_open and os.path.exists(file_path_to_open):
            self.update_status(f"Opening file: {selected_filename}...", color="green")
            os.startfile(file_path_to_open)
        else:
            self.update_status(f"Error: Could not find file path for {selected_filename}", color="red")
    def delete_selected_file(self):
        """
        Shows a robust confirmation dialog and then moves the selected file to the
        Recycle Bin, providing feedback via the status bar.
        """
        if not self.selected_file_button:
            self.update_status("No file selected to delete. Please select a file first.", color="red")
            return

        selected_filename = self.selected_file_button.cget("text")
        file_path_to_delete = self.found_files_map.get(selected_filename)

        if not file_path_to_delete or not os.path.exists(file_path_to_delete):
            self.update_status(f"Error: Could not find file path for {selected_filename}", color="red")
            return

        dialog_text = (f"You are about to move this file to the Recycle Bin:\n\n"
                       f"{file_path_to_delete}\n\n"
                       f"To confirm, please type DELETE below and click OK.")

        dialog = CTkInputDialog(text=dialog_text, title="Confirm Deletion")
        user_input = dialog.get_input()

        if user_input and user_input.upper() == "DELETE":
            try:
                normalized_path = os.path.normpath(file_path_to_delete)
                send2trash(normalized_path)

                self.selected_file_button.destroy()
                self.selected_file_button = None

                self.update_status(f"Successfully moved '{selected_filename}' to the Recycle Bin.", color="green")

            except Exception as e:
                self.update_status(f"Error deleting file: {e}", color="red")
        else:
            self.update_status("Deletion cancelled by user.")

    def perform_search(self, folder_path, keyword):
        """
        Searches for files containing the keyword in their name within a folder.
        """
        found_files = []
        # os.walk recursively goes through all subdirectories and files
        for root, dirs, files in os.walk(folder_path):
            for filename in files:
                # This is a simple case-sensitive "exact match" search for now
                if keyword in filename:
                    full_path = os.path.join(root, filename)
                    found_files.append(full_path)
        return found_files

    def update_status(self, message, color="white"):
        """
        Updates the text and color of the status bar.
        Color can be 'white', 'green', or 'red'.
        """
        self.status_bar.configure(text=message)

        # Set text color based on status
        if color == "green":
            self.status_bar.configure(text_color=("#1B5E20", "#B2FF59"))  # Dark/Light green
        elif color == "red":
            self.status_bar.configure(text_color=("#B71C1C", "#FF5252"))  # Dark/Light red
        else:
            # Default text color
            self.status_bar.configure(text_color=("black", "white"))



# --- Run the Application ---
if __name__ == "__main__":
    app = OrderlyApp()
    app.mainloop()