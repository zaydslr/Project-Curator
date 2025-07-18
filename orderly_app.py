import customtkinter as ctk
import tkinter.filedialog
import os

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
        self.grid_rowconfigure(1, weight=1)

        # --- Top Frame for Search Controls ---
        self.search_frame = ctk.CTkFrame(self)
        self.search_frame.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="ew")
        self.search_frame.grid_columnconfigure(1, weight=1)

        self.select_folder_button = ctk.CTkButton(self.search_frame, text="Select Folder",
                                                  command=self.select_folder_and_search)
        self.select_folder_button.grid(row=0, column=0, padx=10, pady=10)

        self.search_entry = ctk.CTkEntry(self.search_frame, placeholder_text="Enter keyword to search for...")
        self.search_entry.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

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
        Opens a dialog to select a folder, then triggers the search.
        Now allows keyword entry after folder selection.
        """
        # Ask the user to select a directory
        folder_path = tkinter.filedialog.askdirectory(title="Select a Folder to Search")

        if not folder_path:  # If the user cancels the dialog
            self.selected_folder = None
            print("Folder selection cancelled.")
            return

        self.selected_folder = folder_path
        print(f"Selected folder: {self.selected_folder}")

        # Now, we also bind the <Return> key (Enter) to the search entry field
        # so the user can just type and press Enter to search.
        self.search_entry.bind("<Return>", self.trigger_search)
        print("Folder selected. Type a keyword and press Enter to search.")

    def trigger_search(self, event=None):  # event is passed by the key binding
        """
        Gets the keyword and launches the search for the stored folder path.
        """
        if not self.selected_folder:
            print("No folder selected. Please select a folder first.")
            # We could add a popup here to guide the user.
            self.select_folder_and_search()  # Pro-actively open the dialog
            return

        keyword = self.search_entry.get()
        if not keyword:
            print("Search keyword is empty. Please enter a keyword.")
            return

        # 1. Clear previous results
        for widget in self.results_list.winfo_children():
            widget.destroy()

        # 2. Perform the search
        matching_files = self.perform_search(self.selected_folder, keyword)

        # 3. Display new results
        if not matching_files:
            label = ctk.CTkLabel(self.results_list, text="No matching files found.")
            label.pack(padx=10, pady=5, anchor="w")
        else:
            self.found_files_map = {}
            for file_path in matching_files:
                filename_only = os.path.basename(file_path)
                self.found_files_map[filename_only] = file_path

                label = ctk.CTkLabel(self.results_list, text=filename_only)
                label.pack(padx=10, pady=5, anchor="w")


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


# --- Run the Application ---
if __name__ == "__main__":
    app = OrderlyApp()
    app.mainloop()