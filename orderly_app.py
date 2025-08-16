# === IMPORTS =============================================================
import customtkinter as ctk
import tkinter.filedialog
import os
import shutil
from customtkinter import CTkInputDialog
from send2trash import send2trash
from fuzzywuzzy import fuzz
import logging
import re

# === END IMPORTS =========================================================


# === CONFIGURATION =======================================================
# Configure logging to show INFO level messages and above in the console
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# Configure CustomTkinter appearance
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")


# === END CONFIGURATION ===================================================


# === MAIN APPLICATION CLASS ==============================================
class OrderlyApp(ctk.CTk):
    # --- INITIALIZATION (__init__) ---------------------------------------
    def __init__(self):
        super().__init__()

        # --- Window Setup ---
        self.title("Orderly - by Project Curator")
        self.geometry("800x600")
        self.minsize(600, 450)

        # --- Internal State Variables ---
        self.selected_folder = None
        self.found_files_map = {}  # Maps filename to full path for the current search
        self.file_buttons = []  # List of CTkButton widgets for files in the results list
        self.selected_file_button = None  # The currently selected file button widget

        # Internal state for manual placeholder management and text colors
        self.search_entry_placeholder_text_value = "Enter keyword to search for..."
        self.placeholder_color = "gray"
        self.normal_text_color = ("black", "white")  # Default for dark/light mode

        # --- Main Grid Configuration for the CTk Window ---
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)  # TabView takes most space
        self.grid_rowconfigure(1, weight=0)  # Global Status Bar (fixed height)

        # --- Tab View for Search/Organize ---
        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="nsew")

        self.search_tab = self.tabview.add("Search & Act")
        self.organize_tab = self.tabview.add("Organize Files")

        # Configure individual tab grids to expand content correctly
        self.search_tab.grid_columnconfigure(0, weight=1)
        self.search_tab.grid_rowconfigure(0, weight=0)  # Search controls frame
        self.search_tab.grid_rowconfigure(1, weight=10)  # Results list
        self.search_tab.grid_rowconfigure(2, weight=0)  # Action buttons frame

        self.organize_tab.grid_columnconfigure(0, weight=1)
        self.organize_tab.grid_rowconfigure(0, weight=1)  # The main controls frame

        # --- WIDGETS FOR 'Search & Act' TAB ---
        # 1. Search Controls Frame
        self.search_controls_frame = ctk.CTkFrame(self.search_tab)
        self.search_controls_frame.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="ew")
        self.search_controls_frame.grid_columnconfigure(1, weight=1)
        self.search_controls_frame.grid_columnconfigure(2, weight=0)

        self.select_folder_button = ctk.CTkButton(self.search_controls_frame, text="Select Folder",
                                                  command=self.select_folder_and_search)
        self.select_folder_button.grid(row=0, column=0, padx=10, pady=10)

        self.search_entry = ctk.CTkEntry(self.search_controls_frame)
        self.search_entry.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        self.search_entry.bind("<Return>", self.trigger_search)
        self.search_entry.bind("<FocusIn>", self.on_search_entry_focus_in)
        self.search_entry.bind("<FocusOut>", self.on_search_entry_focus_out)

        self.search_button = ctk.CTkButton(self.search_controls_frame, text="Search", command=self.trigger_search)
        self.search_button.grid(row=0, column=2, padx=10, pady=10)

        self.selected_folder_label = ctk.CTkLabel(self.search_controls_frame, text="No folder selected.",
                                                  text_color="gray", anchor="w")
        self.selected_folder_label.grid(row=1, column=0, columnspan=3, padx=10, pady=(0, 10), sticky="ew")

        # 1a. Search Options Frame
        self.options_frame = ctk.CTkFrame(self.search_controls_frame, fg_color="transparent")
        self.options_frame.grid(row=2, column=0, columnspan=3, padx=10, pady=5, sticky="w")

        self.case_sensitive_var = ctk.BooleanVar(value=True)
        self.case_sensitive_check = ctk.CTkCheckBox(self.options_frame, text="Case Sensitive",
                                                    variable=self.case_sensitive_var,
                                                    command=self.update_search_options_state)
        self.case_sensitive_check.pack(side="left", padx=10)

        self.fuzzy_match_var = ctk.BooleanVar(value=False)
        self.fuzzy_match_switch = ctk.CTkSwitch(self.options_frame, text="Fuzzy Match", variable=self.fuzzy_match_var,
                                                onvalue=True, offvalue=False, command=self.on_fuzzy_switch_toggle)
        self.fuzzy_match_switch.pack(side="left", padx=10)

        self.search_mode_var = ctk.StringVar(value="Keyword")
        self.search_mode_switch = ctk.CTkSwitch(self.options_frame, text="Search by Extension",
                                                variable=self.search_mode_var, onvalue="Extension", offvalue="Keyword",
                                                command=self.on_extension_switch_toggle)
        self.search_mode_switch.pack(side="left", padx=20)

        # 1b. Organize Call-to-Action Button
        self.organize_results_button = ctk.CTkButton(self.search_controls_frame, text="Organize Results",
                                                     command=self.switch_to_organize_tab)
        self.organize_results_button.grid(row=3, column=0, columnspan=3, padx=10, pady=(10, 0), sticky="ew")

        # 2. Results List Frame
        self.results_frame = ctk.CTkFrame(self.search_tab)
        self.results_frame.grid(row=1, column=0, padx=10, pady=(5, 10), sticky="nsew")
        self.results_frame.grid_columnconfigure(0, weight=1)
        self.results_frame.grid_rowconfigure(0, weight=1)

        self.results_list = ctk.CTkScrollableFrame(self.results_frame, label_text="Found Files")
        self.results_list.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")

        # 3. Action Buttons Frame
        self.actions_frame = ctk.CTkFrame(self.search_tab)
        self.actions_frame.grid(row=2, column=0, padx=10, pady=(5, 10), sticky="ew")

        self.open_button = ctk.CTkButton(self.actions_frame, text="Open File", command=self.open_selected_file)
        self.open_button.pack(side="left", padx=10, pady=5)

        self.delete_button = ctk.CTkButton(self.actions_frame, text="Delete File", fg_color="#D32F2F",
                                           hover_color="#B71C1C", command=self.delete_selected_file)
        self.delete_button.pack(side="left", padx=10, pady=5)

        # --- WIDGETS FOR 'Organize Files' TAB ---
        self.organize_controls_frame = ctk.CTkFrame(self.organize_tab)
        self.organize_controls_frame.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="nsew")
        self.organize_controls_frame.grid_columnconfigure(0, weight=1)

        self.organize_info_label = ctk.CTkLabel(self.organize_controls_frame,
                                                text="Search for files in 'Search & Act' tab, then come here to organize them.",
                                                anchor="w", wraplength=500)
        self.organize_info_label.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        self.found_files_count_label = ctk.CTkLabel(self.organize_controls_frame, text="Files to organize: 0",
                                                    anchor="w")
        self.found_files_count_label.grid(row=1, column=0, padx=10, pady=10, sticky="ew")

        self.new_folder_label = ctk.CTkLabel(self.organize_controls_frame, text="New Folder Name:", anchor="w")
        self.new_folder_label.grid(row=2, column=0, padx=10, pady=(0, 5), sticky="w")

        self.new_folder_entry = ctk.CTkEntry(self.organize_controls_frame, placeholder_text="e.g., GMC Reports 2024")
        self.new_folder_entry.grid(row=3, column=0, padx=10, pady=(0, 10), sticky="ew")

        self.action_type_var = ctk.StringVar(value="Move")
        self.move_radio = ctk.CTkRadioButton(self.organize_controls_frame, text="Move Files (original removed)",
                                             variable=self.action_type_var, value="Move")
        self.move_radio.grid(row=4, column=0, padx=10, pady=5, sticky="w")

        self.copy_radio = ctk.CTkRadioButton(self.organize_controls_frame, text="Copy Files (original retained)",
                                             variable=self.action_type_var, value="Copy")
        self.copy_radio.grid(row=5, column=0, padx=10, pady=5, sticky="w")

        self.organize_button = ctk.CTkButton(self.organize_controls_frame, text="Organize Files",
                                             command=self.organize_files)
        self.organize_button.grid(row=6, column=0, padx=10, pady=20, sticky="ew")

        # --- GLOBAL STATUS BAR (at bottom of main window) ---
        self.status_bar = ctk.CTkLabel(self, text="Welcome to Orderly! Select a folder to begin.", anchor="w")
        self.status_bar.grid(row=1, column=0, padx=10, pady=(5, 10), sticky="ew")

        # --- Initial Setup Calls ---
        self.update_search_options_state()
        self.update_status("Welcome to Orderly! Select a folder to begin.")
        self.on_search_entry_focus_out(None)
        self.update_organize_ui_state()

    # --- END INITIALIZATION --------------------------------------------

    # --- UI HELPER FUNCTIONS -------------------------------------------
    def update_status(self, message, color="white"):
        """Updates the text and color of the status bar and logs the message."""
        self.status_bar.configure(text=message)

        if color == "green":
            self.status_bar.configure(text_color=("#1B5E20", "#B2FF59"))
            logging.info(f"UI Status (GREEN): {message}")
        elif color == "red":
            self.status_bar.configure(text_color=("#B71C1C", "#FF5252"))
            logging.error(f"UI Status (RED): {message}")
        else:
            self.status_bar.configure(text_color=("black", "white"))
            logging.info(f"UI Status (WHITE): {message}")

    def update_organize_ui_state(self):
        """Centralized function to update the 'Organize Results' button and file count label."""
        has_files = bool(self.found_files_map)

        if has_files:
            # Enable the button and assign its command
            self.organize_results_button.configure(state="normal", command=self.switch_to_organize_tab)
        else:
            # Disable the button and remove its command to be certain it's inactive
            self.organize_results_button.configure(state="disabled", command=lambda: None)

        self.found_files_count_label.configure(text=f"Files to organize: {len(self.found_files_map)}")

    def on_extension_switch_toggle(self):
        """Wrapper for 'Search by Extension' switch."""
        if self.search_mode_var.get() == "Extension":
            self.update_status("Extension search enabled. Enter a new query.", color="white")
            self.search_entry_placeholder_text_value = "Enter extension (e.g., .pdf, .docx)..."
        else:
            self.update_status("Keyword search enabled. Enter a new query.", color="white")
            self.search_entry_placeholder_text_value = "Enter keyword to search for..."

        self.search_entry.delete(0, "end")
        self.clear_results_and_selection()
        self.update_search_options_state()
        self.on_search_entry_focus_out(None)

    def on_fuzzy_switch_toggle(self):
        """Wrapper for 'Fuzzy Match' switch."""
        if self.fuzzy_match_var.get():
            self.update_status("Fuzzy Match enabled. Enter a new query.", color="white")
        else:
            self.update_status("Fuzzy Match disabled. Enter a new query.", color="white")
            if self.search_mode_var.get() != "Extension":
                self.search_entry_placeholder_text_value = "Enter keyword to search for..."

        self.search_entry.delete(0, "end")
        self.clear_results_and_selection()
        self.update_search_options_state()
        self.on_search_entry_focus_out(None)

    def clear_results_and_selection(self):
        """Clears the results list, selection, and updates the organize UI state."""
        for widget in self.results_list.winfo_children():
            widget.destroy()
        self.found_files_map = {}
        self.file_buttons = []
        self.selected_file_button = None
        self.update_organize_ui_state()

    def update_search_options_state(self):
        """Disables/enables the 'Case Sensitive' checkbox based on other options."""
        is_fuzzy_mode = self.fuzzy_match_var.get()
        is_extension_mode = (self.search_mode_var.get() == "Extension")

        if is_fuzzy_mode or is_extension_mode:
            self.case_sensitive_check.deselect()
            self.case_sensitive_check.configure(state="disabled")
        else:
            self.case_sensitive_check.configure(state="normal")

    def on_search_entry_focus_in(self, event):
        """Clears placeholder text on focus and sets normal text color."""
        if self.search_entry.get() == self.search_entry_placeholder_text_value:
            self.search_entry.delete(0, "end")
            self.search_entry.configure(text_color=self.normal_text_color)

    def on_search_entry_focus_out(self, event):
        """Restores placeholder text if entry is empty after losing focus."""
        if not self.search_entry.get():
            self.search_entry.insert(0, self.search_entry_placeholder_text_value)
            self.search_entry.configure(text_color=self.placeholder_color)

    def switch_to_organize_tab(self):
        """Switches the active tab to the 'Organize Files' tab."""
        self.tabview.set("Organize Files")
        self.update_status("Switched to Organize Files tab.", color="white")
        logging.info("Switched to Organize Files tab.")

    # --- END UI HELPER FUNCTIONS ---------------------------------------

    # --- CORE LOGIC FUNCTIONS ------------------------------------------
    def select_folder_and_search(self):
        """Opens a dialog to select a folder, stores the path, and updates the UI."""
        folder_path = tkinter.filedialog.askdirectory(title="Select a Folder to Search")

        if not folder_path:
            self.selected_folder = None
            self.selected_folder_label.configure(text="No folder selected.", text_color="gray")
            self.update_status("Folder selection cancelled.", color="red")
            logging.info("Folder selection cancelled by user.")
            return

        self.selected_folder = folder_path
        self.selected_folder_label.configure(text=f"Searching in: {self.selected_folder}",
                                             text_color=("black", "white"))

        self.search_entry.delete(0, "end")
        self.on_search_entry_focus_out(None)
        self.update_status(
            f"Selected folder: '{os.path.basename(self.selected_folder)}'. Enter keyword and press 'Search' or 'Enter'.",
            color="green")
        logging.info(f"Folder selected: {self.selected_folder}")

    def trigger_search(self, event=None):
        """Gets the keyword, launches the search, and displays results."""
        if not self.selected_folder:
            self.update_status("Please select a folder before searching.", color="red")
            self.select_folder_and_search()
            return

        keyword = self.search_entry.get().strip()

        if not keyword or keyword == self.search_entry_placeholder_text_value:
            self.update_status("Search keyword is empty. Please enter a keyword.", color="red")
            return

        self.update_status(f"Searching for '{keyword}' in '{os.path.basename(self.selected_folder)}'...", color="white")
        self.results_list.update()

        self.clear_results_and_selection()

        matching_files = self.perform_search(self.selected_folder, keyword)

        if not matching_files:
            self.update_status(f"No files found containing '{keyword}'.", color="red")
            label = ctk.CTkLabel(self.results_list, text="No matching files found.")
            label.pack(padx=10, pady=5, anchor="w")
        else:
            for file_path in matching_files:
                filename_only = os.path.basename(file_path)
                self.found_files_map[filename_only] = file_path

                file_button = ctk.CTkButton(self.results_list, text=filename_only, fg_color="transparent",
                                            text_color=self.normal_text_color, anchor="w")
                file_button.configure(command=lambda btn=file_button: self.select_file(btn))
                file_button.pack(fill="x", padx=5, pady=2)
                self.file_buttons.append(file_button)

            self.update_status(f"Search complete. Found {len(matching_files)} file(s).", color="green")
            logging.info(f"Search complete for '{keyword}'. Found {len(matching_files)} files.")

        self.update_organize_ui_state()

    def perform_search(self, folder_path, keyword):
        """Searches for files based on the current search mode and options."""
        logging.info(f"Starting search in '{folder_path}' for '{keyword}' with mode='{self.search_mode_var.get()}', "
                     f"case_sensitive={self.case_sensitive_var.get()}, fuzzy_match={self.fuzzy_match_var.get()}")

        found_files = []

        mode = self.search_mode_var.get()
        is_case_sensitive = self.case_sensitive_var.get()
        is_fuzzy = self.fuzzy_match_var.get()

        keyword_for_comparison = keyword.lower() if not is_case_sensitive else keyword

        for root, dirs, files in os.walk(folder_path):
            for filename in files:
                target_text = filename.lower() if not is_case_sensitive else filename

                match_found = False
                if mode == "Extension":
                    clean_ext_base = re.sub(r'[^a-zA-Z0-9]', '', keyword_for_comparison).strip()

                    if clean_ext_base:
                        clean_ext = '.' + clean_ext_base.lower()
                    else:
                        continue

                    if target_text.lower().endswith(clean_ext):
                        match_found = True
                else:
                    if is_fuzzy:
                        if fuzz.partial_ratio(keyword_for_comparison, target_text) > 75:
                            match_found = True
                    else:
                        if keyword_for_comparison in target_text:
                            match_found = True

                if match_found:
                    full_path = os.path.join(root, filename)
                    found_files.append(full_path)

        return found_files

    # --- END CORE LOGIC FUNCTIONS --------------------------------------

    # --- FILE ACTION FUNCTIONS -----------------------------------------
    def select_file(self, button_to_select):
        """Highlights the selected file button. Allows de-selecting by clicking again."""
        if self.selected_file_button == button_to_select:
            self.selected_file_button.configure(fg_color="transparent")
            self.selected_file_button = None
            self.update_status("File de-selected.")
            logging.info("File de-selected.")
            return

        if self.selected_file_button:
            self.selected_file_button.configure(fg_color="transparent")

        self.selected_file_button = button_to_select
        self.selected_file_button.configure(fg_color=("#3B8ED0", "#1F6AA5"))
        self.update_status(f"Selected: '{self.selected_file_button.cget('text')}'")
        logging.info(f"File selected: '{self.selected_file_button.cget('text')}'")

    def open_selected_file(self):
        """Opens the currently selected file using the default system application."""
        if not self.selected_file_button:
            self.update_status("No file selected to open. Please select a file first.", color="red")
            return

        selected_filename = self.selected_file_button.cget("text")
        file_path_to_open = self.found_files_map.get(selected_filename)

        if file_path_to_open and os.path.exists(file_path_to_open):
            self.update_status(f"Opening file: '{selected_filename}'...", color="green")
            logging.info(f"Opening file: {file_path_to_open}")
            os.startfile(file_path_to_open)
        else:
            self.update_status(f"Error: Could not find file path for '{selected_filename}'", color="red")
            logging.error(
                f"Error: File path not found or does not exist for '{selected_filename}' at '{file_path_to_open}'")

    def delete_selected_file(self):
        """Shows a confirmation dialog and moves the selected file to the Recycle Bin."""
        if not self.selected_file_button:
            self.update_status("No file selected to delete. Please select a file first.", color="red")
            return

        selected_filename = self.selected_file_button.cget("text")
        file_path_to_delete = self.found_files_map.get(selected_filename)

        if not file_path_to_delete or not os.path.exists(file_path_to_delete):
            self.update_status(f"Error: Could not find file path for '{selected_filename}'", color="red")
            logging.error(
                f"Error: File path not found or does not exist for '{selected_filename}' at '{file_path_to_delete}'")
            return

        dialog_text = (f"You are about to move this file to the Recycle Bin:\n\n"
                       f"'{file_path_to_delete}'\n\n"
                       f"To confirm, please type DELETE below and click OK.")

        dialog = CTkInputDialog(text=dialog_text, title="Confirm Deletion")
        user_input = dialog.get_input()

        if user_input and user_input.upper() == "DELETE":
            try:
                normalized_path = os.path.normpath(file_path_to_delete)
                send2trash(normalized_path)

                if selected_filename in self.found_files_map:
                    del self.found_files_map[selected_filename]

                self.selected_file_button.destroy()
                self.selected_file_button = None

                self.update_status(f"Successfully moved '{selected_filename}' to the Recycle Bin.", color="green")
                logging.info(f"Successfully moved '{normalized_path}' to Recycle Bin.")

            except Exception as e:
                self.update_status(f"Error deleting file: {e}", color="red")
                logging.error(f"Error deleting file '{normalized_path}': {e}")
            finally:
                self.update_organize_ui_state()
        else:
            self.update_status("Deletion cancelled by user.", color="white")
            logging.info("Deletion cancelled by user.")

    def organize_files(self):
        """Moves or copies all found files to a new specified folder."""
        # 1. --- Validation ---
        if not self.found_files_map:
            self.update_status("No files found to organize. Please perform a search first.", color="red")
            return

        new_folder_name = self.new_folder_entry.get().strip()
        if not new_folder_name:
            self.update_status("New folder name cannot be empty.", color="red")
            return

        # 2. --- Setup Paths and Action Type ---
        destination_folder_path = os.path.join(self.selected_folder, new_folder_name)
        action_type = self.action_type_var.get()

        # Prevent organizing into an existing folder to avoid accidental merges
        if os.path.exists(destination_folder_path):
            self.update_status(f"Error: A folder named '{new_folder_name}' already exists in this location.",
                               color="red")
            return

        # 3. --- Confirmation Dialog ---
        dialog_text = (
            f"You are about to {action_type.lower()} {len(self.found_files_map)} file(s) into a new folder named:\n\n"
            f"'{new_folder_name}'\n\n"
            f"inside '{self.selected_folder}'\n\n"
            f"To confirm, please type {action_type.upper()} below and click OK.")

        dialog = CTkInputDialog(text=dialog_text, title=f"Confirm File {action_type}")
        user_input = dialog.get_input()

        if user_input and user_input.upper() == action_type.upper():
            # 4. --- Execute Action ---
            try:
                os.makedirs(destination_folder_path)
                logging.info(f"Created new folder: {destination_folder_path}")

                processed_count = 0
                for filename, source_path in self.found_files_map.items():
                    destination_path = os.path.join(destination_folder_path, filename)

                    # Handle potential name conflicts (should be rare if new folder)
                    if os.path.exists(destination_path):
                        base, ext = os.path.splitext(filename)
                        i = 1
                        while os.path.exists(destination_path):
                            destination_path = os.path.jttroin(destination_folder_path, f"{base} ({i}){ext}")
                            i += 1

                    # Perform the copy or move
                    if action_type == "Copy":
                        shutil.copy2(source_path, destination_path)
                    else:  # Move
                        shutil.move(source_path, destination_path)
                    processed_count += 1

                self.update_status(
                    f"Successfully {action_type.lower()}ed {processed_count} file(s) to '{new_folder_name}'.",
                    color="green")
                # Clear the search results after a successful organization
                self.clear_results_and_selection()
                self.search_entry.delete(0, "end")
                self.on_search_entry_focus_out(None)

            except Exception as e:
                self.update_status(f"An error occurred during organization: {e}", color="red")
                logging.error(f"Error during file organization: {e}")
        else:
            self.update_status("Organization cancelled by user.", color="white")
    # --- END FILE ACTION FUNCTIONS -------------------------------------


# === END MAIN APPLICATION CLASS ==========================================


# === APPLICATION LAUNCHER ================================================
if __name__ == "__main__":
    app = OrderlyApp()
    app.mainloop()
# === END APPLICATION LAUNCHER ============================================